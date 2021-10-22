#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . RemoveLocalAimChain import RemoveLocalAimChainUtils

class RemoveLocalAimChainOperator(bpy.types.Operator):
    bl_idname = "view3d.remove_local_aim_chain_operator"
    bl_label = "Simple operator"
    bl_description = "Bakes and removes the constraints of selected controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        result = RemoveLocalAimChainUtils.RemoveLocalAimChain(self, context)
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}