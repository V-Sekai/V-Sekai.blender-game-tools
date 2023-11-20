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
from . import rotationModeAndRelations

class RotationDistributionConstraint:

    def __init__(self):
        print('IK Limb Constraint')

    def CreateRotationDistributionConstraint(rotDistSettingsList):
        ikTargetPBoneList = list()

        bonesToBakeInfo, pboneChainList = SetupRotationDistributionControllers(rotDistSettingsList)

        rotationModeAndRelations.InheritRotation(True, pboneChainList)

        for rotDistSettings in rotDistSettingsList:
            rotDistTargetPBone = rotDistSettings.obj.pose.bones[rotDistSettings.rotDistBoneN]
            ikTargetPBoneList.append(rotDistTargetPBone)
        
        rotfBake.Bake(bonesToBakeInfo)
        
        SetupRotationDistributionBehaviour(rotDistSettingsList)

        return ikTargetPBoneList

    def CreateConstraint(self, obj, constraintInfoList):
        rotDistSettingsList = list()
        errorMessageList = list()
        for constraintInfo in constraintInfoList:
            targetBoneN = constraintInfo['bone_list'][0]
            if obj.data.bones.get(targetBoneN) == None: #check if target bone exists. if not, skips
                errorMessageList.append("Rotation Distribution Constraint|Bone not found: " + obj.name + "[" + targetBoneN + "]")
                continue

            int_list = constraintInfo['int_list']
            chainLength = int_list[0]

            rotDistSettings = RotationDistributionSettings()
            rotDistSettings.obj = obj
            rotDistSettings.targetBoneN = targetBoneN
            rotDistSettings.chainLength = int(chainLength)

            rotDistSettingsList.append(rotDistSettings)

        RotationDistributionConstraint.CreateRotationDistributionConstraint(rotDistSettingsList)

        if errorMessageList:
            return errorMessageList

class RotationDistributionSettings:
    def __init__(self):
        self.chainLength = int()

        self.obj = None
        self.targetBoneN = str()

        self.rotDistBoneN = str()

        #self.boneNChainList = list()

def SetupRotationDistributionControllers(rotDistSettingsList):
    #force edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.context.object.data.use_mirror_x = False

    for rotDistSettings in rotDistSettingsList:
        obj = rotDistSettings.obj
        targetEBone = obj.data.edit_bones[rotDistSettings.targetBoneN]
        baseEBone = targetEBone.parent_recursive[rotDistSettings.chainLength - 1] #base bone of the chain

        newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBone("RotDistribution.", [targetEBone])

        rotDistSettings.rotDistBoneN = newBoneNames[0]
        rotDistTargetEBone = newEditBones[0]
        rotDistTargetEBone.parent = baseEBone #make rotation distribution bone child of the base bone

    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    bonesToBakeInfo = dict()
    pboneChainList = list()

    for rotDistSettings in rotDistSettingsList:
        obj = rotDistSettings.obj
        targetPBone = obj.pose.bones[rotDistSettings.targetBoneN]
        rotDistPBone = obj.pose.bones[rotDistSettings.rotDistBoneN]

        rotDistPBone.bone.use_inherit_rotation = targetPBone.bone.use_inherit_rotation
        rotDistPBone.bone.inherit_scale = targetPBone.bone.inherit_scale

        duplicateBone.AssignPoseBoneGroups([targetPBone], [rotDistPBone])

        #assign controller shape to rotDistPBone
        rotDist_customShape = bpy.context.scene.rotf_ikTarget_customShape
        if rotDist_customShape == None:
            importControllerShapes.ImportControllerShapes(["RotF_Octagon"])
            rotDistPBone.custom_shape = bpy.data.objects['RotF_Octagon']
        else:
            rotDistPBone.custom_shape = bpy.data.objects[rotDist_customShape.name]
        rotDistPBone.bone.show_wire = True
        rotDistPBone.custom_shape_scale_xyz = targetPBone.custom_shape_scale_xyz
        rotDistPBone.custom_shape_transform = targetPBone

        copyRotation = rotDistPBone.constraints.new('COPY_ROTATION')
        copyRotation.name += " RotF"
        copyRotation.target = obj
        copyRotation.subtarget = rotDistSettings.targetBoneN
        copyScale = rotDistPBone.constraints.new('COPY_SCALE')
        copyScale.name += " RotF"
        copyScale.target = obj
        copyScale.subtarget = rotDistSettings.targetBoneN

        bonesToBakeInfo[rotDistPBone] = [
            [targetPBone, rotfBake.Channel.rotationQE, rotfBake.Channel.rotationQE],
            [targetPBone, rotfBake.Channel.scaleXYZ, rotfBake.Channel.scaleXYZ],
            ]

        #add bones from the chain to pboneChainList to switch their inherit rotation to true
        if targetPBone not in pboneChainList:
            pboneChainList.append(targetPBone)
        for i, pbone in zip(range(rotDistSettings.chainLength - 1), targetPBone.parent_recursive):
            if pbone not in pboneChainList:
                pboneChainList.append(pbone)

    return bonesToBakeInfo, pboneChainList

