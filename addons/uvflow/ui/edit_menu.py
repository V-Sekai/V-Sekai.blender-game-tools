import bpy

from uvflow.addon_utils import Register
from bpy.types import UILayout, Context
from uvflow.operators.op_checker import ToggleUvCheckerMaterial
from uvflow.operators.op_unwrap import UVUnwrap
from uvflow.operators.op_mark_seams import UVMarkSeams, UVSeamsFromIslands
from uvflow.operators.op_pack import UVPack

@Register.UI.APPEND(bpy.types.VIEW3D_MT_uv_map, prepend=True)
def draw_uvflow_edit_menu(context: Context, layout: UILayout) -> None:
    UVUnwrap.draw_in_layout(layout, label="UV Flow Unwrap")
    if bpy.app.version > (3, 6, 0):
        UVPack.draw_in_layout(layout, label="UV Flow Pack")
    layout.separator()
    UVMarkSeams.draw_in_layout(layout,  label='Mark Seams by Attribute', op_props={'use_seam':True})
    UVMarkSeams.draw_in_layout(layout, label='Clear Seams by Attribute', op_props={'use_seam':False})
    UVSeamsFromIslands.draw_in_layout(layout)
    layout.separator()
    ToggleUvCheckerMaterial.draw_in_layout(layout, label='Enable UV Checkers', op_props={'enable': True, 'auto': False})
    ToggleUvCheckerMaterial.draw_in_layout(layout, label='Disable UV Checkers', op_props={'enable': False, 'auto': False})
    layout.separator()
