#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . AddTwist import AddTwistUtils

class AddTwistOperator(bpy.types.Operator):
    bl_idname = "view3d.add_twist_operator"
    bl_label = "Simple operator"
    bl_description = "Makes bones driven by the selected controllers partially follow the active controller's Y rotation."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        AddTwistUtils.AddTwist(self, context)
        return {'FINISHED'}