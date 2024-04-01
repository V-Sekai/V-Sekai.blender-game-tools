
import csv
import json
import math
import os
from math import radians
from pathlib import PurePath

import bpy
import numpy as np
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty, FloatProperty
from bpy.types import Object, Action
from mathutils import Euler, Vector, Quaternion, Matrix


from ..core.faceit_data import get_a2f_shape_data, get_arkit_shape_data
from ..core import faceit_utils as futils
from ..core.fc_dr_utils import (frame_value_pairs_to_numpy_array,
                                populate_keyframe_points_from_np_array)
from ..core.pose_utils import reset_pb, reset_pose, restore_saved_pose, save_pose
from ..core.retarget_list_utils import get_all_set_target_shapes
from ..core.retarget_list_base import FaceRegionsBaseProperties
from ..core.shape_key_utils import get_shape_key_names_from_objects, set_slider_max, set_slider_min
from ..ctrl_rig import control_rig_utils as ctrl_utils
from ..ctrl_rig.control_rig_animation_operators import CRIG_ACTION_SUFFIX
from ..panels.draw_utils import draw_ctrl_rig_action_layout, draw_eye_action_layout, draw_head_action_layout, draw_shapes_action_layout, draw_text_block
from .mocap_utils import SmoothBaseProperties, gaussian_filter1d, get_scene_frame_rate, median_filter, moving_average_filter
from ..animate.animate_utils import convert_rotation_values, get_rotation_mode

# Number of channels for each rotation mode
CHANNELS_ROTATION_MODE_DICT = {
    'EULER': 3,
    'AXIS_ANGLE': 4,
    'QUATERNION': 4
}
# FC coordinates to blender (swap Z and Y)
CHANNELS_FACECAP_TO_BLENDER = {
    0: 1,
    1: 2,
    2: 1,
}

CHANNELS_EPIC_TO_BLENDER = {
    0: 2,
    1: 0,
    2: 1,
}

FACECAP_SCALE_TO_BLENDER = .01


