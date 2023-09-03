from bpy.types import Context, Depsgraph, Scene, Mesh

from uvflow.addon_utils import Register
from uvflow.prefs import UVFLOW_Preferences
from uvflow.tool.tool import tool_state # Global tool state.
from uvflow.globals import GLOBALS, CM_SkipMeshUpdates, print_debug
from uvflow.props.mesh import MeshProps
from uvflow.rna_sub.uv_layers import on_UVMap_switch
from uvflow.tool.attributes import save_attributes, apply_attributes, remove_attributes
from uvflow.addon_utils.utils.mode import CM_ModeToggle

from uvflow.operators.op_geo_overlay import set_seam_props
from uvflow.operators.op_checker import update_material_uvmap


# Here the operator idname we will track within the depsgraph handler.
saved_op_id: dict[str, int] = {
    'MESH_OT_mark_seam': 0,
    'MESH_OT_hide': 0,
    'MESH_OT_reveal': 0,
    'MESH_OT_uv_texture_add': 0,
    'MESH_OT_uv_texture_remove': 0,
}


# Here the optional callbacks after the tracked operator execution.
class AfterCallbacks:
    @staticmethod
    def MESH_OT_mark_seam(context: Context) -> None:
        save_attributes(context, seams=True)

    @staticmethod
    def MESH_OT_uv_texture_add(context: Context) -> None:
        mesh: Mesh = context.object.data
        updated, prev_index, curr_index = MeshProps.update_last_uv_layer_index(mesh, get_indices=True)
        name_updated, prev_name, curr_name = MeshProps.update_last_uv_layer_name(mesh, get_names=True)
        count_change = MeshProps.update_last_uv_layer_count(mesh)

        print_debug(f"DEPS|\t> on_UVMap_add {prev_name}[{prev_index}] -> {curr_name}[{curr_index}]")

        prefs = UVFLOW_Preferences.get_prefs(context)
        if not prefs.use_seam_layers:
            return

        # Active UVMap has changed!
        with CM_ModeToggle(context, mode='OBJECT'):
            save_attributes(context, seams=True, seam_layer_id=prev_name)
            apply_attributes(context, seams=True, seam_layer_id=curr_name)

            set_seam_props(context, uv_layer_id=curr_name)
            update_material_uvmap(context, uv_layer_id=curr_name)

    @staticmethod
    def MESH_OT_uv_texture_remove(context: Context) -> None:
        mesh: Mesh = context.object.data

        index_updated, prev_index, curr_index = MeshProps.update_last_uv_layer_index(mesh, get_indices=True)
        name_updated, prev_name, curr_name = MeshProps.update_last_uv_layer_name(mesh, get_names=True)
        count_change = MeshProps.update_last_uv_layer_count(mesh)

        print_debug(f"DEPS|\t> on_UVMap_remove {prev_name}[{prev_index}] -> {curr_name}[{curr_index}]")

        if len(mesh.uv_layers) == 0:
            remove_attributes(context, seams=True, seam_layer_id=prev_name)
            return

        prefs = UVFLOW_Preferences.get_prefs(context)
        if not prefs.use_seam_layers:
            # NOTE: What if we need to remove any seam layer that was there
            # previously but this preference option is disabled?
            return

        # Active UVMap has changed!
        with CM_ModeToggle(context, mode='OBJECT'):
            remove_attributes(context, seams=True, seam_layer_id=prev_name)

            if curr_index != -1:
                apply_attributes(context, seams=True, seam_layer_id=curr_name)

                set_seam_props(context, uv_layer_id=curr_name)
                update_material_uvmap(context, uv_layer_id=curr_name)


# Here we track the operators from 'saved_op_id' and perform the After-Callbacks when defined.
def check_active_operator(context: Context) -> bool:
    ''' Returns True if the operator is we handled the active operator and performed an update. '''
    if context.active_operator is None:
        return False

    op_id = context.active_operator.bl_idname

    if op_id not in saved_op_id:
        # Not a to-track operator.
        return False

    op_pointer = context.active_operator.as_pointer()
    if saved_op_id[op_id] == op_pointer:
        # False update. It is the same last saved operator id.
        return False

    ## print(f"|\t> Store pointer for op_id: '{op_id}'")
    print_debug(f"DEPS|\t> Updating Attributes! op_id: '{op_id}'")

    saved_op_id[op_id] = op_pointer # Update ID.

    # HACK. Prevent recursivity...
    if after_callback := getattr(AfterCallbacks, op_id, None):
        after_callback(context)
    else:
        # By default lets just update all the attributes?
        save_attributes(context,
                        seams=True,
                        hidden=True,
                        pinned=True,
                        selected=True)

    return True


@Register.HANDLER.DEPSGRAPH_UPDATE_POST(persistent=True)
def mesh_change_listener(context: Context, scene: Scene, depsgraph: Depsgraph):
    if GLOBALS.skip_mesh_updates:
        # print("|\t> Skip: GLOBALS.skip_mesh_updates")
        return


    # Pre-check if we need to iterate through updates at all
    if not depsgraph.id_type_updated('MESH'):
        print_debug("DEPS|\t> Skip: id_type is not 'MESH'")
        return

    if context.mode != 'EDIT_MESH':
        print_debug(f"DEPS|\t> Skip: context.mode is not 'EDIT_MESH' but '{context.mode}'")
        return

    # Using the UVFlow tool! (user probably exited the uvflow tool)
    if tool_state.current_tool is not None:
        print_debug("DEPS|\t> Skip: using UVFlow tool")
        # We need to update the last op_id in case it is an accepted one that triggers an update.
        # to avoid a false 'UpdateAttributes' call on exiting the tool.
        if context.active_operator is not None:
            op_id: str = context.active_operator.bl_idname
            if op_id in saved_op_id:
                ## print(f"|\t> Store pointer for op_id: '{op_id}'")
                saved_op_id[op_id] = context.active_operator.as_pointer()
        return


    with CM_SkipMeshUpdates():
        ## print("\n* DEPSGRAPH_UPDATE_POST")

        current_mesh = context.object.data
        for update in depsgraph.updates:
            # Only check for updates from the current active mesh object.
            if isinstance(update.id, Mesh) and current_mesh == update.id.original:
                ## print(f"|\t> Mesh '{update.id.name}' updated.")

                # Update attributes when we detect an external change in seams via mark_seam built-in operator.
                if check_active_operator(context):
                    break

                # Maybe it is a mesh change involving geometry changes...
                # So we need to ensure that the raycast info (aka embedded BMesh) is cleared.
                # And the active_edge is reset since indices may heavily change.
                if tool_state.raycast_info:
                    tool_state.raycast_info.clear()
                tool_state.active_edge = -1
                break
