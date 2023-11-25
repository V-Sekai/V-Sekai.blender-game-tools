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
from uvflow.tool import draw_handler as tool_draw_handler


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


def on_tool_enter(context: Context, region: Region) -> None:
    tool_draw_handler.register_draw_handler()
    region.tag_redraw()


def on_tool_exit(context: Context, region: Region) -> None:
    tool_draw_handler.unregister_draw_handler()
    region.tag_redraw()


@Register.TIMER(first_interval=1.0, step_interval=0.5, one_time_only=False, persistent=True)
def infinite_timer__check_uvflow_tool_state():
    context = bpy.context

    act_ob = context.active_object

    if act_ob is None:
        return 1.0
    if act_ob.type != 'MESH':
        return 2.5

    wnd, area, reg = get_view3d(context)
    if area is None:
        return 2.5

    prefs = UVFLOW_Preferences.get_prefs(context)

    use_checker = prefs.checker_pattern != 'NONE'
    use_gn = prefs.use_seam_highlight
    use_overlays = prefs.use_overlays and (use_checker or use_gn)


    def _toggle_overlays(enable: bool = True):
        if not use_overlays:
            return
        with context.temp_override(window=wnd, area=area, region=reg):
            if use_checker:
                ToggleUvCheckerMaterial.run(enable=enable, auto=True)
            if use_gn:
                UpdateGeoOverlays.run(enable=enable)


    with CM_SkipMeshUpdates():
        # Check if we are in the correct mode.
        global last_active_tool

        if context.mode not in {'EDIT_MESH', 'EDIT'} and act_ob.mode != 'EDIT':
            if last_active_tool == UVFlowTool.bl_idname:
                last_active_tool = None
                print_debug("\n*** UVFLOW TOOL EXIT ***")
                _toggle_overlays(enable=False)
                on_tool_exit(context, reg)
            return 1.0

        # IN EDIT MESH MODE!
        item: ToolDef
        tool_active: WorkSpaceTool
        icon_value: int
        item, tool_active, icon_value = VIEW3D_PT_tools_active._tool_get_active(context, 'VIEW_3D', 'EDIT_MESH')
        if item is None:
            return 1.0

        if item.idname == last_active_tool:
            return 0.2

        if item.idname == UVFlowTool.bl_idname:
            # TOOL ENTER.
            print_debug("\n*** UVFLOW TOOL ENTER ***")
            _toggle_overlays(enable=True)
            on_tool_enter(context, reg)

            # BUG NOTE #99: Hidden by now to avoid the enter/exit edit mode in this context
            # which is the most potential cause of the crashes here on tool enter.
            ###     save_attributes(context, seams=True, pinned=True, selected=True, hidden=True)
            ### else:
            ###     save_attributes(context, seams=True, pinned=True, selected=True, hidden=True)

            # Ensure raycast info is refreshed each time we enter the tool.
            tool_state = ToolState.get()
            if tool_state.raycast_info:
                tool_state.raycast_info.clear()

        elif last_active_tool == UVFlowTool.bl_idname:
            print_debug("\n*** UVFLOW TOOL EXIT ***")
            _toggle_overlays(enable=False)
            on_tool_exit(context, reg)

        last_active_tool = item.idname
