#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils
from . PolygonShapesUtility import PolygonShapes

class LocalAimChainUtils:

    def LocalAimChain (self, context, stretch):
        PolygonShapes.AddControllerShapes() #add conrtoller shapes to the scene

        obj = bpy.context.object
        armature = obj.data

        #armature set to pose mode
        bpy.ops.object.mode_set(mode='POSE')

        selectedPoseBonesList = list()
        for i, pbone in enumerate(bpy.boneSelection):
            #checking if pbone does not already have an IK or Stretch To constraint
            for constraint in pbone.constraints:
                if any (constraint.type == cType for cType in ['IK','STRETCH_TO']):
                    return [{'WARNING'}, "some controllers already have aim constraints"]
            #checking if pbone has a child down the selection order
            nextInSelectionOrder = bpy.boneSelection[i+1:]
            for nextPbone in nextInSelectionOrder:
                if pbone in nextPbone.parent_recursive:
                    return [{'WARNING'}, "controllers cannot aim down hierarchy"]

            selectedPoseBonesList.append(pbone)#add pbone to selectedPoseBonesList

        for i in range(len(selectedPoseBonesList)-1):
            aimPBone = selectedPoseBonesList[i]
            targetPBone = selectedPoseBonesList[i+1]

            if aimPBone.custom_shape == bpy.data.objects["RotF_Circle"]:
                aimPBone.custom_shape = bpy.data.objects["RotF_CirclePointer+Y"]
            elif aimPBone.custom_shape == bpy.data.objects["RotF_Square"]:
                aimPBone.custom_shape = bpy.data.objects["RotF_SquarePointer+Y"]

            if stretch:
                LocalAimChainUtils.StretchToConstraint(obj, aimPBone, targetPBone)
            else:
                LocalAimChainUtils.IKConstraint(obj, aimPBone, targetPBone)

            if i > 0:
                aimPBoneParent = selectedPoseBonesList[i-1]
                aimPBone["Aim Parent"] = str(aimPBoneParent.name)

    @staticmethod
    def IKConstraint (obj, aimPBone, targetPBone):
        ik = aimPBone.constraints.new('IK')
        ik.target = obj
        ik.subtarget = targetPBone.name
        ik.chain_count = 1

    @staticmethod
    def StretchToConstraint (obj, aimPBone, targetPBone):
        stretchConstraint = aimPBone.constraints.new('STRETCH_TO')
        stretchConstraint.target = obj
        stretchConstraint.subtarget = targetPBone.name
        stretchConstraint.keep_axis = 'SWING_Y'
        