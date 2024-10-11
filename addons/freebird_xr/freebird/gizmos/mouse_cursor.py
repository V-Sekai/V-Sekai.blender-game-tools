import bpy
import time
from bpy_extras import view3d_utils

from bl_xr import root, xr_session
from bl_xr import Node, Line, Sphere
from bl_xr.utils import lerp, quaternion_from_vector, log
from bl_xr.consts import BLUE_MS

from mathutils import Vector

from ..settings_manager import settings

area = next(area for area in bpy.context.screen.areas if area.type == "VIEW_3D")
space = next(space for space in area.spaces if space.type == "VIEW_3D")
region = next(region for region in area.regions if region.type == "WINDOW")
region_3d = space.region_3d

starting_mouse_p = None
prev_mouse_move_time = 0  # seconds
last_intersection_dist = None


def on_mouse_move(self, event_name, event):
    global starting_mouse_p, prev_mouse_move_time, last_intersection_dist

    prev_mouse_move_time = time.time()
    dist_threshold = settings["view.mouse_visible_threshold_distance"]

    # if this is a new move, check if it's beyond the move threshold distance
    if starting_mouse_p is None:
        starting_mouse_p = event.mouse_position

    is_visible = mouse_cursor.get_computed_style("visible")
    d = event.mouse_position - starting_mouse_p
    if not is_visible and d.length < dist_threshold:
        last_intersection_dist = None
        return

    # check if within 2D region bounds
    p = (event.mouse_position.x - region.x, event.mouse_position.y - region.y)
    if p[0] < 0 or p[1] < 0 or p[0] > region.width or p[1] > region.height:
        mouse_cursor.style["visible"] = False
        last_intersection_dist = None
        return

    mouse_cursor.style["visible"] = True

    mouse_position = view3d_utils.region_2d_to_origin_3d(region, region_3d, p)
    mouse_forward = view3d_utils.region_2d_to_vector_3d(region, region_3d, p)

    offset = settings["view.mouse_pointer_offset"].y * xr_session.viewer_scale

    mouse_cursor.position = mouse_position + mouse_forward * offset
    mouse_cursor.rotation = quaternion_from_vector(mouse_forward)

    # raycast into the scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    intersects, location, normal, _, ob, _ = bpy.context.scene.ray_cast(depsgraph, mouse_position, mouse_forward)

    mouse_icon, mouse_laser = mouse_cursor.child_nodes

    if intersects:
        last_intersection_dist = (mouse_cursor.position - location).length / xr_session.viewer_scale
    elif last_intersection_dist is None:
        last_intersection_dist = settings["view.mouse_default_laser_length"]

    if settings["view.strict_viewport_sync"]:
        mouse_laser.style["visible"] = False
        mouse_icon.style["visible"] = True
    else:
        mouse_laser.style["visible"] = True
        mouse_icon.style["visible"] = intersects
        last_intersection_dist = last_intersection_dist if intersects else settings["view.mouse_default_laser_length"]

    mouse_laser.length = last_intersection_dist
    mouse_icon.position.y = last_intersection_dist

    radius = lerp(0.0005, 0.015, last_intersection_dist / xr_session.viewer_scale)
    mouse_icon.radius = radius * 2

    if settings["view.strict_viewport_sync"]:
        mouse_icon.radius *= 5


def on_mouse_cursor_update(self):
    global starting_mouse_p, last_intersection_dist

    hide_after_time = settings["view.mouse_hide_threshold_time"]
    if (
        not settings["view.sync_with_viewport"]
        or settings["view.mirror_xr"]
        or time.time() > prev_mouse_move_time + hide_after_time
    ):
        self.style["visible"] = False
        starting_mouse_p = None
        last_intersection_dist = None
        return


mouse_cursor = Node(
    id="mouse_cursor",
    style={"visible": False, "fixed_scale": True},
    intersects=None,
    child_nodes=[
        Sphere(id="mouse_cursor_icon", radius=0.01, style={"opacity": 0.5, "color": BLUE_MS}, position=Vector()),
        Line(id="mouse_cursor_laser", style={"opacity": 0.5}),
    ],
)
mouse_cursor.update = on_mouse_cursor_update.__get__(mouse_cursor)


def enable_gizmo():
    root.append_child(mouse_cursor)
    root.add_event_listener("mouse_move", on_mouse_move)


def disable_gizmo():
    root.remove_child(mouse_cursor)
    root.remove_event_listener("mouse_move", on_mouse_move)
