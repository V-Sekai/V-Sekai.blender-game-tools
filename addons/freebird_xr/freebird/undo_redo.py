import bpy

from bl_xr import root
import time

from .settings_manager import settings
from .utils import log

JOYSTICK_THRESHOLD = 0.8

curr_task = None
last_task_time = None  # seconds
task_interval = None


def undo():
    if _run(bpy.ops.ed.undo):
        root.dispatch_event("fb.undo", None)


def redo():
    if _run(bpy.ops.ed.redo):
        root.dispatch_event("fb.redo", None)


def _run(task):
    try:
        task()
        log.debug(f"ran: {task}")
    except:
        return False

    return True


def on_undo_redo_task_start(self, event_name, event):
    global curr_task, last_task_time, task_interval

    curr_task = undo if event.value < 0 else redo
    last_task_time = time.time()
    task_interval = settings["timeline.long_press_repeat_threshold_time"]

    curr_task()


def on_undo_redo_task_press(self, event_name, event):
    global last_task_time, task_interval

    if abs(event.value) < JOYSTICK_THRESHOLD:
        return

    if last_task_time is None:
        on_undo_redo_task_start(self, event_name, event)
        return

    intended_task = undo if event.value < 0 else redo
    if intended_task != curr_task or time.time() < last_task_time + task_interval:
        return

    curr_task()

    task_interval = settings["timeline.long_press_repeat_interval"]  # subsequent repeats will be faster
    last_task_time = time.time()


def on_undo_redo_task_end(self, event_name, event):
    global last_task_time

    last_task_time = None


def enable():
    root.add_event_listener("joystick_x_alt_press", on_undo_redo_task_press)
    root.add_event_listener("joystick_x_alt_end", on_undo_redo_task_end)


def disable():
    root.remove_event_listener("joystick_x_alt_press", on_undo_redo_task_press)
    root.remove_event_listener("joystick_x_alt_end", on_undo_redo_task_end)
