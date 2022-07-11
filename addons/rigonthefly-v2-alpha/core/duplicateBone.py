import bpy

def DuplicateBone(prefix, eboneList):
    newBones = list()
    newEditBones = list()
    newBoneNames = list()
    for ebone in eboneList:
        armature = ebone.id_data

        #create duplacate of boneN
        newEditBone = armature.edit_bones.new(prefix + ebone.name)
        newEditBone.matrix = ebone.matrix #head position and roll
        newEditBone.tail = ebone.tail #tail position
        newEditBone.parent = ebone.parent #parent bone
        newEditBone.layers = ebone.layers
        
        newEditBone.use_deform = False
        
        newBoneN = newEditBone.name

        newBones.append(newEditBone)
        newEditBones.append(armature.edit_bones[newBoneN])
        newBoneNames.append(newBoneN)

    return newBones, newEditBones, newBoneNames

def AssignPoseBoneGroups(oldPBoneList, newPboneList):
    for oldPBone, newPBone in zip(oldPBoneList, newPboneList):
        newPBone.rotation_mode = oldPBone.rotation_mode
        newPBone.bone_group = oldPBone.bone_group
        newPBone.bone.use_inherit_rotation = oldPBone.bone.use_inherit_rotation
        newPBone.bone.use_inherit_scale = oldPBone.bone.use_inherit_scale
        newPBone.bone.is_rotf = True
    
    
