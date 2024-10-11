# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Object, PoseBone
from mathutils import Vector, Euler, Matrix
from mathutils.geometry import intersect_line_plane
import math
import traceback

from ..dom import Node
from ..consts import VEC_ZERO, VEC_UP, VEC_ONE
from .geometry_utils import nearest_point_on_line_segment, intersect_line_sphere, project_point_on_plane, Bounds
from .mesh_utils import get_bmesh, get_bvh
from .misc_utils import get_node_breadcrumb
from bl_math import lerp

EDIT_BONE_CORNER_SELECTION_THRESHOLD_RATIO = 0.1  # i.e. 10%
"Threshold (ratio to full bone length) below which only the corner will be selected"


def intersects_object_mesh(ob, center, shape, size):
    if ob.hide_get():
        return

    stroke_pt_local = ob.matrix_world.inverted() @ center

    if ob.type == "CURVE" or len(ob.data.polygons) > 0:
        _, loc_local, _, _ = ob.closest_point_on_mesh(stroke_pt_local)
        loc_world = ob.matrix_world @ loc_local
        d = (loc_world - center).length
        # print(ob.name, d, size, stroke_pt_local, center, "nearest", loc_local)

        if d <= size:
            return [ob]
    else:
        bm = get_bmesh(ob)
        mat_world = ob.matrix_world

        for e in bm.edges:
            if e.hide:
                continue

            v0, v1 = e.verts
            v0_world = mat_world @ v0.co
            v1_world = mat_world @ v1.co
            nearest_pt = nearest_point_on_line_segment(center, v0_world, v1_world)
            d = nearest_pt - center
            if d.length <= size:
                return [ob]


def intersects_object_camera(ob, center, shape, size):
    if ob.hide_get():
        return

    frame = ob.data.view_frame(scene=bpy.context.scene)
    frame = [ob.matrix_world @ p for p in frame]
    lines = [(p, ob.location) for p in frame]
    lines += [(frame[0], frame[1]), (frame[1], frame[2]), (frame[2], frame[3]), (frame[3], frame[0])]

    for p0, p1 in lines:
        nearest = nearest_point_on_line_segment(center, p0, p1)
        d = (nearest - center).length
        # print(f"d: {d}, p0: {p0}, p1: {p1}")
        if d <= size:
            return [ob]


def intersects_object_light(ob, center, shape, size):
    if ob.hide_get():
        return

    light = ob.data
    if light.type in ("POINT", "SPOT", "SUN"):
        r = 0.1 if light.type == "SUN" else light.shadow_soft_size
        r *= 1.1  # increase hitbox by 10% for ease of selection

        dist_from_center = (Vector(ob.location) - center).length
        d = dist_from_center - r  # dist from surface
        if d <= size:
            return [ob]
    elif light.type == "AREA":
        plane_pt = ob.matrix_world @ Vector((light.size, light.size_y, 0))
        plane_normal = ob.matrix_world @ VEC_UP

        proj = project_point_on_plane(plane_pt, plane_normal, center)
        proj_local = ob.matrix_world.inverted() @ proj

        if abs(proj_local.x) < light.size * 1.1 and abs(proj_local.y) < light.size_y * 1.1:
            d = (proj - center).length
            if d <= size:
                return [ob]

        dist_from_center = (Vector(ob.location) - center).length
        d = dist_from_center - 0.1  # assume a 0.1 radius sphere around the light
        if d <= size:
            return [ob]


def intersects_edit_mesh(ob, center, shape, size):
    intersecting_elements = set()
    bm = get_bmesh(ob)

    vert_mode, edge_mode, _ = bpy.context.scene.tool_settings.mesh_select_mode
    mat_world = ob.matrix_world

    if vert_mode:
        for v in bm.verts:
            if v.hide:
                continue

            v_world = mat_world @ v.co
            d = v_world - center
            if d.length <= size:
                intersecting_elements.add(v)
    elif edge_mode:
        for e in bm.edges:
            if e.hide:
                continue

            v0, v1 = e.verts
            v0_world = mat_world @ v0.co
            v1_world = mat_world @ v1.co
            nearest_pt = nearest_point_on_line_segment(center, v0_world, v1_world)
            d = nearest_pt - center
            if d.length <= size:
                intersecting_elements.add(e)
    else:
        bvh = get_bvh()

        stroke_pt_local = mat_world.inverted() @ center

        elements = bvh.find_nearest_range(stroke_pt_local)

        for location, _, face_idx, _ in elements:
            face = bm.faces[face_idx]
            if face.hide:
                continue

            loc_world = mat_world @ location
            d = (loc_world - center).length
            is_nearby = d <= size
            # print(ob.name, face_idx, d, size, is_nearby, stroke_pt_local, center, "nearest", loc_world)
            if is_nearby:
                intersecting_elements.add(face)

    if len(intersecting_elements) > 0:
        return list(intersecting_elements)


