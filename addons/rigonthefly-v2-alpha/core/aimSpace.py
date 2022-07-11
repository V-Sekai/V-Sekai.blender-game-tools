#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from mathutils import Matrix, Euler, Vector
from bpy_extras.io_utils import axis_conversion
from . import duplicateBone
from . import removeConstraints
from . import rigState
from . import importControllerShapes
from . import rotfBake


class AimSpaceConstraint:

    def __init__(self):
        print('Aim Space Constraint')

    def CreateAimSpaceConstraint(aimSettingsList):
        aimSettingsList, bonesToBakeInfo, duplicatePBoneList = SetupAimSpaceControllers(aimSettingsList)
        
        rotfBake.Bake(bonesToBakeInfo) #bake aim space bone
        
        removeConstraints.RemoveAllRotFConstraints(duplicatePBoneList) #remove constraints from aim space bones
        
        SetupAimSpaceBehaviour(aimSettingsList) 
        
        return aimSettingsList

    def CreateConstraint(self, obj, constraintInfoList):
        aimSettingsList = list()
        errorMessageList = list()
        for constraintInfo in constraintInfoList:
            aimSettings = AimSettings()
            aimSettings.targetObject = obj
            targetBoneN = constraintInfo['bone_list'][0]
            aimSettings.targetBoneN = targetBoneN

            aimSettings.stretch = constraintInfo['bool_list'][0]
            aimSettings.aimAxis = constraintInfo['string_list'][0]
            aimSettings.distance = constraintInfo['float_list'][0]

            if obj.data.bones.get(constraintInfo['bone_list'][0]) == None: #check if target bone exists. if not, skips
                errorMessageList.append("Aim Constraint|Bone not found: " + obj.name + "[" + targetBoneN + "]")
                continue

            aimSettingsList.append(aimSettings)

        AimSpaceConstraint.CreateAimSpaceConstraint(aimSettingsList)

        if errorMessageList:
            return errorMessageList

class AimSettings:
    def __init__(self):
        self.targetObject = None
        self.targetBoneN = str()
        self.tempBoneN = str()
        self.aimTargetBoneN = str()

        self.stretch = bool()
        self.aimAxis = str()
        self.distance = float()

def SetupAimSpaceControllers(aimSettingsList):
    bonesToBakeInfo = dict()

    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.context.object.data.use_mirror_x = False

    #add aim target and temp bones
    for aimSettings in aimSettingsList:
        obj = aimSettings.targetObject
        armature = obj.data
        ebone = armature.edit_bones[aimSettings.targetBoneN]

        #create aim target bone and place it at the center of the scene
        newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBone("AimTarget.", [ebone])
        aimSettings.aimTargetBoneN = newBoneNames[0]
        aimTargetEBone = newEditBones[0]
        aimTargetEBone.parent = None #remove parent from parent copy bone

        #find the matrix coordinates of the armature object
        armatureMatrix = obj.matrix_world
        #invert armature's matrix to find where global(0,0,0) is in relation to the armature's position/roation
        armatureMatrixInvert= armatureMatrix.copy()
        armatureMatrixInvert.invert()
        #set aim bone position to global (0,0,0) with axis following world's
        aimTargetEBone.matrix = armatureMatrixInvert
        aimTargetEBone.length = ebone.length


        #create temp bone to help have the aim target 
        newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBone("Temp.", [ebone])
        aimSettings.tempBoneN = newBoneNames[0]
        aimTargetEBone = newEditBones[0]
        aimTargetEBone.parent = ebone
        #rotate temp bone so that it's Y axis points to the target bone's aim axis
        aimAxis = aimSettings.aimAxis
        to_forward = 'X' if aimAxis not in {'X', '-X'} else 'Y'
        correction_matrix = axis_conversion(from_forward='X',
                                                    from_up='Y',
                                                    to_forward=to_forward,
                                                    to_up=aimAxis,
                                                    ).to_4x4()
        aimTargetEBone.matrix = ebone.matrix @ correction_matrix

    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')
    duplicatePBoneList = list()
    for aimSettings in aimSettingsList:
        obj = aimSettings.targetObject
        aimTargetPBone = obj.pose.bones[aimSettings.aimTargetBoneN]
        targetPBone = obj.pose.bones[aimSettings.targetBoneN]

        duplicatePBoneList.append(aimTargetPBone)

        duplicateBone.AssignPoseBoneGroups([targetPBone], [aimTargetPBone])

        targetPBone.rotf_previous_shape = targetPBone.custom_shape

        #assign controller shape to target bone
        aim_customShape = bpy.context.scene.rotf_aimSpace_customShape
        if aim_customShape == None:
            importControllerShapes.ImportControllerShapes(["RotF_CirclePointer"])
            targetPBone.custom_shape = bpy.data.objects['RotF_CirclePointer']
        else:
            targetPBone.custom_shape = bpy.data.objects[aim_customShape.name]

        #assign controller shape to aim target bone
        aimTarget_customShape = bpy.context.scene.rotf_aimTarget_customShape
        if aimTarget_customShape == None:
            importControllerShapes.ImportControllerShapes(["RotF_Locator"])
            aimTargetPBone.custom_shape = bpy.data.objects['RotF_Locator']
        else:
            aimTargetPBone.custom_shape = bpy.data.objects[aimTarget_customShape.name]
        
        aimAxis = aimSettings.aimAxis #not working currently
        if aimAxis == "-Y":
            aimTargetPBone.custom_shape_rotation_euler[2] = 3.14159 #180 in Z
        if aimAxis == "X":
            aimTargetPBone.custom_shape_rotation_euler[2] = -1.5708 #-90 in Z
        if aimAxis == "-X":
            aimTargetPBone.custom_shape_rotation_euler[2] = 1.5708 #90 in Z
        if aimAxis == "Z":
            aimTargetPBone.custom_shape_rotation_euler[0] = 1.5708 #90 in X
        if aimAxis == "-Z":
            aimTargetPBone.custom_shape_rotation_euler[0] = -1.5708 #-90 in X

        #have aim target bone location constraint to temp bone's tail
        copyLocation = aimTargetPBone.constraints.new('COPY_LOCATION')
        copyLocation.name += " RotF"
        copyLocation.target = obj
        copyLocation.subtarget = aimSettings.tempBoneN
        copyLocation.head_tail = 1
        #have the aim target stay at a distance from the target bone 
        limitDistance = aimTargetPBone.constraints.new('LIMIT_DISTANCE')
        limitDistance.name += " RotF"
        limitDistance.target = obj
        limitDistance.subtarget = aimSettings.targetBoneN
        limitDistance.limit_mode = 'LIMITDIST_ONSURFACE'
        limitDistance.distance = aimSettings.distance
        #prepare bake info for the aim target
        bonesToBakeInfo[aimTargetPBone] = [[targetPBone, rotfBake.Channel.locationRotationQE, rotfBake.Channel.locationXYZ]]

    return aimSettingsList, bonesToBakeInfo, duplicatePBoneList

