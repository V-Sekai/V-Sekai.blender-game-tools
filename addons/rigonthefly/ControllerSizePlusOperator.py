#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . ControllerSizePlus import ControllerSizePlusUtils

class ControllerSizePlusOperator(bpy.types.Operator):
    bl_idname = "view3d.controller_size_plus_operator"
    bl_label = "Simple operator"
    bl_description = "Increase display size of selected controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ControllerSizePlusUtils.ControllerSizePlus(self, context)
        return {'FINISHED'}