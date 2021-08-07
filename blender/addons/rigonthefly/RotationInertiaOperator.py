#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . TransformInertia import TransformInertiaUtils
from . TransformInertia import TransformDataUtils

class RotationInertiaOperator(bpy.types.Operator):
    bl_idname = "view3d.rotation_inertia_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected controllers' rotation animation following inertia settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        frameStart = bpy.context.object.startFrame
        frameEnd = bpy.context.object.endFrame
        
        frameRange = list(range(frameStart, frameEnd))

        inertia = bpy.context.object.inertia

        getData = TransformDataUtils.GetRotation
        setData = TransformDataUtils.SetRotation

        keyingSet = 'Rotation'

        TransformInertiaUtils.TransformInertia(self, context, inertia, frameRange, keyingSet, getData, setData)
        return {'FINISHED'}