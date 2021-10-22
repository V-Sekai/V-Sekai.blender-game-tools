#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . BakeOnSkeleton import BakeOnSkeletonUtils
from . BakeOrientOnSkeleton import BakeOrientOnSkeletonUtils

class BakeOnSkeletonOperator(bpy.types.Operator):
    bl_idname = "view3d.bake_on_skeleton_operator"
    bl_label = "Simple operator"
    bl_description = "Bake animation on the base skeleton and remove controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = bpy.context.object
        armature = obj.data
        bakeOrient = False

        for bone in armature.bones:
            if ".orient." in bone.name:
                bakeOrient = True
        if bakeOrient:
            result = BakeOrientOnSkeletonUtils.BakeOrientOnSkeleton(self, context)
        else:
            result = BakeOnSkeletonUtils.BakeOnSkeleton(self, context)
        
        BakeOnSkeletonUtils.BoneMotionToArmature(self, context)

        if obj.animation_data.nla_tracks['RotF Rest Pose '+ obj.name]:
            obj.animation_data.nla_tracks.remove(obj.animation_data.nla_tracks['RotF Rest Pose '+ obj.name])
            
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}