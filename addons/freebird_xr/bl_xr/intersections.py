# SPDX-License-Identifier: GPL-2.0-or-later

import bl_xr
from bl_xr import xr_session, ControllerEvent
from bl_xr.events.make_events import controller
from bl_xr.utils import raycast, intersects, is_within_fov, log
from bl_xr.consts import VEC_FORWARD

import bpy
import math

from mathutils import Vector

curr: dict[str, dict] = {
    "raycast": {},  # (node: world_intersection_point)
    "bounds": {},  #  entries of (node: world_intersection_point)
}
prev: dict[str, dict] = {
    "raycast": {},
    "bounds": {},
}
sub_targets: set = None

allow_squeeze = False


def refresh_intersections(base_event: ControllerEvent):
    if not base_event or base_event.hand != "main":
        return

    checks = bl_xr.intersection_checks
    is_main_trigger = controller.input_state.get("trigger_main_press", False)
    is_main_squeeze = allow_squeeze and controller.input_state.get("squeeze_main_press", False)

    object_bounds = "ALL" in checks or ("BOUNDS_ON_MAIN_TRIGGER" in checks and (is_main_trigger or is_main_squeeze))
    ui_bounds = object_bounds
    object_raycast = "ALL" in checks
    ui_raycast = "ALL" in checks or "RAYCAST_UI" in checks

    if "BOUNDS_ON_MAIN_TRIGGER" in checks or "ALL" in checks:
        update_bounds_intersection_cache(base_event, object_bounds, ui_bounds)
    update_raycast_intersection_cache(base_event, object_raycast, ui_raycast)


def update_bounds_intersection_cache(base_event: ControllerEvent, object_bounds=False, ui_bounds=False):
    global sub_targets

    prev["bounds"] = curr["bounds"]
    curr["bounds"] = {}

    if object_bounds:
        objects, sub_targets = get_intersecting_objects(base_event.position)
        for ob in objects:
            curr["bounds"][ob] = None

    if ui_bounds:
        ui_bounds_nodes = check_ui_bounds_intersection(base_event.position)
        for node in ui_bounds_nodes:
            curr["bounds"][node] = None


def update_raycast_intersection_cache(base_event: ControllerEvent, object_raycast=False, ui_raycast=False):
    prev["raycast"] = curr["raycast"]
    curr["raycast"] = {}

    node, point, _ = raycast(base_event.position, base_event.rotation @ VEC_FORWARD, object_raycast, ui_raycast)
    if node and (is_within_fov(point) or node in prev["raycast"]):
        curr["raycast"][node] = point

    # if curr["raycast"]:
    #     # print("intersecting", dist, node.get_breadcrumb())
    #     bl_xr.root.q("#debug").position = point


def check_ui_bounds_intersection(center):
    intersections = intersects(
        bl_xr.root, center, bl_xr.selection_shape, bl_xr.selection_size * xr_session.viewer_scale
    )

    return intersections if intersections else []


def get_intersecting_objects(pointer_location: Vector):
    curr_mode = getattr(bpy.context.view_layer.objects.active, "mode", "OBJECT")
    objects = [bpy.context.view_layer.objects.active] if curr_mode in ("EDIT", "POSE") else bpy.data.objects

    intersecting_elements = []
    for ob in objects:
        elements = intersects(
            ob,
            pointer_location,
            bl_xr.selection_shape,
            bl_xr.selection_size * xr_session.viewer_scale,
        )
        if elements:
            intersecting_elements += elements

    if curr_mode in ("EDIT", "POSE"):
        if len(intersecting_elements) > 0:
            intersecting_objects = objects
            intersecting_elements = set(intersecting_elements)
        else:
            intersecting_objects = intersecting_elements
            intersecting_elements = None
    else:
        intersecting_objects = intersecting_elements
        intersecting_elements = None

    return intersecting_objects, intersecting_elements
