#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . AimChain import AimChainUtils

class AimChainOperator(bpy.types.Operator):
    bl_idname = "view3d.aim_chain_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected controllers to rotate aiming down the hierarchy of selected bones and switch their position to world space"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        AimChainUtils.ChangeToAimChain(self, context)
        return {'FINISHED'}