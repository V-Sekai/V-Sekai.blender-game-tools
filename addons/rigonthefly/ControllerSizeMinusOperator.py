#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . ControllerSizeMinus import ControllerSizeMinusUtils

class ControllerSizeMinusOperator(bpy.types.Operator):
    bl_idname = "view3d.controller_size_minus_operator"
    bl_label = "Simple operator"
    bl_description = "Decrease display size of selected controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ControllerSizeMinusUtils.ControllerSizeMinus(self, context)
        return {'FINISHED'}