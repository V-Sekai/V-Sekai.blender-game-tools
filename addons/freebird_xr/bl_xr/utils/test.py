# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
import bmesh
from bpy.types import SplinePoint
from bmesh.types import BMVert, BMEdge, BMFace

from dataclasses import dataclass
from mathutils import Vector, Quaternion

from bl_input.bindings import THRESHOLD
from bl_xr import (
    Event,
    ControllerEvent,
    TwoHandedControllerEvent,
    DragEvent,
    UIEvent,
    MouseEvent,
    Pose,
    intersections,
)
from bl_xr import root, intersections, xr_session
from bl_xr.utils import vec_equal, quat_equal, to_blender_axis_system, is_equal
from bl_xr.events import make_events

from collections.abc import Iterable
from typing import Union, Callable
from math import radians

from mathutils import Vector, Quaternion


BELOW_THRESHOLD = THRESHOLD["trigger"] * 0.75
ABOVE_THRESHOLD = 1

EVENT_RECORDINGS = []

orig_viewer_location_getter = None
orig_viewer_location_setter = None
orig_viewer_rotation_getter = None
orig_viewer_rotation_setter = None
orig_viewer_scale_getter = None
orig_viewer_scale_setter = None
orig_viewer_camera_position_getter = None
orig_viewer_camera_rotation_getter = None
orig_xr_is_running_getter = None


@dataclass
class StubXrEventData:
    action: str = ""
    bimanual: bool = False
    controller_location: Vector = (0.0, 0.0, 0.0)
    controller_location_other: Vector = (0.0, 0.0, 0.0)
    controller_rotation: Quaternion = (0.0, 0.0, 0.0, 0.0)
    controller_rotation_other: Quaternion = (0.0, 0.0, 0.0, 0.0)
    state: tuple = (0, 0)
    state_other: tuple = (0, 0)
    user_path: str = ""
    user_path_other: str = ""


@dataclass
class StubEvent:
    type: str
    value: str
    xr: StubXrEventData = None
    mouse_x: int = 0
    mouse_y: int = 0


def make_bl_event(
    action: str,
    press_type: str,
    hand: Union[str, list[str]],
    value: Union[float, list[float]] = None,
    position: Union[Vector, list[Vector]] = None,
    rotation: Union[Quaternion, list[Quaternion]] = None,
):
    """
    * action - string
    * press_type - "PRESS", "RELEASE"
    * hand - "right", "left", ["right", "left"]
    * value - float, [float, float]
    """
    hand = [hand] if isinstance(hand, str) else hand
    hand = [f"/user/hand/{h}" for h in hand]

    if value is None:
        value = ABOVE_THRESHOLD if press_type == "PRESS" else BELOW_THRESHOLD
        value = [value] * len(hand)
    elif not isinstance(value, list):
        value = [value]

    if position is None:
        position = [Vector()] * len(hand)
    elif not isinstance(position, list):
        position = [position]

    if rotation is None:
        rotation = Quaternion()

    if not isinstance(rotation, list):
        rotation = [rotation] * len(hand)

    if getattr(make_bl_event, "pitched_rotation", False):
        for i in range(len(rotation)):
            rotation[i] = to_blender_axis_system(rotation[i])

    xr_data = StubXrEventData(
        action=action,
        bimanual=len(hand) > 1,
        controller_location=position[0],
        controller_rotation=rotation[0],
        state=[value[0], 0],
        user_path=hand[0],
    )
    if len(hand) > 1:
        xr_data.controller_location_other = position[1]
        xr_data.controller_rotation_other = rotation[1]
        xr_data.state_other = [value[1], 0]
        xr_data.user_path_other = hand[1]

    return StubEvent("XR_ACTION", press_type, xr_data)


def make_controller_event(
    event_type,
    hand,
    button_name: str = None,
    position: Vector = None,
    rotation: Quaternion = None,
    target=None,
    sub_targets=None,
) -> ControllerEvent:
    hand = [hand] if isinstance(hand, str) else hand
    if position is None:
        position = [Vector()] * len(hand)
    elif not isinstance(position, list):
        position = [position]

    if rotation is None:
        if getattr(make_controller_event, "pitched_rotation", False):
            rotation = [Quaternion((1, 0, 0), radians(-90))] * len(hand)
        else:
            rotation = [Quaternion()] * len(hand)
    elif not isinstance(rotation, list):
        rotation = [rotation]

    value = [0.0 if "_end" in event_type else 1.0] * len(hand)

    if button_name is None:
        button_name = event_type.replace("_start", "").replace("_press", "").replace("_end", "")

    event = TwoHandedControllerEvent() if len(hand) > 1 else ControllerEvent()
    event.type = event_type
    event.targets = t(target)
    event.sub_targets = sub_targets
    event.button_name = button_name
    event.position = position[0]
    event.rotation = rotation[0]
    event.value = value[0]
    event.hand = hand[0]

    if len(hand) > 1:
        event.position_other = position[1]
        event.rotation_other = rotation[1]
        event.hand_other = hand[1]
        event.value_other = value[1]

    return event


