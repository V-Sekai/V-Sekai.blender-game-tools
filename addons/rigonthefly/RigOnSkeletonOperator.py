#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . RigOnSkeleton import RigOnSkeletonUtils
from . AutoBoneOrient import AutoBoneOrientUtils

class RigOnSkeletonOperator(bpy.types.Operator):
    bl_idname = bl_idname = "view3d.rig_on_skeleton_operator"
    bl_label = "Simple operator"
    bl_description = "Adds basic FK rig controllers to skeleton, will cause issues if bones end in .###"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = bpy.context.object

        RigOnSkeletonUtils.RestPoseTrack(self, context) #add a rest pose nla track
        
        #check if armature object has animation data
        if obj.animation_data:
            objHasAnimation = RigOnSkeletonUtils.ArmatureMotionToBone(self, context)
        else:
            objHasAnimation = False
            
        scene = bpy.context.scene
        if scene.orientRig:
            AutoBoneOrientUtils.AutoBoneOrient(self, context)
        else:
            RigOnSkeletonUtils.RigOnSkeleton(self, context)
        
        if objHasAnimation:
            RigOnSkeletonUtils.ArmatureMotionBoneShape(self, context)
            
        return {'FINISHED'}