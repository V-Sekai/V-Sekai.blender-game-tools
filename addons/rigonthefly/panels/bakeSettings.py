import bpy
from .main import ToolPanel, separator

class BakeSettingsPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_bakeSettings'
    bl_label = 'Bake Settings'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.prop(context.scene, "rotf_smart_frames", text="Smart Frames")

        row = layout.row(align=True)
        row.prop(context.scene, "rotf_no_bake_on_remove", text="No Bake on Remove")