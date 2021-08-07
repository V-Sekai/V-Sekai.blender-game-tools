#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility

class DeleteBonesUtils:

    def DeleteBones (self, context):

        #armature is in pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #remove from selection bones that do not end  with ".rig"
        for boneP in bpy.context.selected_pose_bones:
            if not boneP.name.casefold().endswith(".rig"):
                boneP.bone.select = False
        
        for boneP in bpy.context.selected_pose_bones:
            obj = boneP.id_data
            if obj.animation_data:
                #clear all key frames of selected bones
                StateUtility.KeyframeClear()

        #armature is in edit mode
        StateUtility.SetEditMode()

        #delete selected bones
        bpy.ops.armature.delete()

        #armature is in pose mode
        bpy.ops.object.mode_set(mode='POSE')