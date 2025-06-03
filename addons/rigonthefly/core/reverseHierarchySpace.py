#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . import duplicateBone
from . import boneCollections
from . import removeConstraints
from . import rigState
from . import importControllerShapes
from . import rotfBake

class ReverseHierarchySpaceConstraint:

    def __init__(self):
        print('Reorder Hierarchy Constraint')

    def CreateReverseHierarchySpaceConstraint(hierarchySettings):

        hierarchySettings, bonesToBakeInfo, duplicatedPBoneList = SetupReverseHierarchySpaceControllers(hierarchySettings)
        
        rotfBake.Bake(bonesToBakeInfo) #bake reverse hierarchy controls
        
        removeConstraints.RemoveAllRotFConstraints(duplicatedPBoneList) #remove constraints from parent space bones
        
        SetupReverseHierarchySpaceBehaviour(hierarchySettings) 
        
        return hierarchySettings

    def CreateConstraint(self, obj, constraintInfoList):
        hierarchySettingsList = list()
        errorMessageList = list()
        for constraintInfo in constraintInfoList:
            hierarchySettings = HierarchySettings()
            hierarchySettings.targetObject = obj
            targetBoneN = constraintInfo['bone_list'][0]

            if obj.data.bones.get(constraintInfo['bone_list'][0]) == None: #check if target bone exists. if not, skips
                errorMessageList.append("Reverse Constraint|Bone not found: " + obj.name + "[" + targetBoneN + "]")
                continue

            hierarchySettings.targetBoneN = targetBoneN

            hierarchySettingsList.append(hierarchySettings)

        ReverseHierarchySpaceConstraint.CreateReverseHierarchySpaceConstraint(hierarchySettings)

        if errorMessageList:
            return errorMessageList

class HierarchySettings:
    def __init__(self):
        self.targetObject = None
        self.targetBoneN = str()

        self.targetBoneNList = list()
        self.offsetBoneNList = list()
        self.orderedBoneNList = list()

def SetupReverseHierarchySpaceControllers(hierarchySettings):
    bonesToBakeInfo = dict()

    duplicatedPBoneList = list()

    obj = hierarchySettings.targetObject

    targetBoneN = hierarchySettings.targetBoneN
    targetPBone = obj.pose.bones[targetBoneN]
    hierarchySettings.targetBoneNList.append(targetBoneN)
    pbone = targetPBone
    while pbone.parent:
        if pbone.parent.constraints:
            for constraint in pbone.parent.constraints:
                if constraint.type in ['COPY_TRANSFORMS','COPY_LOCATION','COPY_ROTATION','COPY_SCALE']:
                    if constraint.target == obj:
                        boneN = constraint.subtarget
                        hierarchySettings.targetBoneNList.append(boneN)
                        pbone = obj.pose.bones[boneN]
                    break
                else:
                    hierarchySettings.targetBoneNList.append(pbone.parent.name)
                    pbone = pbone.parent
        else:
            hierarchySettings.targetBoneNList.append(pbone.parent.name)
            pbone = pbone.parent

    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    mirrorX = bpy.context.object.data.use_mirror_x
    bpy.context.object.data.use_mirror_x = False

    #for hierarchySettings in hierarchySettingsList:
    obj = hierarchySettings.targetObject
    armature = obj.data
    ebones = armature.edit_bones

    targetEBoneList = list()
    for targetBoneN in hierarchySettings.targetBoneNList:
        targetEBoneList.append(ebones[targetBoneN])

    offsetBoneList, offsetEBoneList, offsetBoneNList = duplicateBone.DuplicateBones("Offset.", targetEBoneList[1:])
    hierarchySettings.offsetBoneNList = offsetBoneNList

    orderedBoneList, orderedEBoneList, orderedBoneNList = duplicateBone.DuplicateBones("Reverse.", targetEBoneList)
    hierarchySettings.orderedBoneNList = orderedBoneNList

    orderedEBoneList[0].parent = None #remove parent of the first bone of the new hierarchy
    orderedEBoneList[0].length *= 1.4
    
    #reorder the ordered bone hierarchy in order of the selection list
    for i, orderedEBone in enumerate(orderedEBoneList[1:]):
        orderedEBone.matrix = targetEBoneList[i].matrix
        orderedEBone.tail = targetEBoneList[i].tail
        orderedEBone.parent = orderedEBoneList[i]
        offsetEBoneList[i].parent = orderedEBoneList[i+1]

    bpy.context.object.data.use_mirror_x = mirrorX
    
    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')

    #for hierarchySettings in hierarchySettingsList:
    obj = hierarchySettings.targetObject
    pbones = obj.pose.bones

    targetPBoneList = list()
    orderedPBoneList = list()
    offsetPBoneList = list()

    for i, orderedBoneN in enumerate(hierarchySettings.orderedBoneNList):
        orderedPBone = pbones[orderedBoneN]
        orderedPBoneList.append(orderedPBone)

        if i == 0:
            targetPBone = pbones[hierarchySettings.targetBoneNList[i]]
        else:
            targetPBone = pbones[hierarchySettings.targetBoneNList[i-1]]
        
        #have the bone follow the target bone
        copyTransforms = orderedPBone.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " RotF"
        copyTransforms.target = obj
        copyTransforms.subtarget = targetPBone.name

        #assign controller shape to reordered hierarchy bones
        offset_customShape = bpy.context.scene.rotf_reverseHierarchySpace_customShape
        if offset_customShape == None:
            importControllerShapes.ImportControllerShapes(["RotF_Octagon"])
            orderedPBone.custom_shape = bpy.data.objects['RotF_Octagon']
        else:
            orderedPBone.custom_shape = bpy.data.objects[offset_customShape.name]

        duplicatedPBoneList.append(orderedPBone)
        
        bonesToBakeInfo[orderedPBone] = [targetPBone]

        if i < len(hierarchySettings.offsetBoneNList):
            offsetPBone = pbones[hierarchySettings.offsetBoneNList[i]]
            targetPBone = pbones[hierarchySettings.targetBoneNList[i+1]]
            #have the bone follow the target bone
            copyTransforms = offsetPBone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.name += " RotF"
            copyTransforms.target = obj
            copyTransforms.subtarget = targetPBone.name

            duplicatedPBoneList.append(offsetPBone)
            offsetPBoneList.append(offsetPBone)

            bonesToBakeInfo[offsetPBone] = [targetPBone]
    
    for targetBoneN in hierarchySettings.targetBoneNList:
        targetPBoneList.append(pbones[targetBoneN])
        
    duplicateBone.AssignPoseBoneGroups(targetPBoneList, orderedPBoneList)
    duplicateBone.AssignPoseBoneGroups(targetPBoneList[1:], offsetPBoneList)

    for orderedPBone in orderedPBoneList:
        orderedPBone.bone.use_inherit_rotation = True
    for offsetPBone in offsetPBoneList:
        offsetPBone.bone.use_inherit_rotation = True
    
    return hierarchySettings, bonesToBakeInfo, duplicatedPBoneList

