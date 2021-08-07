#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . ApplyDistribution import ApplyDistributionUtils

class ApplyDistributionOperator(bpy.types.Operator):
    bl_idname = "view3d.apply_distribution_operator"
    bl_label = "Simple operator"
    bl_description = "Removes selected .parent.rig controllers and it's related controllers and bakes affected controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ApplyDistributionUtils.ApplyDistribution(self, context)
        return {'FINISHED'}