#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . AutoBoneOrient import AutoBoneOrientUtils

class AutoBoneOrientOperator(bpy.types.Operator):
    bl_idname = bl_idname = "view3d.auto_bone_orient_operator"
    bl_label = "Simple opreator"
    bl_description = "Creates basic FK rig on skeleton. Fixing orientation issues. Ideal for rigs coming from other 3D softwares, will cause issues if bones end in .###"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        AutoBoneOrientUtils.AutoBoneOrient(self, context)
        return {'FINISHED'}