def SetupReverseHierarchySpaceBehaviour(hierarchySettings):
    #for hierarchySettings in hierarchySettingsList:
    obj = hierarchySettings.targetObject
    pbones = obj.pose.bones
    unusedLayer = obj.unusedRigBonesLayer

    for i, targetBoneN in enumerate(hierarchySettings.targetBoneNList):
        targetPBone = pbones[targetBoneN]

        orderedBoneN = hierarchySettings.orderedBoneNList[i]
        orderedPBone = pbones[orderedBoneN]

        #have the bone follow the target bone
        copyTransforms = targetPBone.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " Reverse RotF"
        copyTransforms.target = obj
        if i == 0:
            copyTransforms.subtarget = orderedBoneN
        else:
            offsetBoneN = hierarchySettings.offsetBoneNList[i-1]
            offsetPBone = pbones[offsetBoneN]
            copyTransforms.subtarget = offsetBoneN

            for boneN in hierarchySettings.targetBoneNList:
                newPointer = offsetPBone.bone.rotf_pointer_list.add()
                newPointer.name = "REVERSE"
                newPointer.armature_object = obj
                newPointer.bone_name = boneN
        
        appVersion = bpy.app.version
        if appVersion[0] == 4:

            boneCollections.AddBoneToCollections(targetPBone.bone, [boneCollections.RotFUnusedColName])
            #boneCollections.UnassignBoneFromCollections(targetPBone.bone, [boneCollections.RotFAnimationColName])
            targetPBone.bone.hide = True
            if i != 0:
                boneCollections.AddBoneToCollections(offsetPBone.bone, [boneCollections.RotFUnusedColName])
                boneCollections.UnassignBoneFromCollections(offsetPBone.bone, [boneCollections.RotFAnimationColName])
                offsetPBone.bone.hide = True
            
        elif appVersion[0] == 3:
            targetPBone.bone.layers[unusedLayer]=True
            if i != 0:
                offsetPBone.bone.layers[unusedLayer] = True
                
            for layer in range(32):
                if layer != unusedLayer:
                    targetPBone.bone.layers[layer]=False
                    if i != 0:
                        offsetPBone.bone.layers[layer] = False

        for boneN in hierarchySettings.targetBoneNList:
            newPointer = orderedPBone.bone.rotf_pointer_list.add()
            newPointer.name = "REVERSE"
            newPointer.armature_object = obj
            newPointer.bone_name = boneN

        rigState.AddConstraint(
        obj,
        "Reverse Hierarchy Space|" + hierarchySettings.targetBoneN,
        "Reverse Hierarchy Space|" + hierarchySettings.targetBoneN,
        "Reverse Hierarchy Space",
        [hierarchySettings.targetBoneN],
        [True], #is not used
        [""], #is not used
        [0], #is not used
        [0.0] #is not used
        )

