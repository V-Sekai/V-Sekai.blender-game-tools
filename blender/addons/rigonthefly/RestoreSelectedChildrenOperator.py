#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . RestoreParentSpace import RestoreParentSpaceUtils

class RestoreSelectedChildrenOperator(bpy.types.Operator):
    bl_idname = "view3d.restore_selected_children_operator"
    bl_label = "Simple operator"
    bl_description = "Restores selected .child.rig controllers to their original parents"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        RestoreParentSpaceUtils.RestoreSelectedChildren(self, context)
        return {'FINISHED'}