#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . TransformInertia import TransformInertiaUtils
from . TransformInertia import TransformDataUtils

class ScaleInertiaOperator(bpy.types.Operator):
    bl_idname = "view3d.scale_inertia_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected controllers' scale animation following inertia settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        frameStart = bpy.context.object.startFrame
        frameEnd = bpy.context.object.endFrame
        
        frameRange = list(range(frameStart, frameEnd))

        inertia = bpy.context.object.inertia

        getData = TransformDataUtils.GetScale
        setData = TransformDataUtils.SetScale

        keyingSet ='Scaling'

        TransformInertiaUtils.TransformInertia(self, context, inertia, frameRange, keyingSet, getData, setData)
        return {'FINISHED'}