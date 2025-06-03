#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . import rigState
from . import rotfBake

def RemoveSimpleConstraints():
    for pbone in bpy.context.selected_pose_bones:
        constraintToRemoveList = list()
        for constraint in pbone.constraints:
            if " Simple RotF" in constraint.name:
                targetObj = constraint.target
                targetPBone = targetObj.pose.bones[constraint.subtarget]

                if constraint.type in ['COPY_TRANSFORMS', 'COPY_LOCATION', 'COPY_ROTATION', 'COPY_SCALE']:
                    if "Simple Copy Transforms|"+ pbone.name not in constraintToRemoveList:
                        constraintToRemoveList.append("Simple Copy Transforms|"+ pbone.name)

                if constraint.type in ['DAMPED_TRACK']:
                    if "Simple Aim|"+ pbone.name not in constraintToRemoveList:
                        constraintToRemoveList.append("Simple Aim|"+ pbone.name)

                pbone.constraints.remove(constraint)

        obj = pbone.id_data
        for constraintName in constraintToRemoveList:
            SimpleRemoveConstraint(obj,constraintName)

def BakeSimpleConstraints():
    bonesToBakeInfo = dict()
    
    for pbone in bpy.context.selected_pose_bones:    
        constraintToRemoveList = list()
        for constraint in pbone.constraints:
            if " Simple RotF" in constraint.name:
                targetObj = constraint.target
                targetPBone = targetObj.pose.bones[constraint.subtarget]

                if constraint.type == 'COPY_TRANSFORMS':
                    bonesToBakeInfo[pbone] = [targetPBone]
                    if "Simple Copy Transforms|"+ pbone.name not in constraintToRemoveList:
                        constraintToRemoveList.append("Simple Copy Transforms|"+ pbone.name)

                if constraint.type == 'COPY_LOCATION':
                    bonesToBakeInfo[pbone] = [targetPBone]
                    if "Simple Copy Transforms|"+ pbone.name not in constraintToRemoveList:
                        constraintToRemoveList.append("Simple Copy Transforms|"+ pbone.name)

                if constraint.type == 'COPY_ROTATION':
                    bonesToBakeInfo[pbone] = [targetPBone]
                    if "Simple Copy Transforms|"+ pbone.name not in constraintToRemoveList:
                        constraintToRemoveList.append("Simple Copy Transforms|"+ pbone.name)

                if constraint.type == 'COPY_SCALE':
                    bonesToBakeInfo[pbone] = [targetPBone]
                    if "Simple Copy Transforms|"+ pbone.name not in constraintToRemoveList:
                        constraintToRemoveList.append("Simple Copy Transforms|"+ pbone.name)
                
                if constraint.type == 'DAMPED_TRACK':
                    bonesToBakeInfo[pbone] = [targetPBone]
                    if "Simple Aim|"+ pbone.name not in constraintToRemoveList:
                        constraintToRemoveList.append("Simple Aim|"+ pbone.name)

        obj = pbone.id_data
        for constraintName in constraintToRemoveList:
            SimpleRemoveConstraint(obj,constraintName)
    
    rotfBake.Bake(bonesToBakeInfo)

    for pbone in bonesToBakeInfo:
        obj = pbone.id_data

        for constraint in pbone.constraints:
            targetObj = constraint.target
            targetPBone = targetObj.pose.bones[constraint.subtarget]
            if " Simple RotF" in constraint.name:
                pbone.constraints.remove(constraint)

def SimpleRemoveConstraint(obj, name):
    indexList = list()
    for i, constraint in enumerate(obj.rotf_rig_state):
        if constraint.name in name:
            indexList.append(i)

    indexList.sort(reverse=True)
    for i in indexList:
        obj.rotf_rig_state.remove(i)