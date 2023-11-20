#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from mathutils import Matrix
from . import duplicateBone
from . import removeConstraints
from . import rigState
from . import importControllerShapes
from . import rotfBake

class ParentOffsetSpaceConstraint:

    def __init__(self):
        print('Parent Offset Space Constraint')

    def CreateParentOffsetSpaceConstraint(parentSettingsList):        
        parentSettingsList, bonesToBakeInfo, parentPBoneList = SetupParentOffsetSpaceControllers(parentSettingsList)
        
        rotfBake.Bake(bonesToBakeInfo) #bake parent space bone
        
        removeConstraints.RemoveAllRotFConstraints(parentPBoneList) #remove constraints from parent space bones
        
        SetupParentOffsetSpaceBehaviour(parentSettingsList) 
        
        return parentSettingsList

    def CreateConstraint(self, obj, constraintInfoList):
        parentSettingsList = list()
        errorMessageList = list()
        for constraintInfo in constraintInfoList:
            parentSettings = ParentSettings()
            parentSettings.targetObject = obj
            targetBoneN = constraintInfo['bone_list'][0]
            parentSettings.targetBoneN = targetBoneN

            if obj.data.bones.get(constraintInfo['bone_list'][0]) == None: #check if target bone exists. if not, skips
                errorMessageList.append("Parent Offset Constraint|Bone not found: " + obj.name + "[" + targetBoneN + "]")
                continue

            #convert float list to matrix
            matrixAsList = constraintInfo['float_list']
            parentOffsetMatrix = Matrix(list(chunks(matrixAsList, 4)))

            parentSettings.parentOffsetMatrix = parentOffsetMatrix

            parentSettingsList.append(parentSettings)

        ParentOffsetSpaceConstraint.CreateParentOffsetSpaceConstraint(parentSettingsList)

        if errorMessageList:
            return errorMessageList

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
        
class ParentSettings:
    def __init__(self):
        self.targetObject = None
        self.targetBoneN = str()

        self.parentBoneN = str()
        self.childBoneN = str()
        self.tempBoneN = str()

        self.parentOffsetMatrix = None #matrix for the aim target

def SetupParentOffsetSpaceControllers(parentSettingsList):
    bonesToBakeInfo = dict()

    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.context.object.data.use_mirror_x = False

    for parentSettings in parentSettingsList:
        obj = parentSettings.targetObject        
        armature = obj.data
        boneN = parentSettings.targetBoneN
        ebone = armature.edit_bones[boneN]
        
        #create the parent bone and place it at the matrix offset
        parentEBone = armature.edit_bones.new("ParentCopy."+boneN)
        parentEBone.layers = ebone.layers
        parentEBone.matrix = ebone.matrix @ parentSettings.parentOffsetMatrix #cursor position tranformed from pose mode to edit mode
        parentEBone.tail = parentEBone.head + ebone.tail - ebone.head #get the same orientation as the target bone
        parentEBone.roll = ebone.roll
        parentEBone.use_deform = False

        parentSettings.parentBoneN = parentEBone.name

        #create the temp bone and place it at the matrix offset with target bone as it's parent
        tempEBone = armature.edit_bones.new("Temp."+boneN)
        tempEBone.matrix = parentEBone.matrix
        tempEBone.tail = parentEBone.tail
        tempEBone.parent = ebone

        parentSettings.tempBoneN = tempEBone.name

        #create the child bone and parent it to the parent bone
        newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBone("Child.", [ebone])
        childEBone = newEditBones[0]
        childEBone.parent = parentEBone

        parentSettings.childBoneN = childEBone.name

    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')
    
    parentPBoneList = list()
    for parentSettings in parentSettingsList:
        obj = parentSettings.targetObject

        pbone = obj.pose.bones[parentSettings.targetBoneN]
        parentPBone = obj.pose.bones[parentSettings.parentBoneN]
        tempPBone = obj.pose.bones[parentSettings.tempBoneN]
        childPBone = obj.pose.bones[parentSettings.childBoneN]

        #assign bone groups to duplicated bones
        duplicateBone.AssignPoseBoneGroups([pbone, pbone], [parentPBone, childPBone])

        parentBone_customShape = bpy.context.scene.rotf_parentSpace_customShape
        if parentBone_customShape == None:
            importControllerShapes.ImportControllerShapes(["RotF_Octagon"])
            parentPBone.custom_shape = bpy.data.objects['RotF_Octagon']
            childPBone.custom_shape = bpy.data.objects['RotF_Octagon']
        else:
            parentPBone.custom_shape = parentBone_customShape #bpy.data.objects[parentBone_customShape.name]
            childPBone.custom_shape = parentBone_customShape #bpy.data.objects[parentBone_customShape.name]
        
        #have children space bone copy target bone's transforms
        copyTransforms = parentPBone.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " RotF"
        copyTransforms.target = obj
        copyTransforms.subtarget = tempPBone.name

        bonesToBakeInfo[parentPBone] = [
            [pbone, rotfBake.Channel.locationXYZ, rotfBake.Channel.locationXYZ],
            [pbone, rotfBake.Channel.rotationQE, rotfBake.Channel.rotationQE],
            [pbone, rotfBake.Channel.scaleXYZ, rotfBake.Channel.scaleXYZ]
            ]

        parentPBoneList.append(parentPBone)
    return parentSettingsList, bonesToBakeInfo, parentPBoneList

