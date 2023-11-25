import bpy
from uvflow.addon_utils import Register
from bpy.types import UILayout, Context
from uvflow.operators.op_mark_seams import UVSeamsFromIslands

@Register.UI.APPEND(bpy.types.DATA_PT_uv_texture)
def draw_seams_from_islands_button(context: Context, layout: UILayout) -> None:
    if context.mode == 'EDIT_MESH':
        col = layout.column(align=True)
        col.separator()
        UVSeamsFromIslands.draw_in_layout(col)