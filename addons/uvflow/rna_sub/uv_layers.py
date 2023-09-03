from uvflow.addon_utils import Register
from uvflow.props.mesh import MeshProps
from uvflow.prefs import UVFLOW_Preferences
from uvflow.addon_utils.utils.mode import CM_ModeToggle
from uvflow.tool.attributes import save_attributes, apply_attributes
from uvflow.operators.op_geo_overlay import set_seam_props
from uvflow.operators.op_checker import update_material_uvmap
from uvflow.globals import print_debug

from bpy.types import Context, MeshUVLoopLayer, UVLoopLayers, Mesh


@Register.RNA_SUB(UVLoopLayers, 'active_index', data_path='object.data.uv_layers', persistent=True)
def on_UVMap_switch(context: Context, uv_layers: UVLoopLayers, active_index: int):
    mesh: Mesh = uv_layers.id_data
    has_changed, prev_index, curr_index = MeshProps.update_last_uv_layer_index(mesh, get_indices=True)
    if not has_changed:
        # Skip. User probably clicked on the active one or clicked twice.
        return
    
    print_debug(f"RNA|\t> on_UVMap_switch {prev_index} -> {curr_index}")

    changed, prev_name, curr_name = MeshProps.update_last_uv_layer_name(uv_layers.id_data, get_names=True)

    prefs = UVFLOW_Preferences.get_prefs(context)
    if not prefs.use_seam_layers:
        return

    with CM_ModeToggle(context, mode='OBJECT'):
        # Active UVMap has changed!
        save_attributes(context, seams=True, seam_layer_id=prev_name)
        apply_attributes(context, seams=True, seam_layer_id=curr_name)

        set_seam_props(context, uv_layer_id=curr_name)
        update_material_uvmap(context, uv_layer_id=curr_name)


@Register.RNA_SUB(MeshUVLoopLayer, 'name', data_path='object.data.uv_layers.active', persistent=True)
def on_UVMap_rename(context: Context, uv_layer: MeshUVLoopLayer, name: str):
    mesh: Mesh = uv_layer.id_data
    name_updated, prev_name, curr_name = MeshProps.update_last_uv_layer_name(mesh, get_names=True)
    
    print_debug(f"RNA|\t> on_UVMap_rename {prev_name} -> {curr_name}")

    prev_attr_name = prev_name + '_seams'
    for attribute_layer in mesh.attributes:
        if attribute_layer.name == prev_attr_name:
            attribute_layer.name = curr_name + '_seams'
            break
