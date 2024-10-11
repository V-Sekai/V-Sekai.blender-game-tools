# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from .utils.xr_session_utils import xr_session
from .utils.geometry_utils import Bounds, Pose
from .events.types import EventAware
from .consts import VEC_ONE

from mathutils import Vector, Quaternion, Matrix


class Node(EventAware):
    EVENT_TYPES = [
        "on_pointer_main_enter",
        "on_pointer_main_move",
        "on_pointer_main_leave",
        "on_pointer_main_press_start",
        "on_pointer_main_press_press",
        "on_pointer_main_press_end",
    ]
    STYLESHEET = {}

    def __init__(self, **kwargs):
        if "class_name" in kwargs:
            kwargs["class_names"] = kwargs["class_name"].split(" ")
            del kwargs["class_name"]

        self.id: str = kwargs.get("id")

        self._parent: Node = None
        self.child_nodes: NodeList = NodeList()

        self.append_children(kwargs.get("child_nodes", []))

        self.style = kwargs.get("style", {})
        for key in ("position", "rotation", "scale"):
            if key in kwargs:
                self.style[key] = kwargs[key]

        self.class_names: list[str] = kwargs.get("class_names", [])

        self.intersects = kwargs.get("intersects", "all")
        "None, 'all', 'raycast', or 'bounds'"

        self._prevent_trigger_events_on_raycast: bool = kwargs.get("prevent_trigger_events_on_raycast", None)

        for event_type in Node.EVENT_TYPES:
            if event_type in kwargs and callable(kwargs[event_type]):
                self.add_event_listener(event_type[3:], kwargs[event_type])

    @property
    def parent(self) -> Node:
        return self._parent

    def append_child(self, child: Node):
        if not isinstance(child, Node):
            raise ValueError(f"Expected a child of type Node. Got: {type(child)}")

        if child._parent:
            if child in child._parent.child_nodes:
                child._parent.remove_child(child)

        self.child_nodes._nodes.append(child)
        child._parent = self

    def append_children(self, child_nodes: list[Node]):
        for child in child_nodes:
            self.append_child(child)

    def remove_child(self, child: Node):
        self.child_nodes._nodes.remove(child)
        child._parent = None

    @property
    def position(self) -> Vector:
        return self.get_computed_style("position", Vector())

    @property
    def rotation(self) -> Quaternion:
        return self.get_computed_style("rotation", Quaternion())

    @property
    def scale(self) -> Vector:
        scale = self.get_computed_style("scale", Vector((1, 1, 1)))
        scale = scale * VEC_ONE if not isinstance(scale, Vector) else scale
        return scale

    @property
    def position_world(self) -> Vector:
        return self.matrix_world.to_translation()

    @property
    def rotation_world(self) -> Quaternion:
        return self.matrix_world.to_quaternion()

    @property
    def scale_world(self) -> Vector:
        return self.matrix_world.to_scale()

    @position.setter
    def position(self, value: Vector):
        self.style["position"] = value

    @rotation.setter
    def rotation(self, value: Quaternion):
        self.style["rotation"] = value

    @scale.setter
    def scale(self, value: Vector):
        value = VEC_ONE * value if not isinstance(value, Vector) else value
        value /= xr_session.viewer_scale if self.get_computed_style("fixed_scale", False) else 1
        self.style["scale"] = value

    @position_world.setter
    def position_world(self, value: Vector):
        target = self.parent if self.parent else self
        self.position = target.world_to_local_point(value)

    @rotation_world.setter
    def rotation_world(self, value: Quaternion):
        target = self.parent if self.parent else self
        self.rotation = target.world_to_local_rotation(value)

    @scale_world.setter
    def scale_world(self, value: Vector):
        target = self.parent if self.parent else self
        self.scale = target.world_to_local_scale(value)

    @property
    def pose(self) -> Pose:
        return Pose(self.position, self.rotation, self.scale)

    @pose.setter
    def pose(self, p: Pose):
        self.position = p.position
        self.rotation = p.rotation
        self.scale = p.scale_factor

    @property
    def pose_world(self) -> Pose:
        return Pose(self.position_world, self.rotation_world, self.scale_world)

    @pose_world.setter
    def pose_world(self, p: Pose):
        self.position_world = p.position
        self.rotation_world = p.rotation
        self.scale_world = p.scale_factor

    def get_computed_style(self, style_name: str, default=None):
        if style_name in self.style:
            return self.style[style_name]

        selectors = []
        if self.id:
            selectors.append("#" + self.id)

        for class_name in self.class_names.__reversed__():
            selectors.append("." + class_name)

        for selector in selectors:
            if selector in Node.STYLESHEET and style_name in Node.STYLESHEET[selector]:
                return Node.STYLESHEET[selector][style_name]

        return default

    @property
    def matrix_world(self) -> Matrix:
        local_mat = self.matrix_local

        if self.get_computed_style("fixed_scale", False):
            loc, rot, scale = local_mat.decompose()
            local_mat = Matrix.LocRotScale(loc, rot, scale * xr_session.viewer_scale)

        if self.parent is None:
            return local_mat

        return self.parent.matrix_world @ local_mat

    @property
    def matrix_local(self) -> Matrix:
        return Matrix.LocRotScale(self.position, self.rotation, self.scale)

    def world_to_local_point(self, world_point: Vector) -> Vector:
        return self.matrix_world.inverted() @ world_point

    def world_to_local_rotation(self, world_rotation: Quaternion) -> Quaternion:
        return self.matrix_world.inverted().to_quaternion() @ world_rotation

    def world_to_local_scale(self, world_scale: Vector) -> Vector:
        return self.matrix_world.inverted().to_scale() * world_scale

    def local_to_world_point(self, local_point: Vector) -> Vector:
        return self.matrix_world @ local_point

    def local_to_world_rotation(self, local_rotation: Quaternion) -> Quaternion:
        return self.matrix_world.to_quaternion() @ local_rotation

    def local_to_world_scale(self, local_scale: Vector) -> Vector:
        return Vector(x * y for x, y in zip(self.matrix_world.to_scale(), local_scale))

    @property
    def bounds_world(self) -> Bounds:
        bounds_local = self.bounds_local
        matrix_world = self.matrix_world
        min_b, max_b = (
            matrix_world @ bounds_local.min,
            matrix_world @ bounds_local.max,
        )
        t = Vector(min_b)
        min_b.x = min(min_b.x, max_b.x)
        min_b.y = min(min_b.y, max_b.y)
        min_b.z = min(min_b.z, max_b.z)

        max_b.x = max(max_b.x, t.x)
        max_b.y = max(max_b.y, t.y)
        max_b.z = max(max_b.z, t.z)

        return Bounds(min_b, max_b)

    @property
    def bounds_local(self) -> Bounds:
        # if a primitive, then use its own bounds
        # else if has children, then get the children bounds_local, transform with the children's
        #  matrix_local and build a bounding box around those
        # else return zero

        min_b, max_b = None, None
        for child in self.child_nodes:
            if not child.get_computed_style("visible", True):
                continue

            bounds = child.bounds_local
            for b in (bounds.min, bounds.max):
                child_bounds = child.matrix_local @ b
                min_b = Vector(child_bounds) if min_b is None else min_b
                max_b = Vector(child_bounds) if max_b is None else max_b

                min_b.x = min(min_b.x, child_bounds.x)
                min_b.y = min(min_b.y, child_bounds.y)
                min_b.z = min(min_b.z, child_bounds.z)

                max_b.x = max(max_b.x, child_bounds.x)
                max_b.y = max(max_b.y, child_bounds.y)
                max_b.z = max(max_b.z, child_bounds.z)

        min_b = Vector() if min_b is None else min_b
        max_b = Vector() if max_b is None else max_b

        return Bounds(min_b, max_b)

    def intersect(self: Node, center: Vector, shape: str, size: float) -> bool:
        p_l = self.world_to_local_point(center)
        size_local = self.world_to_local_scale(VEC_ONE * size).x
        if self.bounds_local.contains_sphere(p_l, size_local):
            return [self]

    def q(self, selector: str) -> Node:
        nodes = self.q_all(selector)
        return nodes[0] if len(nodes) > 0 else None

    def q_all(self, selector: str) -> NodeList:
        nodes = NodeList()
        for node in self.child_nodes:
            if selector[0] == "#" and node.id and node.id == selector[1:]:
                nodes._nodes.append(node)
                return nodes
            elif selector[0] == "." and selector[1:] in node.class_names:
                nodes._nodes.append(node)
            nodes._nodes += node.q_all(selector)._nodes
        return nodes

    @property
    def prevent_trigger_events_on_raycast(self) -> bool:
        if self._prevent_trigger_events_on_raycast is None:
            return False if self.parent is None else self.parent.prevent_trigger_events_on_raycast

        return self._prevent_trigger_events_on_raycast

    @prevent_trigger_events_on_raycast.setter
    def prevent_trigger_events_on_raycast(self, v: bool):
        self._prevent_trigger_events_on_raycast = v

    def __str__(self):
        id = f'"{self.id}"' if isinstance(self.id, str) else self.id
        return f"{type(self).__name__} [id={id}, class_names=\"{', '.join(self.class_names)}\"]"


class NodeList:
    def __init__(self):
        self._nodes: list[Node] = []

    def __iter__(self):
        return iter(self._nodes)

    def __len__(self):
        return len(self._nodes)

    def __getitem__(self, key):
        return self._nodes[key]

    def __contains__(self, node):
        return node in self._nodes

    def clear(self):
        self._nodes.clear()

    def add_event_listener(self, event_name: str, callback, options={}):
        for node in self._nodes:
            node.add_event_listener(event_name, callback, options)


root = Node()