def SetupAimSpaceBehaviour(aimSettingsList):
    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    for aimSettings in aimSettingsList:
        obj = aimSettings.targetObject
        armature = obj.data
        tempEBone = armature.edit_bones[aimSettings.tempBoneN]
        armature.edit_bones.remove(tempEBone)

    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')

    for aimSettings in aimSettingsList:
        obj = aimSettings.targetObject
        targetPBone = obj.pose.bones[aimSettings.targetBoneN]
        aimTargetPBone = obj.pose.bones[aimSettings.aimTargetBoneN]

        #get the right trackAxis string using the aimSettings.aimAxis
        trackAxis = "TRACK_"
        if "-" in aimSettings.aimAxis:
            trackAxis += "NEGATIVE_"
        trackAxis += aimSettings.aimAxis.replace("-","")
        #have target bone aim at the aim target bone with the appropriate axis
        dampedTrack = targetPBone.constraints.new('DAMPED_TRACK')
        dampedTrack.name += " RotF"
        dampedTrack.target = obj
        dampedTrack.subtarget = aimSettings.aimTargetBoneN
        dampedTrack.track_axis = trackAxis

        newPointer = targetPBone.bone.rotf_pointer_list.add()
        newPointer.name = "AIM"
        newPointer.armature_object = obj
        newPointer.bone_name = aimSettings.targetBoneN

        newPointer = aimTargetPBone.bone.rotf_pointer_list.add()
        newPointer.name = "AIM"
        newPointer.armature_object = obj
        newPointer.bone_name = aimSettings.targetBoneN

        print(aimTargetPBone.custom_shape_rotation_euler)

        rigState.AddConstraint(
            obj,
            "Aim Space|" + aimSettings.targetBoneN,
            "Aim Space|" + aimSettings.targetBoneN,
            "Aim Space",
            [aimSettings.targetBoneN],
            [aimSettings.stretch],
            [aimSettings.aimAxis],
            [0], #is not used
            [aimSettings.distance]
            )

