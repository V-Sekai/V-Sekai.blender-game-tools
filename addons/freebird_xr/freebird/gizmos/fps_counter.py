from bl_xr import root, xr_session
from bl_xr import Text

from freebird import settings

from mathutils import Vector, Quaternion

from math import radians
import time

FRAME_WINDOW = 20

frame_times = []
last_frame_time = None  # seconds


def update(self):
    global last_frame_time

    if last_frame_time is not None:
        delta = time.time() - last_frame_time
        frame_times.append(delta)

        if len(frame_times) > FRAME_WINDOW:
            frame_times.pop(0)

        avg_time = sum(frame_times) / FRAME_WINDOW  # seconds
        avg_fps = 1 / avg_time

        fps_counter.text = f"FPS: {int(avg_fps)}"

    last_frame_time = time.time()

    # reposition
    rot = xr_session.viewer_camera_rotation

    offset = Vector(settings["gizmo.fps_counter.preview_offset"])
    offset = rot @ offset
    offset *= xr_session.viewer_scale

    fps_counter.position = xr_session.viewer_camera_position + offset
    fps_counter.rotation = rot @ Quaternion((1, 0, 0), radians(90))


fps_counter = Text("", font_size=50, intersects=None, style={"fixed_scale": True})
# fps_counter.scale = 0.0005
fps_counter.update = update.__get__(fps_counter)


def enable_gizmo():
    root.append_child(fps_counter)


def disable_gizmo():
    global last_frame_time

    root.remove_child(fps_counter)

    last_frame_time = None
