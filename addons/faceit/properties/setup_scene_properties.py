import bpy
from bpy.types import Scene, PropertyGroup, Object
from bpy.props import CollectionProperty, EnumProperty, IntProperty, BoolProperty, StringProperty, PointerProperty

from ..core import faceit_utils as futils

# --------------- CLASSES --------------------
# | - Property Groups (Collection-/PointerProperty)
# ----------------------------------------------


class Face_Objects(PropertyGroup):
    name: StringProperty(
        name='Object Name',
        description='object name'
    )
    # Problem with object ids, they have to be deleted globally,
    # otherwise they will never be none. Even if deleted from scene..
    obj_pointer: PointerProperty(
        name='Object',
        type=Object
    )
    part: StringProperty(
        name='Facial Part',
        description='The facial part that this object represents'
    )
    warnings: StringProperty(
        name='Warnigns',
        default=''
    )

    def get_object(self):
        return futils.get_object(self.name)


# --------------- FUNCTIONS --------------------
# | - Update/Getter/Setter
# ----------------------------------------------

def update_object_index(self, context):
    scene = self
    if context.mode != 'OBJECT':
        return
    if scene.faceit_face_index_updated != scene.faceit_face_index:
        scene.faceit_face_index_updated = scene.faceit_face_index

        # face_objects = futils.get_faceit_objects_list()
        face_objects = scene.faceit_face_objects

        index = scene.faceit_face_index
        item = face_objects[index]

        # if context.mode == 'EDIT_MESH':
        if context.object:
            if context.object.hide_viewport == False:
                bpy.ops.object.mode_set(mode='OBJECT')

        if futils.get_object(item.name):  # item.get_object():
            futils.clear_object_selection()
            futils.set_active_object(item.name)
            scene.faceit_active_object = context.active_object.name
        else:
            scene.faceit_face_objects.remove(index)
        scene.faceit_face_index_updated = -2


def is_armature_object_rigify(self, object):
    if object.type == 'ARMATURE':
        if object.data.get('rig_id') or object.data.get('faceit_rig_id') or object.name == 'FaceitRig' and object.name in bpy.context.scene.objects:
            return True


# --------------- REGISTER/UNREGISTER --------------------
# |
# --------------------------------------------------------


def register():

    Scene.faceit_face_objects = CollectionProperty(
        type=Face_Objects
    )
    Scene.faceit_face_index = IntProperty(
        default=0,
        update=update_object_index
    )
    Scene.faceit_face_index_updated = IntProperty(
        default=1,
    )
    Scene.faceit_active_object = StringProperty(
        default='',
    )

    Scene.faceit_show_warnings = BoolProperty(
        name='Show Warnings',
        default=False,
    )

    Scene.faceit_armature = PointerProperty(
        name='Faceit Armature',
        description='The armature to be used in the binding and baking operators. Needs to be a Rigify layout.',
        type=Object,
        poll=is_armature_object_rigify,
    )

    Scene.faceit_use_rigify_armature = BoolProperty(
        name='Use Existing Rigify Armature',
        default=False,
        description='When active, you can choose a Rigify Armature from the active scene. You can either use the Faceit Armature OR a Rigify Armature for creating the expressions.',
    )

    Scene.faceit_vgroup_assign_method = EnumProperty(
        name='Assign Method',
        items=(
            ('OVERWRITE', 'Replace', 'Overwrite the Vertex Groups previous assignment'),
            ('ADD', 'Add', 'Add selected verts to previously assigned vertices'),
        ),
    )


def unregister():
    del Scene.faceit_face_objects
    del Scene.faceit_face_index
    del Scene.faceit_face_index_updated
    del Scene.faceit_active_object
    del Scene.faceit_show_warnings
    del Scene.faceit_armature
    del Scene.faceit_use_rigify_armature
    del Scene.faceit_vgroup_assign_method
