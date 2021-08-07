#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . FKLimb import FKLimbUtils

class FKLimbOperator(bpy.types.Operator):
    bl_idname = "view3d.fk_limb_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected IK handle controller back to working in FK"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        FKLimbUtils.FKLimb(self, context)
        return {'FINISHED'}