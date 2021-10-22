#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . AimWorld import AimWorldUtils

class AimWorldOperator(bpy.types.Operator):
    bl_idname = "view3d.aim_world_operator"
    bl_label = "Simple operator"
    bl_description = "Changes rig selected bones to aim world"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        AimWorldUtils.ChangeToAimWorld(self, context)
        return {'FINISHED'}