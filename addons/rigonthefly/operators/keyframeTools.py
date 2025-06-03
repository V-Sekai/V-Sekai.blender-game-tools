#########################################
#######       Rig On The Fly      #######
####### Copyright © 2022 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from ..core import keyRange
from ..core import offsetKeys
from ..core import keyAsActive

KEYRANGE_ID = '_ROTF_KEYRANGE'


class KeyRangeOperator(bpy.types.Operator):
    bl_idname = "rotf.key_range"
    bl_label = "Key Range"
    bl_description = "Add keys to selected controllers between the specified range"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        keyRange.KeyRange()
        return {'FINISHED'}

class OffsetKeysOperator(bpy.types.Operator):
    bl_idname = "rotf.offset_keys"
    bl_label = "Offset Keys"
    bl_description = "Offset selected keyframes of the selected controllers along the timeline"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = offsetKeys.OffsetKeys()
        if result != None:
            self.report(*result)
            return {'CANCELLED'}
        return {'FINISHED'}

class KeyAsActiveOperator(bpy.types.Operator):
    bl_idname = "rotf.key_as_active"
    bl_label = "Key Range"
    bl_description = "Key the controller selection on the same frames as the active controller"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        keyAsActive.KeyAsActive()
        return {'FINISHED'}