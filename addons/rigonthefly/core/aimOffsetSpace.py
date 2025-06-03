#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from mathutils import Matrix, Euler, Vector
from bpy_extras.io_utils import axis_conversion
from . import duplicateBone
from . import boneCollections
from . import removeConstraints
from . import rigState
from . import importControllerShapes
from . import rotfBake


class AimOffsetSpaceConstraint:

    def __init__(self):
        print('Aim Space Constraint')

    def CreateAimOffsetSpaceConstraint(aimSettingsList):
        aimSettingsList, bonesToBakeInfo, duplicatePBoneList = SetupAimOffsetSpaceControllers(aimSettingsList)
        
        rotfBake.Bake(bonesToBakeInfo) #bake aim space bone
        
        removeConstraints.RemoveAllRotFConstraints(duplicatePBoneList) #remove constraints from aim space bones
        
        SetupAimOffsetSpaceBehaviour(aimSettingsList) 
        
        return aimSettingsList

    def CreateConstraint(self, obj, constraintInfoList):
        aimSettingsList = list()
        errorMessageList = list()
        for constraintInfo in constraintInfoList:
            aimSettings = AimOffsetSettings()
            aimSettings.targetObject = obj
            targetBoneN = constraintInfo['bone_list'][0]
            aimSettings.targetBoneN = targetBoneN

            aimSettings.stretch = constraintInfo['bool_list'][0]

            #convert float list to matrix
            matrixAsList = constraintInfo['float_list']
            aimOffsetMatrix = Matrix(list(chunks(matrixAsList, 4)))

            aimSettings.aimOffsetMatrix = aimOffsetMatrix

            if obj.data.bones.get(constraintInfo['bone_list'][0]) == None: #check if target bone exists. if not, skips
                errorMessageList.append("Aim Offset Constraint|Bone not found: " + obj.name + "[" + targetBoneN + "]")
                continue

            aimSettingsList.append(aimSettings)

        AimOffsetSpaceConstraint.CreateAimOffsetSpaceConstraint(aimSettingsList)

        if errorMessageList:
            return errorMessageList

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

class AimOffsetSettings:
    def __init__(self):
        self.targetObject = None
        self.targetBoneN = str()
        self.offsetBoneN = str()
        self.aimTargetBoneN = str()
        self.tempAimTargetBoneN = str()

        self.aimOffsetMatrix = None #matrix for the aim target
        self.stretch = bool()

def SetupAimOffsetSpaceControllers(aimSettingsList):
    bonesToBakeInfo = dict()

    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    mirrorX = bpy.context.object.data.use_mirror_x
    bpy.context.object.data.use_mirror_x = False

    #add aim target and offset bones
    for aimSettings in aimSettingsList:
        obj = aimSettings.targetObject
        armature = obj.data
        boneN = aimSettings.targetBoneN
        ebone = armature.edit_bones[boneN]
        
        aimTargetEBone = armature.edit_bones.new("AimTarget."+boneN)
        
        aimTargetEBone.matrix = ebone.matrix @ aimSettings.aimOffsetMatrix #cursor position tranformed from pose mode to edit mode
        aimTargetEBone.length = ebone.length
        aimTargetEBone.use_deform = False

        aimSettings.aimTargetBoneN = aimTargetEBone.name

        tempAimTargetEBone = armature.edit_bones.new("Temp."+boneN)
        tempAimTargetEBone.matrix = aimTargetEBone.matrix #place tempAimTarget bone at the aimTarget bone's position
        tempAimTargetEBone.parent = ebone #parent tempAimTarget bone to the aiming bone
        tempAimTargetEBone.length = 1.0 #set tempAimTarget bone's length to something other than zero so that it does not get removed for not having length
        tempAimTargetEBone.use_deform = False

        aimSettings.tempAimTargetBoneN = tempAimTargetEBone.name

        newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("AimOffset.", [ebone])
        aimSettings.offsetBoneN = newBoneNames[0]
        aimOffsetEBone = newEditBones[0]

        aimOffsetEBone.tail = aimTargetEBone.head
        aimOffsetEBone.length = ebone.length

    bpy.context.object.data.use_mirror_x = mirrorX
    
    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')
    duplicatePBoneList = list()

    #return aimSettingsList, bonesToBakeInfo, duplicatePBoneList
    for aimSettings in aimSettingsList:
        obj = aimSettings.targetObject
        aimTargetPBone = obj.pose.bones[aimSettings.aimTargetBoneN]
        targetPBone = obj.pose.bones[aimSettings.targetBoneN]
        offsetPBone = obj.pose.bones[aimSettings.offsetBoneN]

        appVersion = bpy.app.version
        if appVersion[0] == 4:
            #for pbone in [targetPBone, aimTargetPBone, offsetPBone]:
            for pbone in [aimTargetPBone, offsetPBone]:
                boneCollections.AddBoneToCollections(pbone.bone, [boneCollections.RotFAnimationColName])
        elif appVersion[0] == 3:
            aimTargetPBone.bone.layers = targetPBone.bone.layers

        duplicatePBoneList.extend([aimTargetPBone, offsetPBone])

        duplicateBone.AssignPoseBoneGroups([targetPBone, targetPBone], [aimTargetPBone, offsetPBone])

        #assign controller shape to offset bone
        offset_customShape = bpy.context.scene.rotf_aimSpace_customShape
        if offset_customShape == None:
            importControllerShapes.ImportControllerShapes(["RotF_CirclePointer"])
            offsetPBone.custom_shape = bpy.data.objects['RotF_CirclePointer']
        else:
            offsetPBone.custom_shape = bpy.data.objects[offset_customShape.name]

        #assign controller shape to aim target bone
        aimTarget_customShape = bpy.context.scene.rotf_aimTarget_customShape
        if aimTarget_customShape == None:
            importControllerShapes.ImportControllerShapes(["RotF_Locator"])
            aimTargetPBone.custom_shape = bpy.data.objects['RotF_Locator']
        else:
            aimTargetPBone.custom_shape = bpy.data.objects[aimTarget_customShape.name]

        #move target bone to the object's unused layer
        unusedLayer = obj.unusedRigBonesLayer

        appVersion = bpy.app.version
        if appVersion[0] == 4:
            targetPBone.bone.hide = True
            boneCollections.AddBoneToCollections(targetPBone.bone, [boneCollections.RotFUnusedColName])
            #boneCollections.UnassignBoneFromCollections(targetPBone.bone, [boneCollections.RotFAnimationColName])
            
        elif appVersion[0] == 3:
            targetPBone.bone.layers[unusedLayer]=True
            for layer in range(32):
                if layer != unusedLayer:
                    targetPBone.bone.layers[layer]=False

        #have the offset bone follow the target bone 
        copyTransforms = offsetPBone.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " RotF"
        copyTransforms.target = obj
        copyTransforms.subtarget = aimSettings.targetBoneN
        copyTransforms.target_space = 'LOCAL_OWNER_ORIENT'
        copyTransforms.owner_space = 'LOCAL'

        #have the aimTarget bone follow the tempAimTarget since it is parented to the target bone
        copyLocation = aimTargetPBone.constraints.new('COPY_LOCATION')
        copyLocation.name += " RotF"
        copyLocation.target = obj
        copyLocation.subtarget = aimSettings.tempAimTargetBoneN

        #prepare bake info for the aim target
        bonesToBakeInfo[offsetPBone] = [targetPBone]
        bonesToBakeInfo[aimTargetPBone] = [targetPBone]

    return aimSettingsList, bonesToBakeInfo, duplicatePBoneList