class MocapBase:
    '''Store mocap values and general functions for live, recording, loading of animations.'''

    fps = 24
    # shape key animation
    objects = None
    source_shape_reference = []
    # the retarget_shapes prop list
    retarget_shapes = None
    # contains references to all target shape keys on all objects
    target_shapes_dict = {}
    use_region_filter = False
    active_regions_dict = {}
    animate_shapes = False
    flip_animation = False
    # Head Transform animation; either object or bone
    head_obj = None
    head_bone = None
    initial_head_rotation = None
    initial_eye_L_rotation = None
    initial_eye_R_rotation = None
    # The intial position of the head target
    initial_location_offset = None
    # The rotation mode in EULER, QUATERNION, AXSI_ANGLE
    head_rotation_mode = 'EULER'
    eye_L_rotation_mode = 'EULER'
    eye_R_rotation_mode = 'EULER'
    # The data path in rotation_euler, rotation_quaternion, rotation_axis_angle
    head_rotation_data_path = 'rotation_euler'
    # Multiply the head location (set by user)
    head_location_multiplier = 1.0
    # scale transforms to blender
    scene_scale_multiplier = 0.01

    source_rotation_units = 'DEG'  # ,'RAD'
    animate_head_rotation = False
    animate_head_location = False
    dynamic_sk_ranges = True
    # For Recording
    eye_rig = None
    eye_L_bone = None
    eye_R_bone = None
    animate_eye_bones = False
    animate_eye_shapes = False
    animation_timestamps = []
    sk_animation_lists = []
    head_rot_animation_lists = []
    head_loc_animation_lists = []
    eye_L_animation_lists = []
    eye_R_animation_lists = []

    # Face Smoothing
    use_smoothing_face = False
    smooth_window_face = 3
    smooth_regions = {}
    smooth_shape_names = []
    smooth_filter_face = 'SMA'  # MEDIAN, GAUSSIAN
    # Head Smoothing
    use_smoothing_head = False
    smooth_window_head = 3
    smooth_filter_head = 'SMA'  # MEDIAN, GAUSSIAN
    # Eye Smoothing
    use_smoothing_eye_bones = False
    smooth_window_eye_bones = 3
    smooth_filter_eye_bones = 'SMA'  # MEDIAN, GAUSSIAN

    sk_action: Action = None
    head_action: Action = None
    eye_action: Action = None

    def __init__(self):
        self._initialize_mocap_settings()
        try:
            self.fps = get_scene_frame_rate()
        except AttributeError:
            pass

    def set_face_smoothing(self, use_smoothing, smooth_regions=None, smooth_filter='SMA', smooth_window=0):
        self.smooth_regions = smooth_regions
        self.use_smoothing_face = use_smoothing
        self.smooth_window_face = smooth_window
        self.smooth_filter_face = smooth_filter

    def set_head_smoothing(self, use_smoothing, smooth_filter, smooth_window=0):
        self.use_smoothing_head = use_smoothing
        self.smooth_window_head = smooth_window
        self.smooth_filter_head = smooth_filter

    def set_eye_bones_smoothing(self, use_smoothing, smooth_filter, smooth_window=0):
        self.use_smoothing_eye_bones = use_smoothing
        self.smooth_window_eye_bones = smooth_window
        self.smooth_filter_eye_bones = smooth_filter

    def set_face_regions_dict(self, active_regions_dict):
        self.active_regions_dict = active_regions_dict

    def set_use_region_filter(self, use_region_filter):
        self.use_region_filter = use_region_filter

    def set_rotation_units(self, unit):
        '''Set rotation units in [DEGREES, RADIANS]'''
        self.source_rotation_units = unit

    def set_sk_action(self, action):
        self.sk_action = action

    def set_scene_frame_rate(self, fps):
        '''Overwrite the scene frame rate.'''
        self.fps = fps

    def set_head_action(self, action):
        self.head_action = action

    def set_eye_action(self, action):
        self.eye_action = action

    def set_source_shape_reference(self, source_shape_list):
        self.source_shape_reference = source_shape_list

    def set_shape_targets(self, objects=None, retarget_shapes=None, animate_eye_look_shapes=True, only_eye_look=False):
        if not objects or not retarget_shapes:
            self.animate_shapes = False
            self.animate_eye_shapes = False
            return
        self.objects = objects
        self.retarget_shapes = retarget_shapes
        self.target_shapes_dict = {}
        # Store references to the shape keys themselves.
        for shape_item in retarget_shapes:
            self.target_shapes_dict[shape_item.name] = []
            if hasattr(shape_item, 'region'):
                region = shape_item.region.lower()
                if region == 'eyes':
                    # if shape_item.name.startswith('eyeLook'):
                    if not animate_eye_look_shapes:
                        continue
                elif only_eye_look:
                    continue
                if self.use_region_filter:
                    if self.active_regions_dict[region] is False:
                        continue
                if self.use_smoothing_face:
                    if self.smooth_regions[region] is True:
                        self.smooth_shape_names.append(shape_item.name)
                # TODO: Skip eye_look shape keys if animate_eye_transforms is False
                # Consider to replace the bool prop animate_eye_transforms with an enum (string).
                # if SHAPES: animate just shapes
                # if BONES: animate just bones
                # if BOTH: animate both
            _target_shapes = []
            if self.flip_animation:
                if 'Left' in shape_item.name:
                    mirror_shape_item = retarget_shapes[shape_item.name.replace('Left', 'Right')]
                    _target_shapes = mirror_shape_item.target_shapes
                elif 'Right' in shape_item.name:
                    mirror_shape_item = retarget_shapes[shape_item.name.replace('Right', 'Left')]
                    _target_shapes = mirror_shape_item.target_shapes
            if not _target_shapes:
                _target_shapes = shape_item.target_shapes
            for obj in objects:
                if obj.data.shape_keys:
                    keys = obj.data.shape_keys.key_blocks
                    for ts in _target_shapes:
                        shape_key = keys.get(ts.name)
                        if shape_key:
                            self.target_shapes_dict[shape_item.name].append(shape_key)
        self.dynamic_sk_ranges = bpy.context.preferences.addons["faceit"].preferences.dynamic_shape_key_ranges

    def normalizeAngle(self, angle):
        """
        :param angle: (float)
        :return: (float) Angle in radian in [-pi, pi]
        """
        while angle > np.pi:
            angle -= 2.0 * np.pi
        while angle < -np.pi:
            angle += 2.0 * np.pi
        return angle

    def set_head_targets(
        self,
        head_obj: Object,
        head_bone_name="",
        head_loc_mult=1.0,
    ) -> None:
        '''Set the head target objects. Optionally specify a bone target. Set which channels should be animated (rotation, location).'''
        self.head_obj = head_obj
        self.head_bone = None
        head_rot_mode = 'EULER'
        if head_obj:
            head_rot_mode = get_rotation_mode(head_obj)
            if self.head_obj.type == 'ARMATURE':
                if head_bone_name:
                    self.head_bone = self.head_obj.pose.bones.get(head_bone_name)
                    world_head_mat = self.head_obj.convert_space(
                        pose_bone=self.head_bone, matrix=self.head_bone.matrix, to_space='WORLD', from_space='POSE')
                    self.initial_head_rotation = world_head_mat.to_quaternion()
                    # self.initial_head_rotation = (self.head_obj.matrix_world.inverted() @ self.head_bone.matrix).to_quaternion()  # self.head_bone.matrix.inverted()
                    if self.head_bone:
                        head_rot_mode = get_rotation_mode(self.head_bone)
                    else:
                        print(f"Couldn't find the bone {head_bone_name} for head animation.")
        else:
            print("You need to specify a valid target object (Object or Armature) in order to animate the head.")
            self.animate_head_location = False
            self.animate_head_rotation = False
            return
        self.head_rotation_data_path = "rotation_" + head_rot_mode.lower()
        self.head_location_multiplier = head_loc_mult * FACECAP_SCALE_TO_BLENDER
        self.head_rotation_mode = head_rot_mode

    def set_eye_targets(self, eye_rig, eye_L_bone_name, eye_R_bone_name):
        '''Set the eye target objects. Optionally specify a bone target.'''
        self.eye_rig = eye_rig
        self.eye_L_bone = None
        self.eye_R_bone = None
        if eye_rig is not None:
            if eye_L_bone_name:
                self.eye_L_bone = self.eye_rig.pose.bones.get(eye_L_bone_name)
                if self.eye_L_bone:
                    world_mat = self.eye_rig.convert_space(
                        pose_bone=self.eye_L_bone, matrix=self.eye_L_bone.matrix, to_space='WORLD', from_space='POSE')
                    self.initial_eye_L_rotation = world_mat.to_quaternion()
                    self.eye_L_rotation_mode = get_rotation_mode(self.eye_L_bone)
                    self.eye_L_rotation_data_path = "rotation_" + self.eye_L_rotation_mode.lower()
                else:
                    print(f"Couldn't find the bone {eye_L_bone_name} for eye animation.")
            if eye_R_bone_name:
                self.eye_R_bone = self.eye_rig.pose.bones.get(eye_R_bone_name)
                if self.eye_R_bone:
                    world_mat = self.eye_rig.convert_space(
                        pose_bone=self.eye_R_bone, matrix=self.eye_R_bone.matrix, to_space='WORLD', from_space='POSE')
                    self.initial_eye_R_rotation = world_mat.to_quaternion()
                    self.eye_R_rotation_mode = get_rotation_mode(self.eye_R_bone)
                    self.eye_R_rotation_data_path = "rotation_" + self.eye_R_rotation_mode.lower()
                else:
                    print(f"Couldn't find the bone {eye_R_bone_name} for eye animation.")

    def _initialize_mocap_settings(self):
        # self.shape_ref = list(get_face_cap_shape_data().keys())
        pass

    def flip_euler_rotation(self, e):
        return Euler((e.x, -e.y, -e.z), e.order)

    def deg_to_rad(self, e):
        '''Convert degrees to radians.'''
        return Euler(map(math.radians, e))

    def _head_rotation_to_blender(self, value=None):
        '''Bring the rotation into the correct format and orientation.'''
        if len(value) < 3:
            return
        rot = Euler(value, 'XYZ')
        # to Blender world coordinates (swap y and z and invert y)
        if self.source_rotation_units == 'DEG':
            rot = self.deg_to_rad(rot)
        if self.flip_animation:
            rot = self.flip_euler_rotation(rot)
        # convert Blender coordinates
        rot = Quaternion((rot.x, -rot.z, rot.y))
        if self.head_bone:
            # for some reason I need to conjugate the quaternion to get the correct rotation on bones
            rot = rot.conjugated()
            # Rotational difference between the incoming and the initial head rotation
            rot = rot.rotation_difference(self.initial_head_rotation)
            rot = self.initial_head_rotation.inverted() @ rot
        # if self.head_rotation_mode == 'EULER':
        #     rot = rot.to_euler()
        rot = convert_rotation_values(
            rot,
            rot_mode_from='QUATERNION',
            rot_mode_to=self.head_rotation_mode
        )
        return rot

    def _eye_L_rotation_to_blender(self, value: list = None):
        if len(value) < 2:
            return
        rot = Euler(value, 'XYZ')
        # to Blender world coordinates (swap y and z and invert y)
        if self.source_rotation_units == 'DEG':
            rot = self.deg_to_rad(rot)
        if self.flip_animation:
            rot = self.flip_euler_rotation(rot)
        # convert Face Cap to Blender coordinates
        rot = Quaternion((rot.x, -rot.z, rot.y))
        if self.eye_L_bone:
            # for some reason I need to conjugate the quaternion to get the correct rotation
            rot = rot.conjugated()
            # Rotational difference between the incoming and the initial head rotation
            rot = rot.rotation_difference(self.initial_eye_L_rotation)
            rot = self.initial_eye_L_rotation.inverted() @ rot
        if self.eye_L_rotation_mode == 'EULER':
            rot = rot.to_euler()
        return rot

    def _eye_R_rotation_to_blender(self, value: list = None):
        if len(value) < 2:
            return
        rot = Euler(value, 'XYZ')
        # to Blender world coordinates (swap y and z and invert y)
        if self.source_rotation_units == 'DEG':
            rot = self.deg_to_rad(rot)
        if self.flip_animation:
            rot = self.flip_euler_rotation(rot)
        # convert Face Cap to Blender coordinates
        rot = Quaternion((rot.x, -rot.z, rot.y))
        if self.eye_R_bone:
            # for some reason I need to conjugate the quaternion to get the correct rotation
            rot = rot.conjugated()
            # Rotational difference between the incoming and the initial head rotation
            rot = rot.rotation_difference(self.initial_eye_R_rotation)
            rot = self.initial_eye_R_rotation.inverted() @ rot
        if self.eye_R_rotation_mode == 'EULER':
            rot = rot.to_euler()
        return rot

    def _location_to_blender(self, value=None):
        if not self.head_bone:
            loc = Vector((value[0], -value[2], value[1]))
        else:
            loc = Vector(value)
        if self.flip_animation:
            loc.x *= -1
        loc *= self.head_location_multiplier
        return loc

    def _get_initial_location_offset(self, value):
        '''Calculate the location offset from the first incoming location value'''
        offset = Vector()
        if bpy.context.scene.faceit_use_head_location_offset:
            if not self.head_bone:
                offset = self.head_obj.location.copy()
        self.initial_location_offset = offset - self._location_to_blender(value)

    def _anim_values_to_keyframes(self, fc, frames, anim_values):
        '''Convert animation values to keyframes
        Args:
        fc: animation fcurve
        frames: list of timestamps
        anim_values: the animation values for this fcurve
        '''
        mocap_keyframe_points = frame_value_pairs_to_numpy_array(frames, anim_values)
        populate_keyframe_points_from_np_array(
            fc,
            mocap_keyframe_points,
            add=True,
            join_with_existing=True
        )

    def parse_animation_data(self, data, frame_start=0, record_frame_rate=1000):
        '''Parse and populate the animation data into animation lists.'''
        pass

    def clear_animation_targets(self):
        self.animate_shapes = False
        self.objects = []
        self.target_shapes_dict = {}
        self.head_obj = None
        self.head_bone = None
        self.head_action = None
        self.eye_action = None

    def clear_animation_data(self):
        self.animation_timestamps = []
        self.sk_animation_lists = []
        self.head_rot_animation_lists = []
        self.head_loc_animation_lists = []
        self.eye_L_animation_lists = []
        self.eye_R_animation_lists = []

    def recording_to_keyframes(self) -> bool:
        sk_animation_lists = self.sk_animation_lists
        # Test smoothing
        head_rot_animation_lists = self.head_rot_animation_lists
        head_loc_animation_lists = self.head_loc_animation_lists
        eye_L_animation_lists = self.eye_L_animation_lists
        eye_R_animation_lists = self.eye_R_animation_lists
        keyframes_added = False
        if self.animate_shapes or self.animate_eye_shapes:
            if not self.sk_action:
                print("Couldn't find a valid shape key action.")
            if sk_animation_lists:
                sk_animation_lists = np.array(sk_animation_lists)
                # Shape Key animation (isolate all individual animation curves and convert to keyframes)
                for i, name in enumerate(self.source_shape_reference):
                    shape_keys = self.target_shapes_dict.get(name)
                    if not shape_keys:
                        continue
                    try:
                        anim_values = sk_animation_lists[:, i]
                    except IndexError:
                        print(f'failed at index {i}')
                        continue
                    if name.startswith('eyeLook') and self.use_smoothing_eye_bones:
                        if self.smooth_filter_eye_bones == 'SMA':
                            anim_values = moving_average_filter(anim_values, self.smooth_window_eye_bones)
                        elif self.smooth_filter_eye_bones == 'MEDIAN':
                            anim_values = median_filter(anim_values, kernel_size=self.smooth_window_eye_bones)
                        else:
                            anim_values = gaussian_filter1d(anim_values, self.smooth_window_eye_bones, 2)
                    # smooth values
                    elif self.use_smoothing_face and name in self.smooth_shape_names:
                        if self.smooth_filter_face == 'SMA':
                            anim_values = moving_average_filter(anim_values, self.smooth_window_face)
                        elif self.smooth_filter_face == 'MEDIAN':
                            anim_values = median_filter(anim_values, kernel_size=self.smooth_window_face)
                        else:
                            anim_values = gaussian_filter1d(anim_values, self.smooth_window_face, 2)
                    amplify = self.retarget_shapes[name].amplify
                    anim_values *= amplify
                    shape_dps = set()
                    for sk in shape_keys:
                        # Make sure that the shape key max/min values are set correctly
                        if self.dynamic_sk_ranges:
                            set_slider_max(sk, max(anim_values))
                            set_slider_min(sk, min(anim_values))
                        # print(min(min(sk.slider_max - 0.001, 0.0), min(anim_values)))
                        shape_dps.add(f"{sk.path_from_id()}.value")
                    for dp in shape_dps:
                        fc = self.sk_action.fcurves.find(dp)
                        if not fc:
                            fc = self.sk_action.fcurves.new(dp)
                        self._anim_values_to_keyframes(fc, self.animation_timestamps, anim_values)
                        keyframes_added = True

        # Head Transform Animation
        if self.head_obj and (self.animate_head_location or self.animate_head_rotation):
            head_dp_base = ""
            loc_dp = "location"
            rot_channel_count = CHANNELS_ROTATION_MODE_DICT.get(self.head_rotation_mode, 3)
            if not self.head_obj.animation_data:
                self.head_obj.animation_data_create()
            self.head_obj.animation_data.action = self.head_action
            if self.head_bone:
                head_dp_base = f'pose.bones["{self.head_bone.name}"].'
            # Head Rotation
            if self.animate_head_rotation and head_rot_animation_lists:
                # print(head_rot_animation_lists)
                head_rot_animation_lists = list(map(self._head_rotation_to_blender, head_rot_animation_lists))
                head_rot_animation_lists = np.array(head_rot_animation_lists)
                for i in range(rot_channel_count):
                    try:
                        anim_values = head_rot_animation_lists[:, i]
                    except IndexError:
                        print('Index Error when getting anim values from head rot:')
                        continue
                    if self.use_smoothing_head:
                        if self.smooth_filter_head == 'SMA':
                            anim_values = moving_average_filter(anim_values, self.smooth_window_head)
                        elif self.smooth_filter_head == 'MEDIAN':
                            anim_values = median_filter(anim_values, kernel_size=self.smooth_window_head)
                        else:
                            anim_values = gaussian_filter1d(anim_values, self.smooth_window_head, 2)
                    fc = self.head_action.fcurves.find(head_dp_base + self.head_rotation_data_path, index=i)
                    if not fc:
                        fc = self.head_action.fcurves.new(head_dp_base + self.head_rotation_data_path, index=i)
                    self._anim_values_to_keyframes(fc, self.animation_timestamps, anim_values)
                    keyframes_added = True
            # Head Location
            if self.animate_head_location and head_loc_animation_lists:
                head_loc_animation_lists = list(map(self._location_to_blender, head_loc_animation_lists))
                head_loc_animation_lists = np.array(head_loc_animation_lists)
                head_loc_animation_lists += self.initial_location_offset
                for i in range(3):
                    try:
                        anim_values = head_loc_animation_lists[:, i]
                    except IndexError:
                        print('Index Error when getting anim values from head loc:')
                        continue
                    if self.use_smoothing_head:
                        if self.smooth_filter_head == 'SMA':
                            anim_values = moving_average_filter(anim_values, self.smooth_window_head)
                        elif self.smooth_filter_head == 'MEDIAN':
                            anim_values = median_filter(anim_values, kernel_size=self.smooth_window_head)
                        else:
                            anim_values = gaussian_filter1d(anim_values, self.smooth_window_head, 2)
                    # blender_index = self.CHANNELS_FACECAP_TO_BLENDER_[i]
                    fc = self.head_action.fcurves.find(head_dp_base + loc_dp, index=i)
                    if not fc:
                        fc = self.head_action.fcurves.new(head_dp_base + loc_dp, index=i)
                    self._anim_values_to_keyframes(fc, self.animation_timestamps, anim_values)
                    keyframes_added = True
            # Eye Rotation
        if self.animate_eye_bones:
            if self.eye_L_bone:
                self.eye_rig.animation_data.action = self.eye_action
                rot_channel_count_L = CHANNELS_ROTATION_MODE_DICT.get(self.eye_L_rotation_mode, 3)
                eye_L_dp = f'pose.bones["{self.eye_L_bone.name}"].{self.eye_L_rotation_data_path}'
                eye_L_animation_lists = list(map(self._eye_L_rotation_to_blender, eye_L_animation_lists))
                eye_L_animation_lists = np.array(eye_L_animation_lists)
                # Left Eye Rotation
                for i in range(rot_channel_count_L):
                    try:
                        anim_values = eye_L_animation_lists[:, i]
                    except IndexError:
                        print('Index Error when getting anim values from eye rot:')
                        continue
                    if self.use_smoothing_eye_bones:
                        if self.smooth_filter_eye_bones == 'SMA':
                            anim_values = moving_average_filter(anim_values, self.smooth_window_eye_bones)
                        elif self.smooth_filter_eye_bones == 'MEDIAN':
                            anim_values = median_filter(anim_values, kernel_size=self.smooth_window_eye_bones)
                        else:
                            anim_values = gaussian_filter1d(anim_values, self.smooth_window_eye_bones, 2)
                    fc = self.eye_action.fcurves.find(eye_L_dp, index=i)
                    if not fc:
                        fc = self.eye_action.fcurves.new(eye_L_dp, index=i, action_group=self.eye_L_bone.name)
                    self._anim_values_to_keyframes(fc, self.animation_timestamps, anim_values)
                    keyframes_added = True
            # Right Eye Rotation
            if self.eye_R_bone:
                self.eye_rig.animation_data.action = self.eye_action
                rot_channel_count_R = CHANNELS_ROTATION_MODE_DICT.get(self.eye_R_rotation_mode, 3)
                eye_R_dp = f'pose.bones["{self.eye_R_bone.name}"].{self.eye_R_rotation_data_path}'
                eye_R_animation_lists = list(map(self._eye_R_rotation_to_blender, eye_R_animation_lists))
                eye_R_animation_lists = np.array(eye_R_animation_lists)
                for i in range(rot_channel_count_R):
                    try:
                        anim_values = eye_R_animation_lists[:, i]
                    except IndexError:
                        print('Index Error when getting anim values from eye rot:')
                        continue
                    if self.use_smoothing_eye_bones:
                        if self.smooth_filter_eye_bones == 'SMA':
                            anim_values = moving_average_filter(anim_values, self.smooth_window_eye_bones)
                        elif self.smooth_filter_eye_bones == 'MEDIAN':
                            anim_values = median_filter(anim_values, kernel_size=self.smooth_window_eye_bones)
                        else:
                            anim_values = gaussian_filter1d(anim_values, self.smooth_window_eye_bones, 2)
                    fc = self.eye_action.fcurves.find(eye_R_dp, index=i)
                    if not fc:
                        fc = self.eye_action.fcurves.new(eye_R_dp, index=i, action_group=self.eye_R_bone.name)
                    self._anim_values_to_keyframes(fc, self.animation_timestamps, anim_values)
                    keyframes_added = True
        return keyframes_added


