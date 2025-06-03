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
        for pbone in selectedRigBonesListP:
            pbone.custom_shape_scale_xyz *= 0.8
            if context.scene.rotf_mirror_controller_size:
                scaleMirrorPBone(pbone)
        return {'FINISHED'}

class ControllerSizePlusOperator(bpy.types.Operator):
    bl_idname = "view3d.controller_size_plus"
    bl_label = "Shape Size Plus"
    bl_description = "Increase display size of selected controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selectedRigBonesListP = list(bpy.context.selected_pose_bones)
        for pbone in selectedRigBonesListP:
            pbone.custom_shape_scale_xyz *= 1.2
            if context.scene.rotf_mirror_controller_size:
                scaleMirrorPBone(pbone)
        return {'FINISHED'}

def scaleMirrorPBone(pbone):
    leftSide = ["left","_l","l_",".l","l.","-l","l-"," left","left "]
    rightSide = ["right","_r","r_",".r","r.","-r","r-"," right","right "]
    
    boneNameMirror = ""
    for i, left in enumerate(leftSide):
        if pbone.name.casefold().startswith(left):
            rightPrefix = switchSide(pbone.name[:len(left)], rightSide[i])
            boneNameMirror = rightPrefix + pbone.name[len(left):]
            break
        if pbone.name.casefold().endswith(left):
            rightSuffix = switchSide(pbone.name[-len(left):], rightSide[i])
            boneNameMirror = pbone.name[:-len(left)] + rightSuffix
            break

    for i, right in enumerate(rightSide):
        if pbone.name.casefold().startswith(right):
            leftPrefix = switchSide(pbone.name[:len(right)], leftSide[i])
            boneNameMirror = leftPrefix + pbone.name[len(right):]
            break
        if pbone.name.casefold().endswith(right):
            leftSuffix = switchSide(pbone.name[-len(right):], leftSide[i])
            boneNameMirror = pbone.name[:-len(right)] + leftSuffix
            break
        
    obj = pbone.id_data
    pboneMirror = obj.pose.bones.get(boneNameMirror)

    if pboneMirror:
        pboneMirror.custom_shape_scale_xyz = pbone.custom_shape_scale_xyz

def switchSide(boneNSide, oppositeSide):
    
    switchedSide = ""
    for leftLetter, rightLetter in zip(boneNSide, oppositeSide):
        if leftLetter.isupper():
            switchedSide += rightLetter.upper()
        else:
            switchedSide += rightLetter

    if len(oppositeSide) > len(boneNSide):
        switchedSide += oppositeSide[len(switchedSide):]
    return switchedSide