#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . RotationDistribution import RotationDistributionUtils

class RotationDistributionOperator(bpy.types.Operator):
    bl_idname = "view3d.rotation_distribution_operator"
    bl_label = "Simple operator"
    bl_description = "Distributes rotation linearly from active bone down hierarchy of selected controllers. Select at least three controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        RotationDistributionUtils.RotationDistribution(self, context)
        return {'FINISHED'}