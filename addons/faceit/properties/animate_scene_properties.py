

import bpy
from bpy.types import Scene, PropertyGroup
from bpy.props import CollectionProperty, IntProperty, BoolProperty, StringProperty

from ..core import shape_key_utils
from ..core import faceit_utils as futils

# --------------- CLASSES --------------------
# | - Property Groups (Collection-/PointerProperty)
# ----------------------------------------------


class Anim_Properties(PropertyGroup):
    name: StringProperty(
        options=set(),
    )
    side: StringProperty(
        options=set(),
    )
    frame: IntProperty(
        options=set(),
    )
    index: IntProperty(
        options=set(),
    )
    mirror_name: StringProperty(
        options=set(),
    )
    corr_shape_key: BoolProperty(
        name='Shape Key',
        description='Corrective Shape Key active on this expression',
        default=False
    )


# --------------- FUNCTIONS --------------------
# | - Update/Getter/Setter
# ----------------------------------------------


def update_expression_list_index(self, context):
    scene = self

    if scene.faceit_expression_list:

        new_expression = scene.faceit_expression_list[scene.faceit_expression_list_index]

        rig = futils.get_faceit_armature()
        if rig:
            actions_disabled = rig.hide_viewport == True or scene.faceit_shapes_generated
        else:
            actions_disabled = scene.faceit_shapes_generated

        if actions_disabled:
            if self.faceit_sync_shapes_index:
                if new_expression:
                    bpy.ops.faceit.set_active_shape_key_index(
                        'EXEC_DEFAULT', shape_name=new_expression.name, get_arkit_target_shapes=False)
        else:
            use_mirror = new_expression.mirror_name == ''

            scene.frame_current = new_expression.frame

            if rig and scene.faceit_use_auto_mirror_x:
                rig.pose.use_mirror_x = use_mirror
            if context.scene.faceit_try_mirror_corrective_shapes:
                for obj in futils.get_faceit_objects_list():
                    obj.data.use_mirror_x = use_mirror


def update_corrective_shape_key_values(self, context):
    use_corr = self.faceit_use_corrective_shapes
    faceit_objects = futils.get_faceit_objects_list()
    for obj in faceit_objects:
        if shape_key_utils.has_shape_keys(obj):
            for sk in obj.data.shape_keys.key_blocks:
                if sk.name.startswith('faceit_cc_'):
                    sk.mute = not use_corr


def update_auto_mirror_x(self, context):
    rig = futils.get_faceit_armature()
    expression = self.faceit_expression_list[self.faceit_expression_list_index]
    use_mirror = expression.mirror_name == ''
    name = expression.name
    if rig is not None:
        rig.pose.use_mirror_x = use_mirror

    if expression.corr_shape_key and context.scene.faceit_try_mirror_corrective_shapes:
        for obj in futils.get_faceit_objects_list():
            obj.data.use_mirror_x = use_mirror


# --------------- REGISTER/UNREGISTER --------------------
# |
# --------------------------------------------------------


def register():

    Scene.faceit_expression_list_index = IntProperty(
        default=0,
        update=update_expression_list_index,
        options=set(),
    )

    Scene.faceit_expression_list = CollectionProperty(
        name='animation property collection',
        description='holds all expressions',
        type=Anim_Properties,
        options=set(),
    )

    Scene.faceit_use_corrective_shapes = BoolProperty(
        name='Use Corrective Shape Keys',
        description='Add Corrective Shape Keys to all generated Expressions. Shows options to add corrective shape for active object. (Prefix: "faceit_cc_")',
        default=True, update=update_corrective_shape_key_values,)

    Scene.faceit_try_mirror_corrective_shapes = BoolProperty(
        name='Try Mirror Corrective Shapes',
        description='Try to mirror the Corrective Shape Key for mirrored Expressions. all registered objects. (Prefix: "faceit_cc_")',
        default=True, update=update_corrective_shape_key_values,)

    Scene.faceit_shape_key_mirror_use_topology = BoolProperty(
        name='Use Topology',
        default=False,
    )

    Scene.faceit_use_auto_mirror_x = BoolProperty(
        name='Auto Mirror X',
        default=True,
        description='Automatically enable mirrorX pose option on expression change',
        update=update_auto_mirror_x,
    )


def unregister():
    del Scene.faceit_expression_list_index
    del Scene.faceit_expression_list
    del Scene.faceit_use_corrective_shapes
    del Scene.faceit_try_mirror_corrective_shapes
    del Scene.faceit_use_auto_mirror_x