def make_drag_event(
    event_type,
    button_name: str = None,
    pose_delta: Pose = None,
    pivot_position: Vector = None,
    target=None,
) -> DragEvent:
    event = DragEvent()
    event.type = event_type
    event.targets = t(target)
    event.button_name = button_name
    event.pose_delta = pose_delta
    event.pivot_position = pivot_position

    return event


def make_ui_event(event_type, hand: str, position: Vector = None, target=None) -> UIEvent:
    skip_default_position = event_type.endswith("_leave") or event_type == "controller_main_enter"
    if position is None and not skip_default_position:
        position = Vector()

    return UIEvent(
        type=event_type,
        targets=t(target),
        hand=hand,
        position=position,
    )


def make_move_event(hand: str, position: Vector = None, rotation: Quaternion = None, target=None):
    event_type = f"controller_{hand.lower()}_move"
    event = make_controller_event(
        event_type,
        hand=hand,
        position=position,
        rotation=rotation,
        target=target,
        button_name="pose",
    )
    event.value = None
    return event


def make_bl_mouse_event(mouse_x: int, mouse_y: int):
    return StubEvent("MOUSEMOVE", "", mouse_x=mouse_x, mouse_y=mouse_y)


def make_mouse_event(event_type, mouse_position, target=None):
    return MouseEvent(event_type, mouse_position=mouse_position, targets=t(target))


def reset_input_tracking():
    make_events.controller.input_state = {}
    make_events.click_drag._events_tracking = {}

    intersections.curr["bounds"] = {}
    intersections.curr["raycast"] = {}
    intersections.prev["bounds"] = {}
    intersections.prev["raycast"] = {}
    intersections.sub_targets = None


def t(target):
    if not target:
        return None
    return target if isinstance(target, list) else [target]


def assert_events_nested_list_equal(actual_seq: list[list[Event]], expected_seq: list[list[Event]]):
    assert len(actual_seq) == len(expected_seq), f"{len(actual_seq)} != {len(expected_seq)}"

    i = 1
    for actual_events, expected_events in zip(actual_seq, expected_seq):
        assert_events_list_equal(actual_events, expected_events)

        print(f"frame {i} passed")
        i += 1


def assert_events_list_equal(actual_events: list[Event], expected_events: list[Event]) -> bool:
    length_error = f"event count: {len(actual_events)} != {len(expected_events)}. "
    length_error += f"actual: {actual_events}, expected: {expected_events}"
    assert len(actual_events) == len(expected_events), length_error

    i = 1
    for actual_event, expected_event in zip(actual_events, expected_events):
        assert type(actual_event) == type(expected_event), f"{i} {type(actual_event)} != {type(expected_event)}"
        if actual_event is None and expected_event is None:
            i += 1
            continue

        assert actual_event.type == expected_event.type, f"{i} {actual_event.type} != {expected_event.type}"
        assert_objects_equal(actual_event, expected_event)

        print(f"event {i} passed")
        i += 1


def assert_target_event_pairs_equal(
    actual_events: list[tuple[str, Event]], expected_events: list[tuple[str, Event]]
) -> bool:
    a = list(map(lambda x: (x[0], x[1].type) if x else x, actual_events))
    e = list(map(lambda x: (x[0], x[1].type) if x else x, expected_events))

    length_error = f"event count: {len(actual_events)} != {len(expected_events)}. "
    length_error += f"actual: {a}, expected: {e}"
    assert len(actual_events) == len(expected_events), length_error

    actual_targets, actual_events = zip(*actual_events)
    expected_targets, expected_events = zip(*expected_events)

    assert actual_targets == expected_targets, f"{actual_targets} != {expected_targets}"
    assert_events_list_equal(actual_events, expected_events)