def SetupRotationDistributionBehaviour(rotDistSettingsList):
    for rotDistSettings in rotDistSettingsList:
        obj = rotDistSettings.obj
        targetPBone = obj.pose.bones[rotDistSettings.targetBoneN]
        rotDistPBone = obj.pose.bones[rotDistSettings.rotDistBoneN]

        #remove constraints on the rotation distribution bone now that it has the target bone's rotation and scale
        removeConstraints.RemoveAllRotFConstraints([rotDistPBone])

        #ik constrain the target bone to the rotation distribution bone
        ikRotationConstraint = targetPBone.constraints.new('IK')
        ikRotationConstraint.name += " RotF"
        ikRotationConstraint.target = obj
        ikRotationConstraint.subtarget = rotDistSettings.rotDistBoneN
        ikRotationConstraint.use_location = False
        ikRotationConstraint.use_rotation = True
        ikRotationConstraint.chain_count = rotDistSettings.chainLength

        #move non relevant bones to unused layer
        unusedLayer = obj.unusedRigBonesLayer
        pboneToMoveList = [targetPBone]
        for i, pbone in zip(range(rotDistSettings.chainLength - 1), targetPBone.parent_recursive):
            pboneToMoveList.append(pbone)

        for pbone in pboneToMoveList:
            bone = pbone.bone
            bone.layers[unusedLayer]=True
            for layer in range(32):
                if layer != unusedLayer:
                    bone.layers[layer]=False

        newPointer = rotDistPBone.bone.rotf_pointer_list.add()
        newPointer.name = "ROTATION_DISTRIBUTION"
        newPointer.armature_object = obj
        newPointer.bone_name = targetPBone.name

        rigState.AddConstraint(
            rotDistSettings.obj,
            "Rotation Distribution|" + rotDistSettings.targetBoneN,
            "Rotation Distribution|" + rotDistSettings.targetBoneN + "|length:" + str(rotDistSettings.chainLength),
            "Rotation Distribution",
            [rotDistSettings.targetBoneN],
            [True], #is not used
            [""], #is not used
            [rotDistSettings.chainLength],
            [0.0] #is not used
            )

def RotationDistribution():
    scene = bpy.context.scene

    chainLength = scene.rotf_rotation_distribution_chain_length

    pboneList = bpy.context.selected_pose_bones
    rotDistSettingsList = list()
    for pbone in pboneList:
        if len(pbone.parent_recursive) < chainLength:
            return [{'WARNING'}, "not enough parents"]
            
        targetBoneN = pbone.name

        rotDistSettings = RotationDistributionSettings()
        rotDistSettings.obj = pbone.id_data
        rotDistSettings.targetBoneN = targetBoneN
        rotDistSettings.chainLength = int(chainLength)

        rotDistSettingsList.append(rotDistSettings)

    rotDistTargetPBoneList = RotationDistributionConstraint.CreateRotationDistributionConstraint(rotDistSettingsList)

    #end script with new ik handles selected
    for rotDistTargetPBone in rotDistTargetPBoneList:
        rotDistTargetPBone.bone.select = True

