#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility
from . TempBoneUtility import TempBoneUtility

class RotationModeUtils:

    def RotationMode (self, context, rotationMode):
        #obj = bpy.context.object
        initialSelectionP = list()
        selectedBonesListN = list()

        obj = bpy.context.object

        for boneP in bpy.context.selected_pose_bones:
            if boneP.rotation_mode == rotationMode:
                boneP.bone.select = False
            else:
                selectedBonesListN.append(boneP.name)
            
            initialSelectionP.append(boneP)

        if obj.animation_data:
            selectedBonesListN = TempBoneUtility.TempBoneCopySelectedBones()
                
        #change rotation mode of selected bones
        for bone in selectedBonesListN:
            bpy.context.object.pose.bones[bone].rotation_mode = rotationMode

        if obj.animation_data:
            TempBoneUtility.SelectedBonesCopyTempBones(selectedBonesListN)

        for boneP in initialSelectionP:
            boneP.bone.select = True