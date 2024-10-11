import bpy

from bl_xr import root, xr_session
from bl_xr import Text, Image
import time

from freebird.utils import desktop_viewport

from mathutils import Vector, Quaternion
from math import radians

from ..settings_manager import settings
from ..utils import log

JOYSTICK_THRESHOLD = 0.8

curr_task = None
task_start_time = None  # seconds
last_task_time = None  # seconds
task_interval = None
num_frames_to_move: float = None


def move_to_prev_frame():
    bpy.context.scene.frame_current -= int(num_frames_to_move)


def move_to_next_frame():
    bpy.context.scene.frame_current += int(num_frames_to_move)


def on_keyframe_insert(self, event_name, event):
    prev = bpy.context.scene.tool_settings.use_keyframe_insert_auto

    ov = bpy.context.copy()
    ov["area"] = desktop_viewport.get_area()  # fix for "incorrect context" errors in bl 3.2

    bpy.context.scene.tool_settings.use_keyframe_insert_auto = True

    with bpy.context.temp_override(**ov):
        bpy.ops.transform.translate()
        bpy.ops.transform.rotate()
        bpy.ops.transform.resize(value=(1, 1, 1))

    bpy.context.scene.tool_settings.use_keyframe_insert_auto = prev


def on_keyframe_move_start(self, event_name, event):
    global curr_task, task_start_time, last_task_time, task_interval, num_frames_to_move

    curr_task = move_to_prev_frame if event.value < 0 else move_to_next_frame
    task_start_time = time.time()
    last_task_time = time.time()
    task_interval = settings["gizmo.joystick_for_keyframe.long_press_repeat_threshold_time"]
    num_frames_to_move = 1.0

    curr_task()


def on_keyframe_move_press(self, event_name, event):
    global last_task_time, task_interval, num_frames_to_move

    if abs(event.value) < JOYSTICK_THRESHOLD:
        return

    if last_task_time is None:
        on_keyframe_move_start(self, event_name, event)
        return

    intended_task = move_to_prev_frame if event.value < 0 else move_to_next_frame
    if intended_task != curr_task or time.time() < last_task_time + task_interval:
        return

    curr_task()

    task_interval = 0  # settings["timeline.long_press_repeat_interval"]  # subsequent repeats will be faster
    last_task_time = time.time()

    acceleration = settings["gizmo.joystick_for_keyframe.long_press_repeat_frame_acceleration"]
    num_frames_to_move *= acceleration

    last_task_time = time.time()


def on_keyframe_move_end(self, event_name, event):
    global task_start_time, last_task_time, num_frames_to_move

    task_start_time = None
    last_task_time = None
    num_frames_to_move = None


def update(self):
    frame_counter.text = f"Frame: {bpy.context.scene.frame_current}"

    # reposition
    rot = xr_session.viewer_camera_rotation

    offset = Vector(settings["gizmo.joystick_for_keyframe.camera_preview_offset"])
    offset = rot @ offset
    offset *= xr_session.viewer_scale

    frame_counter.position = xr_session.viewer_camera_position + offset
    frame_counter.rotation = rot @ Quaternion((1, 0, 0), radians(90))


frame_counter = Text("", font_size=36, intersects=None, style={"fixed_scale": True})
frame_counter.update = update.__get__(frame_counter)

clone_icon_texture = None


def enable_gizmo():
    global clone_icon_texture

    root.append_child(frame_counter)

    clone_btn = root.q("#controller_main_a")
    clone_icon_texture = clone_btn.icon._texture

    panel = root.q("#anim_panel")
    insert_icon = panel.child_nodes[1].icon
    clone_btn.tooltip.text = "ADD FRAME"
    clone_btn.icon._texture = insert_icon._texture

    root.add_event_listener("joystick_x_main_press", on_keyframe_move_press)
    root.add_event_listener("joystick_x_main_end", on_keyframe_move_end)

    root.add_event_listener("button_a_main_start", on_keyframe_insert)


def disable_gizmo():
    global clone_icon_texture

    root.remove_child(frame_counter)

    root.remove_event_listener("joystick_x_main_press", on_keyframe_move_press)
    root.remove_event_listener("joystick_x_main_end", on_keyframe_move_end)

    root.remove_event_listener("button_a_main_start", on_keyframe_insert)

    clone_btn = root.q("#controller_main_a")
    clone_btn.tooltip.text = "CLONE"
    clone_btn.icon._texture = clone_icon_texture
    clone_icon_texture = None
