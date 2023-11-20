#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . import duplicateBone
from . import removeConstraints
from . import rigState
from . import importControllerShapes
from . import rotfBake

class ParentSpaceConstraint:

    def __init__(self):
        print('Parent Space Constraint')

    def CreateParentSpaceConstraint(parentSettingsList):        
        parentSettingsList, bonesToBakeInfo, duplicatePBoneList = SetupParentSpaceControllers(parentSettingsList)
        
        rotfBake.Bake(bonesToBakeInfo) #bake parent space bone
        
        removeConstraints.RemoveAllRotFConstraints(duplicatePBoneList) #remove constraints from parent space bones
        
        SetupParentSpaceBehaviour(parentSettingsList) 
        
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
                errorMessageList.append("Parent Constraint|Bone not found: " + obj.name + "[" + targetBoneN + "]")
                continue

            parentObjectName = constraintInfo['string_list'][0]
            parentObject = bpy.data.objects.get(parentObjectName)
            if parentObject == None: #check if parent object exists. if not, skips
                errorMessageList.append("Parent Constraint|Object not found: " + parentObjectName)
                continue
            parentSettings.parentObject = parentObject                
            
            targetParentBoneN = constraintInfo['string_list'][1]
            if parentObject.data.bones.get(targetParentBoneN) == None: #check if target bone exists. if not, skips
                errorMessageList.append("Parent Constraint|Bone not found: " + parentObjectName + "[" + targetBoneN + "]")
                continue
            parentSettings.targetParentBoneN = targetParentBoneN
            
            parentSettings.parentCopy = constraintInfo['bool_list'][0]

            parentSettingsList.append(parentSettings)

        ParentSpaceConstraint.CreateParentSpaceConstraint(parentSettingsList)

        if errorMessageList:
            return errorMessageList

class ParentSettings:
    def __init__(self):
        self.targetObject = None
        self.targetBoneN = str()

        self.parentObject = None
        self.targetParentBoneN = str()

        self.parentCopy = bool()

        self.parentBoneN = str()
        self.childBoneN = str()

