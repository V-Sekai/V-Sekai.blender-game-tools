#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy

class ControllerSizeMinusOperator(bpy.types.Operator):
    bl_idname = "view3d.controller_size_minus"
    bl_label = "Shape Size Minus"
    bl_description = "Decrease display size of selected controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selectedRigBonesListP = list(bpy.context.selected_pose_bones)
        for selectedPBone in selectedRigBonesListP:
            selectedPBone.custom_shape_scale_xyz *= 0.8
        return {'FINISHED'}

class ControllerSizePlusOperator(bpy.types.Operator):
    bl_idname = "view3d.controller_size_plus"
    bl_label = "Shape Size Plus"
    bl_description = "Increase display size of selected controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selectedRigBonesListP = list(bpy.context.selected_pose_bones)
        for selectedPBone in selectedRigBonesListP:
            selectedPBone.custom_shape_scale_xyz *= 1.2
        return {'FINISHED'}

