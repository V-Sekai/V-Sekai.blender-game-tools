#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . AddExtraBone import AddExtraBoneUtils

class AddExtraBoneOperator(bpy.types.Operator):
    bl_idname = "view3d.add_extra_bone_operator"
    bl_label = "Simple operator"
    bl_description = "adds an extra bone at the center of the scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        AddExtraBoneUtils.AddExtraBone(self, context)
        return {'FINISHED'}