def SetupParentSpaceControllers(parentSettingsList):
    bonesToBakeInfo = dict()

    #select parent objects if they were not already selected so that they can change mode
    for parentSettings in parentSettingsList:
        parentSettings.parentObject.select_set(True)

    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.context.object.data.use_mirror_x = False

    existingParentCopyNList = list()
    for parentSettings in parentSettingsList:
        obj = parentSettings.targetObject
        parentCopy = parentSettings.parentCopy

        targetParentBoneN = parentSettings.targetParentBoneN
        parentObj = parentSettings.parentObject
        parentArmature = parentObj.data
        targetParentEBone = parentArmature.edit_bones[targetParentBoneN]
        
        armature = obj.data
        targetEBone = armature.edit_bones[parentSettings.targetBoneN]
        
        if parentCopy: #if parent copy is true
            if obj.name +"|ParentCopy."+targetParentBoneN in existingParentCopyNList: #if the parent copy bone already exists in the armature
                parentSettings.parentBoneN = "ParentCopy."+targetParentBoneN
            else: #if no parent copy bone in armature, create one
                newParentBones, newParentEditBones, newParentBoneNames = duplicateBone.DuplicateBone("ParentCopy.", [targetParentEBone])
                newParentBoneE = newParentEditBones[0]
                newParentBoneE.parent = None #remove parent from parent copy bone

                parentSettings.parentBoneN = newParentBoneNames[0]

                existingParentCopyNList.append(obj.name +"|ParentCopy."+targetParentBoneN) #add this string to existingParetnCopyList to prevent more than one ParentCopy bone

        elif armature != parentArmature: #if target parent bone is from another armature, add a parentCopy to the child object
            if obj.name +"|ParentCopy."+targetParentBoneN in existingParentCopyNList: #if the parent copy bone already exists in the armature
                parentSettings.parentBoneN = "ParentCopy."+targetParentBoneN
            else: #if no parent copy bone in armature, create one 
                newParentBoneE = armature.edit_bones.new("ParentCopy." + targetParentBoneN)
                newParentBoneE.length = parentArmature.edit_bones[targetParentBoneN].length
                newParentBoneE.use_deform = False
                newParentBoneN = newParentBoneE.name

                parentSettings.parentBoneN = newParentBoneN

                existingParentCopyNList.append(obj.name +"|ParentCopy."+targetParentBoneN) #add this string to existingParetnCopyList to prevent more than one ParentCopy bone
        else:
            parentSettings.parentBoneN = targetParentBoneN

        newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBone("Child.", [targetEBone])
        parentSettings.childBoneN = newBoneNames[0]

        #assign the appropriate parent to the new child bone
        for ebone in newEditBones:
            if armature != parentArmature or parentCopy:
                ebone.parent = newParentBoneE
            else:
                ebone.parent = targetParentEBone

    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')
    
    createdPBoneList = list()
    for parentSettings in parentSettingsList:
        obj = parentSettings.targetObject
        parentCopy = parentSettings.parentCopy

        targetParentBoneN = parentSettings.targetParentBoneN
        parentObj = parentSettings.parentObject

        targetPBone = obj.pose.bones[parentSettings.targetBoneN]
        childPBone = obj.pose.bones[parentSettings.childBoneN]

        #list selected bones and duplicated bones separately to assign bone groups
        pboneList = list()
        newPBoneList = list() #list duplicated bones in pose mode

        pboneList.append(targetPBone)
        newPBoneList.append(childPBone)

        #if parent copy is true or if the target parent bone is from another armature
        if parentSettings.parentCopy or parentSettings.parentObject != parentSettings.targetObject:
            if parentSettings.parentCopy and parentSettings.parentObject != parentSettings.targetObject:
                parentPBone = parentSettings.parentObject.pose.bones[parentSettings.parentBoneN]
            else:
                parentPBone = parentSettings.targetObject.pose.bones[parentSettings.parentBoneN]
            #have parent copy bone copy target parent bone's transforms
            if 'COPY_TRANSFORMS' not in parentPBone.constraints:
                copyTransforms = parentPBone.constraints.new('COPY_TRANSFORMS')
                copyTransforms.name += " RotF"
                copyTransforms.target = parentSettings.parentObject
                copyTransforms.subtarget = parentSettings.targetParentBoneN

        if parentSettings.parentCopy:
            targetParentPBone = parentSettings.parentObject.pose.bones[parentSettings.targetParentBoneN]
            bonesToBakeInfo[parentPBone] = [
                [targetParentPBone, rotfBake.Channel.locationXYZ, rotfBake.Channel.locationXYZ],
                [targetParentPBone, rotfBake.Channel.rotationQE, rotfBake.Channel.rotationQE],
                [targetParentPBone, rotfBake.Channel.scaleXYZ, rotfBake.Channel.scaleXYZ]
                ]
            pboneList.append(targetParentPBone)
            newPBoneList.append(parentPBone)

            parentBone_customShape = bpy.context.scene.rotf_parentSpace_customShape
            if parentBone_customShape == None:
                importControllerShapes.ImportControllerShapes(["RotF_Octagon"])
                parentPBone.custom_shape = bpy.data.objects['RotF_Octagon']
            else:
                parentPBone.custom_shape = bpy.data.objects[parentBone_customShape.name]

        #assign bone groups to duplicated bones
        duplicateBone.AssignPoseBoneGroups(pboneList, newPBoneList)
        
        #assign controller shape to parentPbone
        targetPbone = obj.pose.bones[parentSettings.targetBoneN]
        childPBone = obj.pose.bones[parentSettings.childBoneN]

        parentBone_customShape = bpy.context.scene.rotf_parentSpace_customShape
        if parentBone_customShape == None:
            importControllerShapes.ImportControllerShapes(["RotF_Octagon"])
            childPBone.custom_shape = bpy.data.objects['RotF_Octagon']
        else:
            childPBone.custom_shape = bpy.data.objects[parentBone_customShape.name]
        
        #have children space bone copy target bone's transforms
        copyTransforms = childPBone.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " RotF"
        copyTransforms.target = obj
        copyTransforms.subtarget = targetPbone.name

        bonesToBakeInfo[childPBone] = [
            [targetPbone, rotfBake.Channel.locationXYZ, rotfBake.Channel.locationXYZ],
            [targetPbone, rotfBake.Channel.rotationQE, rotfBake.Channel.rotationQE],
            [targetPbone, rotfBake.Channel.scaleXYZ, rotfBake.Channel.scaleXYZ]
            ]

        createdPBoneList.extend(newPBoneList)
    return parentSettingsList, bonesToBakeInfo, createdPBoneList

