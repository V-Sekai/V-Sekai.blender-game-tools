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

def AddBone():
    obj = bpy.context.object
    CreateBone(obj, prefix="Extra")
    
def CreateBone(obj, prefix):
    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    mirrorX = bpy.context.object.data.use_mirror_x
    bpy.context.object.data.use_mirror_x = False

    obj = bpy.context.object
    armature = obj.data

    newBoneN = ExtraBoneName(obj, prefix, 1)

    newEBone = armature.edit_bones.new(newBoneN)
    newEBone.use_deform = False
    newEBone.tail = (0,0,1) #tail position

    #find the matrix coordinates of the armature object
    objectMatrix = obj.matrix_world
    #invert armature's matrix to find where global(0,0,0) is in relation to the armature's position/roation
    objectMatrixInvert= objectMatrix.copy()
    objectMatrixInvert.invert()
    #set aim bone position to global (0,0,0) with axis following world's
    newEBone.matrix = objectMatrixInvert

    bpy.context.object.data.use_mirror_x = mirrorX

    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    #select new extra bone to change it's custom shape and viewport display
    armature.bones[newBoneN].select = True
    newPBone = obj.pose.bones[newBoneN]
    #assign controller shape to worldPbone
    newBone_customShape = bpy.context.scene.rotf_extraBone_customShape
    if newBone_customShape == None:
        importControllerShapes.ImportControllerShapes(["RotF_Locator"])
        newPBone.custom_shape = bpy.data.objects['RotF_Locator']
    else:
        newPBone.custom_shape = bpy.data.objects[newBone_customShape.name]
        
    newPBone.bone.show_wire=False

    newPBone.bone.is_rotf = True #mark newPBone as a rotf bone
    return newPBone.name

def ExtraBoneName(obj, prefix, count):
    boneName = prefix+str(count)

    if obj.data.bones.get(boneName)==None:
        return boneName
    else:
        return ExtraBoneName(obj, prefix, count+1)
