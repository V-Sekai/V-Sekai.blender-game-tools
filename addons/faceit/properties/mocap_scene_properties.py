from enum import Enum
from pydoc import describe
import bpy
from bpy.props import BoolProperty, EnumProperty, PointerProperty, StringProperty, IntProperty, FloatProperty
from bpy.types import PropertyGroup, Scene, SoundSequence, Object, Action

from ..core.retarget_list_base import FaceRegionsBase
from ..core.faceit_utils import get_faceit_objects_list

# --------------- CLASSES --------------------
# | - Property Groups (Collection-/PointerProperty)
# ----------------------------------------------


class Mocap_Engine_Properties(PropertyGroup):
    filename: StringProperty(
        name='Filename',
        default='',
    )
    audio_filename: StringProperty(
        name='Audio File',
        default='',
    )
    master_expanded: BoolProperty(
        name='Expand UI',
        default=False,
    )
    file_import_expanded: BoolProperty(
        name='Expand UI',
        default=False,
    )
    live_mode_expanded: BoolProperty(
        name='Expanded UI',
        default=False,
    )
    mocap_engine: StringProperty(
        name='Mocap Engine',
        description='The software or app to record or stream motion'
    )
    indices_order: StringProperty(
        name='Order of Shape Key Indices',
        description='The order of the Shape Keys used by this engine'
    )


# --------------- FUNCTIONS --------------------
# | - Update/Getter/Setter
# ----------------------------------------------


def update_record_face_cap(self, context):
    shape_key_set = False
    # if self.MOM_items:
    for item in self.MOM_Items:
        if not shape_key_set:
            if item.osc_address == '/W':
                item.record = self.faceit_record_face_cap
                shape_key_set = True
        elif item.osc_address != '/W':
            item.record = self.faceit_record_face_cap


def shapes_action_poll(self, action):
    '''Check if the action is suitable for shape key animation.'''
    return any(['key_block' in fc.data_path for fc in action.fcurves]) or len(action.fcurves) == 0


def rig_action_poll(self, action):
    '''Check if the action is suitable for shape key animation.'''
    return any(['pose.bones' in fc.data_path for fc in action.fcurves]) or len(action.fcurves) == 0


def head_action_poll(self, action):
    '''Check if the action is suitable for bone animation'''
    if action.name in ("faceit_shape_action", "faceit_shape_action"):
        return False
    head_obj = self.faceit_head_target_object
    if head_obj:
        if head_obj.type == 'ARMATURE':
            return any(['pose.bones' in fc.data_path for fc in action.fcurves]) or len(action.fcurves) == 0
        else:
            return not any(['pose.bones' in fc.data_path for fc in action.fcurves]) or len(action.fcurves) == 0


def update_head_target_object(self, context):
    '''Create animation data. Check if the sub target is valid for assigned armature.'''
    head_obj = self.faceit_head_target_object
    if not head_obj:
        return
    if not head_obj.animation_data:
        head_obj.animation_data_create()
    head_bone_name = self.faceit_head_sub_target
    if head_bone_name:
        if head_obj.type == 'ARMATURE':
            self.faceit_head_sub_target = head_bone_name if head_obj.pose.bones.get(head_bone_name) else ""


def update_mocap_action(self, context):
    action = self.faceit_mocap_action
    if action is None:
        bpy.ops.faceit.populate_action(remove_action=True, set_mocap_action=False)
    else:
        bpy.ops.faceit.populate_action(action_name=action.name, set_mocap_action=False)


def update_head_action(self, context):
    action = self.faceit_head_action
    if action is None:
        bpy.ops.faceit.populate_head_action(remove_action=True, set_mocap_action=False)
    else:
        bpy.ops.faceit.populate_head_action(action_name=action.name, set_mocap_action=False)


