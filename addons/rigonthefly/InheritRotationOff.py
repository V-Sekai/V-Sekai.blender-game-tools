#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility
from . TempBoneUtility import TempBoneUtility

class InheritRotationOffUtils:

    def InheritRotationOff (self, context):
        initialSelectionP = list()
        selectedBonesListN = list()

        for boneP in bpy.context.selected_pose_bones:
            if not boneP.bone.use_inherit_rotation:
                boneP.bone.select = False
            else:
                selectedBonesListN.append(boneP.name)
            
            initialSelectionP.append(boneP)

        selectedBonesListN = TempBoneUtility.TempBoneCopySelectedBones()

        #remove inherit rotation to original bone selection
        for bone in selectedBonesListN:
            bpy.context.object.data.bones[bone].use_inherit_rotation = False

        TempBoneUtility.SelectedBonesCopyTempBones(selectedBonesListN)

        for boneP in initialSelectionP:
            boneP.bone.select = True