intersects_object_curve = intersects_object_mesh


def check_custom_bone_shape_mesh(ob, center, shape, size, mat_world, bone_length):
    intersecting_elements = set()
    bm = get_bmesh(ob)

    for e in bm.edges:
        if e.hide:
            continue

        v0, v1 = e.verts
        v0_world = mat_world @ (v0.co * bone_length)
        v1_world = mat_world @ (v1.co * bone_length)
        nearest_pt = nearest_point_on_line_segment(center, v0_world, v1_world)
        d = nearest_pt - center
        if d.length <= size:
            intersecting_elements.add(e)

    if len(intersecting_elements) > 0:
        return list(intersecting_elements)


def intersects_object_armature(ob, center, shape, size):
    if ob.hide_get():
        return

    armature = ob.data
    bones = ob.pose.bones
    intersecting_elements = get_intersecting_bones(ob, center, shape, size, armature, bones)

    if len(intersecting_elements) > 0:
        return [ob]


def intersects_edit_curve(ob, center, shape, size):
    intersecting_elements = []
    mat_world = ob.matrix_world

    curve = ob.data
    if len(curve.splines) == 0:
        return intersecting_elements

    spline = curve.splines[0]

    for v in spline.points:
        if v.hide:
            continue

        p = Vector((v.co[0], v.co[1], v.co[2]))
        p_world = mat_world @ p
        d = (p_world - center).length
        # print(ob.name, d, size, stroke_pt_local, center, v, v.co)
        if d <= size:
            intersecting_elements.append(v)

    if len(intersecting_elements) > 0:
        return intersecting_elements


def intersects_edit_armature(ob, center, shape, cursor_size):
    armature = ob.data
    bones = armature.edit_bones if ob.mode == "EDIT" else ob.pose.bones

    intersecting_elements = get_intersecting_bones(ob, center, shape, cursor_size, armature, bones)

    # print("intersecting elements:", [(b.name, t) for b, t in intersecting_elements])

    if len(intersecting_elements) > 0:
        return intersecting_elements


def intersects_pose_armature(ob, center, shape, size):
    intersecting_elements = intersects_edit_armature(ob, center, shape, size)

    if intersecting_elements:
        intersecting_elements = [(bone, "BOTH") for bone, _ in intersecting_elements]

    return intersecting_elements


