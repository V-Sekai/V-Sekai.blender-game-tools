
import bpy

from .. import modifiers


class BGE_OT_modifier_info(bpy.types.Operator):
    """Shows the modifier tooltip"""
    bl_idname = "bge.modifier_info"
    bl_label = "Show modifier info"

    modifier_name: bpy.props.StringProperty()

    @classmethod
    def description(cls, context, properties):
        for x in modifiers.modifiers_dict.values():
            if x['global'].id == properties.modifier_name:
                return x['global'].tooltip

    def invoke(self, context, event):
        return {'FINISHED'}