def SetupParentOffsetSpaceBehaviour(parentSettingsList):
    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    for parentSettings in parentSettingsList:
        obj = parentSettings.targetObject
        armature = obj.data
        tempEBone = armature.edit_bones.get(parentSettings.tempBoneN)
        if tempEBone:
            armature.edit_bones.remove(tempEBone)

    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')
    for parentSettings in parentSettingsList:
        obj = parentSettings.targetObject
        boneN = parentSettings.targetBoneN
        pbone = obj.pose.bones[boneN]

        childBoneN = parentSettings.childBoneN
        childPBone = obj.pose.bones[childBoneN]

        rotfBake.KeyframeClear([pbone]) #remove keys on the target bones as they follow the world space bones

        #have target bone copy world space bone's transforms
        copyTransforms = pbone.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " RotF"
        copyTransforms.target = obj
        copyTransforms.subtarget = childBoneN

        #move non relevant bones to unused layer
        unusedLayer = obj.unusedRigBonesLayer
        pbone.bone.layers[unusedLayer]=True
        for layer in range(32):
            if layer == unusedLayer:
                continue
            else:
                pbone.bone.layers[layer]=False

        newPointer = childPBone.bone.rotf_pointer_list.add()
        newPointer.name = "CHILD"
        newPointer.armature_object = obj
        newPointer.bone_name = boneN

        #parentPBone = obj.pose.bones[parentSettings.parentBoneN]
        #newPointer = parentPBone.bone.rotf_pointer_list.add()
        #newPointer.name = "CHILD"
        #newPointer.armature_object = obj
        #newPointer.bone_name = boneN

        #turn parent offset matrix into a list of floats to save into the rig state
        matrixInListForm = list()
        for row in parentSettings.parentOffsetMatrix:
            for i in row:
                matrixInListForm.append(i)

        rigState.AddConstraint(
                obj,
                "Parent Offset Space|" + boneN,
                "Parent Offset Space|" + boneN,
                "Parent Offset Space",
                [boneN],
                [True], #is not used
                [""], #is not used
                [0], #is not used
                matrixInListForm
                )

def ParentOffsetSpace():
    cursorMatrix = bpy.context.scene.cursor.matrix
    parentSettingsList = list()

    for pbone in bpy.context.selected_pose_bones:
        parentSettings = ParentSettings()
        parentSettings.targetObject = pbone.id_data
        parentSettings.targetBoneN = pbone.name

        #find the offset matrix between the bone and the 3D cursor
        pboneInverseMatrix = pbone.matrix.copy()
        pboneInverseMatrix.invert()

        objectMatrixInvert= pbone.id_data.matrix_world.copy()
        objectMatrixInvert.invert()

        localCM = objectMatrixInvert @ cursorMatrix

        offsetMatrix = pboneInverseMatrix @ localCM

        parentSettings.parentOffsetMatrix = offsetMatrix

        parentSettingsList.append(parentSettings)
    
    parentSettingsList = ParentOffsetSpaceConstraint.CreateParentOffsetSpaceConstraint(parentSettingsList)

    #end script with parent bone controller selected
    bpy.ops.pose.select_all(action='DESELECT')
    for parentSettings in parentSettingsList:
        obj = parentSettings.targetObject
        parentBoneN = parentSettings.parentBoneN
        parentPBone = obj.pose.bones[parentBoneN]
        parentPBone.bone.select = True