#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . RotationMode import RotationModeUtils

class RotationModeOperator(bpy.types.Operator):
    bl_idname = "view3d.rotation_mode_operator"
    bl_label = "Simple operator"
    bl_description = "Changes rotation mode of the selected controllers"
    bl_options = {'REGISTER', 'UNDO'}

    rotationMode: bpy.props.StringProperty(name="text",default='QUATERNION')

    def execute(self, context):

        print(self.rotationMode)

        RotationModeUtils.RotationMode(self, context, self.rotationMode)
        return {'FINISHED'}