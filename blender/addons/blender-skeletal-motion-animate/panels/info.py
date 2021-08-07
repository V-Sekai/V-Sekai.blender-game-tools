import bpy

from .main import ToolPanel, separator
from ..operators import info
from ..core.icon_manager import Icons


class InfoPanel(ToolPanel, bpy.types.Panel):
    bl_idname = 'VIEW3D_PT_rsl_info_v2'
    bl_label = 'Info'

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text='Skeletal Motion Retargeting')
        row = layout.row(align=True)
        row.scale_y = 0.1
        separator(layout, 0.01)

        row = layout.row(align=True)
        row.label(text='Developed by', icon='BLANK1')
        row.scale_y = 0.6

        row = layout.row(align=True)
        row.scale_y = 0.3
        row.label(text='K. S. Ernest (iFire) Lee', icon='BLANK1')

        separator(layout, 0.1)

        row = layout.row(align=True)
        row.scale_y = 0.3
        row.label(text='Based by previous work by', icon='BLANK1')

        row = layout.row(align=True)
        row.scale_y = 0.3
        row.label(text='Rokoko Electronics ApS', icon='BLANK1')


        separator(layout, 0.1)

        col = layout.column(align=True)

        row = col.row(align=True)
        row.operator(info.LicenseButton.bl_idname)
