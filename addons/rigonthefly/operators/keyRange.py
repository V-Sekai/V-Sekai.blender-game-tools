#########################################
#######       Rig On The Fly      #######
####### Copyright © 2022 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from ..core import keyRange

KEYRANGE_ID = '_ROTF_KEYRANGE'


class KeyRangeOperator(bpy.types.Operator):
    bl_idname = "rotf.key_range"
    bl_label = "Key Range"
    bl_description = "Add keys to selected controllers between the specified range"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        keyRange.KeyRange()
        return {'FINISHED'}