def get_intersecting_bones(ob, center, shape, cursor_size, armature, bones):
    mat_local_to_world = ob.matrix_world

    intersecting_elements = []
    for bone in bones:
        bone_hidden = bone.bone.hide if isinstance(bone, PoseBone) else bone.hide
        if bone_hidden:
            continue

        if isinstance(bone, PoseBone) and bone.custom_shape:
            bone_length = (bone.head - bone.tail).length

            loc = bone.custom_shape_translation
            rot = bone.custom_shape_rotation_euler.to_quaternion()
            scale = bone.custom_shape_scale_xyz

            custom_shape_transform = Matrix.LocRotScale(loc, rot, scale)
            bone_matrix = bone.custom_shape_transform.matrix if bone.custom_shape_transform else bone.matrix

            transform_matrix = ob.matrix_world @ bone_matrix @ custom_shape_transform

            intersecting = check_custom_bone_shape_mesh(
                bone.custom_shape, center, shape, cursor_size, transform_matrix, bone_length
            )
            if intersecting:
                intersecting_elements.append((bone.name, "BOTH"))

            continue

        bone_head_world = mat_local_to_world @ bone.head
        bone_tail_world = mat_local_to_world @ bone.tail
        bone_length = (bone_head_world - bone_tail_world).length

        p0, p1 = intersect_line_sphere(bone_head_world, bone_tail_world, center, cursor_size)
        # print("d1", bone.name, p0, p1, "bone len", bone_length, "cursor size", cursor_size, "world cursor pt", center, "head w", bone_head_world, "tail w", bone_tail_world)

        if p0 is None and p1 is None:
            nearest_pt = nearest_point_on_line_segment(center, bone_head_world, bone_tail_world)
            d = nearest_pt - center
            bone_line_dist_from_cursor_center = d.length

            if bone_line_dist_from_cursor_center < cursor_size:  # bone is fully inside the sphere
                intersecting_elements.append((bone.name, "BOTH"))
            else:  # bone might be intersecting with the visualization envelope/octahedron
                envelope_size = 0
                t = (nearest_pt - bone_head_world).length / bone_length

                if armature.display_type == "OCTAHEDRAL":
                    # the octahedral peaks at 10%, and is of size 10% (of total length). it's linear to the head and tail
                    # the tail sphere radius is 5% of the bone length
                    # the head sphere radius is the same as the parent tail sphere
                    # if the head has no parent, then it has the same radius as its tail sphere

                    max_envelope_size = 0.1 * bone_length
                    if t <= 0.1:
                        envelope_size = lerp(0, max_envelope_size, t * 10)
                    else:
                        envelope_size = lerp(max_envelope_size, 0, (t - 0.1) / 0.9)
                elif armature.display_type == "ENVELOPE":
                    b = bone.bone if isinstance(bone, PoseBone) else bone
                    envelope_size = lerp(b.head_radius, b.tail_radius, t)
                    envelope_size *= ob.scale.x

                bone_surface_dist_from_cursor_center = bone_line_dist_from_cursor_center - envelope_size
                # print("d2", bone.name, bone_line_dist_from_cursor_center, t, bone_surface_dist_from_cursor_center, envelope_size, cursor_size, nearest_pt, armature.display_type)
                if bone_surface_dist_from_cursor_center <= cursor_size:
                    if t < EDIT_BONE_CORNER_SELECTION_THRESHOLD_RATIO:
                        target = "HEAD"
                    elif t > 1 - EDIT_BONE_CORNER_SELECTION_THRESHOLD_RATIO:
                        target = "TAIL"
                    else:
                        target = "BOTH"
                    intersecting_elements.append((bone.name, target))

        elif p0 and p1:  # full overlap, sphere is smaller than bone
            intersecting_elements.append((bone.name, "BOTH"))
        else:  # partial overlap, i.e. intersecting a corner
            p = p0 or p1
            target = "HEAD" if (bone_head_world - center).length <= cursor_size else "TAIL"
            overlap = bone_head_world - p if target == "HEAD" else bone_tail_world - p

            if overlap.length / bone_length > EDIT_BONE_CORNER_SELECTION_THRESHOLD_RATIO:
                target = "BOTH"

            intersecting_elements.append((bone.name, target))

    return intersecting_elements


def intersects_node(node: Node, center: Vector, shape: str, size: float) -> bool:
    if not node.get_computed_style("visible", True) or node.intersects not in ("all", "bounds"):
        return

    if len(node.child_nodes) == 0:
        return [node] if node.intersect(center, shape, size) else None

    intersections = []
    for child in node.child_nodes:
        if not child.get_computed_style("visible", True) or child.intersects not in ("all", "bounds"):
            continue

        child_intersections = intersects_node(child, center, shape, size)
        if child_intersections:
            intersections += child_intersections

    return intersections if len(intersections) > 0 else None


def intersects_object(ob, center, shape, size):
    if not ob.visible_get():
        return

    curr_mode = getattr(ob, "mode", "OBJECT")
    if ob.mode != curr_mode:
        return

    fn_name = f"intersects_{curr_mode.lower()}_{ob.type.lower()}"
    intersect_fn = globals().get(fn_name, lambda *args: None)

    return intersect_fn(ob, center, shape, size)


def intersects(element, center, shape, size):
    try:
        if isinstance(element, Node):
            return intersects_node(element, center, shape, size)
        elif isinstance(element, Object):
            return intersects_object(element, center, shape, size)
    except Exception as e:
        print(traceback.format_exc())
        print(f"error finding the intersection with {element} for center: {center}, size: {size}", e)


def nearest_point_on_line_segment(point: Vector, line_start: Vector, line_end: Vector):
    a = point - line_start
    l = line_end - line_start

    p = a.project(l) + line_start
    line_len = (line_end - line_start).length

    if (p - line_start).length > line_len:
        p = line_end
    elif (p - line_end).length > line_len:
        p = line_start

    return p


