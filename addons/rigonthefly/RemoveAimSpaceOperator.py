#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . RemoveAimSpace import RemoveAimSpaceUtils

class RemoveAimSpaceOperator(bpy.types.Operator):
    bl_idname = "view3d.remove_aim_space_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected controllers containing .aim.rig in their name back to FK"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        RemoveAimSpaceUtils.RemoveAimSpace(self, context)
        return {'FINISHED'}