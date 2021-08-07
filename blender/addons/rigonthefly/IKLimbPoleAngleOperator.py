#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . IKLimbPoleAngle import IKLimbPoleAngleUtils

class IKLimbPoleAngleOperator(bpy.types.Operator):
    bl_idname = "view3d.ik_pole_angle_operator"
    bl_label = "Simple operator"
    bl_description = "Turns selected ik pole angles by 90°"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        IKLimbPoleAngleUtils.IKLimbPoleAngle(self, context)
        return {'FINISHED'}