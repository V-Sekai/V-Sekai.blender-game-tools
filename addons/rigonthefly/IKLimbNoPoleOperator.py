#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . IKLimbNoPole import IKLimbNoPoleUtils

class IKLimbNoPoleOperator(bpy.types.Operator):
    bl_idname = "view3d.ik_limb_no_pole_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected controllers and their two parents to work in IK with no pole vector. Use this if regular IK does not give expected results"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        IKLimbNoPoleUtils.IKLimbNoPole(self, context)
        return {'FINISHED'}