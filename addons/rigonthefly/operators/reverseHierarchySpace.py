#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from ..core import reverseHierarchySpace

REORDERHIERARCHYSPAE_ID = "_ROTF_ReverseHierarchySpace"


class ReverseHierarchySpaceOperator(bpy.types.Operator):
    bl_idname = "rotf.reverse_hierarchy_space"
    bl_label = "Reorder Hierarchy Space"
    bl_description = "Changes the hierarchy of selected bones following the selection order"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = reverseHierarchySpace.ReverseHierarchySpace()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}

class RestoreHierarchySpaceOperator(bpy.types.Operator):
    bl_idname = "rotf.restore_hierarchy_space"
    bl_label = "Reset Hierarchy Space"
    bl_description = "Return reordered hierarchy to it's original hierarchy"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = reverseHierarchySpace.RestoreHierarchySpace()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}