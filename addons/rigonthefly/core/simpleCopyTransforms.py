#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . import rigState


class SimpleCopyTransformsConstraint:

    def __init__(self):
        print('Simple Copy Transforms Constraint')

    def CreateSimpleCopyTransformsConstraint(copyTransformsSettingsList):        
        SetupSimpleCopyTransformsConstraint(copyTransformsSettingsList)

    def CreateConstraint(self, obj, constraintInfoList):
        copyTransformsSettingsList = list()
        errorMessageList = list()
        for constraintInfo in constraintInfoList:
            copyTransformsSettings = CopyTransformsSettings()
            copyTransformsSettings.targetObject = obj

            targetObj = bpy.data.objects.get(constraintInfo['string_list'][0])
            boneN = constraintInfo['bone_list'][0]
            targetBoneN = constraintInfo['bone_list'][1]

            copyTransformsSettings.object = obj
            copyTransformsSettings.boneN = boneN

            copyTransformsSettings.targetObject = targetObj
            copyTransformsSettings.targetBoneN = targetBoneN

            copyTransformsSettings.copyLocation = constraintInfo['bool_list'][0]
            copyTransformsSettings.copyRotation = constraintInfo['bool_list'][1]
            copyTransformsSettings.copyScale = constraintInfo['bool_list'][2]

            copyTransformsSettings.influence = constraintInfo['float_list'][0]

            if obj.data.bones.get(boneN) == None: #check if target bone exists. if not, skips
                errorMessageList.append("Copy Transforms Constraint|Bone not found: " + obj.name + "[" + boneN + "]")
                continue

            if targetObj == None: #check if target object exists. if not, skips
                errorMessageList.append("Copy Transforms Constraint|Object not found: " + obj.name)
                continue
            if targetObj.data.bones.get(targetBoneN) == None: #check if target bone exists. if not, skips
                errorMessageList.append("Copy Transforms Constraint|Bone not found: " + obj.name + "[" + targetBoneN + "]")
                continue

            copyTransformsSettingsList.append(copyTransformsSettings)

        SimpleCopyTransformsConstraint.CreateSimpleCopyTransformsConstraint(copyTransformsSettingsList)

        if errorMessageList:
            return errorMessageList

class CopyTransformsSettings:
    def __init__(self):
        self.object = None
        self.boneN = str()

        self.targetObject = None
        self.targetBoneN = str()

        self.copyLocation = bool()
        self.copyRotation = bool()
        self.copyScale = bool()

        self.influence = float()

def SetupSimpleCopyTransformsConstraint(copyTransformsSettingsList):
    for copyTransformsSettings in copyTransformsSettingsList:
        obj = copyTransformsSettings.object
        targetObj = copyTransformsSettings.targetObject

        boneN = copyTransformsSettings.boneN
        targetBoneN = copyTransformsSettings.targetBoneN

        pbone = obj.pose.bones[boneN]

        copyLocationBool  = copyTransformsSettings.copyLocation
        copyRotationBool  = copyTransformsSettings.copyRotation
        copyScaleBool  = copyTransformsSettings.copyScale

        if copyLocationBool and copyRotationBool and copyScaleBool:
            copyTransforms = pbone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.name += " Simple RotF"
            copyTransforms.target = targetObj
            copyTransforms.subtarget = targetBoneN
            copyTransforms.influence = copyTransformsSettings.influence

        else:
            if copyLocationBool:
                copyLocation = pbone.constraints.new('COPY_LOCATION')
                copyLocation.name += " Simple RotF"
                copyLocation.target = targetObj
                copyLocation.subtarget = targetBoneN
                copyLocation.influence = copyTransformsSettings.influence

            if copyRotationBool:
                copyRotation = pbone.constraints.new('COPY_ROTATION')
                copyRotation.name += " Simple RotF"
                copyRotation.target = targetObj
                copyRotation.subtarget = targetBoneN
                copyRotation.influence = copyTransformsSettings.influence
            
            if copyScaleBool:
                copyScale = pbone.constraints.new('COPY_SCALE')
                copyScale.name += " Simple RotF"
                copyScale.target = targetObj
                copyScale.subtarget = targetBoneN
                copyScale.influence = copyTransformsSettings.influence

        rigState.AddConstraint(
            obj,
            "Simple Copy Transforms|" + boneN,
            "Simple Copy Transforms|" + boneN + "|Location:" + str(copyLocationBool) + "|Rotation:" + str(copyRotationBool) + "|Scale:" + str(copyScaleBool),
            "Simple Copy Transforms",
            [boneN, targetBoneN],
            [copyLocationBool, copyRotationBool, copyScaleBool],
            [targetObj.name],
            [0], #is not used
            [copyTransformsSettings.influence]
            )

def SimpleCopyTransforms():
    scene = bpy.context.scene
    copyTransformsSettingsList = list()

    obj = bpy.context.object
    activePbone = bpy.context.active_pose_bone
    for pbone in bpy.context.selected_pose_bones:
        if pbone != activePbone:

            copyTransformsSettings = CopyTransformsSettings()
            copyTransformsSettings.object = pbone.id_data
            copyTransformsSettings.boneN = pbone.name

            copyTransformsSettings.targetObject = activePbone.id_data
            copyTransformsSettings.targetBoneN = activePbone.name

            copyTransformsSettings.copyLocation = scene.rotf_simple_copy_location
            copyTransformsSettings.copyRotation = scene.rotf_simple_copy_rotation
            copyTransformsSettings.copyScale = scene.rotf_simple_copy_scale

            copyTransformsSettings.influence = scene.rotf_simple_influence

            copyTransformsSettingsList.append(copyTransformsSettings)

    SimpleCopyTransformsConstraint.CreateSimpleCopyTransformsConstraint(copyTransformsSettingsList)


