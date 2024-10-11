import bpy

from bl_xr import root, xr_session
from bl_xr import Line
from bl_xr.utils import vec_abs
from bl_xr.consts import RED, GREEN, BLUE_MS, VEC_FORWARD, VEC_RIGHT, VEC_UP

from math import copysign
from mathutils import Vector

from ..settings_manager import settings
from ..utils import reset_scale, log, link_to_configured_collection
from ..utils import enable_bounds_check, disable_bounds_check

shape_start_pt = None
shape_ob = None

axis_lines = [
    Line(direction=VEC_RIGHT, style={"color": RED, "visible": False}),
    Line(direction=VEC_FORWARD, style={"color": GREEN, "visible": False}),
    Line(direction=VEC_UP, style={"color": BLUE_MS, "visible": False}),
]
root.append_children(axis_lines)


def on_shape_brush_start(self, event_name, event):
    global shape_start_pt, shape_ob

    disable_bounds_check()

    log.info("shape start")
    shape_start_pt = event.position

    shape_type = settings["shape.type"]
    if shape_type == "cube":
        bpy.ops.mesh.primitive_cube_add(location=shape_start_pt, size=1, scale=(1, 1, 1))
    elif shape_type == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(location=shape_start_pt, scale=(1, 1, 1))
    elif shape_type == "torus":
        bpy.ops.mesh.primitive_torus_add(location=shape_start_pt)

        ob = bpy.context.view_layer.objects.active
        ob.scale = (1, 1, 1)
    elif shape_type == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(location=shape_start_pt, scale=(1, 1, 1))
    elif shape_type == "cone":
        bpy.ops.mesh.primitive_cone_add(location=shape_start_pt, scale=(1, 1, 1))
    elif shape_type == "monkey":
        bpy.ops.mesh.primitive_monkey_add(location=shape_start_pt, size=1, scale=(1, 1, 1))

    shape_ob = bpy.context.view_layer.objects.active
    shape_ob.name = shape_type.capitalize()
    shape_ob.hide_viewport = True

    if settings["gizmo.mirror.enabled"]:
        mirror = shape_ob.modifiers.new("Mirror", "MIRROR")
        mirror.use_axis = [
            settings["gizmo.mirror.axis_x"],
            settings["gizmo.mirror.axis_y"],
            settings["gizmo.mirror.axis_z"],
        ]
        mirror.mirror_object = bpy.data.objects["freebird_mirror_global"]

    link_to_configured_collection(shape_ob)


def on_shape_brush(self, event_name, event):
    if shape_ob is None:
        return

    shape_type = settings["shape.type"]
    constraint = settings[f"shape.constraint.{shape_type}"]
    mirror = settings[f"shape.mirror.{shape_type}"]

    if settings.get("shape.disable_constraints"):
        constraint = None

    start, end = constrain_point(event.position, shape_start_pt, constraint, mirror)
    mid_pt = (start + end) / 2
    size = vec_abs(end - start)
    shape_ob.location = mid_pt

    if shape_type == "cube":
        shape_ob.scale = size
    elif shape_type in ["sphere", "cylinder", "cone"]:
        shape_ob.scale = size / 2
    elif shape_type == "torus":
        shape_ob.scale = (size.x / 2.5, size.y / 2.5, size.z / 0.5)
    elif shape_type == "monkey":
        if constraint is None:
            shape_ob.scale = (size.x * 2 / 2.73, size.y * 2 / 1.7, size.z * 2 / 1.97)
        else:
            shape_ob.scale = size

    shape_ob.hide_viewport = False

    show_axis_line(start, end, mid_pt, mirror)


def on_shape_brush_end(self, event_name, event):
    global shape_ob

    enable_bounds_check()

    if shape_ob is None:
        return

    shape_ob.hide_viewport = False

    log.info("shape end")
    reset_scale(shape_ob)

    shape_ob = None

    shape_type = settings["shape.type"]
    bpy.ops.ed.undo_push(message=f"{shape_type} add")

    hide_axis_line()


def show_axis_line(start, end, mid_pt, mirror):
    if mirror is None:
        hide_axis_line()
        return

    nav_scale = xr_session.viewer_scale

    def show_line(axis):
        dir = 1 if start[axis] > end[axis] else -1

        from_pt = Vector(mid_pt)
        to_pt = Vector(mid_pt)

        from_pt[axis] = start[axis] + dir * 0.05 * nav_scale
        to_pt[axis] = end[axis] - dir * 0.05 * nav_scale

        axis_lines[axis].position_world = from_pt
        axis_lines[axis].length = (to_pt - from_pt)[axis]
        axis_lines[axis].style["visible"] = True

    show_line(axis=2)

    if mirror == "XYZ":
        show_line(axis=0)


def hide_axis_line():
    for axis_line in axis_lines:
        axis_line.style["visible"] = False


def constrain_point(p, origin, constraint, mirror) -> tuple[Vector, Vector]:
    "Returns the effective start and end point, after applying the constraints"

    constraint_indices = get_axis_indices(constraint)
    mirror_indices = get_axis_indices(mirror)

    start, end = Vector(origin), Vector(p)

    # 1. double the dimensions that will be mirrored
    d = p - origin
    for i in mirror_indices:
        end[i] += d[i]

    # 2. apply length constraint
    if len(constraint_indices) > 1:  # needs a min of 2 edges to compare
        d = vec_abs(end - start)
        max_size = max(size for i, size in enumerate(d) if i in constraint_indices)

        for i in constraint_indices:
            direction = copysign(1, end[i] - start[i])
            end[i] = start[i] + direction * max_size

    # 3. adjust mirrored dimensions around the origin
    d = (end - start) * 0.5
    for i in mirror_indices:
        start[i] -= d[i]
        end[i] -= d[i]

    return start, end


def get_axis_indices(axes) -> list[int]:
    "Converts a string, like XY, into a list of ints denoting their indices, e.g. [0, 1]"
    ALL_AXES = "xyz"
    axes = axes or ""
    axes = [ALL_AXES.index(a) for a in axes.lower()]
    return axes


def on_alt_shape_start(self, event_name, event):
    settings["shape.disable_constraints"] = True


def on_alt_shape_end(self, event_name, event):
    settings["shape.disable_constraints"] = False


def enable_tool():
    root.add_event_listener("trigger_main_start", on_shape_brush_start)
    root.add_event_listener("trigger_main_press", on_shape_brush)
    root.add_event_listener("trigger_main_end", on_shape_brush_end)

    root.add_event_listener("trigger_alt_start", on_alt_shape_start)
    root.add_event_listener("trigger_alt_end", on_alt_shape_end)


def disable_tool():
    root.remove_event_listener("trigger_main_start", on_shape_brush_start)
    root.remove_event_listener("trigger_main_press", on_shape_brush)
    root.remove_event_listener("trigger_main_end", on_shape_brush_end)

    root.remove_event_listener("trigger_alt_start", on_alt_shape_start)
    root.remove_event_listener("trigger_alt_end", on_alt_shape_end)
