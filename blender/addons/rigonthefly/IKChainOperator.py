#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . IKChain import IKChainUtils

class IKChainOperator(bpy.types.Operator):
    bl_idname = "view3d.ik_chain_operator"
    bl_label = "Simple operator"
    bl_description = "add IK to each bone in a chain pointing it's child bone"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        IKChainUtils.IKChain(self, context)
        return {'FINISHED'}