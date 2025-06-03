import bpy

from . import boneCollections

def DuplicateBones(prefix, eboneList):
    newBones = list()
    newEditBones = list()
    newBoneNames = list()
    for ebone in eboneList:
        newEditBone, newBoneN = DuplicateBone(prefix, ebone)
        newBones.append(newEditBone)
        newEditBones.append(newEditBone)
        newBoneNames.append(newBoneN)
    return newBones, newEditBones, newBoneNames

def DuplicateBone(prefix, ebone):
    armature = ebone.id_data

    #create duplacate of boneN
    newEditBone = armature.edit_bones.new(prefix + ebone.name)
    newEditBone.matrix = ebone.matrix #head position and roll
    newEditBone.tail = ebone.tail #tail position
    newEditBone.parent = ebone.parent #parent bone

    appVersion = bpy.app.version
    if appVersion[0] == 4:
        #for bCollection in ebone.collections:
            #print(bCollection.name)
            #bCollection.assign(newEditBone)
            #if "Rig On The Fly Only" not in newEditBone.id_data.data.collections:
            #    newEditBone.id_data.data.collections.new("Rig On The Fly Only")
            #    
            #newEditBone.id_data.data.collections['Rig On The Fly Only']
        pass
    elif appVersion[0] == 3:
        newEditBone.layers = ebone.layers
    
    newEditBone.use_deform = False
    
    newBoneN = newEditBone.name

    
    return newEditBone, newBoneN 

def AssignPoseBoneGroups(oldPBoneList, newPboneList):

    appVersion = bpy.app.version
    if appVersion[0] == 4:
        for oldPBone, newPBone in zip(oldPBoneList, newPboneList):
            boneCollections.AddBoneToCollections(newPBone.bone, [boneCollections.RotFAnimationColName, 
                                                                 boneCollections.RotFOnlyColName])
            newPBone.rotation_mode = oldPBone.rotation_mode

            newPBone.bone.use_inherit_rotation = oldPBone.bone.use_inherit_rotation
            newPBone.bone.inherit_scale = oldPBone.bone.inherit_scale
            
            newPBone.custom_shape_translation = oldPBone.custom_shape_translation
            newPBone.custom_shape_rotation_euler = oldPBone.custom_shape_rotation_euler
            newPBone.custom_shape_scale_xyz = oldPBone.custom_shape_scale_xyz 
            newPBone.bone.color.palette = oldPBone.bone.color.palette
            if oldPBone.bone.color.is_custom:
                newPBone.bone.color.custom.normal = oldPBone.bone.color.custom.normal
                newPBone.bone.color.custom.select = oldPBone.bone.color.custom.select
                newPBone.bone.color.custom.active = oldPBone.bone.color.custom.active

            newPBone.bone.is_rotf = True
        pass
    elif appVersion[0] == 3:
        for oldPBone, newPBone in zip(oldPBoneList, newPboneList):
            newPBone.rotation_mode = oldPBone.rotation_mode
            newPBone.bone_group = oldPBone.bone_group
            newPBone.bone.use_inherit_rotation = oldPBone.bone.use_inherit_rotation
            newPBone.bone.inherit_scale = oldPBone.bone.inherit_scale
            newPBone.bone.is_rotf = True