#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . AimOffset import AimOffsetUtils

class AimOffsetOperator(bpy.types.Operator):
    bl_idname = "view3d.aim_offset_operator"
    bl_label = "Simple operator"
    bl_description = "Makes Active controllers aim towards the 3d cursor's position"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        AimOffsetUtils.AimOffset(self, context)
        return {'FINISHED'}