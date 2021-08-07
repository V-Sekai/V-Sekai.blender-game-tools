#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . IKLimb import IKLimbUtils

class IKLimbOperator(bpy.types.Operator):
    bl_idname = "view3d.ik_limb_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected controllers and their two parents to work in IK. Unexpected results if the limb chain does not have a clear bending angle in bind pose and/or middle controller has non 0 Y rotation"

    def execute(self, context):
        result = IKLimbUtils.IKLimb(self, context)
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}