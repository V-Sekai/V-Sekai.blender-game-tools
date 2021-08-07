#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility
from . PolygonShapesUtility import PolygonShapes
from . RigProxy import RigProxyUtils
from . Utility import BakeOptions
from . DypsloomBake import DypsloomBakeUtils

class BakeProxyUtils:
    def BakeProxy (self, context):
        PolygonShapes.AddControllerShapes()

        copiedObject = bpy.context.active_object # object rig that drives the proxy rig
        copiedObjectN = copiedObject.name        

        proxyObject = bpy.data.objects[copiedObjectN.replace(".copy","")]
        proxyObject.hide_set(False)

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = proxyObject
        proxyObject.select_set(True)        

        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')

        bakeOptions=BakeOptions()
        if copiedObject.animation_data:
            bakeOptions.frame_start=copiedObject.animation_data.action.frame_range.x
            bakeOptions.frame_end=copiedObject.animation_data.action.frame_range.y

            StateUtility.BakeAnimationWithOptions(bakeOptions)
        #remove constraints on selected pose bones
        StateUtility.RemoveConstraintsOfSelectedPoseBones()
        obj = bpy.data.objects
        obj.remove(copiedObject, do_unlink=True)