def assert_objects_equal(actual_object: object, expected_object: object):
    assert type(actual_object) == type(expected_object), f"type: {type(actual_object)} != {type(expected_object)}"

    fields = {v for v in dir(actual_object) if not (v.startswith("__") or callable(getattr(actual_object, v)))}
    for field in fields:
        assert_field_equal(actual_object, expected_object, field)


def assert_field_equal(actual_object: object, expected_object: object, field: str):
    actual = getattr(actual_object, field)
    expected = getattr(expected_object, field)

    assert_error = f"field '{field}': {actual} != {expected}"

    assert is_equal(actual, expected), assert_error


def make_primitive_shape(primitive_type, position=Vector(), undo_entry=True, name=None):
    prev_active_obj = bpy.context.view_layer.objects.active
    primitive_type = primitive_type.lower()

    if primitive_type == "cube":
        bpy.ops.mesh.primitive_cube_add(location=position, size=2, scale=(1, 1, 1))
    elif primitive_type == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(location=position, scale=(1, 1, 1))
    elif primitive_type == "torus":
        bpy.ops.mesh.primitive_torus_add(location=position)
    elif primitive_type == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(location=position, scale=(1, 1, 1))
    elif primitive_type == "cone":
        bpy.ops.mesh.primitive_cone_add(location=position, scale=(1, 1, 1))
    elif primitive_type == "monkey":
        bpy.ops.mesh.primitive_monkey_add(location=position, size=2, scale=(1, 1, 1))

    new_ob = bpy.context.view_layer.objects.active

    if name is not None:
        new_ob.name = name

    if undo_entry:
        bpy.ops.ed.undo_push(message="make shape")

    if new_ob == prev_active_obj:
        raise Exception("Couldn't create primitive shape: " + primitive_type)
    return new_ob


def make_nurbs_curve(
    name: str = "Curve",
    points: list[Vector] = None,
    radius: float = 0.1,
    position: Vector = None,
    rotation: Quaternion = None,
    undo_entry=True,
) -> bpy.types.Object:
    position, rotation = make_defaults_if_needed(position, rotation)
    if points is None:
        points = [Vector((0, 0, 0)), Vector((0, 1, 0)), Vector((1, 1, 0))]

    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_mode = "ROUND"
    curve.bevel_resolution = 4

    ob = bpy.data.objects.new(name, curve)
    ob.location = position
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = rotation
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob

    polyline = curve.splines.new("NURBS")

    for i, p in enumerate(points):
        if i > 0:
            polyline.points.add(1)  # adding one by one, to mimic the behavior of hand-drawn strokes

        polyline.points[-1].co = p.to_tuple() + (1,)
        polyline.points[-1].radius = 1

    polyline.use_endpoint_u = True  # mimic the behavior of hand-drawn strokes

    if undo_entry:
        bpy.ops.ed.undo_push(message="make curve")

    return ob


def make_hull(
    name: str = "Hull",
    points: list[Vector] = None,
    position: Vector = None,
    rotation: Quaternion = None,
    undo_entry=True,
) -> bpy.types.Object:
    position, rotation = make_defaults_if_needed(position, rotation)
    if points is None:  # pyramid
        points = [
            Vector((-1, -1, 0)),
            Vector((-1, 1, 0)),
            Vector((1, 1, 0)),
            Vector((1, -1, 0)),
            Vector((0, 0, 1)),
        ]
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0), size=1, scale=(1, 1, 1))
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.location = position
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = rotation
    bm = bmesh.new()
    # adding each point one-by-one, to mimic the behavior of hand-drawn hulls
    for p in points:
        bm.verts.new(p)
        hull = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=True)
        geom_to_remove = list(set(hull["geom_interior"]) | set(hull["geom_unused"]))
        bmesh.ops.delete(bm, geom=geom_to_remove, context="VERTS")
        bm.to_mesh(ob.data)
    bm.free()

    if undo_entry:
        bpy.ops.ed.undo_push(message="make hull")

    return ob


def make_tuning_fork_armature(
    name: str = "Armature", position: Vector = None, rotation: Quaternion = None
) -> bpy.types.Object:
    "Makes an armature that looks like a tuning fork"

    return make_armature(
        name,
        [  # head, tail, parentIdx
            ((0, 0, 0), (0, 1, 0), -1),
            ((0, 1, 0), (0, 2, 0), 0),
            ((0, 2, 0), (-1, 3, 0), 1),  # fork 1
            ((0, 2, 0), (1, 3, 0), 1),  # fork 2
            ((-1, 3, 0), (-1, 4, 0), 2),  # fork 1 arm
            ((1, 3, 0), (1, 4, 0), 3),  # fork 2 arm
        ],
        position,
        rotation,
    )


