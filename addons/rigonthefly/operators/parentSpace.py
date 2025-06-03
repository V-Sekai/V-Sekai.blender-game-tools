#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from ..core import parentSpace
from ..core import parentOffsetSpace

PARENTSPACE_ID = '_ROTF_PARENTSPACE'


class ParentSpaceOperator(bpy.types.Operator):
    bl_idname = "rotf.parent_space"
    bl_label = "Parent Space"
    bl_description = "Changes selected controllers to parent space of the active bone"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = parentSpace.ParentSpace(False)
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}


class ParentCopySpaceOperator(bpy.types.Operator):
    bl_idname = "rotf.parent_copy_space"
    bl_label = "Parent Copy Space"
    bl_description = "Changes selected controllers to parent space of a copy of the active bone"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = parentSpace.ParentSpace(True)
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}

class ParentOffsetSpaceOperator(bpy.types.Operator):
    bl_idname = "rotf.parent_offset_space"
    bl_label = "Parent Offset Space"
    bl_description = "Changes selected controllers to parent space of the cursor's position"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = parentOffsetSpace.ParentOffsetSpace()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}

class RemoveParentSpaceOperator(bpy.types.Operator):
    bl_idname = "rotf.remove_parent_space"
    bl_label = "Remove Parent Space"
    bl_description = "Changes selected parent space controllers back to their original space"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = parentSpace.RemoveParentSpace()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}

class RemoveParentSpaceSiblingsOperator(bpy.types.Operator):
    bl_idname = "rotf.remove_parent_space_siblings"
    bl_label = "Remove Parent Space Siblings"
    bl_description = "Changes selected parent space controllers and their siblings back to their original space"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = parentSpace.RemoveSiblingsParentSpace()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}
