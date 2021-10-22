#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . AimSpace import AimSpaceUtils

class AimSpaceOperator(bpy.types.Operator):
    bl_idname = "view3d.aim_space_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected controllers to rotate using aim bones in world space"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        AimSpaceUtils.ChangeToAimSpace(self, context)
        return {'FINISHED'}