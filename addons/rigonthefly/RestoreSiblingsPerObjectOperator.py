#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . RestoreParentSpace import RestoreParentSpaceUtils

class RestoreSiblingsPerObjectOperator(bpy.types.Operator):
    bl_idname = "view3d.restore_siblings_per_object_operator"
    bl_label = "Simple operator"
    bl_description = "Restores .child.rig controllers and all their .child.rig siblings to their original parents"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        RestoreParentSpaceUtils.SelectSiblingsPerArmature(self, context)
        RestoreParentSpaceUtils.RestoreSelectedChildren(self, context)        
        return {'FINISHED'}