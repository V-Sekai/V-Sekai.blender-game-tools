#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . import boneCollections
from . import removeConstraints
from . import rigState
from . import rotfBake

def BakeRig(objectList):
    rotfBoneNDict = dict()
    for obj in objectList:
        armature = obj.data

        bonesToBakeInfo = dict()
        rotfPBoneList = list()
        
        rotfBoneNDict[armature] = list()

        for pbone in obj.pose.bones:
            if pbone.bone.is_rotf:
                rotfPBoneList.append(pbone)
                rotfBoneNDict[armature].append(pbone.name)

            else:
                pboneConstraintTargetList = list()
                for constraint in pbone.constraints:
                    if "RotF" in constraint.name:
                        pboneConstraintTarget = constraint.target.pose.bones[constraint.subtarget]
                        pboneConstraintTargetList.append(pboneConstraintTarget)

                        if constraint.type == "IK":
                            for parentPBone in pbone.parent_recursive[:constraint.chain_count]:
                                bonesToBakeInfo[parentPBone] = [pboneConstraintTarget]
                
                if len(pboneConstraintTargetList) > 0:
                    bonesToBakeInfo[pbone] = list()
                    for pboneConstraintTarget in pboneConstraintTargetList:
                        bonesToBakeInfo[pbone].append(pboneConstraintTarget)

        if bpy.context.scene.rotf_no_bake_on_remove == False:
            rotfBake.Bake(bonesToBakeInfo)

        removeConstraints.RemoveAllRotFConstraints(bonesToBakeInfo)

        rotfBake.KeyframeClear(rotfPBoneList)

        #reset the object's rig state to zero
        while len(obj.rotf_rig_state) > 0:
            rigState.RemoveConstraint(obj, obj.rotf_rig_state[0].name)

        appVersion = bpy.app.version
        if appVersion[0] == 4:
            boneCollections.RemoveRotFBoneCollections(armature)

            for pbone in obj.pose.bones:
                pbone.bone.hide = False

        elif appVersion[0] == 3:
            baseLayer = obj.baseBonesLayer
            layerList = [obj.unusedRigBonesLayer, obj.notOrientedBonesLayer]
            for pbone in obj.pose.bones:
                for layer in range(32):
                    if layer in layerList:
                        pbone.bone.layers[baseLayer] = True
                        pbone.bone.layers[layer] = False

    #remove rotf bones
    bpy.ops.object.mode_set(mode='EDIT')

    for armature in rotfBoneNDict:
        for boneN in rotfBoneNDict[armature]:
            ebone = armature.edit_bones.get(boneN)
            if ebone:
                armature.edit_bones.remove(ebone)

    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')