def make_simple_armature(
    name: str = "Armature", position: Vector = None, rotation: Quaternion = None
) -> bpy.types.Object:
    "Makes a two-bone armature"

    return make_armature(
        name,
        [  # head, tail, parentIdx
            ((0, 0, 0), (0, 0, 1), -1),
            ((0, 0, 1), (0, 0, 2), 0),
        ],
        position,
        rotation,
    )


def make_armature(
    name: str = "Armature",
    bone_points=[],
    position: Vector = None,
    rotation: Quaternion = None,
):
    "Makes an armature with the bone points specified in a list[(head_pos, tail_pos, parentIdx)]"

    position, rotation = make_defaults_if_needed(position, rotation)
    bpy.ops.object.armature_add()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.location = position
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = rotation
    armature = ob.data
    bpy.ops.object.mode_set(mode="EDIT")
    for i, data in enumerate(bone_points):
        head, tail, parent_idx = data
        if i > 0:
            b = armature.edit_bones.new("Bone")
        b = armature.edit_bones[-1]
        b.head, b.tail = head, tail
        if parent_idx != -1:
            parent = armature.edit_bones[parent_idx]
            b.select, parent.select = True, True
            armature.edit_bones.active = parent
            bpy.ops.armature.parent_set()
            b.select, parent.select = False, False
    bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.ed.undo_push(message="make armature")

    return ob


def make_camera(name: str = "Camera", position: Vector = None, rotation: Quaternion = None):
    rotation = rotation if rotation is not None else Quaternion((1, 0, 0), radians(90))
    position, rotation = make_defaults_if_needed(position, rotation)

    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.camera = cam
    bpy.context.scene.collection.objects.link(cam)

    cam.location = position
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = rotation
    cam.rotation_mode = "XYZ"

    bpy.context.view_layer.objects.active = cam

    bpy.ops.ed.undo_push(message="make camera")

    return cam


def make_light(name: str = "Light", type: str = "POINT", position: Vector = None, rotation: Quaternion = None):
    rotation = rotation if rotation is not None else Quaternion((1, 0, 0), radians(90))
    position, rotation = make_defaults_if_needed(position, rotation)

    light_data = bpy.data.lights.new("Light", type=type)
    light = bpy.data.objects.new(name, light_data)
    bpy.context.scene.camera = light
    bpy.context.scene.collection.objects.link(light)

    light.location = position
    light.rotation_mode = "QUATERNION"
    light.rotation_quaternion = rotation
    light.rotation_mode = "XYZ"

    if type == "AREA":
        light.data.size = 0.1
        light.data.size_y = 0.2
    else:
        light.data.shadow_soft_size = 0.1

    bpy.context.view_layer.objects.active = light

    bpy.ops.ed.undo_push(message="make light")

    return light


def make_defaults_if_needed(position, rotation):
    if position is None:
        position = Vector()
    if rotation is None:
        rotation = Quaternion()
    return position, rotation


def assert_mesh_verts_equal(actual_verts: Union[list[Vector], set[BMVert]], expected_verts: list[Vector]):
    actual_verts = transform_sub_targets(actual_verts, lambda v: v.co, BMVert)
    assert_unordered_nested_equal(actual_verts, expected_verts)


def assert_mesh_edges_equal(actual_edges: Union[list[Vector], set[BMEdge]], expected_edges: list[Vector]):
    actual_edges = transform_sub_targets(actual_edges, lambda e: tuple(v.co for v in e.verts), BMEdge)
    assert_unordered_nested_equal(actual_edges, expected_edges)


def assert_mesh_faces_equal(actual_faces: Union[list[Vector], set[BMFace]], expected_faces: list[Vector]):
    actual_faces = transform_sub_targets(actual_faces, lambda f: tuple(v.co for v in f.verts), BMFace)
    assert_unordered_nested_equal(actual_faces, expected_faces)


def assert_spline_points_equal(actual_points: Union[list[Vector], set[SplinePoint]], expected_points: list[Vector]):
    actual_points = transform_sub_targets(actual_points, lambda v: Vector(v.co[:-1]), SplinePoint)
    assert_unordered_nested_equal(actual_points, expected_points)


