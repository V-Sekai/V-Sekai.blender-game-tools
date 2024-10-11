from bl_xr import root

import bpy
from bpy.types import Object

from freebird import settings
from freebird.utils import log

disable_gizmo_upon_release = False
cam = None


def on_transform_start(self, event_name, event):
    global disable_gizmo_upon_release, cam

    from freebird.gizmos import active_gizmos, enable_gizmo

    cam = next((ob for ob in event.targets if getattr(ob, "type", None) == "CAMERA"), None)
    if cam is None:
        disable_gizmo_upon_release = False
        return

    if "camera_preview" in active_gizmos:
        disable_gizmo_upon_release = False
    else:
        enable_gizmo("camera_preview")
        disable_gizmo_upon_release = True

    cam_preview = root.q("#camera_preview")
    cam_preview.camera = cam


def on_transform_end(self, event_name, event):
    global disable_gizmo_upon_release

    if cam is None:
        return

    if not bpy.app.background:
        preview_duration_after_release = settings["gizmo.camera_preview_on_grab.preview_duration_after_release"]
        bpy.app.timers.register(release_camera, first_interval=preview_duration_after_release)
    else:
        release_camera()


def release_camera():
    global disable_gizmo_upon_release

    from freebird.gizmos import disable_gizmo

    cam_preview = root.q("#camera_preview")
    cam_preview.camera = bpy.context.scene.camera

    if disable_gizmo_upon_release:
        disable_gizmo("camera_preview")

    disable_gizmo_upon_release = False


def enable_gizmo():
    Object.add_event_listener("fb.transform_start", on_transform_start)
    Object.add_event_listener("fb.transform_end", on_transform_end)


def disable_gizmo():
    Object.remove_event_listener("fb.transform_start", on_transform_start)
    Object.remove_event_listener("fb.transform_end", on_transform_end)
