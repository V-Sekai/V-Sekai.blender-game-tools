from uvflow.addon_utils import Register

import bpy
from bpy.types import WorkSpaceTool, Context, Window, Area, Region, Mesh
from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active

from bl_ui.space_toolsystem_common import ToolDef

from .tool.tool import UVFlowTool, ToolState
from .operators.op_checker import ToggleUvCheckerMaterial
from .operators.op_geo_overlay import UpdateGeoOverlays
from .tool.attributes import save_attributes
from .prefs import UVFLOW_Preferences
from .props.mesh import MeshProps
from uvflow.globals import CM_SkipMeshUpdates, print_debug


last_active_tool: WorkSpaceTool = None
last_mesh_id: int = 0


def get_view3d(context: Context) -> tuple[Window, Area, Region]:
    for _wnd in context.window_manager.windows:
        for _area in _wnd.screen.areas:
            if _area.type == 'VIEW_3D':
                for _reg in _area.regions:
                    if _reg.type == 'WINDOW':
                        return _wnd, _area, _reg
    return None, None, None


@Register.TIMER(first_interval=1.0, step_interval=0.5, one_time_only=False, persistent=True)
def infinite_timer__check_uvflow_tool_state():
    context = bpy.context

    if context.object is None:
        return 2.0
    if context.object.type != 'MESH':
        return 2.5
    
    # Initialize/Ensure UVMap MeshProps.
    global last_mesh_id
    if last_mesh_id != context.object.data.as_pointer():
        print_debug("TIMER|\t> MeshProps.ensure_last_uv_layer")
        last_mesh_id = context.object.data.as_pointer()
        MeshProps.ensure_last_uv_layer(context.object.data)


    with CM_SkipMeshUpdates():
        # Check if we are in the correct mode.
        global last_active_tool

        if context.mode != 'EDIT_MESH':
            if last_active_tool == UVFlowTool.bl_idname:
                last_active_tool = None
                print_debug("\n*** UVFLOW TOOL EXIT ***")
                wnd, area, reg = get_view3d(context)
                if area is None:
                    return 2.0
                with context.temp_override(window=wnd, area=area, region=reg):
                    ToggleUvCheckerMaterial.run(enable=False, auto=True)
                    UpdateGeoOverlays.run(enable=False)
            return 1.0

        # IN EDIT MESH MODE!
        wnd, area, reg = get_view3d(context)
        if area is None:
            return 1.0

        prefs = UVFLOW_Preferences.get_prefs(context)
        # tools = context.workspace.tools.from_space_view3d_mode('EDIT_MESH', create=False)

        # item is of type ToolDef.
        item: ToolDef
        tool_active: WorkSpaceTool
        icon_value: int
        item, tool_active, icon_value = VIEW3D_PT_tools_active._tool_get_active(context, 'VIEW_3D', 'EDIT_MESH')
        # print(item, tool_active, icon_value)

        # print("IS?", tool_active == UVFlowTool)
        # print(item.idname, UVFlowTool.bl_idname)


        if item.idname == last_active_tool:
            return 0.2

        if item.idname == UVFlowTool.bl_idname:
            # TOOL ENTER.
            print_debug("\n*** UVFLOW TOOL ENTER ***")
            with context.temp_override(window=wnd, area=area, region=reg):
                if prefs.use_overlays:
                    ToggleUvCheckerMaterial.run(enable=True, auto=True)
                    save_attributes(context, seams=True, pinned=True, selected=True, hidden=True)
                    UpdateGeoOverlays.run(enable=True)
                else:
                    save_attributes(context, seams=True, pinned=True, selected=True, hidden=True)

            # Ensure raycast info is refreshed each time we enter the tool.
            tool_state = ToolState.get()
            if tool_state.raycast_info:
                tool_state.raycast_info.clear()

        elif last_active_tool == UVFlowTool.bl_idname:
            # TOOL EXIT.
            print_debug("\n*** UVFLOW TOOL EXIT ***")
            if prefs.use_overlays:
                with context.temp_override(window=wnd, area=area, region=reg):
                    UpdateGeoOverlays.run(enable=False)
                    ToggleUvCheckerMaterial.run(enable=False, auto=True)

        last_active_tool = item.idname