def SetupParentSpaceBehaviour(parentSettingsList):
    for parentSettings in parentSettingsList:
        obj = parentSettings.targetObject
        parentCopy = parentSettings.parentCopy

        targetParentBoneN = parentSettings.targetParentBoneN
        parentObj = parentSettings.parentObject

        targetBoneN = parentSettings.targetBoneN
        targetPBone = obj.pose.bones[targetBoneN]

        childBoneN = parentSettings.childBoneN
        childPBone = obj.pose.bones[childBoneN]

        rotfBake.KeyframeClear([targetPBone]) #remove keys on the target bones as they follow the world space bones

        #have target bone copy world space bone's transforms
        copyTransforms = targetPBone.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " RotF"
        copyTransforms.target = obj
        copyTransforms.subtarget = childBoneN

        #move non relevant bones to unused layer
        unusedLayer = obj.unusedRigBonesLayer
        targetBone = targetPBone.bone
        targetBone.layers[unusedLayer]=True
        for layer in range(32):
            if layer == unusedLayer:
                continue
            else:
                targetBone.layers[layer]=False

        newPointer = childPBone.bone.rotf_pointer_list.add()
        newPointer.name = "CHILD"
        newPointer.armature_object = obj
        newPointer.bone_name = targetBoneN

        rigState.AddConstraint(
                obj,
                "Parent Space|" + targetBoneN,
                "Parent Space|" + targetBoneN + "|" + parentObj.name + "|" + targetParentBoneN,
                "Parent Space",
                [targetBoneN],
                [parentCopy],
                [parentObj.name, targetParentBoneN],
                [0], #is not used
                [0.0] #is not used
                )

def ParentSpace(parentCopy):
    targetParentPBone = bpy.context.active_pose_bone
    targetParentBoneN = targetParentPBone.name
    parentObject = targetParentPBone.id_data
    childrenPboneList = bpy.context.selected_pose_bones
    
    parentSettingsList = list()
    for childPBone in childrenPboneList:
        if childPBone != targetParentPBone:
            parentSettings = ParentSettings()
            parentSettings.targetObject = childPBone.id_data
            parentSettings.targetBoneN = childPBone.name
            parentSettings.parentObject = parentObject
            parentSettings.targetParentBoneN = targetParentBoneN
            parentSettings.parentCopy = parentCopy

            parentSettingsList.append(parentSettings)
    
    parentSettingsList = ParentSpaceConstraint.CreateParentSpaceConstraint(parentSettingsList)

    #end script with parent bone controller selected
    bpy.ops.pose.select_all(action='DESELECT')
    if parentCopy:
        parentBoneN = "ParentCopy."+ targetParentBoneN
    else:
        parentBoneN = targetParentBoneN
    parentPBone = parentObject.pose.bones[parentBoneN]
    parentPBone.bone.select = True

def RemoveParentSpace():
    #filter selection, keeping only targetPoseBonesWithWorld
    targetPoseBonesWithParent = list()
    for pbone in bpy.context.selected_pose_bones:
        if 'CHILD' in pbone.bone.rotf_pointer_list:
            obj = pbone.bone.rotf_pointer_list['CHILD'].armature_object
            bonename = pbone.bone.rotf_pointer_list['CHILD'].bone_name

            targetBoneP = obj.pose.bones[bonename]
            if targetBoneP not in targetPoseBonesWithParent:
                targetPoseBonesWithParent.append(targetBoneP)
    
    #remove PARENT from targetPoseBonesWithParent
    RemoveParent(targetPoseBonesWithParent)
    
    #end with only the targetPoseBonesWithIK selected
    bpy.ops.pose.select_all(action='DESELECT')
    for pbone in targetPoseBonesWithParent:
        pbone.bone.select = True

