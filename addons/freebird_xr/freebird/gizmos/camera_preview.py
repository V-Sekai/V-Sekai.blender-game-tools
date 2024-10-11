from bl_xr import root

import bpy

from bl_xr import root, xr_session
from bl_xr.consts import BLUE_MS
from freebird import settings

from math import radians
from mathutils import Vector, Quaternion

from .common.camera_preview import CameraPreview


cam_preview = CameraPreview(
    id="camera_preview",
    camera=bpy.context.scene.camera,
    style={
        "scale": Vector(settings["gizmo.camera_preview.preview_scale"]),
        "fixed_scale": True,
        "border": (0.007, BLUE_MS),
        "border_radius": (0.01),
    },
)


def on_navigate_start(self, event_name, event):
    cam_preview.style["visible"] = False


def on_navigate_end(self, event_name, event):
    cam_preview.style["visible"] = True

    update_camera_pose()


def update_camera_pose():
    rot = xr_session.viewer_camera_rotation

    offset = Vector(settings["gizmo.camera_preview.preview_offset"])
    offset = rot @ offset
    offset *= xr_session.viewer_scale

    cam_preview.position = xr_session.viewer_camera_position + offset
    cam_preview.rotation = rot @ Quaternion((1, 0, 0), radians(90))


def enable_gizmo():
    root.append_child(cam_preview)

    root.add_event_listener("fb.navigate_start", on_navigate_start)
    root.add_event_listener("fb.navigate_end", on_navigate_end)

    cam_preview.style["visible"] = True

    update_camera_pose()

    cam_preview.start_preview()


def disable_gizmo():
    root.remove_child(cam_preview)

    root.remove_event_listener("fb.navigate_start", on_navigate_start)
    root.remove_event_listener("fb.navigate_end", on_navigate_end)

    cam_preview.stop_preview()
