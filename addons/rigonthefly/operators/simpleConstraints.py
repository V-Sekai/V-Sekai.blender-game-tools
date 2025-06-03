#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from ..core import simpleCopyTransforms
from ..core import simpleAim
from ..core import simpleConstraints

SIMPLECONSTRAINTS_ID = '_ROTF_SIMPLECONSTRAINTS'


class SimpleCopyTransformsOperator(bpy.types.Operator):
    bl_idname = "rotf.simple_copy_transforms"
    bl_label = "Simple Copy Transforms"
    bl_description = "Adds a copy constraint with the active pose bone as the target"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        simpleCopyTransforms.SimpleCopyTransforms()
        return {'FINISHED'}

class SimpleAimOperator(bpy.types.Operator):
    bl_idname = "rotf.simple_aim"
    bl_label = "Simple Aim"
    bl_description = "Adds an aim constraint with the next controller in the selection order as the target"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        simpleAim.SimpleAim()
        return {'FINISHED'}

class RemoveSimpleConstraintsOperator(bpy.types.Operator):
    bl_idname = "rotf.remove_simple_constraints"
    bl_label = "Remove Simple Constraint"
    bl_description = "Removes simple constraints on the selected bones"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        simpleConstraints.RemoveSimpleConstraints()
        return {'FINISHED'}

class BakeSimpleConstraintsOperator(bpy.types.Operator):
    bl_idname = "rotf.bake_simple_constraints"
    bl_label = "Bake Simple Constraints"
    bl_description = "Bakes and removes simple constraints on the selected bones"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        simpleConstraints.BakeSimpleConstraints()
        return {'FINISHED'}