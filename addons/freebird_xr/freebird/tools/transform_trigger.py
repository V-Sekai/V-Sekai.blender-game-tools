import bpy
from bpy.types import Object
from bmesh.types import BMEdge, BMFace
from bl_xr import root
from bl_xr.utils import filter_event_by_buttons, is_within_fov, get_bmesh
from math import radians

import time
import logging

from ..settings_manager import settings
from ..utils import set_select_state_all, set_select_state, log, desktop_viewport
from ..utils import enable_bounds_check, disable_bounds_check

from .transform_common import (
    transform_state as T,
    get_selected_elements,
    pre_process_edit_bones,
    pre_process_pose_bones,
    dispatch_event,
    on_transform_object as on_transform_object_orig,
    on_transform_edit_curve,
    on_transform_edit_mesh,
    on_transform_edit_armature,
    on_transform_pose_armature,
    on_joystick_vertical,
    allow_transform,
)

is_transform_dragging = False
trigger_press_start_time = {}  # trigger_name -> seconds


def on_transform_drag_start(self, event_name, event):
    global is_transform_dragging

    if self.mode == "OBJECT" and self != event.targets[0]:
        return

    disable_bounds_check()

    if not allow_transform(event):
        return

    if self.hide_select:
        T["allow_transform"] = False
        log.debug("Skipping transform since the object is not selectable!")
        return

    if (
        settings["transform.check_for_fov"]
        and not T["has_transformed"]
        and not is_within_fov(event.pivot_position, radians(45))
    ):
        T["allow_transform"] = False
        log.debug("Skipping transform since it is outside the FOV!")
        return

    event.stop_propagation = True

    trigger_alt_start_time = trigger_press_start_time.get("trigger_alt")
    trigger_main_start_time = trigger_press_start_time.get("trigger_main")
    alt_trigger_debounce_time = settings["transform.alt_trigger_debounce_time"]
    if (
        trigger_alt_start_time is not None
        and trigger_main_start_time > trigger_alt_start_time + alt_trigger_debounce_time
    ):
        log.error(
            "Ignoring transform drag because the main trigger was pressed after the alt trigger, "
            + "beyond the threshold alt debounce time! "
            + f"trigger_main_start_time: {trigger_main_start_time}, trigger_alt_start_time: {trigger_alt_start_time}, "
            + f"alt_trigger_debounce_time: {alt_trigger_debounce_time}"
        )
        return

    is_transform_dragging = True

    # calculate the transform matrices
    T["transform_m"] = self.matrix_world
    T["transform_m_inv"] = T["transform_m"].inverted()

    # figure out whether to transform existing selections or de-select them
    event_targets = list(target for target in event.targets if isinstance(target, Object))
    cursor_targets = event.sub_targets if self.mode in ("EDIT", "POSE") else event_targets
    selected_cursor_targets = get_selected_elements(cursor_targets)
    T["preselected_targets"] = get_selected_elements()

    if self.type == "MESH" and self.mode == "EDIT" and settings["edit.perform_extrude"]:
        if len(selected_cursor_targets) == 0:
            set_select_state_all(False)

        set_select_state(cursor_targets, True)

        bpy.ops.mesh.extrude_context()

        T["transform_elements"] = T["preselected_targets"]
    else:
        T["transform_elements"] = set(cursor_targets)
        if len(selected_cursor_targets) > 0:
            T["transform_elements"] |= T["preselected_targets"]  # include preselected mesh elements

    if self.type == "ARMATURE":
        if self.mode == "EDIT":
            T["transform_elements"], T["siblings_affected_indirectly"] = pre_process_edit_bones(
                self, T["transform_elements"]
            )
            T["preselected_targets"] = [(self.data.edit_bones[b], el_type) for b, el_type in T["preselected_targets"]]
        elif self.mode == "POSE":
            T["transform_elements"] = pre_process_pose_bones(self, T["transform_elements"], event.sub_targets)
            T["siblings_affected_indirectly"] = {}
            T["preselected_targets"] = [(self.pose.bones[b], el_type) for b, el_type in T["preselected_targets"]]
    else:
        T["siblings_affected_indirectly"] = {}

    # now select the elements that we'll transform
    set_select_state(T["preselected_targets"], False)
    set_select_state(T["transform_elements"], True)

    if len(T["transform_elements"]) > 0 and isinstance(list(T["transform_elements"])[0], (BMEdge, BMFace)):
        T["transform_elements"] = {v for e in T["transform_elements"] for v in e.verts}

    T["object_to_transform"] = list(event_targets)[0]

    T["context_override"] = desktop_viewport.temp_override()

    if self == event_targets[0]:
        dispatch_event(self, "fb.transform_start", event)

    on_transform_drag(self, event_name, event)


