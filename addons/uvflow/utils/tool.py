from bl_ui.space_toolsystem_common import ToolSelectPanelHelper, ToolDef
from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active
from bpy.types import Context, WorkSpaceTool


def get_tool_from_context(context: Context) -> WorkSpaceTool | None:
    return VIEW3D_PT_tools_active._tool_active_from_context(context, 'VIEW_3D', mode=context.mode, create=False)


def get_tool_item_from_context(context: Context, with_icon: bool = False) -> tuple[ToolDef, WorkSpaceTool, int] | None:
    return VIEW3D_PT_tools_active._tool_get_active(context, 'VIEW_3D', mode=context.mode, with_icon=with_icon)


def get_tool_id_from_context(context: Context) -> tuple[str, str] | str:
    act_tool = get_tool_from_context(context)
    if act_tool is None:
        return 'NONE'
    if '.' in act_tool.idname:
        # Builtin.
        return act_tool.idname.split('.')
    if '_TOOL_' in act_tool.idname:
        # Custom tool using `addon_utils` submodule.
        return act_tool.idname.split('_TOOL_')
    return act_tool.idname


def get_tool_label_from_context(context: Context) -> str:
    act_tool_item, tool_active, _icon_value = get_tool_item_from_context(context, with_icon=False)
    if act_tool_item is None:
        return 'NONE'
    return act_tool_item.label
