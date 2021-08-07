#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . InheritRotationOn import InheritRotationOnUtils

class InheritRotationOnOperator(bpy.types.Operator):
    bl_idname = "view3d.inherit_rotation_on_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected controllers to inherit rotation from their parent controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        InheritRotationOnUtils.InheritRotationOn(self, context)
        return {'FINISHED'}