def ReverseHierarchySpace():
    #selectedPBoneList = bpy.rotf_pose_bone_selection
    activeObject = bpy.context.object

    #hierarchySettingsList = list()
    #boneNList = list()

    #list bones from the active object in order of selection
    #for selectedPBone in selectedPBoneList:
    #    if selectedPBone.id_data == activeObject:
    #        boneNList.append(selectedPBone.name)

    hierarchySettings = HierarchySettings()
    hierarchySettings.targetObject = activeObject
    hierarchySettings.targetBoneN = bpy.context.active_pose_bone.name

    #.append(hierarchySettings)

    hierarchySettings = ReverseHierarchySpaceConstraint.CreateReverseHierarchySpaceConstraint(hierarchySettings)

    bpy.ops.pose.select_all(action='DESELECT')
    orderedRootBoneN = hierarchySettings.orderedBoneNList[0]
    rootPBone = activeObject.pose.bones.get(orderedRootBoneN)
    if rootPBone:
        rootPBone.bone.select = True

def RestoreHierarchySpace():
    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')

    #targetPBone = None
    targetPBoneList = list()
    #look into the selected bones for the the REVERSE pointer list
    for pbone in bpy.context.selected_pose_bones:
        for bonePointer in pbone.bone.rotf_pointer_list:
            if bonePointer['name'] == "REVERSE":
                targetBoneN = bonePointer['bone_name']
                targetPBone = bonePointer['armature_object'].pose.bones[targetBoneN]
                targetPBoneList.append(targetPBone)
            else:
                break

    RemoveReverseHierarchyConstraint(targetPBoneList)
    
    bpy.ops.pose.select_all(action='DESELECT')
    if targetPBoneList:
        targetPBoneList[0].bone.select = True

def RemoveReverseHierarchyConstraint(targetPBoneList):
    bonesToBakeInfo = dict()

    obj = targetPBoneList[0].id_data

    boneNToRemoveList = list()
    reverseRootPBone = None
    for i, targetPBone in enumerate(targetPBoneList):
        for constraint in targetPBone.constraints:
            if constraint.type == 'COPY_TRANSFORMS' and constraint.target == obj:
                constrainingBoneN = constraint.subtarget
                constrainingPBone = obj.pose.bones[constrainingBoneN]

                if constrainingPBone.bone.rotf_pointer_list.get('REVERSE'):
                    bonesToBakeInfo[targetPBone] = [constrainingPBone]

                    #put target bone to the right layers
                    appVersion = bpy.app.version
                    if appVersion[0] == 4:
                        #boneCollections.AddBoneToCollections(targetPBone.bone, [boneCollections.RotFAnimationColName])
                        targetPBone.bone.hide = False
                        boneCollections.UnassignBoneFromCollections(targetPBone.bone, [boneCollections.RotFUnusedColName])
                        if i == 0:
                            reverseRootPBone = constrainingPBone

                    elif appVersion[0] == 3:
                        if i == 0:
                            targetPBone.bone.layers = constrainingPBone.bone.layers
                            reverseRootPBone = constrainingPBone
                        else:
                            targetPBone.bone.layers = constrainingPBone.parent.bone.layers

    if bpy.context.scene.rotf_no_bake_on_remove == False:
        rotfBake.Bake(bonesToBakeInfo) #bake reverse hierarchy space bones

    #removeConstraints.RemoveAllRotFConstraints(targetPBoneList)
    for targetPBone in targetPBoneList:
        obj = targetPBone.id_data

        rotfConstraints = list()
        for constraint in targetPBone.constraints:
            if "Reverse RotF" in constraint.name:
                rotfConstraints.append(constraint)

        #if there is no animation data on the object, keeptransform from the constraint
        if not obj.animation_data:
            # Get the matrix in world space.
            #bone = context.pose_bone
            mat = obj.matrix_world @ targetPBone.matrix
        for constraint in rotfConstraints:
            constraint.influence = 0.0
        #set matrix
        if not obj.animation_data:
            targetPBone.matrix = obj.matrix_world.inverted() @ mat

        while rotfConstraints:
            targetPBone.constraints.remove(rotfConstraints[0])
            rotfConstraints.remove(rotfConstraints[0])

    #pbones = obj.pose.bones
    reversedPBoneHierarchyList = [reverseRootPBone] + reverseRootPBone.children_recursive
    for targetPBone in reversedPBoneHierarchyList:
        boneNToRemoveList.append(targetPBone.name)

    rotfBake.KeyframeClear(reversedPBoneHierarchyList)

    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')

    ebones = obj.data.edit_bones
    for boneN in boneNToRemoveList:
        ebone = ebones.get(boneN)
        if ebone:
            ebones.remove(ebone)

    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')

    rigState.RemoveConstraint(obj, "Reverse Hierarchy Space|"+ targetPBoneList[0].name)

    return 