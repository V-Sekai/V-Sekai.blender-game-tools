import bpy

from .main import ToolPanel, separator
from ..core.icon_manager import Icons

class SingleFramePosePanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_singleFramePose'
    bl_label = 'Single Frame Pose'

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        if context.active_object:
            if context.active_object.rotf_sfp_rig_state == "" :
                row.operator('rotf.set_up_single_frame_pose', text="Set Up")
            else:
                row.operator('rotf.apply_single_frame_pose', text="Apply Pose")