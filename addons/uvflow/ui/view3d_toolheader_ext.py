''' UI extension for the 3D Viewport's ToolHeader. '''

from uvflow.addon_utils import Register

from uvflow.operators.op_editor_management import ToggleUVEditor
from uvflow.props.scene import SceneProps

from bl_ui.space_view3d import VIEW3D_HT_tool_header
from bpy.types import UILayout, Context
from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active


# @Register.UI.APPEND(VIEW3D_HT_tool_header)
# def draw_ui(context: Context, layout: UILayout) -> None:
#     from uvflow.tool.tool import UVFlowTool
#     item, tool_active, icon_value = VIEW3D_PT_tools_active._tool_get_active(context, 'VIEW_3D', 'EDIT_MESH')
#     if item is None or item.idname != UVFlowTool.bl_idname:
#         return
#     ToggleUVEditor.draw_in_layout(layout, label='UV Editor', icon='UV', depress=context.scene.uvflow.uv_editor_enabled)
