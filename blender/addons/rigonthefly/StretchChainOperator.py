#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . StretchChain import StretchChainUtils

class StretchChainOperator(bpy.types.Operator):
    bl_idname = "view3d.stretch_chain_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected controllers to rotate stretching down the hierarchy of selected bones and switch their position to world space"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        StretchChainUtils.ChangeToStretchChain(self, context)
        return {'FINISHED'}