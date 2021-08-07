#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . DypsloomBake import DypsloomBakeUtils

class DypsloomBakeOperator(bpy.types.Operator):
    bl_idname = "view3d.dypsloom_bake_operator"
    bl_label = "Simple operator"
    bl_description = "Bakes animation of selected bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = bpy.context.object
        action = obj.animation_data.action
        frames = list(range(int(action.frame_range[0]), int(action.frame_range[1]+1)))
        print(frames)
        selectedPBones = bpy.context.selected_pose_bones

        DypsloomBakeUtils.DypsloomBake(obj, action, frames, selectedPBones)

        return {'FINISHED'}