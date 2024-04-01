import bpy
from bpy.props import BoolProperty, EnumProperty

from ..core.modifier_utils import populate_bake_modifier_items
from ..core.faceit_utils import get_faceit_objects_list


class FACEIT_OT_LoadBakeModifiers(bpy.types.Operator):
    '''Find all bake operators on the registered objects.'''
    bl_idname = 'faceit.load_bake_modifiers'
    bl_label = 'Load Bake Modifiers'
    bl_options = {'UNDO', 'INTERNAL'}

    object_target: EnumProperty(
        items=(
            ('ACTIVE', 'Active Object', 'Active Object'),
            ('ALL', 'All Faceit Objects', 'All Faceit Objects')
        )
    )
    initialize: BoolProperty(
        name="Initialize",
        default=False,
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        target_objects = [context.object] if self.object_target == 'ACTIVE' else get_faceit_objects_list()
        populate_bake_modifier_items(target_objects)
        return {'FINISHED'}


class FACEIT_OT_MoveBakeModifier(bpy.types.Operator):
    '''Move Modfifiers to new index'''
    bl_idname = 'faceit.move_bake_modifier'
    bl_label = 'Move'
    bl_options = {'UNDO', 'INTERNAL'}

    # the name of the facial part
    direction: bpy.props.EnumProperty(
        items=(
            ('UP', 'Up', ''),
            ('DOWN', 'Down', ''),
        ),
        options={'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        return context.scene.faceit_face_objects

    def execute(self, context):
        scene = context.scene
        obj_idx = scene.faceit_face_index
        faceit_objects = scene.faceit_face_objects
        active_item = faceit_objects[obj_idx]
        obj = active_item.get_object()
        index = active_item.active_mod_index
        mod = obj.modifiers[index]
        list_length = len(obj.modifiers) - 1
        new_index = max(0, min((index + (-1 if self.direction == 'UP' else 1)), list_length))
        if bpy.app.version < (3, 6, 0):
            override = {'object': obj, 'active_object': obj}
            bpy.ops.object.modifier_move_to_index(override, modifier=mod.name, index=max(0, min(new_index, list_length)))
        else:
            obj.modifiers.move(index, new_index)
            active_item.modifiers.move(index, new_index)
        active_item.active_mod_index = new_index
        return {'FINISHED'}