def register():
    ############## Mocap General ##################

    Scene.faceit_mocap_action = PointerProperty(
        type=bpy.types.Action,
        name='Shapes Action',
        poll=shapes_action_poll,
        update=update_mocap_action,
    )
    Scene.faceit_bake_sk_to_crig_action = PointerProperty(
        type=bpy.types.Action,
        name='Shapes Action',
        poll=shapes_action_poll,
        # update=update_mocap_action,
    )
    Scene.faceit_bake_crig_to_sk_action = PointerProperty(
        type=bpy.types.Action,
        name='Ctrl Rig Action',
        poll=rig_action_poll,
        # update=update_mocap_action,
    )
    Scene.faceit_head_target_object = PointerProperty(
        type=Object,
        name="Head Object",
        description="The Head Target Object. MESH or ARMATURE",
        update=update_head_target_object
    )
    Scene.faceit_head_sub_target = StringProperty(
        name="Head Bone",
        description="The Target Bone for OSC animation."
    )
    Scene.faceit_use_head_location_offset = BoolProperty(
        name="Use Head Offset",
        description="Use the current position as location offset. (Only for mesh objects)",
        default=True
    )
    Scene.faceit_head_action = PointerProperty(
        name="Head Action",
        type=Action,
        description="The active action on the head object. ARMATURE or BONE",
        update=update_head_action,
        poll=head_action_poll
    )
    ############## Face Cap App ##################

    Scene.faceit_face_cap_mocap_settings = PointerProperty(
        type=Mocap_Engine_Properties,
        name='Face Cap Properties',
    )
    Scene.faceit_record_face_cap = BoolProperty(
        name='Record Face Cap Live Mode',
        update=update_record_face_cap,
        default=False,
        description='Record on Play - Setup AddRoutes first'
    )

    ############## Live Link Face ##################

    Scene.faceit_epic_mocap_settings = PointerProperty(
        type=Mocap_Engine_Properties,
        name='Live Link Face Properties',
    )

    ############## Audio2Face ######################

    Scene.faceit_a2f_mocap_settings = PointerProperty(
        type=Mocap_Engine_Properties,
        name='Audio2Face Properties',
    )

    SoundSequence.faceit_audio = BoolProperty(
        name='Faceit Audio',
        description='Whether this is a Faceit audio sequence',
        default=False
    )

    ############## OSC #####################

    Scene.faceit_osc_address = StringProperty(
        name='Address',
        default='0.0.0.0',
        description='Enter the IP address of where the hallway tile app is currently running. Only works in MacOS for now.'
    )
    Scene.faceit_osc_port = IntProperty(
        name='Port',
        default=9001,
        description='Default Port = 9001',
    )
    Scene.faceit_osc_receiver_enabled = BoolProperty(
        name="Receiver Enabled",
        default=False,
        description="OSC Connection open/closed."
    )
    Scene.faceit_osc_animate_shapes = BoolProperty(
        name="Animate Shapes",
        description="Whether to animate ARKit target shape keys.",
        default=True,
    )
    Scene.faceit_osc_animate_head_rotation = BoolProperty(
        name="Head Rotation",
        description="Whether to animate the head rotation or not.",
        default=True,
    )
    Scene.faceit_osc_animate_head_location = BoolProperty(
        name="Head Location",
        description="Whether to animate the head location or not.",
        default=False,
    )
    Scene.faceit_osc_head_location_multiplier = FloatProperty(
        name="Location Multiplier",
        default=1.0,
        description="strengthen or weaken the head location effect."
    )
    Scene.faceit_osc_rotation_units = EnumProperty(
        name="Rotation Units",
        items=(
            ('RAD', 'Radians', 'Use radian as rotation untis'),
            ('DEG', 'Degrees', 'Use degree as rotation untis'),
        ),
        default='DEG'
    )
    Scene.faceit_osc_face_regions = PointerProperty(
        name='Face Regions (OSC)',
        type=FaceRegionsBase,
    )
    Scene.faceit_osc_use_region_filter = BoolProperty(
        name="Filter Target Shapes",
        default=False,
        description="Disable or enable the face regions filter for live animation."
    )
    Scene.faceit_osc_flip_animation = BoolProperty(
        name="Flip Animation",
        default=False,
        description="Flip the animation on the X axis."
    )
    Scene.faceit_auto_disconnect_ctrl_rig = BoolProperty(
        name="Auto Disconnect Drivers",
        description="Disconnect the control rig drivers while recording.",
        default=True,
    )


def unregister():
    del Scene.faceit_mocap_action
    del Scene.faceit_bake_sk_to_crig_action
    del Scene.faceit_face_cap_mocap_settings
    del Scene.faceit_record_face_cap
    del Scene.faceit_epic_mocap_settings
    del Scene.faceit_a2f_mocap_settings
    del SoundSequence.faceit_audio
    del Scene.faceit_osc_address
    del Scene.faceit_osc_port
    del Scene.faceit_osc_receiver_enabled
    del Scene.faceit_osc_face_regions
    del Scene.faceit_osc_animate_head_rotation
    del Scene.faceit_osc_animate_head_location
    del Scene.faceit_osc_head_location_multiplier
    del Scene.faceit_osc_rotation_units
    del Scene.faceit_head_target_object
    del Scene.faceit_head_sub_target
    del Scene.faceit_auto_disconnect_ctrl_rig