def transform_sub_targets(actual_elements: set, transform: Callable, element_type: type) -> list:
    assert isinstance(actual_elements, set), f"type(actual_elements) is {type(actual_elements)}. expected a set"
    assert all(isinstance(e, element_type) for e in iter(actual_elements)), f"Not an instance of {element_type}"

    return list(map(transform, iter(actual_elements)))


def assert_unordered_nested_equal(actual_elements: Union[list[Vector], set], expected_elements: list[set[Vector]]):
    def key(a, b):
        if isinstance(b, Iterable):
            return is_unordered_equal(a, b, key=key)
        return is_equal(a, b)

    assert is_unordered_equal(actual_elements, expected_elements, key=key), f"{actual_elements} != {expected_elements}"


def is_unordered_equal(list_a: Iterable, list_b: Iterable, key: Callable) -> bool:
    assert len(list_a) == len(list_b), f"{len(list_a)} != {len(list_b)}"

    if not isinstance(list_a, Iterable):
        list_a = [list_a]
    if not isinstance(list_b, Iterable):
        list_b = [list_b]

    matched = set()
    for b in list_b:
        for a in list_a:
            if id(a) in matched:
                continue

            if key(a, b):
                matched.add(id(a))
                break

    return len(matched) == len(list_a)


def apply_xr_session_override():
    global orig_viewer_location_getter, orig_viewer_location_setter
    global orig_viewer_rotation_getter, orig_viewer_rotation_setter
    global orig_viewer_scale_getter, orig_viewer_scale_setter
    global orig_viewer_camera_position_getter, orig_viewer_camera_rotation_getter
    global orig_xr_is_running_getter

    orig_viewer_location_getter = type(xr_session).viewer_location.__get__
    orig_viewer_location_setter = type(xr_session).viewer_location.__set__
    orig_viewer_rotation_getter = type(xr_session).viewer_rotation.__get__
    orig_viewer_rotation_setter = type(xr_session).viewer_rotation.__set__
    orig_viewer_scale_getter = type(xr_session).viewer_scale.__get__
    orig_viewer_scale_setter = type(xr_session).viewer_scale.__set__
    orig_viewer_camera_position_getter = type(xr_session).viewer_camera_position.__get__
    orig_viewer_camera_rotation_getter = type(xr_session).viewer_camera_rotation.__get__

    orig_xr_is_running_getter = type(xr_session).is_running.__get__

    reset_xr_session_override_values()


def reset_xr_session_override_values():
    type(xr_session).viewer_location = Vector()
    type(xr_session).viewer_rotation = Quaternion()
    type(xr_session).viewer_scale = 1
    type(xr_session).viewer_camera_position = Vector()
    type(xr_session).viewer_camera_rotation = Quaternion()
    type(xr_session).is_running = False

    xr_session.viewer_location = Vector()
    xr_session.viewer_rotation = Quaternion()
    xr_session.viewer_scale = 1
    xr_session.viewer_camera_position = Vector()
    xr_session.viewer_camera_rotation = Quaternion()
    xr_session.is_running = False


def remove_xr_session_override():
    type(xr_session).viewer_location = property(orig_viewer_location_getter)
    type(xr_session).viewer_location = type(xr_session).viewer_location.setter(orig_viewer_location_setter)
    type(xr_session).viewer_rotation = property(orig_viewer_rotation_getter)
    type(xr_session).viewer_rotation = type(xr_session).viewer_rotation.setter(orig_viewer_rotation_setter)
    type(xr_session).viewer_scale = property(orig_viewer_scale_getter)
    type(xr_session).viewer_scale = type(xr_session).viewer_scale.setter(orig_viewer_scale_setter)
    type(xr_session).viewer_camera_position = property(orig_viewer_camera_position_getter)
    type(xr_session).viewer_camera_rotation = property(orig_viewer_camera_rotation_getter)

    type(xr_session).is_running = property(orig_xr_is_running_getter)


def set_mode(mode, ob=None, mesh_mode=None):
    if ob:
        bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode=mode)
    if ob:
        bpy.context.view_layer.objects.active = ob
    if mode == "EDIT" and bpy.context.view_layer.objects.active.type == "MESH" and mesh_mode:
        bpy.ops.mesh.select_mode(type=mesh_mode)


def recording_event_handler(target):
    def handler(self, event_name: str, event: Event):
        if isinstance(target, bpy.types.Object):
            node_name = target.name
        elif target == root:
            node_name = "root"
        else:
            node_name = target.id

        EVENT_RECORDINGS.append((node_name, event))

    return handler
