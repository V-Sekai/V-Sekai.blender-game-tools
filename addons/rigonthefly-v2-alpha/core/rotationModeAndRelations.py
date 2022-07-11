#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . import duplicateBone
from . import removeConstraints
from . import rotfBake

def RotationModeAndRelations(rotationMode, pboneList):

    boneNamesDict = dict()
    rotationModeAndRelationsDict = dict()

    for pbone in pboneList:
        boneNamesDict[pbone.id_data] = list()
        rotationModeAndRelationsDict[pbone.id_data] = list()

    for pbone in pboneList:
        boneNamesDict[pbone.id_data].append(pbone.name)
        rotationModeAndRelationsDict[pbone.id_data].append(rotationMode)

    ChangeRotationAndScaleMode(boneNamesDict, rotationModeAndRelationsDict, None, None)



def InheritRotation(inheritRotation, pboneList):
    boneNamesDict = dict()

    inheritRotationDict = dict()

    for pbone in pboneList:
        boneNamesDict[pbone.id_data] = list()

        inheritRotationDict[pbone.id_data] = list()



    for pbone in pboneList:
        boneNamesDict[pbone.id_data].append(pbone.name)
        inheritRotationDict[pbone.id_data].append(inheritRotation)

    ChangeRotationAndScaleMode(boneNamesDict, None, inheritRotationDict, None)

def InheritScale(inheritScale, pboneList):
    boneNamesDict = dict()

    inheritScaleDict = dict()

    for pbone in pboneList:
        boneNamesDict[pbone.id_data] = list()

        inheritScaleDict[pbone.id_data] = list()

    for pbone in pboneList:
        boneNamesDict[pbone.id_data].append(pbone.name)
        inheritScaleDict[pbone.id_data].append(inheritScale)

    ChangeRotationAndScaleMode(boneNamesDict, None, None, inheritScaleDict)

def ChangeRotationAndScaleMode(boneNamesDict, rotationModeDict, inheritRotationDict, inheritScaleDict):
    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.context.object.data.use_mirror_x = False

    for obj in boneNamesDict:
        armature = obj.data
        eboneList = list()
        for boneN in boneNamesDict[obj]:
            ebone = armature.edit_bones[boneN]
            eboneList.append(ebone)
        newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBone("temp.", eboneList) #duplicate bones to change

    bpy.ops.object.mode_set(mode='POSE')

    tempBonesToBakeInfo = dict()
    for obj in boneNamesDict:
        #have copies follow the selected bones motion
        for boneN in boneNamesDict[obj]:
            tempBoneN = "temp." + boneN

            selectedPBone = obj.pose.bones[boneN]
            tempPBone = obj.pose.bones[tempBoneN]

            tempBonesToBakeInfo[tempPBone] = list()
            if rotationModeDict or inheritRotationDict: #if RotationModeAndRelationsDict or inheritRotationDict is not null constrain rotation
                copyRotation = tempPBone.constraints.new('COPY_ROTATION')
                copyRotation.name += " RotF"
                copyRotation.target = obj
                copyRotation.subtarget = boneN

                tempBonesToBakeInfo[tempPBone].append([selectedPBone, rotfBake.Channel.rotationQE, rotfBake.Channel.rotationQE])

            if inheritScaleDict: #if inheritScaleDict is not null constrain scale
                copyScale = tempPBone.constraints.new('COPY_SCALE')
                copyScale.name += " RotF"
                copyScale.target = obj
                copyScale.subtarget = boneN

                tempBonesToBakeInfo[tempPBone].append([selectedPBone ,rotfBake.Channel.scaleXYZ, rotfBake.Channel.scaleXYZ])

    rotfBake.Bake(tempBonesToBakeInfo) #bake the motion onto the copied bones

    selectedBonesToBakeInfo = dict()
    for obj in boneNamesDict:
        #reverse the constraints so that the selected bones follow the copied bones motion
        for i, boneN in enumerate(boneNamesDict[obj]):
            tempBoneN = "temp." + boneN

            selectedPBone = obj.pose.bones[boneN]
            tempPBone = obj.pose.bones[tempBoneN]

            pointer = selectedPBone.bone.rotf_pointer_list.get("Orient") #check if selectedPBone is the orient version of another bone in the armature
            orientedPBone = None
            if pointer:
                orientedPBone = obj.pose.bones.get(pointer['bone_name'])

            removeConstraints.RemoveAllRotFConstraints([tempPBone]) #remove constraints from copied bones

            if rotationModeDict:
                selectedPBone.rotation_mode = rotationModeDict[obj][i] #change selected bones' RotationMode
            if inheritRotationDict:
                selectedPBone.bone.use_inherit_rotation = inheritRotationDict[obj][i] #change selected bones' inherit rotation
                if orientedPBone:
                    orientedPBone.bone.use_inherit_rotation = selectedPBone.bone.use_inherit_rotation #have the orientedPBone use the same inherit rotation as selectedPBone

            if inheritScaleDict:
                selectedPBone.bone.use_inherit_scale = inheritScaleDict[obj][i] #change selected bones' inherit scale
                if orientedPBone:
                    orientedPBone.bone.use_inherit_rotation = selectedPBone.bone.use_inherit_rotation #have the orientedPBone use the same inherit scale as selectedPBone

            selectedBonesToBakeInfo[selectedPBone] = list()

            if rotationModeDict or inheritRotationDict: #if RotationModeAndRelationsDict or inheritRotationDict is not null constrain rotation
                copyRotation = selectedPBone.constraints.new('COPY_ROTATION')
                copyRotation.name = "Temp Copy Rotation RotF"
                copyRotation.target = obj
                copyRotation.subtarget = tempBoneN

                selectedBonesToBakeInfo[selectedPBone].append([tempPBone ,rotfBake.Channel.rotationQE, rotfBake.Channel.rotationQE])

            if inheritScaleDict: #if inheritScaleDict is not null constrain scale
                copyScale = selectedPBone.constraints.new('COPY_SCALE')
                copyScale.name = "Temp Copy Scale RotF"
                copyScale.target = obj
                copyScale.subtarget = tempBoneN

                selectedBonesToBakeInfo[selectedPBone].append([tempPBone ,rotfBake.Channel.scaleXYZ, rotfBake.Channel.scaleXYZ])

    rotfBake.Bake(selectedBonesToBakeInfo) #bake selected bones' motion now that the setting has been changed
    
    for obj in boneNamesDict:
        for boneN in boneNamesDict[obj]:
            tempBoneN = "temp." + boneN

            selectedPBone = obj.pose.bones[boneN]
            tempPBone = obj.pose.bones[tempBoneN]

            #remove rotation and or scale constraints
            for constraint in selectedPBone.constraints:
                if "Temp Copy Rotation RotF" in constraint.name:
                    selectedPBone.constraints.remove(constraint)

                elif "Temp Copy Scale RotF" in constraint.name:
                    selectedPBone.constraints.remove(constraint)

            rotfBake.KeyframeClear([tempPBone]) #remove TempBones' keyframes before deleting them

    #set to edit mode to remove the temp bones
    bpy.ops.object.mode_set(mode='EDIT')

    for obj in boneNamesDict:
        #remove TempBones
        for boneN in boneNamesDict[obj]:
            tempBoneN = "temp." + boneN

            try:
                armature.edit_bones.remove(armature.edit_bones[tempBoneN])
            except:
                pass
            
    #return to pose mode
    bpy.ops.object.mode_set(mode='POSE')


