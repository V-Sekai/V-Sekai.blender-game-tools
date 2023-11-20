#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy

from . import removeConstraints
from . import rigState
from . import rotfBake

def FKLimb():

    #filter selection, keeping only targetPoseBonesWithIK
    targetPBonesWithIK = list()
    for pbone in bpy.context.selected_pose_bones:
        if 'IK' in pbone.bone.rotf_pointer_list:
            obj = pbone.bone.rotf_pointer_list['IK'].armature_object
            bonename = pbone.bone.rotf_pointer_list['IK'].bone_name

            targetBoneP = obj.pose.bones[bonename]
            if targetBoneP not in targetPBonesWithIK:
                targetPBonesWithIK.append(targetBoneP)

    #remove IK from targetPoseBonesWithIK
    #for pbone in targetPBonesWithIK:
    RemoveIK(targetPBonesWithIK)

    #end with only the targetPoseBonesWithIK selected
    bpy.ops.pose.select_all(action='DESELECT')
    for pbone in targetPBonesWithIK:
        pbone.bone.select = True

def RemoveIK(targetPBonesWithIK):

    #set up the bonesToBakeInfo dictionary for baking
    bonesToBakeInfo = dict()
    boneNToRemoveDict = dict()
    pbonesKeysToClear = list()
    
    for targetPBone in targetPBonesWithIK:
        obj = targetPBone.id_data
        armature = obj.data
        #poleBoneP = targetBoneP.parent
        #baseBoneP = poleBoneP.parent

        ikTargetPBone = None
        ikPolePBone = None
        constrainedPBone = None #the pose bone with the ik constraint
        pboneChainList = list()
        pboneStretchChainList = list()

        hasPole = False
        hasStretch = False
        hasLocationStretch = False
        hasScaleStretch = False

        #find all the IK bones to remove
        ikTargetBoneN = targetPBone.constraints["Copy Rotation RotF"].subtarget
        ikTargetPBone = obj.pose.bones[ikTargetBoneN]
        if "Copy Location RotF" in targetPBone.constraints:
            hasStretch = True
        if hasStretch:
            constrainedBoneN = targetPBone.parent.constraints["Copy Rotation RotF"].subtarget
            constrainedPBone = obj.pose.bones[constrainedBoneN]

            if "Copy Scale RotF" in constrainedPBone.constraints:
                hasScaleStretch = True
            else:
                hasLocationStretch = True
        else:
            constrainedPBone = targetPBone.parent

        #get the ik constraint to find the chain length and the pole vector
        ikConstraint = constrainedPBone.constraints["IK RotF"]
        chainLength = ikConstraint.chain_count
        if ikConstraint.pole_target: #check if IK constraint uses a pole vector
            ikPolePBone = obj.pose.bones[ikConstraint.pole_subtarget]
            hasPole = True

        if hasStretch: #get pboneStretchChainList
            stretchPBone = constrainedPBone
            for i in range(chainLength):
                pboneStretchChainList.append(stretchPBone)
                stretchPBone = stretchPBone.parent

        #get pboneChainList
        pbone = targetPBone.parent
        for i in range(chainLength):
            pboneChainList.append(pbone)
            pbone = pbone.parent
        
        
        #bake info for targetBoneP, the last bone of the chain
        bonesToBakeInfo[targetPBone] = [
            [ikTargetPBone, rotfBake.Channel.locationRotationQE, rotfBake.Channel.rotationQE],
            [ikTargetPBone, rotfBake.Channel.scaleXYZ, rotfBake.Channel.scaleXYZ]
            ]
        if hasPole:
            bonesToBakeInfo[targetPBone].append([ikPolePBone, rotfBake.Channel.locationXYZ, rotfBake.Channel.rotationQE])
        if hasLocationStretch:
            bonesToBakeInfo[targetPBone].append([ikTargetPBone, rotfBake.Channel.locationXYZ, rotfBake.Channel.locationXYZ])
        if hasScaleStretch:
            bonesToBakeInfo[targetPBone].append([ikTargetPBone, rotfBake.Channel.locationXYZ, rotfBake.Channel.scaleXYZ])

        #bake info for baseBoneP and poleBoneP
        for pbone in pboneChainList:
            bonesToBakeInfo[pbone] = [[ikTargetPBone, rotfBake.Channel.locationXYZ, rotfBake.Channel.rotationQE]]
            if hasPole:
                bonesToBakeInfo[pbone].append([ikPolePBone, rotfBake.Channel.locationXYZ, rotfBake.Channel.rotationQE])

            if hasScaleStretch:
                bonesToBakeInfo[pbone].append([ikTargetPBone, rotfBake.Channel.locationXYZ, rotfBake.Channel.scaleXYZ])
        
            if hasLocationStretch:
                bonesToBakeInfo[pbone].append([ikTargetPBone, rotfBake.Channel.locationXYZ, rotfBake.Channel.locationXYZ])


        #move fk bones to the same layers as the ikTargetBone
        for layer in range(32):
            targetPBone.bone.layers[layer] = ikTargetPBone.bone.layers[layer]
            for pbone in pboneChainList:
                pbone.bone.layers[layer] = armature.bones[ikTargetBoneN].layers[layer]
        
        pbonesKeysToClear.append(ikTargetPBone)
        if hasPole:
            pbonesKeysToClear.append(ikPolePBone)
        if hasStretch:
            pbonesKeysToClear.extend(pboneStretchChainList)

    #
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
            try:
                armature.edit_bones.remove(armature.edit_bones[boneN])
            except:
                print(boneN)

    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    for targetPBone in targetPBonesWithIK:
        rigState.RemoveConstraint(obj, "IK Limb|"+ targetPBone.name)