#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . OffsetKeys import OffsetKeysUtils

class OffsetKeysOperator(bpy.types.Operator):
    bl_idname = "view3d.offset_keys_operator"
    bl_label = "Simple operator"
    bl_description = "Offset the selected keys down the selection order"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        OffsetKeysUtils.OffsetKeys(self, context)
        return {'FINISHED' }