import bpy

from bl_xr import root, xr_session
from bl_xr import Pose, TwoHandedControllerEvent, DragEvent
from bl_xr.utils import filter_event_by_buttons
from mathutils import Quaternion

import logging

from .settings_manager import settings
from .utils import log
from .utils import enable_bounds_check, disable_bounds_check

nav_pose = None


def on_nav_transform_start(self, event_name, event: DragEvent):
    global nav_pose

    disable_bounds_check()

    nav_pose = xr_session.viewer_pose

    event = event.clone()
    event.type = "fb.navigate_start"

    root.dispatch_event("fb.navigate_start", event)

    on_nav_transform(self, event_name, event)


def on_nav_transform(self, event_name, event: DragEvent):
    from bl_xr.events.make_events.controller import input_state

    if nav_pose is None:
        return

    if input_state.get("trigger_main_press"):
        log.debug("Skipping world navigate when the main trigger is pressed")
        return

    if log.isEnabledFor(logging.DEBUG):
        log.debug(f"world nav delta: {event_name} {event.pose_delta} {event.pivot_position}")

    event = event.clone()
    event.type = "fb.navigate"

    if not isinstance(event, TwoHandedControllerEvent) and settings["world_nav.lock_rotation.single_handed"]:
        yaw = event.pose_delta.rotation.to_euler().z
        event.pose_delta.rotation = Quaternion((0, 0, 1), yaw)

    event.pose_delta = event.pose_delta.inverted()
    nav_pose.transform(event.pose_delta, event.pivot_position)

    pose = nav_pose

    if log.isEnabledFor(logging.DEBUG):
        log.debug(f"SETTING to: {pose}")

    if settings["world_nav.interpolate_movement"]:
        t = settings["world_nav.interpolation_factor"]
        pose = Pose.lerp(xr_session.viewer_pose, pose, t)  # interpolate for smoothness

    xr_session.viewer_pose = pose

    root.dispatch_event("fb.navigate", event)


def on_nav_transform_end(self, event_name, event):
    global nav_pose

    enable_bounds_check()

    if nav_pose is None:
        return

    nav_pose = None

    event = event.clone()
    event.type = "fb.navigate_end"

    root.dispatch_event("fb.navigate_end", event)


filter_fn = filter_event_by_buttons(["squeeze_main", "squeeze_both", "squeeze_alt"])


def enable():
    root.add_event_listener("drag_start", on_nav_transform_start, {"filter_fn": filter_fn})
    root.add_event_listener("drag", on_nav_transform, {"filter_fn": filter_fn})
    root.add_event_listener("drag_end", on_nav_transform_end, {"filter_fn": filter_fn})


def disable():
    root.remove_event_listener("drag_start", on_nav_transform_start)
    root.remove_event_listener("drag", on_nav_transform)
    root.remove_event_listener("drag_end", on_nav_transform_end)
