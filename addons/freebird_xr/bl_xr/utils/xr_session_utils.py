# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
import bl_xr
from .geometry_utils import Pose, to_blender_axis_system as q

from mathutils import Vector, Quaternion
from bpy.types import XrSessionState, XrSessionSettings


class XRSession:
    @property
    def session_state(self) -> XrSessionState:
        return bpy.context.window_manager.xr_session_state

    @property
    def session_settings(self) -> XrSessionSettings:
        return bpy.context.window_manager.xr_session_settings

    @property
    def is_running(self) -> bool:
        return self.session_state and self.session_state.is_running(bpy.context)

    @property
    def viewer_pose(self) -> Pose:  # this is wrong, it should use the actual viewer_loc etc, not navigation_loc
        "Base offset applied to the XR Camera"
        return Pose(self.viewer_location, self.viewer_rotation, self.viewer_scale)

    @viewer_pose.setter
    def viewer_pose(self, pose: Pose):
        self.viewer_location = pose.position
        self.viewer_rotation = pose.rotation
        self.viewer_scale = pose.scale_factor

    @property
    def viewer_location(self) -> Vector:
        "Base offset applied to the XR Camera"
        return self.session_state.navigation_location if self.session_state else Vector()

    @viewer_location.setter
    def viewer_location(self, value: Vector):
        self.session_state.navigation_location = value

    @property
    def viewer_rotation(self) -> Quaternion:
        "Base offset applied to the XR Camera"
        return self.session_state.navigation_rotation if self.session_state else Quaternion()

    @viewer_rotation.setter
    def viewer_rotation(self, value: Quaternion):
        self.session_state.navigation_rotation = value

    @property
    def viewer_scale(self) -> float:
        "Zoom-out == larger values, zoom-in == smaller values"
        return self.session_state.navigation_scale * self.session_settings.base_scale if self.session_state else 1.0

    @viewer_scale.setter
    def viewer_scale(self, value: float):
        self.session_state.navigation_scale = value / self.session_settings.base_scale

    @property
    def viewer_camera_pose(self) -> Pose:
        "World pose of the XR Camera"
        return Pose(self.viewer_camera_position, self.viewer_camera_rotation, 1)

    @property
    def viewer_camera_position(self):
        "World position of the XR Camera"
        return self.session_state.viewer_pose_location

    @property
    def viewer_camera_rotation(self):
        "World rotation of the XR Camera"
        return q(self.session_state.viewer_pose_rotation)

    @property
    def show_controllers(self) -> bool:
        return self.session_settings.show_controllers

    @show_controllers.setter
    def show_controllers(self, value: bool):
        self.session_settings.show_controllers = value

    @property
    def controller_main_grip_position(self) -> Vector:
        return Vector(self.session_state.controller_grip_location_get(bpy.context, self.get_controller_index("main")))

    @property
    def controller_main_grip_rotation(self) -> Quaternion:
        return q(self.session_state.controller_grip_rotation_get(bpy.context, self.get_controller_index("main")))

    @property
    def controller_alt_grip_position(self) -> Vector:
        return Vector(self.session_state.controller_grip_location_get(bpy.context, self.get_controller_index("alt")))

    @property
    def controller_alt_grip_rotation(self) -> Quaternion:
        return q(self.session_state.controller_grip_rotation_get(bpy.context, self.get_controller_index("alt")))

    @property
    def controller_main_aim_position(self) -> Vector:
        return Vector(self.session_state.controller_aim_location_get(bpy.context, self.get_controller_index("main")))

    @property
    def controller_main_aim_rotation(self) -> Quaternion:
        return q(self.session_state.controller_aim_rotation_get(bpy.context, self.get_controller_index("main")))

    @property
    def controller_alt_aim_position(self) -> Vector:
        return Vector(self.session_state.controller_aim_location_get(bpy.context, self.get_controller_index("alt")))

    @property
    def controller_alt_aim_rotation(self) -> Quaternion:
        return q(self.session_state.controller_aim_rotation_get(bpy.context, self.get_controller_index("alt")))

    @property
    def base_pose_type(self) -> str:
        return self.session_settings.base_pose_type

    @base_pose_type.setter
    def base_pose_type(self, value):
        self.session_settings.base_pose_type = value

    def get_controller_index(self, hand) -> int:
        actual_hand = self.get_actual_hand_name(hand)

        return 1 if actual_hand == "right" else 0

    def get_actual_hand_name(self, hand) -> str:
        "Translate 'main' and 'alt' into 'right' or 'left' (i.e. the actual name of the hand)"

        if bl_xr.main_hand == "right":
            return "right" if hand == "main" else "left"

        return "left" if hand == "main" else "right"


xr_session = XRSession()
