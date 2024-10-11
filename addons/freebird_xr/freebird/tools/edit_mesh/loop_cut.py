import bpy
import time

from bl_xr import root, xr_session
from bl_xr.utils import get_bmesh, get_bvh, nearest_point_on_line_segment

from freebird.utils import make_bmesh_copy, get_bmesh_copy, revert_to_bmesh_copy, free_bmesh_copy, get_bvh_copy, log

from mathutils import Vector

MIN_CONTROLLER_DIST_FROM_EDGE = 0.02

"""
How this works:

Blender does some "clever" things to determine which direction the edge should slide, i.e. it uses
the mouse and desktop screen viewport to do some really weird shit to the "slide_factor" value.

Sometimes, the positive slide_factor value given by you will be flipped by Blender to negative, and sometimes it won't.
The "clever" logic used by Blender for edge sliding is very convoluted. And I don't want to recreate all that logic here,
since I don't want to implement a custom 3D engine.

So this implementation is a cheeky ugly hack. It just slides the edge with a positive factor, and if it's sliding in the
wrong direction (i.e. moving away from the controller), then it just flips the sign and tries again. And just because
Blender does weird shit, this logic sometimes has to try one more time, but without flipping the sign.

And that works. Magic.
"""

prev_edge_id = None
loop_verts = []


def on_controller_move(self, event_name, event):
    global prev_edge_id

    ob = bpy.context.view_layer.objects.active
    if ob is None or ob.mode != "EDIT" or ob.type != "MESH":
        return

    mat_world = ob.matrix_world
    pt = xr_session.controller_main_aim_position
    pt_local = mat_world.inverted() @ pt
    viewer_scale = xr_session.viewer_scale

    # find the closest edge
    closest_edge = None
    closest_edge_pt = None
    bm = get_bmesh_copy()
    bvh = get_bvh_copy()
    loc, norm, face_id, dist = bvh.find_nearest(pt_local)
    if face_id is None:
        return

    face = bm.faces[face_id]

    closest_edge_dist = 100000
    for edge in face.edges:
        v0, v1 = edge.verts
        v0 = mat_world @ v0.co
        v1 = mat_world @ v1.co
        nearest_pt = nearest_point_on_line_segment(pt, v0, v1)
        d = (nearest_pt - pt).length
        if d < closest_edge_dist and d < MIN_CONTROLLER_DIST_FROM_EDGE * viewer_scale:
            closest_edge = (edge.index, v0, v1)
            closest_edge_pt = nearest_pt
            closest_edge_dist = d

    if closest_edge is None:
        if prev_edge_id is not None:
            revert_to_bmesh_copy()
            log.debug("Out of range, reverted to orig mesh")

        prev_edge_id = None
        return

    # originally inspired by https://blender.stackexchange.com/a/43076

    # find the "slide factor"
    closest_edge_id, v0, v1 = closest_edge
    mid = (v0 + v1) / 2
    slide_factor = (mid - closest_edge_pt).length
    slide_factor /= 0.5 * (v1 - v0).length

    # perform the loop cut.
    if prev_edge_id is None or prev_edge_id != closest_edge_id:
        revert_to_bmesh_copy()

        bpy.ops.mesh.loopcut(number_cuts=1, object_index=0, edge_index=closest_edge_id)
        log.debug(f"Cut loop at {closest_edge_id}")

        bm = get_bmesh()

        loop_verts.clear()
        for vert in bm.verts:
            if not vert.select:
                continue

            v_world = mat_world @ vert.co
            d = (v_world - pt).length
            loop_verts.append((vert.index, d, Vector(vert.co), v_world))

        loop_verts.sort(key=lambda x: x[1])

        if len(loop_verts) == 0:
            revert_to_bmesh_copy()
            prev_edge_id = closest_edge_id
            return

    if len(loop_verts) == 0:
        return

    bm = get_bmesh()
    loop_closest_vert_idx = loop_verts[0][0]

    # reset the new edge loop, and try sliding it in the positive direction
    for vert_idx, _, orig_pos, _ in loop_verts:
        vert = bm.verts[vert_idx]
        vert.co = orig_pos

    d = (mat_world @ bm.verts[loop_closest_vert_idx].co - pt).length
    bpy.ops.transform.edge_slide(value=slide_factor)

    # if that direction was wrong, try sliding it in the negative direction
    if (mat_world @ bm.verts[loop_closest_vert_idx].co - pt).length > d:
        for vert_idx, _, orig_pos, _ in loop_verts:
            vert = bm.verts[vert_idx]
            vert.co = orig_pos

        d = (mat_world @ bm.verts[loop_closest_vert_idx].co - pt).length
        bpy.ops.transform.edge_slide(value=-slide_factor)

        # one more time, without flipping the sign. this happens sometimes
        if (mat_world @ bm.verts[loop_closest_vert_idx].co - pt).length > d:
            for vert_idx, _, orig_pos, _ in loop_verts:
                vert = bm.verts[vert_idx]
                vert.co = orig_pos

            d = (mat_world @ bm.verts[loop_closest_vert_idx].co - pt).length
            bpy.ops.transform.edge_slide(value=-slide_factor)

    prev_edge_id = closest_edge_id


def on_trigger_start(self, event_name, event):
    global prev_edge_id

    ob = bpy.context.view_layer.objects.active
    if ob is None or ob.mode != "EDIT" or ob.type != "MESH":
        return

    event.stop_propagation_immediate = True

    prev_edge_id = None

    log.info("Cut an edge loop")
    bpy.ops.ed.undo_push(message="Loop cut")

    make_bmesh_copy()


def on_undo_redo(self, event_name, event):
    global prev_edge_id

    ob = bpy.context.view_layer.objects.active
    if ob is None or ob.mode != "EDIT" or ob.type != "MESH":
        return

    prev_edge_id = None
    make_bmesh_copy()


def is_tool_allowed():
    ob = bpy.context.view_layer.objects.active
    if ob is None or ob.mode != "EDIT" or ob.type != "MESH":
        return False

    return True


def enable_tool():
    global prev_edge_id

    prev_edge_id = None

    make_bmesh_copy()

    root.add_event_listener("controller_main_move", on_controller_move)
    root.add_event_listener("trigger_main_start", on_trigger_start)

    root.add_event_listener("fb.undo", on_undo_redo)
    root.add_event_listener("fb.redo", on_undo_redo)


def disable_tool():
    revert_to_bmesh_copy()

    free_bmesh_copy()

    root.remove_event_listener("controller_main_move", on_controller_move)
    root.remove_event_listener("trigger_main_start", on_trigger_start)

    root.remove_event_listener("fb.undo", on_undo_redo)
    root.remove_event_listener("fb.redo", on_undo_redo)
