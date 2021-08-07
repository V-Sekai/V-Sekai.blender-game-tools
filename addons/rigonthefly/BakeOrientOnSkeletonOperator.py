#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . BakeOrientOnSkeleton import BakeOrientOnSkeletonUtils

class BakeOrientOnSkeletonOperator(bpy.types.Operator):
    bl_idname = "view3d.bake_orient_on_skeleton_operator"
    bl_label = "Simple operator"
    bl_description = "Bake oriented animation on the base skeleton and remove controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        result = BakeOrientOnSkeletonUtils.BakeOrientOnSkeleton(self, context)
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}