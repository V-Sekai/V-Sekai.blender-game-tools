#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . InheritRotationOff import InheritRotationOffUtils

class InheritRotationOffOperator(bpy.types.Operator):
    bl_idname = "view3d.inherit_rotation_off_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected controllers to not inherit rotation from their parent controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        InheritRotationOffUtils.InheritRotationOff(self, context)
        return {'FINISHED'}