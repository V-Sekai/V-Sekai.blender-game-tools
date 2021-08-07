#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . KeyRange import KeyRangeUtils

class KeyRangeOperator(bpy.types.Operator):
    bl_idname = "view3d.key_range_operator"
    bl_label = "Simple operator"
    bl_description = "Add keys on selected controllers on available channels between frames Start and End"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        KeyRangeUtils.KeyRange(self, context)
        return {'FINISHED'}