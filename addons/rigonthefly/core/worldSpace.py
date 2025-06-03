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

class WorldSpaceConstraint:

    def __init__(self):
        print('World Space Constraint')

    def CreateWorldSpaceConstraint (pboneList):
                
        wolrdPBoneList, bonesToBakeInfo = SetupWorldSpaceControllers(pboneList)

        rotfBake.Bake(bonesToBakeInfo) #bake world space bones

        removeConstraints.RemoveAllRotFConstraints(wolrdPBoneList) #remove constraints from world space bone

        SetupWorldSpaceBehaviour(pboneList, wolrdPBoneList) 
        
        return wolrdPBoneList

    def CreateConstraint(self, obj, constraintInfoList):
        targetPBoneList = list()
        errorMessageList = list()
        for constraintInfo in constraintInfoList:
            targetBoneN = constraintInfo['bone_list'][0]
            if obj.data.bones.get(targetBoneN) == None: #check if target bone exists. if not, skips
                errorMessageList.append("World Space Constraint|Bone not found: " + obj.name + "[" + targetBoneN + "]")
                continue

            targetPBone = obj.pose.bones[targetBoneN]
            targetPBoneList.append(targetPBone)

        WorldSpaceConstraint.CreateWorldSpaceConstraint(targetPBoneList)

        if errorMessageList:
            return errorMessageList

def SetupWorldSpaceControllers(pboneList):
    bonesToBakeInfo = dict()

    boneList = list()
    objectList = list()
    for pbone in pboneList:
        boneList.append(pbone.bone)
        objectList.append(pbone.id_data)

    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    mirrorX = bpy.context.object.data.use_mirror_x
    bpy.context.object.data.use_mirror_x = False

    eboneList = list()
    for bone in boneList:
        armature = bone.id_data
        eboneList.append(armature.edit_bones[bone.name])

    newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("World.", eboneList)

    for obj, editBone, newEditBone in zip(objectList, eboneList, newEditBones):
        newEditBone.parent = None
        newEditBone.use_connect = False

        #find the matrix coordinates of the armature object
        armatureMatrix = obj.matrix_world
        #invert armature's matrix to find where global(0,0,0) is in relation to the armature's position/roation
        armatureMatrixInvert= armatureMatrix.copy()
        armatureMatrixInvert.invert()
        #set aim bone position to global (0,0,0) with axis following world's
        newEditBone.matrix = armatureMatrixInvert

        newEditBone.length = editBone.length

    bpy.context.object.data.use_mirror_x = mirrorX
    
    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')
    newPBoneList = list() #list duplicated bones in pose mode
    for obj, newBoneName in zip(objectList, newBoneNames):
        newPbone = obj.pose.bones[newBoneName]
        newPBoneList.append(newPbone)

    duplicateBone.AssignPoseBoneGroups(pboneList, newPBoneList)
    
    for pbone, worldPbone in zip(pboneList, newPBoneList):
        #assign controller shape to worldPbone
        worldBone_customShape = bpy.context.scene.rotf_worldSpace_customShape
        if worldBone_customShape == None:
            importControllerShapes.ImportControllerShapes(["RotF_Square"])
            worldPbone.custom_shape = bpy.data.objects['RotF_Square']
        else:
            worldPbone.custom_shape = bpy.data.objects[worldBone_customShape.name]
        
        #have world space bone copy target bone's transforms
        copyTransforms = worldPbone.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " RotF"
        copyTransforms.target = obj
        copyTransforms.subtarget = pbone.name

        bonesToBakeInfo[worldPbone] = [pbone]
        
    return newPBoneList, bonesToBakeInfo

def SetupWorldSpaceBehaviour(pboneList, wolrdPBones):
    
    rotfBake.KeyframeClear(pboneList) #remove keys on the target bones as they follow the world space bones

    for pbone, worldPbone in zip(pboneList, wolrdPBones):
        obj = pbone.id_data
        #have target bone copy world space bone's transforms
        copyTransforms = pbone.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " RotF"
        copyTransforms.target = obj
        copyTransforms.subtarget = worldPbone.name

        #move non relevant bones to unused layer
        unusedLayer = obj.unusedRigBonesLayer
        bone = pbone.bone

        appVersion = bpy.app.version
        if appVersion[0] == 4:
            boneCollections.AddBoneToCollections(bone, [boneCollections.RotFUnusedColName])
            #boneCollections.UnassignBoneFromCollections(bone, [boneCollections.RotFAnimationColName])
            bone.hide = True
        elif appVersion[0] == 3:
            bone.layers[unusedLayer]=True
            for layer in range(32):
                if layer == unusedLayer:
                    continue
                else:
                    bone.layers[layer]=False

        newPointer = worldPbone.bone.rotf_pointer_list.add()
        newPointer.name = "WORLD"
        newPointer.armature_object = obj
        newPointer.bone_name = pbone.name

        rigState.AddConstraint(
                obj,
                "World Space|" + pbone.name,
                "World Space|" + pbone.name,
                "World Space",
                [pbone.name],
                [True], #is not used
                [""], #is not  used
                [0], #is not used
                [0.0] #is not used
                )

