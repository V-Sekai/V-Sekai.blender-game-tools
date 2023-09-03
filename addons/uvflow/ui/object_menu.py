import bpy

from uvflow.addon_utils import Register
from bpy.types import UILayout, Context
from uvflow.operators.op_checker import ToggleUvCheckerMaterial
from uvflow.operators.op_unwrap import UVUnwrapFromObject
from uvflow.operators.op_pack import UVPackFromObject

@Register.UI.MENU
class VIEW3D_MT_object_uvflow:
    def draw_ui(self, context: Context, layout: UILayout) -> None:
        UVUnwrapFromObject.draw_in_layout(layout, label="Unwrap UVs")
        if bpy.app.version > (3, 6, 0):
            UVPackFromObject.draw_in_layout(layout, label="Pack UVs")
        ToggleUvCheckerMaterial.draw_in_layout(layout, label='Enable UV Checkers', op_props={'enable': True, 'auto': False})
        ToggleUvCheckerMaterial.draw_in_layout(layout, label='Disable UV Checkers', op_props={'enable': False, 'auto': False})


@Register.UI.APPEND(bpy.types.VIEW3D_MT_object)
def draw_uvflow_menu(context: Context, layout: UILayout) -> None:
    layout.separator()
    VIEW3D_MT_object_uvflow.draw_in_layout(layout, label="UVFlow")
