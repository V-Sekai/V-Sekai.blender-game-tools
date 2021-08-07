#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . RemoveWorldTransforms import RemoveWorldTransformsUtils

class RemoveWorldTransformsOperator(bpy.types.Operator):
    bl_idname = "view3d.remove_world_transforms_operator"
    bl_label = "Simple operator"
    bl_description = "Returns selected controllers to local space"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        RemoveWorldTransformsUtils.RemoveWorldTransforms(self, context)
        return {'FINISHED'}