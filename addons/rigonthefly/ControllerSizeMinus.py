#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility

class ControllerSizeMinusUtils:

    def ControllerSizeMinus (self, context):
        selectedRigBonesListP = list(bpy.context.selected_pose_bones)
        for selectedBone in selectedRigBonesListP:
            selectedBone.custom_shape_scale *= 0.8