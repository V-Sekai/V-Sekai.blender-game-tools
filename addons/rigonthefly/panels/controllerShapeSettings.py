import bpy
from .main import ToolPanel, separator

class ControllerShapeSettingsPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_controllerShapeSettings'
    bl_label = 'Controller Shape Settings'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.label(text="Controller Size")
        row = col.row(align=True)
        row.prop(context.scene, 'rotf_mirror_controller_size', text="Mirror")
        row.operator('view3d.controller_size_minus', text="-")
        row.operator('view3d.controller_size_plus', text="+")

        row = layout.row(align=True)
        row.prop(context.scene, 'rotf_controller_shape_thickness', text="Thickness")
        