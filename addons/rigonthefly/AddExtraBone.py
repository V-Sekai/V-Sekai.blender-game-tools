#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility
from . PolygonShapesUtility import PolygonShapes

class AddExtraBoneUtils:

    def AddExtraBone (self,context):
        #add controller shapes to the scene
        PolygonShapes.AddControllerShapes()

        #force edit mode
        StateUtility.SetEditMode()

        obj = bpy.context.object
        armature = obj.data

        newBoneN = AddExtraBoneUtils.ExtraBoneName(1)

        newBoneE = armature.edit_bones.new(newBoneN)
        newBoneE.use_deform = False
        newBoneE.tail = (0,0,1) #tail position

        #find the matrix coordinates of the armature object
        objectMatrix = obj.matrix_world
        #invert armature's matrix to find where global(0,0,0) is in relation to the armature's position/roation
        objectMatrixInvert= objectMatrix.copy()
        objectMatrixInvert.invert()
        #set aim bone position to global (0,0,0) with axis following world's
        newBoneE.matrix = objectMatrixInvert

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #select new extra bone to change it's custom shape and viewport display
        armature.bones[newBoneN].select = True
        newBoneP = obj.pose.bones[newBoneN]
        newBoneP.custom_shape = bpy.data.objects["RotF_Locator"]
        armature.bones[newBoneN].show_wire=True

        #add pose bone's groups
        if obj.pose.bone_groups.get('RigOnTheFly Base') is None:
            baseBoneGroup = obj.pose.bone_groups.new(name="RigOnTheFly Base")
            baseBoneGroup.color_set = 'THEME09'
            newBoneP.bone_group = baseBoneGroup
        else:
            #set bone group of new extra bone to Base layer
            newBoneP.bone_group = obj.pose.bone_groups['RigOnTheFly Base']

        objDimensions = (obj.dimensions[0] + obj.dimensions[1] + obj.dimensions[2])/3
        objWorldScaleV = obj.matrix_world.to_scale()
        objWorldScale = (objWorldScaleV[0] + objWorldScaleV[1] + objWorldScaleV[2])/3
        objSize = objDimensions / objWorldScale
        sizeMultiplyer = objSize / newBoneP.length
        newBoneP.custom_shape_scale *= sizeMultiplyer/12
        
        return newBoneP


    @staticmethod
    def ExtraBoneName (count):
        boneName = "extra"+str(count)+".rig"

        if bpy.context.object.data.bones.get(boneName)==None:
            return boneName
        else:
            return AddExtraBoneUtils.ExtraBoneName(count+1)
