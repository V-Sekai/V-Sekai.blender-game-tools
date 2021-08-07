#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . InheritScaleOn import InheritScaleOnUtils

class InheritScaleOnOperator(bpy.types.Operator):
    bl_idname = "view3d.inherit_scale_on_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected controllers to inherit scale from their parent controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        InheritScaleOnUtils.InheritScaleOn(self, context)
        return {'FINISHED'}