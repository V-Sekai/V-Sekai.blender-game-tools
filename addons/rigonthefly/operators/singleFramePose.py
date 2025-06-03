import bpy
from ..core import singleFramePose

SINGLEFRAMEPOSE_ID = '_ROTF_SINGLEFRAMEPOSE'

class SetUpSingleFramePoseOperator(bpy.types.Operator):
    bl_idname = "rotf.set_up_single_frame_pose"
    bl_label = "Set Up Single Frame Pose"
    bl_description = "Sets up single frame pose"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        singleFramePose.Setup([bpy.context.active_object])
        return {'FINISHED'}

class ApplySingleFramePoseOperator(bpy.types.Operator):
    bl_idname = "rotf.apply_single_frame_pose"
    bl_label = "Apply Single Frame Pose"
    bl_description = "Applies single frame pose"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        singleFramePose.Apply([bpy.context.active_object])
        return {'FINISHED'}
    
class RemoveSingleFramePoseOperator(bpy.types.Operator):
    bl_idname = "rotf.remove_single_frame_pose"
    bl_label = "Remove Single Frame Pose"
    bl_description = "Removes single frame pose state"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        singleFramePose.Remove([bpy.context.active_object])
        return {'FINISHED'}