#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility
from . TempBoneUtility import TempBoneUtility

class InheritScaleOnUtils:

    def InheritScaleOn (self, context):
        initialSelectionP = list()
        selectedBonesListN = list()

        for boneP in bpy.context.selected_pose_bones:
            if boneP.bone.use_inherit_scale:
                boneP.bone.select = False
            else:
                selectedBonesListN.append(boneP.name)
            
            initialSelectionP.append(boneP)
        
        selectedBonesListN = TempBoneUtility.TempBoneCopySelectedBones()

        #inherit scale to original bone selection
        for bone in selectedBonesListN:
            bpy.context.object.data.bones[bone].use_inherit_scale = True

        TempBoneUtility.SelectedBonesCopyTempBones(selectedBonesListN)

        for boneP in initialSelectionP:
            boneP.bone.select = True