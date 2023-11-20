import bpy
from .main import ToolPanel, separator

class ControllerShapeSettingsPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_controllerShapeSettings'
    bl_label = 'Controller Shape Settings'

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.label(text="Controller Size")
        row = col.row(align=True)
        row.operator('view3d.controller_size_minus', text="-")
        row.operator('view3d.controller_size_plus', text="+")
        