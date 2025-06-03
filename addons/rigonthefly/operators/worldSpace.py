import bpy
from ..core import worldSpace

WORLDSPACE_ID = '_ROTF_WORLDSPACE'


class WorldSpaceOperator(bpy.types.Operator):
    bl_idname = "rotf.world_space"
    bl_label = "World Space"
    bl_description = "Changes selected controllers to world space"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = worldSpace.WorldSpace()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}

class RemoveWorldSpaceOperator(bpy.types.Operator):
    bl_idname = "rotf.remove_world_space"
    bl_label = "Remove World Space"
    bl_description = "Changes selected world space controllers back to their original space"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = worldSpace.RemoveWorldSpace()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}