def raycast(ray_origin, ray_dir, object_raycast=True, ui_raycast=True) -> tuple[object, Vector, float]:
    """
    Returns: tuple(node, intersection_point_world, dist)

    Search order:
    1. Lists all the leaf nodes and node-with-children [*] that intersect with the ray. Sorted by distance (nearest to farthest).
    2. Returns the nearest leaf node. For e.g. a leaf node will be picked even if a node-with-children is closer.
    3. If no leaf node is found, it returns the first node-with-children.

    [*] node-with-children == a node that intersects, but none of its children intersect. E.g. in the blank spaces between child nodes.
    """
    import bl_xr
    from bl_xr import Node

    intersecting_nodes: list[tuple[object, Vector, float]] = []

    def raycast_node(node: Node):
        if not node.get_computed_style("visible", True) or node.intersects not in ("all", "raycast"):
            return False

        if len(node.child_nodes) == 0:
            intersects, pt_world, pt_local, dist = raycast_individual_node(node, ray_origin, ray_dir)
            if intersects and node != bl_xr.root:
                intersecting_nodes.append((node, pt_world, dist))

                return True
        elif node.get_computed_style("visible", True):
            child_intersections = [raycast_node(child_node) for child_node in node.child_nodes]
            if not any(child_intersections):
                intersects, pt_world, pt_local, dist = raycast_individual_node(node, ray_origin, ray_dir)
                if intersects and node != bl_xr.root:
                    intersecting_nodes.append((node, pt_world, dist))

                    return True

        return False

    def raycast_objects():
        curr_mode = getattr(bpy.context.view_layer.objects.active, "mode", "OBJECT")
        objects = [bpy.context.view_layer.objects.active] if curr_mode in ("EDIT", "POSE") else bpy.data.objects
        for ob in objects:
            if ob.type not in ("MESH", "CURVE"):
                continue

            try:
                ray_origin_local = ob.matrix_world.inverted() @ ray_origin
                ray_dir_local = ob.matrix_world.inverted().to_quaternion() @ ray_dir
                is_intersecting, point_local, _, _ = ob.ray_cast(ray_origin_local, ray_dir_local)
                point_world = ob.matrix_world @ point_local
                dist = (point_world - ray_origin).length
                if is_intersecting:
                    intersecting_nodes.append((ob, point_world, dist))
            except:
                pass

    if ui_raycast:
        raycast_node(bl_xr.root)

    if object_raycast:
        raycast_objects()

    if len(intersecting_nodes) == 0:
        return None, None, 0

    intersecting_nodes.sort(key=lambda n: int(n[2] * 1000))  # avoid z-fighting by using epsilon 0.001
    leaf_node = next(
        iter(n for n in intersecting_nodes if isinstance(n[0], Object) or len(n[0].child_nodes) == 0), None
    )

    return leaf_node if leaf_node else intersecting_nodes[0]


def raycast_individual_node(node: Node, ray_start, ray_dir, ray_dist=math.inf) -> tuple[bool, Vector, Vector, float]:
    """
    Returns: tuple(intersected : bool, intersection_world : Vector|None, intersection_local : Vector|None, intersection_dist : float|None)

    Restrictions:
    * currently only works for 2D bounds, not 3D bounds
    """

    NOT_INTERSECTED = (False, None, None, None)

    if not node.get_computed_style("visible", True) or node.intersects not in ("all", "raycast"):
        return NOT_INTERSECTED

    p0_local = node.world_to_local_point(ray_start)
    p1_local = node.world_to_local_point(ray_start + ray_dir)

    intersection_local = intersect_line_plane(p0_local, p1_local, VEC_ZERO, VEC_UP)

    if intersection_local is None:
        return NOT_INTERSECTED

    bounds_local = node.bounds_local
    if (
        intersection_local.x < bounds_local.min.x
        or intersection_local.x > bounds_local.max.x
        or intersection_local.y < bounds_local.min.y
        or intersection_local.y > bounds_local.max.y
    ):
        # print('out of bounds:', get_node_breadcrumb(node))
        return NOT_INTERSECTED

    intersection_world = node.local_to_world_point(intersection_local)
    intersection_dist = (intersection_world - ray_start).length

    if intersection_dist > ray_dist:
        return NOT_INTERSECTED

    return True, intersection_world, intersection_local, intersection_dist