def on_transform_drag(self, event_name, event):
    if self.mode == "OBJECT" and self != event.targets[0]:
        return

    if not allow_transform(event):
        return

    if not T["allow_transform"]:
        return

    event.stop_propagation = True

    if not is_transform_dragging or (event.sub_targets is None and self != T["object_to_transform"]):
        return

    if log.isEnabledFor(logging.DEBUG):
        log.debug(f"TRANSFORMING {self} by {event.pose_delta} pivot: {event.pivot_position}")

    T["has_transformed"] = True

    if self.mode == "OBJECT":
        on_transform_object(self, event_name, event)
    elif self.mode == "EDIT":
        if self.type == "CURVE":
            on_transform_edit_curve(self, event_name, event)
        elif self.type == "MESH":
            on_transform_edit_mesh(self, event_name, event)
        elif self.type == "ARMATURE":
            on_transform_edit_armature(self, event_name, event)
    elif self.mode == "POSE":
        if self.type == "ARMATURE":
            on_transform_pose_armature(self, event_name, event)

    dispatch_event(self, "fb.transform", event)


def on_transform_drag_end(self, event_name, event):
    global is_transform_dragging

    if self.mode == "OBJECT" and self != event.targets[0]:
        return

    enable_bounds_check()

    if not allow_transform(event):
        return

    if not T["allow_transform"]:
        T["allow_transform"] = True
        return

    event.stop_propagation = True

    if T["has_transformed"] and not T["has_cloned"]:
        bpy.ops.ed.undo_push(message="transform")
        log.debug("CREATED UNDO EVENT for transform")

        bpy.ops.transform.translate()

        dispatch_event(self, "fb.transform_end", event)

    is_transform_dragging = False
    T["object_to_transform"] = None
    T["has_transformed"] = False
    T["has_cloned"] = False

    if self.type == "MESH" and self.mode == "EDIT" and settings["edit.perform_extrude"]:
        get_bmesh(skip_cache=True)  # refresh the bmesh and bvh


def on_transform_object(self, event_name, event):
    on_transform_object_orig(self, event_name, event)

    if len(T["transform_elements"]) > 0:
        bpy.context.view_layer.objects.active = list(T["transform_elements"])[-1]


def on_trigger_press_start(self, event_name, event):
    trigger_press_start_time[event.button_name] = time.time()


def on_trigger_press_end(self, event_name, event):
    trigger_press_start_time[event.button_name] = None


def on_cloned(self, event_name, event):
    T["has_cloned"] = True


def enable_tool():
    # enable_bounds_check()

    Object.add_event_listener(
        "drag_start", on_transform_drag_start, {"filter_fn": filter_event_by_buttons(["trigger_main", "trigger_both"])}
    )
    Object.add_event_listener(
        "drag", on_transform_drag, {"filter_fn": filter_event_by_buttons(["trigger_main", "trigger_both"])}
    )
    Object.add_event_listener(
        "drag_end", on_transform_drag_end, {"filter_fn": filter_event_by_buttons(["trigger_main", "trigger_both"])}
    )

    Object.add_event_listener("trigger_alt_start", on_trigger_press_start)
    Object.add_event_listener("trigger_alt_end", on_trigger_press_end)
    Object.add_event_listener("trigger_main_start", on_trigger_press_start)
    Object.add_event_listener("trigger_main_end", on_trigger_press_end)
    root.add_event_listener("trigger_alt_start", on_trigger_press_start)
    root.add_event_listener("trigger_alt_end", on_trigger_press_end)
    root.add_event_listener("trigger_main_start", on_trigger_press_start)
    root.add_event_listener("trigger_main_end", on_trigger_press_end)

    root.add_event_listener("joystick_y_main_press", on_joystick_vertical)

    root.add_event_listener("fb.clone", on_cloned)


def disable_tool():
    # disable_bounds_check()

    Object.remove_event_listener("drag_start", on_transform_drag_start)
    Object.remove_event_listener("drag", on_transform_drag)
    Object.remove_event_listener("drag_end", on_transform_drag_end)

    Object.remove_event_listener("trigger_alt_start", on_trigger_press_start)
    Object.remove_event_listener("trigger_alt_end", on_trigger_press_end)
    Object.remove_event_listener("trigger_main_start", on_trigger_press_start)
    Object.remove_event_listener("trigger_main_end", on_trigger_press_end)
    root.remove_event_listener("trigger_alt_start", on_trigger_press_start)
    root.remove_event_listener("trigger_alt_end", on_trigger_press_end)
    root.remove_event_listener("trigger_main_start", on_trigger_press_start)
    root.remove_event_listener("trigger_main_end", on_trigger_press_end)

    root.remove_event_listener("joystick_y_main_press", on_joystick_vertical)

    root.remove_event_listener("fb.clone", on_cloned)
