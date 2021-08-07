import bpy

from .. import gp_draw


class BGE_OT_fence_clear(bpy.types.Operator):
    bl_idname = "bge.fence_clear"
    bl_label = "Clear Fences"
    bl_description = "Clears all drawn fences in the scene"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        gp_draw.clear()
        return {'FINISHED'}
