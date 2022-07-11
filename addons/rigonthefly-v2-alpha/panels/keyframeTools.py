import bpy

from .main import ToolPanel, separator
from ..core.icon_manager import Icons

class KeyframeToolsPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_keyframeTools'
    bl_label = 'Keyframe Tools'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        selectedObjects = bpy.context.selected_objects
        selectedPBones = bpy.context.selected_pose_bones

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('rotf.key_range', text="Key Range")
        row.prop(context.scene, "rotf_frame_range_step")

        row = col.row(align=True)
        row.prop(context.scene, "rotf_frame_range_start")
        row.prop(context.scene, "rotf_frame_range_end")