def update_new_action_name(self, context):
    self.new_action_exists = bool(bpy.data.actions.get(self.new_action_name))


def update_bake_ctrl_rig(self, context):
    crig = futils.get_faceit_control_armature()
    if not crig.animation_data:
        crig.animation_data_create()


def update_frame_rate(self, context):
    self.record_frame_rate = int(self.frame_rate_presets)


class MocapImporterBase(FaceRegionsBaseProperties, SmoothBaseProperties):
    '''Base class for importing raw mocap data from text or csv files'''
    bl_label = "Import"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    new_action_name: StringProperty(
        name='New Action Name',
        update=update_new_action_name,
        options={'SKIP_SAVE', }
    )
    new_action_exists: BoolProperty(
        name='Action Exists',
        default=False,
        options={'SKIP_SAVE', }
    )
    overwrite_method: EnumProperty(
        name='Overwrite Method',
        items=(
            ('REPLACE', 'Replace', 'Replace the entire Action. All existing keyframes will be removed.'),
            ('MIX', 'Mix', 'Mix with existing keyframes, replacing only the new range.'),
        ),
        options={'SKIP_SAVE', }
    )
    bake_to_control_rig: BoolProperty(
        name='Bake to Control Rig',
        default=False,
        description='Loads the mocap action directly on the control rig. Creates a temp Action with the 52 Shape Keys.',
        update=update_bake_ctrl_rig,
        options={'SKIP_SAVE', }
    )
    frame_start: IntProperty(
        name='Start Frame',
        description='Start frame for the new keyframes. If append method is selected, the specified frame will present an offset to existing keyframes in the given action.',
        default=0,
        soft_min=0,
        soft_max=50000,
    )
    use_region_filter: BoolProperty(
        name='Filter Face Regions',
        default=False,
        description='Filter face regions that should be animated.'
    )
    set_scene_frame_range: BoolProperty(
        name='Set Scene Frame Range',
        description='Sets the scene frame range to the range of the new action',
        default=True,
    )
    audio_filename: StringProperty(
        name='Strip Name',
        default='',
        description='The name of the audio strip in sequencer',
        options={'SKIP_SAVE', }
    )
    load_audio_file: BoolProperty(
        name='Load Audio',
        default=False,
        options={'SKIP_SAVE', }
    )
    remove_audio_tracks_with_same_name: BoolProperty(
        name='Remove Identical Soundstrips',
        default=True,
        # options={'SKIP_SAVE', }
    )
    animate_head_rotation: BoolProperty(
        name="Rotation",
        default=True,
        description="Whether the recorded head rotation should be animated."
    )
    animate_head_location: BoolProperty(
        name="Location",
        default=False,
        description="Whether the recorded head location should be animated."
    )
    animate_shapes: BoolProperty(
        name="Animate Shapes",
        default=True,
        description="Whether the recorded expressions should be animated."
    )
    animate_eye_rotation_shapes: BoolProperty(
        name="Shapes",
        description="When this option is enabled, the shape keys for eye rotation are animated/recorded",
        default=True
    )
    animate_eye_rotation_bones: BoolProperty(
        name="Bones",
        description="When this option is enabled the rotation of the eyes (eye bones) is animated/recorded.",
        default=True
    )
    attempt_to_skip_shape_keys_on_eye_objects: BoolProperty(
        name='Attempt to Skip Shape Keys on Eye Objects',
        default=True,
        description='If the eye objects have shape keys, try to skip them when importing eye rotation to transforms. This avoids double deformation.'
    )
    can_bake_control_rig: BoolProperty(
        name="Can Bake Control Rig",
        default=True,
    )
    record_frame_rate: FloatProperty(
        name="Record Frame Rate",
        description="The frame rate used to record the animation data.",
        default=60.0,
        min=1,
        max=1000,
        soft_min=10,
        soft_max=200,
        options={'SKIP_SAVE'}
    )
    # record_frame_rate = 1 / 60
    frame_rate_presets: EnumProperty(
        name='Frame Rate',
        description='Set according to frame rate settings in Live Link Face app.',
        items=(
            ('24', '24', '24'),
            ('25', '25', '25'),
            ('30', '30', '30'),
            ('60', '60', '60'),
        ),
        default='60',
        update=update_frame_rate,
    )

    def __init__(self):
        self.engine_name = "FACECAP"
        self.can_load_audio = False
        self.target_shapes_prop_name = "faceit_arkit_retarget_shapes"
        self.engine_settings = None
        self.filename = ""
        # self.can_bake_control_rig = True
        self.can_import_head_location = True
        self.can_import_head_rotation = True
        self.can_import_eye_transforms = True

    @classmethod
    def poll(cls, context):
        return True

    def _get_engine_specific_settings(self, context):
        self.engine_settings = context.scene.faceit_live_mocap_settings.get(self.engine_name)

    def _get_mocap_importer(self) -> MocapBase:
        return MocapBase()

    def _get_engine_target_shapes(self, scene):
        return getattr(scene, self.target_shapes_prop_name)

    def _get_engine_target_objects(self, scene):
        return getattr(scene, self.target_objects_prop_name)

    def invoke(self, context, event):
        self._get_engine_specific_settings(context)
        self.can_import_head_location = self.engine_settings.can_animate_head_location
        self.can_import_head_rotation = self.engine_settings.can_animate_head_rotation
        self.can_import_eye_transforms = self.engine_settings.can_animate_eye_rotation
        raw_animation_data = self._get_raw_animation_data()
        if not raw_animation_data:
            self.report({'WARNING'}, "No recorded data found.")
            return {'CANCELLED'}
        if not self._check_file_path(self.engine_settings.filename):
            self.report({'ERROR'}, 'Mocap File not set or invalid')
            return {'CANCELLED'}
        self.filename = self._get_clean_filename(self.engine_settings.filename)
        if self.engine_name == 'A2F':
            if getattr(self, "a2f_solver", None):
                with open(self.engine_settings.filename, 'r') as f:
                    data = json.load(f)
                    if "exportFps" in data:
                        self.record_frame_rate = data.get("exportFps")
                        numPoses = data["numPoses"]
                        if numPoses == 52:
                            setattr(self, "a2f_solver", 'ARKIT')
                            setattr(self, "found_solver", 'ARKIT')
                        elif numPoses == 46:
                            setattr(self, "a2f_solver", 'A2F')
                            setattr(self, "found_solver", 'A2F')
                        else:
                            self.report(
                                {'ERROR'},
                                "It looks like you used a blendshape solver that is unknown in Faceit. Please reach out through discord or blendermarket for support.")
                            return {'CANCELLED'}
                if self.a2f_solver == 'ARKIT':
                    self.can_bake_control_rig = True
        elif self.engine_name == 'EPIC':
            # Read the frame rate from the file:
            with open(self.engine_settings.filename) as csvfile:
                reader = csv.reader(csvfile)
                timecodes = []
                for i, row in enumerate(reader):
                    if i == 0:
                        continue
                    elif i > 200:
                        break
                    timecodes.append(row[0])
                    # Extract the frame values
                frames = []
                for tc in timecodes:
                    frames.append(int(tc.split(':')[-1].split('.')[0]))
                self.record_frame_rate = max(frames) + 1

        ctrl_rig = context.scene.faceit_control_armature
        if ctrl_rig and self.can_bake_control_rig:
            if ctrl_utils.is_control_rig_connected(ctrl_rig):
                self.bake_to_control_rig = True
        else:
            self.can_bake_control_rig = False
        self.new_action_name = self.filename
        audio_file = self.engine_settings.audio_filename
        if audio_file:
            self.audio_filename = self._get_clean_filename(audio_file)
            self.can_load_audio = True
            self.load_audio_file = True

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        if self.engine_name in ('EPIC', 'A2F') and self._get_mocap_importer().__class__.__name__ != 'LiveAnimator':
            row = col.row(align=True)
            row.prop(self, "record_frame_rate")
            row.prop_menu_enum(self, "frame_rate_presets", text="", icon='DOWNARROW_HLT')
        row = col.row(align=True)
        row.label(text="Shapes Animation")
        row = col.row(align=True)
        row.prop(self, "animate_shapes", icon='BLANK1')
        if self.animate_shapes:
            if self.can_bake_control_rig:
                self._draw_control_rig_ui(col)
            if self.use_region_filter:
                icon = 'TRIA_DOWN'
            else:
                icon = 'TRIA_RIGHT'
            row = col.row(align=True)
            row.prop(self, 'use_region_filter', icon=icon)
            if self.use_region_filter:
                self._draw_region_filter_ui(self, col)
            # col.separator()
            row = col.row(align=True)
            row.prop(self, 'use_smooth_face_filter', text='Smooth Face', icon='MOD_SMOOTH')
            if self.use_smooth_face_filter:
                col.use_property_split = True
                col.separator()
                # row = col.row()
                # row.prop(self, 'smoothing_filter_face')
                row = col.row()
                row.prop(self, 'smooth_window_face')
                # self._draw_region_filter_ui(self.smooth_regions, col)
                col.separator()
                if self.brows or not self.use_region_filter:
                    row = col.row(align=True)
                    icon_value = 'CHECKBOX_HLT' if self.smooth_regions.brows else 'CHECKBOX_DEHLT'
                    row.prop(self.smooth_regions, 'brows', icon=icon_value)
                # if self.eyes or not self.use_region_filter:
                #     row = col.row(align=True)
                #     icon_value = 'CHECKBOX_HLT' if self.smooth_regions.eyes else 'CHECKBOX_DEHLT'
                #     row.prop(self.smooth_regions, 'eyes', icon=icon_value)
                if self.eyelids or not self.use_region_filter:
                    row = col.row(align=True)
                    icon_value = 'CHECKBOX_HLT' if self.smooth_regions.eyes else 'CHECKBOX_DEHLT'
                    row.prop(self.smooth_regions, 'eyelids', icon=icon_value)
                if self.cheeks or not self.use_region_filter:
                    row = col.row(align=True)
                    icon_value = 'CHECKBOX_HLT' if self.smooth_regions.cheeks else 'CHECKBOX_DEHLT'
                    row.prop(self.smooth_regions, 'cheeks', icon=icon_value)
                if self.nose or not self.use_region_filter:
                    row = col.row(align=True)
                    icon_value = 'CHECKBOX_HLT' if self.smooth_regions.nose else 'CHECKBOX_DEHLT'
                    row.prop(self.smooth_regions, 'nose', icon=icon_value)
                if self.mouth or not self.use_region_filter:
                    row = col.row(align=True)
                    icon_value = 'CHECKBOX_HLT' if self.smooth_regions.mouth else 'CHECKBOX_DEHLT'
                    row.prop(self.smooth_regions, 'mouth', icon=icon_value)
                if self.tongue or not self.use_region_filter:
                    row = col.row(align=True)
                    icon_value = 'CHECKBOX_HLT' if self.smooth_regions.tongue else 'CHECKBOX_DEHLT'
                    row.prop(self.smooth_regions, 'tongue', icon=icon_value)
                col.use_property_split = False
                col.separator()
            row = col.row(align=True)
            sub = row.split(align=True)
            sub.alignment = 'RIGHT'
            if self.bake_to_control_rig:
                sub.label(text="See Control Tab for Target Shapes Selection")
            else:
                sub.label(text="See Shapes Tab for Target Shapes Selection")
        if self.can_import_head_location or self.can_import_head_rotation:
            self._draw_head_motion_types(col)
            if self.animate_head_location or self.animate_head_rotation:
                row = col.row(align=True)
                row.prop(self, 'smooth_head', icon='MOD_SMOOTH')
                if self.smooth_head:
                    col.separator()
                    col.use_property_split = True
                    # row = col.row()
                    # row.prop(self, 'smoothing_filter_head')
                    row = col.row()
                    row.prop(self, 'smooth_window_head')
                col.use_property_split = False
                row = col.row(align=True)
                sub = row.split(align=True)
                sub.alignment = 'RIGHT'
                sub.label(text="See Head Setup for Target Selection")

        if self.can_import_eye_transforms:
            self._draw_eye_motion_types(col)
            if self.animate_eye_rotation_shapes or self.animate_eye_rotation_bones:
                row = col.row(align=True)
                row.prop(self, 'smooth_eye_look_animation', icon='MOD_SMOOTH')
                if self.smooth_eye_look_animation:
                    col.separator()
                    col.use_property_split = True
                    # row = col.row()
                    # row.prop(self, 'smoothing_filter_eye_bones')
                    row = col.row()
                    row.prop(self, 'smooth_window_eye_bones')
                    col.use_property_split = False
                row = col.row(align=True)
                sub = row.split(align=True)
                sub.alignment = 'RIGHT'
                sub.label(text="See Eye Setup for Eye Target Selection")
        if self.animate_shapes or self.animate_head_location or self.animate_head_rotation:
            self._draw_load_to_action_ui(col, context)
            col.use_property_split = True
            row = col.row(align=True)
            row.prop(self.engine_settings, "mirror_x", icon='MOD_MIRROR')
            col.use_property_split = False
        else:
            # if not (self.animate_head_location or self.animate_head_rotation):
            draw_text_block(
                context,
                layout=layout,
                text='Enable at least one type of motion.',
                heading='WARNING',
                in_operator=True,
            )
        self._draw_load_audio_ui(col)

    def _draw_load_to_action_ui(self, layout, context):
        scene = context.scene
        prop_split = layout.use_property_split
        layout.use_property_split = True
        layout.use_property_decorate = False

        row = layout.row()
        row.label(text='Action Settings')
        if self.bake_to_control_rig:
            ctrl_rig = scene.faceit_control_armature
            if ctrl_rig:
                draw_ctrl_rig_action_layout(layout, ctrl_rig)
        elif self.animate_shapes:
            draw_shapes_action_layout(layout, context)
        head_obj = scene.faceit_head_target_object
        if self.animate_head_location or self.animate_head_rotation:
            if head_obj:
                draw_head_action_layout(layout, head_obj)
        if self.animate_eye_rotation_bones:
            eye_rig = scene.faceit_eye_target_rig
            if eye_rig and eye_rig is not head_obj:
                draw_eye_action_layout(layout, eye_rig)
        layout.separator()
        row = layout.row()
        row.prop(self, 'overwrite_method', expand=True)
        row = layout.row()
        row.prop(self, 'frame_start', icon='CON_TRANSFORM')

        layout.use_property_split = prop_split

    def _draw_control_rig_ui(self, layout):
        row = layout.row()
        if futils.get_faceit_control_armature():
            row.prop(self, 'bake_to_control_rig', icon='CON_ARMATURE')

    def _draw_head_motion_types(self, layout):
        '''Draw the motion types for this operator.'''
        row = layout.row(align=True)
        row.label(text="Head Animation")
        row = layout.row(align=True)
        sub_row = row.row(align=True)
        sub_row.prop(self, "animate_head_rotation", icon='BLANK1')
        sub_row.enabled = self.can_import_head_rotation
        sub_row = row.row(align=True)
        sub_row.prop(self, "animate_head_location", icon='BLANK1')
        sub_row.enabled = self.can_import_head_location

    def _draw_eye_motion_types(self, layout):
        '''Draw the motion types for this operator.'''
        row = layout.row(align=True)
        row.label(text="Eye Rotation")
        row = layout.row(align=True)
        sub_row = row.row(align=True)
        sub_row.prop(self, "animate_eye_rotation_shapes", icon='BLANK1')
        # sub_row.enabled = self.can_import_head_rotation
        sub_row = row.row(align=True)
        sub_row.prop(self, "animate_eye_rotation_bones", icon='BLANK1')
        # sub_row.enabled = self.can_animate_eye_rotation

    def _draw_load_audio_ui(self, layout):
        if self.can_load_audio:
            row = layout.row()
            row.label(text='Audio (Sequencer)')
            row = layout.row()
            row.prop(self, 'load_audio_file', icon='SEQUENCE')
            if self.load_audio_file:
                row = layout.row()
                row.prop(self, 'audio_filename', icon='SEQUENCE')
                row = layout.row()
                row.prop(self, 'remove_audio_tracks_with_same_name', icon='TRASH')
            layout.separator()

    def _draw_region_filter_ui(self, regions_class, layout):
        layout = layout.column(align=True)
        row = layout.row(align=True)
        icon_value = 'CHECKBOX_HLT' if regions_class.brows else 'CHECKBOX_DEHLT'
        row.prop(regions_class, 'brows', icon=icon_value)
        # row = layout.row(align=True)
        # icon_value = 'CHECKBOX_HLT' if regions_class.eyes else 'CHECKBOX_DEHLT'
        # row.prop(regions_class, 'eyes', icon=icon_value)
        icon_value = 'CHECKBOX_HLT' if regions_class.eyelids else 'CHECKBOX_DEHLT'
        row.prop(regions_class, 'eyelids', icon=icon_value)
        row = layout.row(align=True)
        icon_value = 'CHECKBOX_HLT' if regions_class.cheeks else 'CHECKBOX_DEHLT'
        row.prop(regions_class, 'cheeks', icon=icon_value)
        icon_value = 'CHECKBOX_HLT' if regions_class.nose else 'CHECKBOX_DEHLT'
        row.prop(regions_class, 'nose', icon=icon_value)
        row = layout.row(align=True)
        icon_value = 'CHECKBOX_HLT' if regions_class.mouth else 'CHECKBOX_DEHLT'
        row.prop(regions_class, 'mouth', icon=icon_value)
        icon_value = 'CHECKBOX_HLT' if regions_class.tongue else 'CHECKBOX_DEHLT'
        row.prop(regions_class, 'tongue', icon=icon_value)

    def _check_file_path(self, filename):
        '''Returns True when filename is valid'''
        if not filename or not os.path.exists(filename) or not os.path.isfile(filename):
            return False
        return True

    def _get_clean_filename(self, filename):
        '''Returns the string filename - strips directories and file extension'''
        if filename:
            return PurePath(filename).stem

    def _get_action(self, action_name, replace=False):
        '''Get an action by name, create it if it does not exist'''
        action = bpy.data.actions.get(action_name)
        if action and replace:
            bpy.data.actions.remove(action, do_unlink=True)
            action = None
        if not action:
            self.report({'INFO'}, 'Creating new Action with name {}'.format(action_name))
            action = bpy.data.actions.new(name=action_name)
        return action

    def _load_new_audio_file(self, scene, start_frame_mocap, audio_file):
        channel = 1
        create_new = True
        if not scene.sequence_editor:
            scene.sequence_editor_create()
        else:
            soundstrip = scene.sequence_editor.sequences.get(self.audio_filename)
            if soundstrip:
                if soundstrip.frame_start == start_frame_mocap:
                    self.report(
                        {'INFO'},
                        f'The audio file {self.audio_filename} is already loaded on frame {start_frame_mocap}')
                    create_new = False
                else:
                    if self.remove_audio_tracks_with_same_name:
                        scene.sequence_editor.sequences.remove(soundstrip)
        if create_new:
            # Find the first free channel if the sequencer isn't empty
            occupied_channels = set((x.channel for x in scene.sequence_editor.sequences))
            if occupied_channels:
                possible_channels = set(range(1, max(occupied_channels) + 2))
                channel = min(possible_channels - occupied_channels)
            soundstrip = scene.sequence_editor.sequences.new_sound(
                self.audio_filename, audio_file, channel, start_frame_mocap)

        if soundstrip is not None:
            soundstrip.faceit_audio = True

    def _get_raw_animation_data(self):
        '''Return the raw animation data. Filename or osc queue for live animation'''
        return self.engine_settings.filename

    def _get_audio_file(self):
        '''Get the audio file.'''
        if self.load_audio_file:
            audio_file = self.engine_settings.audio_filename
            if not self._check_file_path(audio_file):
                self.report({'WARNING'}, 'Audio File not set or invalid')
                self.load_audio_file = False
                return None
            return audio_file
            # if audio_file:

    def execute(self, context):
        state_dict = futils.save_scene_state(context)
        animate_loc = self.animate_head_location
        animate_rot = self.animate_head_rotation
        animate_shapes = self.animate_shapes
        if not (animate_shapes or animate_loc or animate_rot or self.animate_eye_rotation_shapes or self.animate_eye_rotation_bones):
            self.report({'ERROR'}, "You need to enable at least one type of motion!")
            return {'CANCELLED'}
        raw_animation_data = self._get_raw_animation_data()
        if not raw_animation_data:
            self.report({'ERROR'}, "No recorded data found.")
            return {'CANCELLED'}
        for obj in context.scene.objects:
            futils.set_hidden_state_object(obj, False, False)
        if context.object is not None:
            bpy.ops.object.mode_set()
        audio_file = self._get_audio_file()
        mocap_importer = self._get_mocap_importer()
        mocap_importer.clear_animation_targets()
        mocap_importer.animate_head_location = animate_loc
        mocap_importer.animate_head_rotation = animate_rot
        mocap_importer.animate_shapes = animate_shapes
        mocap_importer.animate_eye_shapes = self.animate_eye_rotation_shapes
        mocap_importer.animate_eye_bones = self.animate_eye_rotation_bones
        mocap_importer.flip_animation = self.engine_settings.mirror_x
        mocap_importer.set_face_smoothing(
            use_smoothing=self.use_smooth_face_filter,
            smooth_regions=self.smooth_regions.get_active_regions(),
            smooth_filter=self.smoothing_filter_face,
            smooth_window=self.smooth_window_face
        )
        mocap_importer.set_head_smoothing(
            self.smooth_head,
            self.smoothing_filter_head,
            self.smooth_window_head
        )
        mocap_importer.set_eye_bones_smoothing(
            self.smooth_eye_look_animation,
            self.smoothing_filter_eye_bones,
            self.smooth_window_eye_bones
        )
        scene = context.scene
        start_frame_mocap = self.frame_start
        if animate_shapes or self.animate_eye_rotation_shapes:
            if getattr(self, "a2f_solver", None):
                if self.a2f_solver == 'A2F':
                    self.target_shapes_prop_name = "faceit_a2f_retarget_shapes"
                    mocap_importer.set_source_shape_reference(list(get_a2f_shape_data().keys()))
                else:
                    self.target_shapes_prop_name = "faceit_arkit_retarget_shapes"
                    mocap_importer.set_source_shape_reference(list(get_arkit_shape_data().keys()))
            if self.bake_to_control_rig:
                c_rig = futils.get_faceit_control_armature()
                if not c_rig:
                    self.report(
                        {'ERROR'},
                        'Can\'t find the active control rig. Please create/choose control rig first or import directly to the meshes.')
                    return {'CANCELLED'}
                # Get target action
                mocap_action = self._get_action("mocap_import", replace=True)
                # Get target objects and shapes
                target_objects = ctrl_utils.get_crig_objects_list(c_rig)
                target_shapes = c_rig.faceit_crig_targets
            else:
                # Get target action
                if scene.faceit_mocap_action is None or self.overwrite_method == 'REPLACE':
                    bpy.ops.faceit.new_action(
                        'EXEC_DEFAULT',
                        action_name=self.new_action_name,
                        overwrite_action=self.overwrite_method == 'REPLACE',
                        use_fake_user=True,
                    )
                mocap_action = scene.faceit_mocap_action
                target_objects = futils.get_faceit_objects_list()
                target_shapes = self._get_engine_target_shapes(scene)

            if not target_objects:
                self.report(
                    {'WARNING'},
                    'No registered objects found. {}'.format(
                        'Please update the control rig'
                        if self.bake_to_control_rig else
                        'Please register objects in Setup panel in order to animate shape keys.'))
                futils.restore_scene_state(context, state_dict)
                return {'CANCELLED'}
            available_shape_keys = set(get_shape_key_names_from_objects(objects=target_objects))
            if not available_shape_keys:
                self.report(
                    {'WARNING'},
                    'The registered objects hold no Shape Keys. Please create Shape Keys before loading mocap data.')
                futils.restore_scene_state(context, state_dict)
                return {'CANCELLED'}
            all_set_target_shapes = set(get_all_set_target_shapes(target_shapes))
            if all_set_target_shapes.intersection(available_shape_keys):
                # futils.restore_scene_state(context, state_dict)
                # return {'CANCELLED'}
                # TODO: Strip objects from target objects that are assigned to eye deform groups in case the eye rotation target is set to transforms.
                # Otherwise a double transformation will be applied.
                # Get the objects that are assigned to faceit_left_eyes_other and faceit_right_eyes_other
                # left_eye_objects = get_objects_with_vertex_group(vgroup_name='faceit_left_eyes_other', objects=target_objects, get_all=True)
                # if left_eye_objects:
                #     target_objects = [obj for obj in target_objects if obj not in left_eye_objects]
                # right_eye_objects = get_objects_with_vertex_group(vgroup_name='faceit_right_eyes_other', objects=target_objects, get_all=True)
                # if right_eye_objects:
                #     target_objects = [obj for obj in target_objects if obj not in right_eye_objects]
                # Shape Settings
                mocap_importer.use_region_filter = self.use_region_filter
                mocap_importer.active_regions_dict = self.get_active_regions()
                mocap_importer.set_shape_targets(
                    objects=target_objects,
                    retarget_shapes=target_shapes,
                    animate_eye_look_shapes=self.animate_eye_rotation_shapes,
                    only_eye_look=not animate_shapes,
                )
                mocap_importer.set_sk_action(mocap_action)
            else:
                self.report({'WARNING'}, 'Target Shapes are not properly configured. {}'.format(
                    'Please update the control rig' if self.bake_to_control_rig else 'Set up target shapes in Shapes panel.'))
        head_obj = None
        head_action = None
        if animate_loc or animate_rot:
            # Head Settings
            head_obj = context.scene.faceit_head_target_object
            head_loc_multiplier = self.engine_settings.head_location_multiplier
            head_bone_name = context.scene.faceit_head_sub_target
            saved_pose = None
            if head_obj:
                if head_obj.type == 'ARMATURE':
                    futils.set_active_object(head_obj.name)
                    futils.set_hide_obj(head_obj, False)
                    # It's important to reset the pose before setting the head targets to get accurate rotation data.
                    # Save the pose to restore it later
                    saved_pose = save_pose(head_obj)
                    # reset_pose(head_obj)
                    head_bone = head_obj.pose.bones.get(head_bone_name)
                    if head_bone:
                        reset_pb(head_bone)
                    dg = context.evaluated_depsgraph_get()
                    dg.update()
                mocap_importer.set_head_targets(
                    head_obj=head_obj,
                    head_bone_name=head_bone_name,
                    head_loc_mult=head_loc_multiplier,
                )
                if head_obj.animation_data:
                    head_action = head_obj.animation_data.action
                if head_action is None or self.overwrite_method == 'REPLACE':
                    bpy.ops.faceit.new_head_action(
                        'EXEC_DEFAULT',
                        overwrite_action=self.overwrite_method == 'REPLACE',
                        use_fake_user=True,
                    )
                    head_action = head_obj.animation_data.action
                mocap_importer.set_head_action(head_action)
            if saved_pose:
                restore_saved_pose(head_obj, saved_pose)
        if self.animate_eye_rotation_bones:
            saved_pose = None
            eye_rig = context.scene.faceit_eye_target_rig
            if eye_rig is not None:
                eye_L_bone_name = context.scene.faceit_eye_L_sub_target
                eye_R_bone_name = context.scene.faceit_eye_R_sub_target
                futils.set_hide_obj(eye_rig, False)
                saved_pose = save_pose(eye_rig)
                eye_L_bone = eye_rig.pose.bones.get(eye_L_bone_name)
                if eye_L_bone:
                    reset_pb(eye_L_bone)
                else:
                    eye_L_bone_name = None
                eye_R_bone = eye_rig.pose.bones.get(eye_R_bone_name)
                if eye_R_bone:
                    reset_pb(eye_R_bone)
                else:
                    eye_R_bone_name = None
                dg = context.evaluated_depsgraph_get()
                dg.update()
                if eye_R_bone or eye_L_bone:
                    mocap_importer.set_eye_targets(
                        eye_rig=eye_rig,
                        eye_L_bone_name=eye_L_bone_name,
                        eye_R_bone_name=eye_R_bone_name,
                    )
                    # Set the bone action
                    eye_action = None
                    if eye_rig is not head_obj or head_action is None:
                        if eye_rig.animation_data:
                            eye_action = eye_rig.animation_data.action
                        if (eye_action is None or self.overwrite_method == 'REPLACE'):
                            bpy.ops.faceit.new_eye_action(
                                'EXEC_DEFAULT',
                                overwrite_action=self.overwrite_method == 'REPLACE',
                                use_fake_user=True,
                            )
                            eye_action = eye_rig.animation_data.action
                        mocap_importer.set_eye_action(eye_action)
                    else:
                        mocap_importer.set_eye_action(head_action)
                else:
                    mocap_importer.animate_eye_bones = False
            if saved_pose:
                restore_saved_pose(eye_rig, saved_pose)
        # Process & Import Animation
        mocap_importer.fps = get_scene_frame_rate()
        mocap_importer.parse_animation_data(
            raw_animation_data,
            frame_start=self.frame_start,
            record_frame_rate=self.record_frame_rate
        )
        result = mocap_importer.recording_to_keyframes()
        if result == False:
            self.report({'ERROR'}, "Failed to import animation data.")
            futils.restore_scene_state(context, state_dict)
            return {'CANCELLED'}
        if self.set_scene_frame_range:
            if (animate_rot or animate_loc) and mocap_importer.head_action:
                try:
                    scene.frame_start, scene.frame_end = (int(x)
                                                          for x in futils.get_action_frame_range(
                                                          mocap_importer.head_action))
                except ReferenceError:
                    pass
        if animate_shapes:
            if self.bake_to_control_rig:
                if mocap_action.fcurves:
                    scene.faceit_bake_sk_to_crig_action = mocap_action
                    bpy.ops.faceit.bake_shape_keys_to_control_rig(
                        'EXEC_DEFAULT',
                        use_mocap_action=False,
                        overwrite_method=self.overwrite_method,
                        new_action_name=self.new_action_name + CRIG_ACTION_SUFFIX,
                        compensate_amplify_values=True,
                    )
                else:
                    self.report({'WARNING'}, 'No target shapes found. Please update control rig first!')
                    bpy.data.actions.remove(mocap_action, do_unlink=True)
                    mocap_action = None
                    futils.restore_scene_state(context, state_dict)
                    return {'CANCELLED'}
            else:
                bpy.ops.faceit.populate_action(action_name=mocap_action.name, set_frame_current=False)
                if self.set_scene_frame_range:
                    if animate_shapes and mocap_action is not None and mocap_action.fcurves:
                        try:
                            scene.frame_start, scene.frame_end = (int(x)
                                                                  for x in futils.get_action_frame_range(mocap_action))
                        except ReferenceError:
                            pass
        # ----------- Load Audio ----------------
        if self.load_audio_file:
            self._load_new_audio_file(scene, start_frame_mocap, audio_file)
        futils.restore_scene_state(context, state_dict)
        return {'FINISHED'}