def AimSpace():
    scene = bpy.context.scene
    aimSettingsList = list()

    for pbone in bpy.context.selected_pose_bones:
        aimSettings = AimSettings()
        aimSettings.targetObject = pbone.id_data
        aimSettings.targetBoneN = pbone.name

        aimSettings.stretch = scene.rotf_aim_stretch
        aimSettings.aimAxis = scene.rotf_aim_axis
        aimSettings.distance = scene.rotf_aim_distance
        aimSettingsList.append(aimSettings)

    AimSpaceConstraint.CreateAimSpaceConstraint(aimSettingsList)

    #end with only the aim target bones selected
    bpy.ops.pose.select_all(action='DESELECT')
    for aimSettings in aimSettingsList:
        obj = aimSettings.targetObject
        obj.pose.bones[aimSettings.aimTargetBoneN].bone.select = True

class RemoveAimInfo:
    def __init__(self):
        self.object = None
        self.boneN = str()
        self.constraint = None
        self.aimTargetBoneN = str()
        self.offsetBoneN = str()

def RemoveAimSpace():
    removeAimInfoList = list()
    aimSpaceBoneNList = list()
    for pbone in bpy.context.selected_pose_bones:
        if "AIM" in pbone.bone.rotf_pointer_list:
            obj = pbone.id_data
            aimSpaceBoneN = pbone.bone.rotf_pointer_list['AIM'].bone_name
            aimSpaceBone = obj.pose.bones[aimSpaceBoneN].bone

            #removes bone pointer from aim space bone
            pointerIndex= aimSpaceBone.rotf_pointer_list.find('AIM')
            aimSpaceBone.rotf_pointer_list.remove(pointerIndex)

            if aimSpaceBoneN not in aimSpaceBoneNList:
                aimSpaceBoneNList.append(aimSpaceBoneN)
                removeAimInfo = RemoveAimInfo()
                removeAimInfo.object = obj
                removeAimInfo.boneN = aimSpaceBoneN

                removeAimInfoList.append(removeAimInfo)

    RemoveAim(removeAimInfoList)

    #end with only the aim space bones selected
    bpy.ops.pose.select_all(action='DESELECT')
    for removeAimInfo in removeAimInfoList:
        pbone = removeAimInfo.object.pose.bones[removeAimInfo.boneN]
        pbone.bone.select = True

def RemoveAim(removeAimInfoList):
    bonesToBakeInfo = dict()
    pboneKeyframeClearList = list()

    for removeAimInfo in removeAimInfoList:
        obj = removeAimInfo.object
        pbone = obj.pose.bones[removeAimInfo.boneN]

        copyTransforms = pbone.constraints.get('Copy Transforms RotF')
        dampedTo = pbone.constraints.get('Damped Track RotF')

        if copyTransforms:
            offsetBoneN = copyTransforms.subtarget

            removeAimInfo.constraint = copyTransforms
            removeAimInfo.offsetBoneN = offsetBoneN

            dampedTo = obj.pose.bones[offsetBoneN].constraints.get('Damped Track RotF')

            offsetPBone = obj.pose.bones[offsetBoneN]
            pboneKeyframeClearList.append(offsetPBone)

            pbone.bone.layers = offsetPBone.bone.layers
        
        if dampedTo:
            if removeAimInfo.constraint == None:
                removeAimInfo.constraint = dampedTo

            aimTargetBoneN = dampedTo.subtarget

            removeAimInfo.aimTargetBoneN = aimTargetBoneN

            aimTargetPBone = obj.pose.bones[aimTargetBoneN]
            pboneKeyframeClearList.append(aimTargetPBone)

        bonesToBakeInfo[pbone] = [[aimTargetPBone, rotfBake.Channel.locationXYZ, rotfBake.Channel.rotationQE]]

    rotfBake.Bake(bonesToBakeInfo)

    rotfBake.KeyframeClear(pboneKeyframeClearList)

    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')

    #remove aim target bones
    for removeAimInfo in removeAimInfoList:
        armature = removeAimInfo.object.data
        
        offsetEBone = armature.edit_bones.get(removeAimInfo.offsetBoneN)
        if offsetEBone:
            armature.edit_bones.remove(offsetEBone)

        aimTargetEBone = armature.edit_bones.get(removeAimInfo.aimTargetBoneN)
        if aimTargetEBone:
            armature.edit_bones.remove(aimTargetEBone)
    
    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')

    for removeAimInfo in removeAimInfoList:
        obj = removeAimInfo.object
        boneN = removeAimInfo.boneN
        pbone = obj.pose.bones[boneN]
        pbone.constraints.remove(removeAimInfo.constraint)
        if removeAimInfo.offsetBoneN:
            rigState.RemoveConstraint(obj, "Aim Offset Space|"+ removeAimInfo.boneN)
        else:
            rigState.RemoveConstraint(obj, "Aim Space|"+ removeAimInfo.boneN)
        pbone.custom_shape = pbone.rotf_previous_shape