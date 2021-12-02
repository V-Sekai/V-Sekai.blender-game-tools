import bpy
from bpy.types import Action, Object, PropertyGroup, Scene
from bpy.props import CollectionProperty, BoolProperty,  IntProperty, PointerProperty, EnumProperty

from ..properties.retarget_scene_properties import Retarget_Shapes
from ..core import faceit_utils as futils


def poll_is_obj_type_mesh(self, object):
    return object.type == 'MESH'


def poll_is_action_shape_key(self, action):
    return any(['key_block' in fc.data_path for fc in action.fcurves])


def get_mapping_targets_enum(self, context):
    items = (
        ('FACEIT', 'Registered Faceit Objects', 'Use all registered Faceit objects to find a valid shape key mapping'),
        ('TARGET', 'Single Target Object', 'Use a specific object to find a valid shape key mapping'),
    )
    c_rig = futils.get_faceit_control_armature()
    if c_rig:
        if c_rig.faceit_crig_objects:
            items += (('CRIG', 'Control Rig Targets', 'Use the control rig target objects as mapping targets'),)
    return items


class FBX_Retargeting(PropertyGroup):
    if bpy.app.version <= (2, 90, 0):
        mapping_target: EnumProperty(
            items=get_mapping_targets_enum,
        )
    else:
        mapping_target: EnumProperty(
            items=get_mapping_targets_enum,
            default=0,
        )
    mapping_source: EnumProperty(
        items=(
            ('OBJECT', 'Object', 'Find source Shape Keys on a Scene Object (type Mesh only)'),
            ('ACTION', 'Shape Key Action', 'Find source Shape Keys from a Shape Key Action'),
        ),
        default='OBJECT'
    )

    source_obj: PointerProperty(
        type=Object,
        name='Source Object',
        poll=poll_is_obj_type_mesh,
        description='Find source Shape Keys on a Scene Object (type Mesh only)',
    )
    source_action: PointerProperty(
        type=Action,
        name='Source Action',
        poll=poll_is_action_shape_key,
        description='Find source Shape Keys from a Shape Key Action'
    )
    target_obj: PointerProperty(
        type=Object,
        name='Target Object',
        poll=poll_is_obj_type_mesh,
        description='Use a specific object to find a valid shape key mapping (type mesh only)',
    )
    mapping_list: CollectionProperty(
        type=Retarget_Shapes,
        name='Retarget Shape Key Mapping'
    )
    mapping_list_index: IntProperty(
        name='List Index',
        default=0,
        options=set(),
    )
    expand_ui: BoolProperty(
        name='Expand UI',
        default=False,
        description='Exand the Retargeting UI',
    )
    # shapes_index = IntProperty(
    #     name='Expression Index',
    #     default=0,
    #     options=set(),
    # )


def register():
    ############## Mocap General ##################

    Scene.faceit_retarget_fbx_mapping = PointerProperty(
        type=FBX_Retargeting,
        name='FBX Mapping'
    )

    # Scene.faceit_retarget_fbx_shapes_index = IntProperty(
    #     name='Expression Index',
    #     default=0,
    #     options=set(),
    # )


def unregister():
    del Scene.faceit_retarget_fbx_mapping
