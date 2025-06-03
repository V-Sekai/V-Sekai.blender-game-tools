#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . import rigState


class SimpleAimConstraint:

    def __init__(self):
        print('Simple Aim Constraint')

    def CreateSimpleAimConstraint(aimSettingsList):        
        SetupSimpleAimConstraint(aimSettingsList)

    def CreateConstraint(self, obj, constraintInfoList):
        aimSettingsList = list()
        errorMessageList = list()
        for constraintInfo in constraintInfoList:
            aimSettings = SimpleAimSettings()
            aimSettings.targetObject = obj

            targetObj = bpy.data.objects.get(constraintInfo['string_list'][0])
            boneN = constraintInfo['bone_list'][0]
            targetBoneN = constraintInfo['bone_list'][1]

            aimAxis = constraintInfo['string_list'][1]
            influence = constraintInfo['float_list'][0]

            aimSettings.object = obj
            aimSettings.boneN = boneN

            aimSettings.targetObject = targetObj
            aimSettings.targetBoneN = targetBoneN

            aimSettings.aimAxis = aimAxis
            aimSettings.influence = influence

            if obj.data.bones.get(boneN) == None: #check if target bone exists. if not, skips
                errorMessageList.append("Copy Transforms Constraint|Bone not found: " + obj.name + "[" + boneN + "]")
                continue

            if targetObj == None: #check if target object exists. if not, skips
                errorMessageList.append("Copy Transforms Constraint|Object not found: " + obj.name)
                continue
            if targetObj.data.bones.get(targetBoneN) == None: #check if target bone exists. if not, skips
                errorMessageList.append("Copy Transforms Constraint|Bone not found: " + obj.name + "[" + targetBoneN + "]")
                continue

            aimSettingsList.append(aimSettings)

        SimpleAimConstraint.CreateSimpleAimConstraint(aimSettingsList)

        if errorMessageList:
            return errorMessageList

class SimpleAimSettings:
    def __init__(self):
        self.object = None
        self.boneN = str()

        self.targetObject = None
        self.targetBoneN = str()

        self.aimAxis = str()
        self.influence = float()

def SetupSimpleAimConstraint(aimSettingsList):
    for aimSettings in aimSettingsList:
        obj = aimSettings.object
        targetObj = aimSettings.targetObject

        boneN = aimSettings.boneN
        targetBoneN = aimSettings.targetBoneN

        pbone = obj.pose.bones[boneN]

        #get the right trackAxis string using the aimSettings.aimAxis
        trackAxis = "TRACK_"
        if "-" in aimSettings.aimAxis:
            trackAxis += "NEGATIVE_"
        trackAxis += aimSettings.aimAxis.replace("-","")

        aim = pbone.constraints.new('DAMPED_TRACK')
        aim.name += " Simple RotF"
        aim.target = targetObj
        aim.subtarget = targetBoneN
        aim.track_axis = trackAxis
        aim.influence = aimSettings.influence

        rigState.AddConstraint(
            obj,
            "Simple Aim|" + boneN,
            "Simple Aim|" + boneN + "|Axis:" + aimSettings.aimAxis,
            "Simple Aim",
            [boneN, targetBoneN],
            [True], #is not used
            [targetObj.name, aimSettings.aimAxis],
            [0], #is not used
            [aimSettings.influence]
            )

def SimpleAim():
    scene = bpy.context.scene
    aimSettingsList = list()

    pboneSelection = bpy.rotf_pose_bone_selection

    for i, pbone in enumerate(pboneSelection[:-1]):
        aimSettings = SimpleAimSettings()
        aimSettings.object = pbone.id_data
        aimSettings.boneN = pbone.name

        targetPBone = pboneSelection[i+1]

        aimSettings.targetObject = targetPBone.id_data #activePbone.id_data
        aimSettings.targetBoneN = targetPBone.name #activePbone.name

        aimSettings.aimAxis = scene.rotf_simple_aim_axis
        aimSettings.influence = scene.rotf_simple_influence

        aimSettingsList.append(aimSettings)

    SimpleAimConstraint.CreateSimpleAimConstraint(aimSettingsList)

