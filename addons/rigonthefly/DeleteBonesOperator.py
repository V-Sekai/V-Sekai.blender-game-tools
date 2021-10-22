#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . DeleteBones import DeleteBonesUtils

class DeleteBonesOperator(bpy.types.Operator):
    bl_idname = "view3d.delete_bones_operator"
    bl_label = "Simple operator"
    bl_description = "delete selected bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        DeleteBonesUtils.DeleteBones(self, context)
        return {'FINISHED'}