def RemoveSiblingsParentSpace():
    #filter selection, keeping only targetPoseBonesWithParent
    parentPBoneList = list()
    for pbone in bpy.context.selected_pose_bones:
        if 'CHILD' in pbone.bone.rotf_pointer_list:
            parentPBoneList.append(pbone.parent)

    targetPoseBonesWithParent = list()
    for parentPBone in parentPBoneList:
        for childPBone in parentPBone.children:
            if 'CHILD' in childPBone.bone.rotf_pointer_list:
                obj = childPBone.bone.rotf_pointer_list['CHILD'].armature_object
                bonename = childPBone.bone.rotf_pointer_list['CHILD'].bone_name

                targetBoneP = obj.pose.bones[bonename]
                if targetBoneP not in targetPoseBonesWithParent:
                    targetPoseBonesWithParent.append(targetBoneP)
        
    #remove PARENT from targetPoseBonesWithParent
    RemoveParent(targetPoseBonesWithParent)
    
    #end with only the targetPoseBonesWithIK selected
    bpy.ops.pose.select_all(action='DESELECT')
    for pbone in targetPoseBonesWithParent:
        pbone.bone.select = True

def RemoveParent(targetPoseBonesWithParent):
    bonesToBakeInfo = dict()
    copyTransformsConstraintList = list()
    childrenPBoneList = list()
    childrenBoneList = list()
    parentPBoneList = list()
    for targetBoneP in targetPoseBonesWithParent:
        obj = targetBoneP.id_data
        armature = obj.data

        if "Copy Transforms RotF" in targetBoneP.constraints:
            copyTransforms = targetBoneP.constraints["Copy Transforms RotF"]
            childTargetBoneN = copyTransforms.subtarget
            childTargetPBone = obj.pose.bones[childTargetBoneN]
            
            copyTransformsConstraintList.append(copyTransforms)
            childrenPBoneList.append(childTargetPBone)
            childrenBoneList.append(childTargetPBone.bone)
        for layer in range(32):
            targetBoneP.bone.layers[layer] = childTargetPBone.bone.layers[layer]

        bonesToBakeInfo[targetBoneP] = [
                [childTargetPBone, rotfBake.Channel.locationXYZ, rotfBake.Channel.locationXYZ],
                [childTargetPBone, rotfBake.Channel.rotationQE, rotfBake.Channel.rotationQE],
                [childTargetPBone, rotfBake.Channel.scaleXYZ, rotfBake.Channel.scaleXYZ],
                [childTargetPBone.parent, rotfBake.Channel.locationRotationQE, rotfBake.Channel.locationRotationQE],
                [childTargetPBone.parent, rotfBake.Channel.scaleXYZ, rotfBake.Channel.scaleXYZ]
                ]

        if childTargetPBone.parent not in parentPBoneList:
            parentPBoneList.append(childTargetPBone.parent)
    
    parentPBonesToRemove = list()
    parentBonesToRemove = list()
    for parentPBone in parentPBoneList:
        if "ParentCopy." in parentPBone.name:
            parentBoneShouldBeRemoved = True
            for childPBone in parentPBone.children:
                if childPBone not in childrenPBoneList:
                    parentBoneShouldBeRemoved = False
            if parentBoneShouldBeRemoved:
                parentPBonesToRemove.append(parentPBone)
                parentBonesToRemove.append(parentPBone.bone)

    rotfBake.Bake(bonesToBakeInfo)

    rotfBake.KeyframeClear(childrenPBoneList + parentPBonesToRemove)

    for targetBoneP, copyTransforms in zip(targetPoseBonesWithParent, copyTransformsConstraintList):
        targetBoneP.constraints.remove(copyTransforms) #remove copy transforms constraint from target bone

    bonesToRemove = childrenBoneList + parentBonesToRemove
    #force edit mode to remove World bones
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in bonesToRemove:
        armature = bone.id_data
        boneN = bone.name
        try:
            armature.edit_bones.remove(armature.edit_bones[boneN])
        except:
            print(boneN)

    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    for targetBoneP in targetPoseBonesWithParent:
        rigState.RemoveConstraint(obj, "Parent Space|"+ targetBoneP.name)
        rigState.RemoveConstraint(obj, "Parent Offset Space|"+ targetBoneP.name)

