#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . InheritScaleOff import InheritScaleOffUtils

class InheritScaleOffOperator(bpy.types.Operator):
    bl_idname = "view3d.inherit_scale_off_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected controllers to not inherit scale from their parent controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        InheritScaleOffUtils.InheritScaleOff(self, context)
        return {'FINISHED'}