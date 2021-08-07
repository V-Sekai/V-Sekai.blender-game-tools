import bpy

from .. import bundles
from .. import modifiers
from ..modifiers import modifier_collider

from ..settings import engines


class BGE_OT_create_box_collider(bpy.types.Operator):
    """Creates a box collider"""
    bl_idname = "bge.create_box_collider"
    bl_label = "Create Box Collider"

    engine: bpy.props.EnumProperty(items=engines)

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object in context.selected_objects and (bpy.context.object.mode == 'OBJECT' or bpy.context.object.mode == 'EDIT')

    def execute(self, context):
        modifier_collider.create_box_collider(context.active_object, self.engine)
        return {'FINISHED'}
