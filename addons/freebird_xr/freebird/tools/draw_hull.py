import bpy
import bmesh

from bl_xr import root, xr_session

from mathutils import Vector

from ..settings_manager import settings
from ..utils import log, reset_scale, link_to_configured_collection
from ..utils import enable_bounds_check, disable_bounds_check


ob = None
bm = None
prev_pt = None
nav_scale = 1


def on_hull_stroke_start(self, event_name, event):
    global ob, bm

    disable_bounds_check()

    log.info("new hull")
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0), size=0.0001, scale=(1, 1, 1))
    ob = bpy.context.view_layer.objects.active
    ob.name = "VolumeHull"

    if settings["gizmo.mirror.enabled"]:
        mirror = ob.modifiers.new("Mirror", "MIRROR")
        mirror.use_axis = [
            settings["gizmo.mirror.axis_x"],
            settings["gizmo.mirror.axis_y"],
            settings["gizmo.mirror.axis_z"],
        ]
        mirror.mirror_object = bpy.data.objects["freebird_mirror_global"]

    link_to_configured_collection(ob)

    bm = bmesh.new()

    on_hull_stroke(self, event_name, event)


def on_hull_stroke(self, event_name, event):
    if ob is None:
        return

    global prev_pt

    if prev_pt is not None:
        d = (event.position - prev_pt).length
        d /= xr_session.viewer_scale

        if d < settings["hull.min_stroke_distance"]:
            return

    bm.verts.new(event.position)
    prev_pt = Vector(event.position)

    hull = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=True)
    geom_to_remove = list(set(hull["geom_interior"]) | set(hull["geom_unused"]))
    bmesh.ops.delete(bm, geom=geom_to_remove, context="VERTS")

    bm.to_mesh(ob.data)


def on_hull_stroke_end(self, event_name, event):
    global ob, bm, prev_pt

    enable_bounds_check()

    if ob is None:
        return

    log.info("finished hull")
    reset_scale(ob)

    bpy.ops.ed.undo_push(message="hull add")
    ob = None
    bm.free()
    bm = None
    prev_pt = None


def enable_tool():
    root.add_event_listener("trigger_main_start", on_hull_stroke_start)
    root.add_event_listener("trigger_main_press", on_hull_stroke)
    root.add_event_listener("trigger_main_end", on_hull_stroke_end)


def disable_tool():
    root.remove_event_listener("trigger_main_start", on_hull_stroke_start)
    root.remove_event_listener("trigger_main_press", on_hull_stroke)
    root.remove_event_listener("trigger_main_end", on_hull_stroke_end)
