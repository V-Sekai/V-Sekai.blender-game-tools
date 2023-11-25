import bpy
from uvflow.addon_utils import Register
from bpy.types import UILayout, Context
from uvflow.operators.op_material import MaterialSelectObjects, MaterialSelectFaces
from uvflow.operators.op_pack import UVPack

def draw_material_buttons(context: Context, layout: UILayout) -> None:
    if context.mode == 'OBJECT' and context.object.type =='MESH':
        row = layout.row(align=True)
        MaterialSelectObjects.draw_in_layout(row)
        MaterialSelectFaces.draw_in_layout(row)
        UVPack.draw_in_layout(row, label='Pack UVs', op_props={'pack_active_material': True})

if hasattr(bpy.types, 'CYCLES_PT_context_material'):
    @Register.UI.APPEND(bpy.types.CYCLES_PT_context_material)
    def draw_material_buttons_Cycles(context: Context, layout: UILayout) -> None:
        draw_material_buttons(context, layout)

if hasattr(bpy.types, 'EEVEE_MATERIAL_PT_context_material'):
    @Register.UI.APPEND(bpy.types.EEVEE_MATERIAL_PT_context_material)
    def draw_material_buttons_Cycles(context: Context, layout: UILayout) -> None:
        draw_material_buttons(context, layout)


