#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from ..core import rotationModeAndRelations
from ..core import rotationDistribution

ROTATIONSCALETOOLS_ID = '_ROTF_ROTATIONSCALETOOLS'


class RotationModeAndRelationsOperator(bpy.types.Operator):
    bl_idname = "rotf.rotation_mode"
    bl_label = "Rotation Mode"
    bl_description = "Changes selected controllers' rotation mode"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    rotationMode : bpy.props.StringProperty()

    def execute(self, context):
        rotationModeAndRelations.RotationModeAndRelations(self.rotationMode, bpy.context.selected_pose_bones)
        return {'FINISHED'}
    
class InheritRotationOperator (bpy.types.Operator):
    bl_idname = "rotf.inherit_rotation"
    bl_label = "Inherit Rotation"
    bl_description = "Changes selected controllers' rotation inheritance"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    inheritRotation : bpy.props.BoolProperty()

    def execute(self, context):
        rotationModeAndRelations.InheritRotation(self.inheritRotation, bpy.context.selected_pose_bones)
        return {'FINISHED'}

class InheritScaleOperator(bpy.types.Operator):
    bl_idname = "rotf.inherit_scale"
    bl_label = "Inherit Scale"
    bl_description = "Changes selected controllers' scale inheritance"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    inheritScale : bpy.props.BoolProperty()
    def execute(self, context):
        rotationModeAndRelations.InheritScale(self.inheritScale, bpy.context.selected_pose_bones)
        return {'FINISHED'}

class RotationDistributionOperator(bpy.types.Operator):
    bl_idname = "rotf.rotation_distribution"
    bl_label = "Rotation Distribution"
    bl_description = "Distributes rotation from the selected bone down the hierarchy depending on the chain length"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = rotationDistribution.RotationDistribution()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}

class ApplyRotationDistributionOperator(bpy.types.Operator):
    bl_idname = "rotf.apply_rotation_distribution"
    bl_label = "Apply Rotation Distribution"
    bl_description = "Apply the rotation distribution"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = rotationDistribution.ApplyRotationDistribution()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}