#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . LocalAimChain import LocalAimChainUtils

class LocalStretchChainOperator(bpy.types.Operator):
    bl_idname = "view3d.local_stretch_chain_operator"
    bl_label = "Simple operator"
    bl_description = "Add stretch constraint to the selection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        stretch = True
        result = LocalAimChainUtils.LocalAimChain(self, context, stretch)
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}