import bpy
import datetime

from ..core.icon_manager import Icons

row_scale = 0.75
paired_inputs = {}


# Initializes the Rokoko panel in the toolbar
class ToolPanel(object):
    bl_label = 'Pose Transfer'
    bl_idname = 'VIEW3D_TS_pose_transfer'
    bl_category = 'Pose Transfer'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'


def separator(layout, scale=1):
    # Add small separator
    row = layout.row(align=True)
    row.scale_y = scale
    row.label(text='')


# Main panel of the Rokoko panel
class ReceiverPanel(ToolPanel, bpy.types.Panel):
    bl_idname = 'VIEW3D_PT_rsl_receiver_v2'
    bl_label = 'Pose Transfer'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False

        col = layout.column()

        row = col.row(align=True)
        row.label(text='Scene Scale:')
        row.prop(context.scene, 'rsl_scene_scaling', text='')

        layout.separator()

        row = layout.row(align=True)
        row.prop(context.scene, 'rsl_reset_scene_on_stop')

        row = layout.row(align=True)
        row.prop(context.scene, 'rsl_hide_mesh_during_play')


def add_indent(split, empty=False):
    row = split.row(align=True)
    row.alignment = 'LEFT'
    if empty:
        row.label(text="", icon='BLANK1')
    else:
        row.label(text="", icon_value=Icons.PAIRED.get_icon())
