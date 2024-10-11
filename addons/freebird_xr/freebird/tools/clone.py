import bpy
from bpy.types import Object

from bl_xr import root
from bl_xr.utils import filter_event_by_buttons
from bl_xr.consts import VEC_ONE
import time

from ..settings_manager import settings
from ..utils import log, link_to_configured_collection

clone_press_start_time = 0  # seconds
clone_state = None  # or "CLONING" or "CLONED"
object_being_held = None
object_being_transformed = False


def _duplicate(obj, data=True):
    obj_copy = obj.copy()
    if data:
        obj_copy.data = obj_copy.data.copy()
    if obj_copy.animation_data and obj_copy.animation_data.action:
        obj_copy.animation_data.action = None

    link_to_configured_collection(obj_copy)

    return obj_copy


def on_clone_start(self, event_name, event):
    global clone_press_start_time, clone_state

    if object_being_held:
        if clone_state == "CLONED":
            # another clone within a single trigger press. make an undo entry for clone
            bpy.ops.ed.undo_push(message="clone")
            log.debug(f"CREATED UNDO event for previous clone")
        elif object_being_transformed:
            # clone after dragging a held object for a while. make an undo entry for transform
            bpy.ops.ed.undo_push(message="transform")
            log.debug(f"CREATED UNDO event for transform before clone")

    clone_state = None

    clone_press_start_time = time.time()


def on_clone_press(self, event_name, event):
    global clone_state, object_being_held

    from freebird import gizmos

    if "joystick_for_keyframe" in gizmos.active_gizmos:  # HACK
        return

    if object_being_held and object_being_held not in bpy.context.scene.objects:
        object_being_held = None

    if clone_state == "CLONED" or (
        not object_being_held and time.time() < clone_press_start_time + settings["clone.long_press_threshold_time"]
    ):
        return

    ob = bpy.context.view_layer.objects.active
    if ob is None or ob.mode != "OBJECT":
        return

    if object_being_held is not None and not bpy.context.scene.objects[object_being_held].select_get():
        selected_objects = bpy.context.scene.objects[object_being_held]
        selected_objects = [selected_objects]
    else:
        selected_objects = bpy.context.selected_objects

    if len(selected_objects) == 0:
        return

    clone_state = "CLONING"

    for ob in selected_objects:
        ob_copy = _duplicate(ob)
        log.info(f"CLONED: {ob_copy} FROM {ob}")

        # move slightly
        if object_being_held is None:
            ob.location += 0.1 * VEC_ONE

        # swap selection
        if settings["transform.grab_button"] == "trigger":
            ob.select_set(True)
        ob_copy.select_set(False)

        bpy.context.view_layer.objects.active = ob

        root.dispatch_event("fb.clone", ob_copy)

    if not object_being_held:
        bpy.ops.ed.undo_push(message="clone")
        log.debug(f"CREATED UNDO event for clone")

    clone_state = "CLONED"


def on_object_drag_start(self, event_name, event):
    global object_being_transformed

    expected_button_name = "trigger_main" if settings["transform.grab_button"] == "trigger" else "squeeze_main"
    if event.button_name != expected_button_name:
        return

    object_being_transformed = True


def on_object_drag_end(self, event_name, event):
    global object_being_transformed

    expected_button_name = "trigger_main" if settings["transform.grab_button"] == "trigger" else "squeeze_main"
    if event.button_name != expected_button_name:
        return

    object_being_transformed = False

    # hack: incase the squeeze_end event wasn't sent (due to the bounds-intersection optimizations)
    if object_being_held:
        clear_held_object()


def on_squeeze_start(self, event_name, event):
    global object_being_held

    expected_button_name = "trigger_main" if settings["transform.grab_button"] == "trigger" else "squeeze_main"
    if event.button_name != expected_button_name:
        return

    object_being_held = self.name

    if settings["transform.grab_button"] == "squeeze":
        ui_btn = root.q("#controller_main_a")
        ui_btn.style["visible"] = True


def on_squeeze_end(self, event_name, event):
    global object_being_held, clone_state

    expected_button_name = "trigger_main" if settings["transform.grab_button"] == "trigger" else "squeeze_main"
    if event.button_name != expected_button_name:
        return

    clear_held_object()


def clear_held_object():
    global object_being_held, clone_state

    if object_being_held and clone_state == "CLONED":
        bpy.ops.ed.undo_push(message="clone")
        log.debug(f"CREATED UNDO event for clone on grab end")

    object_being_held = None
    clone_state = None

    if settings["transform.grab_button"] == "squeeze" and not bpy.context.view_layer.objects.selected:
        ui_btn = root.q("#controller_main_a")
        ui_btn.style["visible"] = False


def enable_tool():
    root.add_event_listener("button_a_main_start", on_clone_start)
    root.add_event_listener("button_a_main_press", on_clone_press)

    Object.add_event_listener("trigger_main_start", on_squeeze_start)
    Object.add_event_listener("trigger_main_end", on_squeeze_end)
    Object.add_event_listener("squeeze_main_start", on_squeeze_start)
    Object.add_event_listener("squeeze_main_end", on_squeeze_end)

    Object.add_event_listener("drag_start", on_object_drag_start)
    Object.add_event_listener("drag_end", on_object_drag_end)

    if settings["transform.grab_button"] == "trigger":
        ui_btn = root.q("#controller_main_a")
        ui_btn.style["visible"] = True


def disable_tool():
    root.remove_event_listener("button_a_main_start", on_clone_start)
    root.remove_event_listener("button_a_main_press", on_clone_press)

    Object.remove_event_listener("trigger_main_start", on_squeeze_start)
    Object.remove_event_listener("trigger_main_end", on_squeeze_end)
    Object.remove_event_listener("squeeze_main_start", on_squeeze_start)
    Object.remove_event_listener("squeeze_main_end", on_squeeze_end)

    Object.remove_event_listener("drag_start", on_object_drag_start)
    Object.remove_event_listener("drag_end", on_object_drag_end)

    if settings["transform.grab_button"] == "trigger":
        ui_btn = root.q("#controller_main_a")
        ui_btn.style["visible"] = False