def WorldSpace():
    pboneList = bpy.context.selected_pose_bones
    wolrdPBones = WorldSpaceConstraint.CreateWorldSpaceConstraint(pboneList)

    #end script with world controllers selected
    for pbone in wolrdPBones:
        pbone.bone.select = True

def RemoveWorldSpace():
    #filter selection, keeping only targetPoseBonesWithWorld
    targetPoseBonesWithWorld = list()
    for boneP in bpy.context.selected_pose_bones:
        if 'WORLD' in boneP.bone.rotf_pointer_list:
            obj = boneP.bone.rotf_pointer_list['WORLD'].armature_object
            bonename = boneP.bone.rotf_pointer_list['WORLD'].bone_name

            targetPBone = obj.pose.bones[bonename]
            if targetPBone not in targetPoseBonesWithWorld:
                targetPoseBonesWithWorld.append(targetPBone)
    
    #remove WORLD from targetPoseBonesWithWorld
    RemoveWorld(targetPoseBonesWithWorld)
    
    #end with only the targetPoseBonesWithIK selected
    bpy.ops.pose.select_all(action='DESELECT')
    for pbone in targetPoseBonesWithWorld:
        pbone.bone.select = True

def RemoveWorld(targetPoseBonesWithWorld):
    bonesToBakeInfo = dict()
    copyTransformsConstraintList = list()
    wolrdPBoneList = list()
    wolrdBoneList = list()
    for targetPBone in targetPoseBonesWithWorld:
        obj = targetPBone.id_data
        armature = obj.data

        if "Copy Transforms RotF" in targetPBone.constraints:
            copyTransforms = targetPBone.constraints["Copy Transforms RotF"]
            worldTargetBoneN = copyTransforms.subtarget
            worldtargetPBone = obj.pose.bones[worldTargetBoneN]
            
            copyTransformsConstraintList.append(copyTransforms)
            wolrdPBoneList.append(worldtargetPBone)
            wolrdBoneList.append(worldtargetPBone.bone)
        
        appVersion = bpy.app.version
        if appVersion[0] == 4:
            #boneCollections.AddBoneToCollections(targetPBone.bone, [boneCollections.RotFAnimationColName])
            targetPBone.bone.hide = False
            boneCollections.UnassignBoneFromCollections(targetPBone.bone, [boneCollections.RotFUnusedColName])
        elif appVersion[0] == 3:
            for layer in range(32):
                targetPBone.bone.layers[layer] = worldtargetPBone.bone.layers[layer]

        bonesToBakeInfo[targetPBone] = [worldtargetPBone]

    if bpy.context.scene.rotf_no_bake_on_remove == False:
        rotfBake.Bake(bonesToBakeInfo)

    rotfBake.KeyframeClear(wolrdPBoneList)

    for targetPBone, copyTransforms in zip(targetPoseBonesWithWorld, copyTransformsConstraintList):
        targetPBone.constraints.remove(copyTransforms) #remove copy transforms constraint from target bone

    #force edit mode to remove World bones
    bpy.ops.object.mode_set(mode='EDIT')
    for worldBone in wolrdBoneList:
        armature = worldBone.id_data
        worldBoneName = worldBone.name
        worldEBone = armature.edit_bones[worldBoneName]
        if worldEBone:
            armature.edit_bones.remove(worldEBone)

    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    appVersion = bpy.app.version
    if appVersion[0] == 4:
        boneCollections.RemoveEmptyBoneCollection(armature) #for some reason it has to be in Pose mode to work otherwise in Edit mode collections are considered empty

    for targetPBone in targetPoseBonesWithWorld:
        rigState.RemoveConstraint(obj, "World Space|"+ targetPBone.name)