def ApplyRotationDistribution():
    #filter selection, keeping only targetPoseBonesWithWorld
    pboneWithRotDistList = list()
    for pbone in bpy.context.selected_pose_bones:
        if 'ROTATION_DISTRIBUTION' in pbone.bone.rotf_pointer_list:
            obj = pbone.bone.rotf_pointer_list['ROTATION_DISTRIBUTION'].armature_object
            boneN = pbone.bone.rotf_pointer_list['ROTATION_DISTRIBUTION'].bone_name

            targetPBone = obj.pose.bones[boneN]
            if targetPBone not in pboneWithRotDistList:
                pboneWithRotDistList.append(targetPBone)
    
    RemoveRotationDistribution(pboneWithRotDistList)

    #end with only the targetPoseBonesWithIK selected
    bpy.ops.pose.select_all(action='DESELECT')
    for pbone in pboneWithRotDistList:
        pbone.bone.select = True

def RemoveRotationDistribution(pboneWithRotDistList):
    bonesToBakeInfo = dict()
    boneNToRemoveDict = dict()
    pbonesKeysToClear = list()

    for targetPBone in pboneWithRotDistList:
        obj = targetPBone.id_data
        armature = obj.data

        #get the ik constraint to find the chain length and the pole vector
        ikConstraint = targetPBone.constraints["IK RotF"]
        rotDistPBone = obj.pose.bones[ikConstraint.subtarget]
        chainLength = ikConstraint.chain_count

        pboneChainList = list()
        pbone = targetPBone.parent
        for i in range(chainLength):
            pboneChainList.append(pbone)
            pbone = pbone.parent

        #bake info for targetBoneP, the last bone of the chain
        bonesToBakeInfo[targetPBone] = [
            [rotDistPBone, rotfBake.Channel.locationRotationQE, rotfBake.Channel.rotationQE],
            [rotDistPBone, rotfBake.Channel.scaleXYZ, rotfBake.Channel.scaleXYZ]
            ]

        for pbone in pboneChainList:
            bonesToBakeInfo[pbone] = [[rotDistPBone, rotfBake.Channel.locationXYZ, rotfBake.Channel.rotationQE]]

        #move bones to the same layers as the rotation distribution bone
        for layer in range(32):
            targetPBone.bone.layers[layer] = rotDistPBone.bone.layers[layer]
            for pbone in pboneChainList:
                pbone.bone.layers[layer] = armature.bones[rotDistPBone.name].layers[layer]

        pbonesKeysToClear.append(rotDistPBone)

    for pbone in pbonesKeysToClear:
        armature = pbone.id_data.data
        if armature in boneNToRemoveDict:
            boneNToRemoveDict[armature].append(pbone.name)
        else:
            boneNToRemoveDict[armature] = [pbone.name]

    rotfBake.Bake(bonesToBakeInfo)

    removeConstraints.RemoveAllRotFConstraints(bonesToBakeInfo)
    
    rotfBake.KeyframeClear(pbonesKeysToClear)

    #force edit mode to remove IK bones
    bpy.ops.object.mode_set(mode='EDIT')
    for armature in boneNToRemoveDict:
        for boneN in boneNToRemoveDict[armature]:
            ebone = armature.edit_bones.get(boneN)
            if ebone:
                armature.edit_bones.remove(ebone)

    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    for targetPBone in pboneWithRotDistList:
        rigState.RemoveConstraint(obj, "Rotation Distribution|"+ targetPBone.name)