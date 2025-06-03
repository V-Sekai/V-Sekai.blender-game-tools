import bpy

from .main import ToolPanel, separator
from ..core.icon_manager import Icons


class InfoPanel(ToolPanel, bpy.types.Panel):
    bl_idname = 'VIEW3D_PT_rotf_info'
    bl_label = 'Info'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.scale_y = 0.6
        row.label(text='Rig On The Fly', icon='BLANK1')
        row = layout.row(align=True)
        row.scale_y = 0.3
        row.label(text='2.0.9', icon='BLANK1')

        separator(layout, 0.01)
        
        row = layout.row(align=True)
        row.label(text='Developed by ', icon='BLANK1')
        row.scale_y = 0.6
        row = layout.row(align=True)
        row.scale_y = 0.3
        row.label(text='Dypsloom', icon='BLANK1')

        separator(layout, 0.01)


    
