#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . RemoveTwist import RemoveTwistUtils

class RemoveTwistOperator(bpy.types.Operator):
    bl_idname = "view3d.remove_twist_operator"
    bl_label = "Simple operator"
    bl_description = "Remove twist constraint of base bones driven by the selected controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        RemoveTwistUtils.RemoveTwist(self, context)
        return {'FINISHED'}