def SetupAimOffsetSpaceBehaviour(aimSettingsList):
    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    for aimSettings in aimSettingsList:
        obj = aimSettings.targetObject
        armature = obj.data
        tempAimTargetEBone = armature.edit_bones.get(aimSettings.tempAimTargetBoneN)
        if tempAimTargetEBone:
            armature.edit_bones.remove(tempAimTargetEBone)

    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')

    for aimSettings in aimSettingsList:
        obj = aimSettings.targetObject
        targetPBone = obj.pose.bones[aimSettings.targetBoneN]
        offsetPBone = obj.pose.bones[aimSettings.offsetBoneN]
        aimTargetPBone = obj.pose.bones[aimSettings.aimTargetBoneN]

        #have the offset bone follow the target bone 
        copyTransforms = targetPBone.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " RotF"
        copyTransforms.target = obj
        copyTransforms.subtarget = aimSettings.offsetBoneN
        copyTransforms.target_space = 'LOCAL_OWNER_ORIENT'
        copyTransforms.owner_space = 'LOCAL'

        #have offset bone aim at the aim target bone with the Y axis
        dampedTrack = offsetPBone.constraints.new('DAMPED_TRACK')
        dampedTrack.name += " RotF"
        dampedTrack.target = obj
        dampedTrack.subtarget = aimSettings.aimTargetBoneN

        newPointer = offsetPBone.bone.rotf_pointer_list.add()
        newPointer.name = "AIM"
        newPointer.armature_object = obj
        newPointer.bone_name = aimSettings.targetBoneN

        newPointer = aimTargetPBone.bone.rotf_pointer_list.add()
        newPointer.name = "AIM"
        newPointer.armature_object = obj
        newPointer.bone_name = aimSettings.targetBoneN

        #turn aim offset matrix into a list of floats to save into the rig state
        matrixInListForm = list()
        for row in aimSettings.aimOffsetMatrix:
            for i in row:
                matrixInListForm.append(i)

        rigState.AddConstraint(
            obj,
            "Aim Offset Space|" + aimSettings.targetBoneN,
            "Aim Offset Space|" + aimSettings.targetBoneN,
            "Aim Offset Space",
            [aimSettings.targetBoneN],
            [True], #is not used
            [""], #is not used
            [0], #is not used
            matrixInListForm
            )

def AimOffsetSpace():
    cursorMatrix = bpy.context.scene.cursor.matrix
    aimSettingsList = list()

    for pbone in bpy.context.selected_pose_bones:
        aimSettings = AimOffsetSettings()
        aimSettings.targetObject = pbone.id_data
        aimSettings.targetBoneN = pbone.name

        #find the offset matrix between the bone and the 3D cursor
        pboneInverseMatrix = pbone.matrix.copy()
        pboneInverseMatrix.invert()

        objectMatrixInvert= pbone.id_data.matrix_world.copy()
        objectMatrixInvert.invert()

        localCM = objectMatrixInvert @ cursorMatrix

        offsetMatrix = pboneInverseMatrix @ localCM

        aimSettings.aimOffsetMatrix = offsetMatrix

        aimSettingsList.append(aimSettings)

    AimOffsetSpaceConstraint.CreateAimOffsetSpaceConstraint(aimSettingsList)

    #end with only the aim target bones selected
    bpy.ops.pose.select_all(action='DESELECT')
    for aimSettings in aimSettingsList:
        obj = aimSettings.targetObject
        obj.pose.bones[aimSettings.aimTargetBoneN].bone.select = True
