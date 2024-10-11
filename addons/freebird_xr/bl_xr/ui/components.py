# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from bl_xr.consts import VEC_ZERO, VEC_ONE, VEC_FORWARD, BLACK, WHITE

import bpy
from mathutils import Vector
import blf
import os
import math
import gpu
from os import path

from ..dom import Node

from bl_xr import Bounds
from bl_xr.utils import (
    make_sphere,
    make_ring_mesh,
    make_pyramid,
    make_cube,
    make_cone,
    quaternion_from_vector,
    apply_haptic_feedback,
    log,
)


class Mesh:
    def __init__(self, vertices=[], faces=[]):
        self.vertices: list = vertices
        self.faces: list = faces

    def new_sphere(radius: float, segments: int = 8, rings: int = 12) -> Mesh:
        verts, faces = make_sphere(radius, segments, rings)
        return Mesh(verts, faces)

    def new_ring(radius: float = 1, thickness: float = 0.1, width: float = 0.1, segments: int = 12) -> Mesh:
        t_half = thickness * 0.5
        verts, faces = make_ring_mesh(radius - t_half, radius + t_half, width, segments)
        return Mesh(verts, faces)

    def new_pyramid(size: float = 1) -> Mesh:
        verts, faces = make_pyramid(size)
        return Mesh(verts, faces)

    def new_cube(size: float = 1) -> Mesh:
        verts, faces = make_cube(size)
        return Mesh(verts, faces)

    def new_cone(radius: float = 1, height: float = 1, segments: int = 12) -> Mesh:
        verts, faces = make_cone(radius, height, segments)
        return Mesh(verts, faces)


class Sphere(Node):
    def __init__(self, radius: float = 1, **kwargs):
        super().__init__(**kwargs)

        self.radius = radius

    @property
    def radius(self) -> float:
        return self._radius

    @radius.setter
    def radius(self, r: float):
        self._radius = r
        self.mesh = Mesh.new_sphere(r)

    @property
    def bounds_local(self) -> Bounds:
        r = self._radius
        return Bounds(-r * VEC_ONE, r * VEC_ONE)

    def intersect(self: Node, center: Vector, shape: str, size: float) -> bool:
        size_local = self.world_to_local_scale(VEC_ONE * size).x
        p_local = self.world_to_local_point(center)
        r = self.radius
        d = p_local.length

        if d <= size_local + r:
            return [self]


class Ring(Node):
    def __init__(self, radius: float = 1, thickness: float = 0.1, width: float = 0.1, segments: int = 12, **kwargs):
        super().__init__(**kwargs)

        self.thickness = thickness
        self.width = width
        self.segments = segments
        self.radius = radius

    @property
    def radius(self) -> float:
        return self._radius

    @radius.setter
    def radius(self, r: float):
        self._radius = r
        self.mesh = Mesh.new_ring(r, self.thickness, self.width, self.segments)

    @property
    def bounds_local(self) -> Bounds:
        r = self._radius
        half_t = self.thickness * 0.5
        return Bounds(Vector((-r, -r, -half_t)), Vector((r, r, half_t)))

    def intersect(self: Node, center: Vector, shape: str, size: float) -> bool:
        size_local = self.world_to_local_scale(VEC_ONE * size).x

        half_w = self.width * 0.5
        half_t = self.thickness * 0.5

        p_local = self.world_to_local_point(center)
        if p_local.z > half_w + size_local or p_local.z < -(half_w + size_local):
            return

        r = self.radius
        r_inner = r - half_t
        r_outer = r + half_t
        r_inner_effective = r_inner - size_local
        r_outer_effective = r_outer + size_local

        r_inner_effective = r_inner_effective if r_inner_effective > 0 else 0

        p_local.z = 0
        d = p_local.length

        if d <= r_outer_effective and d >= r_inner_effective:
            return [self]


class Pyramid(Node):
    def __init__(self, size: float = 1, **kwargs):
        super().__init__(**kwargs)

        self.size = size

    @property
    def size(self) -> float:
        return self._size

    @size.setter
    def size(self, s: float):
        self._size = s
        self.mesh = Mesh.new_pyramid(s)

    @property
    def bounds_local(self) -> Bounds:
        half_s = self._size * 0.5
        return Bounds(-half_s * VEC_ONE, half_s * VEC_ONE)

    # TODO - Implement an `intersect()` function to work with a Pyramid's shape
    # rather than using the bounding box for intersections


class Cube(Node):
    def __init__(self, size: float = 1, **kwargs):
        super().__init__(**kwargs)

        self.size = size

    @property
    def size(self) -> float:
        return self._size

    @size.setter
    def size(self, s: float):
        self._size = s
        self.mesh = Mesh.new_cube(s)

    @property
    def bounds_local(self) -> Bounds:
        half_s = self._size * 0.5
        return Bounds(-half_s * VEC_ONE, half_s * VEC_ONE)


class Cone(Node):
    def __init__(self, radius: float = 1, height: float = 1, **kwargs):
        super().__init__(**kwargs)

        self.height = height
        self.radius = radius

    @property
    def radius(self) -> float:
        return self._radius

    @radius.setter
    def radius(self, r: float):
        self._radius = r
        self.mesh = Mesh.new_cone(r, self.height)

    @property
    def bounds_local(self) -> Bounds:
        half_s = self._radius * 0.5
        extent = Vector((half_s, half_s, self.height / 2))
        return Bounds(-extent, extent)

    # TODO - Implement an `intersect()` function to work with a Cone's shape
    # rather than using the bounding box for intersections


class Image(Node):
    base_dir: str = None

    def __init__(self, src: str = None, width: float = None, height: float = None, **kwargs):
        super().__init__(**kwargs)

        self.width = width if src or width is not None else 0
        self.height = height if src or width is not None else 0
        self.src = src

    @property
    def src(self):
        return self._src

    @src.setter
    def src(self, img_src):
        "Warning: Don't set `src` inside an application timer. It'll cause Blender to crash!"

        self._src = img_src

        if self._src:
            img_path = path.join(Image.base_dir, self._src) if Image.base_dir else self._src
            img_path = path.abspath(img_path)

            image_name = path.basename(img_path)
            log.debug(f"Loading image {image_name} from {img_path}")

            if image_name not in bpy.data.images:
                bpy.data.images.load(img_path)

            image = bpy.data.images[image_name]
            gpu_texture = gpu.texture.from_image(image) if not bpy.app.background else None

            image_width, image_height = image.size
            if self.height is None and self.width is not None:
                self.height = self.width * image_height / image_width
            elif self.width is None and self.height is not None:
                self.width = self.height * image_width / image_height
            elif self.height is None and self.width is None:
                self.width = self.height = 1

            bpy.data.images.remove(image)
            self._texture = gpu_texture

    @property
    def bounds_local(self) -> Bounds:
        return Bounds(VEC_ZERO, Vector((self.width, self.height, 0)))


class FontDB:
    _CACHE = {}

    def get_font(font_face):
        if font_face not in FontDB._CACHE:
            font_path = bpy.path.abspath(font_face)
            FontDB._CACHE[font_face] = blf.load(font_path) if os.path.exists(font_path) else 0

        return FontDB._CACHE[font_face]


class Text(Node):
    def __init__(
        self,
        text: str,
        font_size: int = None,
        font_face: str = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.text = text
        if font_size:
            self.style["font_size"] = font_size
        if font_face:
            self.style["font_face"] = font_face

        self.scale = 0.00625 * VEC_ONE

    @property
    def bounds_local(self) -> Bounds:
        font_id = FontDB.get_font(self.font_face)

        blf.position(font_id, 0, 0, 0)
        if bpy.app.version < (3, 4, 0):
            blf.size(font_id, self.font_size, 72)
        else:
            blf.size(font_id, self.font_size)

        width, height = blf.dimensions(font_id, self.text)
        return Bounds(VEC_ZERO, Vector((width, height, 0)))

    @property
    def font_face(self) -> str:
        return self.get_computed_style("font_face", "//Zeyada.ttf")

    @property
    def font_size(self) -> str:
        return self.get_computed_style("font_size", 50)

    def draw(self):
        font_id = FontDB.get_font(self.font_face)
        color = self.get_computed_style("color", BLACK)

        blf.position(font_id, 0, 0, 0)

        if bpy.app.version < (3, 4, 0):
            blf.size(font_id, self.font_size, 72)
        else:
            blf.size(font_id, self.font_size)

        blf.color(font_id, *color)
        blf.draw(font_id, self.text)


class Line(Node):
    def __init__(self, length: float = 1, **kwargs):
        super().__init__(**kwargs)

        self.length = length

        if "direction" in kwargs:
            self.direction = kwargs["direction"]

        self.mesh = Mesh(vertices=[(0, 0, 0), (0, 1, 0)])

    @property
    def length(self) -> float:
        return self.scale.y

    @length.setter
    def length(self, value: float):
        self.scale = Vector((1, value, 1))

    @property
    def direction(self) -> Vector:
        return self.rotation @ VEC_FORWARD

    @direction.setter
    def direction(self, value: Vector):
        self.rotation = quaternion_from_vector(value)

    @property
    def bounds_local(self) -> Bounds:
        return Bounds(VEC_ZERO, Vector((0, self.length, 0)))


class Grid2D(Node):
    def __init__(
        self,
        num_rows: int = None,
        num_cols: int = None,
        cell_width: float = 0.25,
        cell_height: float = 0.25,
        z_offset: float = 0,  # hack
        **kwargs,
    ):
        self._is_ready = False

        super().__init__(**kwargs)

        if num_rows is None and num_cols is None:
            raise Exception("Grid2D needs atleast one of num_rows or num_cols to be set!")

        self.num_rows = num_rows
        self.num_cols = num_cols
        self.cell_width = cell_width
        self.cell_height = cell_height
        self.z_offset = z_offset
        self._is_ready = True

        self._update_layout()

    def _update_layout(self):
        if not self._is_ready:
            return

        num_cols = self.num_cols if self.num_cols else math.ceil(len(self.child_nodes) / self.num_rows)

        for i, node in enumerate(self.child_nodes):
            row_idx, col_idx = i // num_cols, i % num_cols
            node.position = Vector((col_idx * self.cell_width, row_idx * self.cell_height, self.z_offset))

        self._num_layout_children = len(self.child_nodes)

    def append_child(self, child: Node):
        super().append_child(child)

        self._update_layout()

    def append_children(self, child_nodes: list[Node]):
        super().append_children(child_nodes)

        self._update_layout()

    def remove_child(self, child: Node):
        super().remove_child(child)

        self._update_layout()


class Button(Node):
    def __init__(self, icon: str, tooltip: str = "", **kwargs):
        super().__init__(**kwargs)

        self.icon = Image(src=icon, intersects=None)
        self.tooltip = Text(
            text=tooltip,
            position=Vector((0, 0, 0.01)),
            style={
                "color": WHITE,
                "font_size": 35,
            },
            intersects=None,
        )

        tooltip_width = self.tooltip.bounds_local.size.x * self.tooltip.scale.x

        if tooltip_width > 1:
            font_scale = 1 / tooltip_width
            self.tooltip.style["font_size"] *= font_scale * 0.95
            tooltip_width = 0.95
            self.tooltip.position.y = (1 - 0.95) / 2

        # center align
        self.tooltip.position.x = 0.5 - tooltip_width / 2

        self.tooltip_bg = Image(
            width=1,
            height=0.19,
            style={"background": BLACK, "visible": False, "opacity": 0.95},
            position=Vector((0, 0, 0.001)),
        )

        self.prevent_trigger_events_on_raycast = True
        self.haptic_feedback_hand = kwargs.get("haptic_feedback_hand", "main")
        self.highlight_checker = kwargs.get("highlight_checker", None)
        self.tooltip_only_on_highlight = kwargs.get("tooltip_only_on_highlight", True)

        self._stop_highlight_checker = False
        self._is_highlighted = False

        self.tooltip.style["visible"] = not self.tooltip_only_on_highlight

        self.add_event_listener("pointer_main_enter", self.on_pointer_enter)
        self.add_event_listener("pointer_main_leave", self.on_pointer_leave)

        self.append_child(self.icon)
        self.append_child(self.tooltip_bg)
        self.append_child(self.tooltip)

    def on_pointer_enter(self, event_name, event):
        self._stop_highlight_checker = True
        self.highlight(True)

    def on_pointer_leave(self, event_name, event):
        self._stop_highlight_checker = False
        self.highlight(False)

    def highlight(self, state: bool):
        if self._is_highlighted == state:
            return

        self._is_highlighted = state

        if self.tooltip_only_on_highlight:
            self.tooltip.style["visible"] = state
            self.tooltip_bg.style["visible"] = state

        if state:
            self.icon.style["background"] = (0.064, 0.155, 0.662, 1.0)
            self.icon.style["border"] = (0.015 * self.icon.width, (0.0, 0.0, 0.1, 1.0))
            self.icon.style["border_radius"] = 0.1 * self.icon.width

            if self.haptic_feedback_hand:
                apply_haptic_feedback(hand=self.haptic_feedback_hand)
        elif "background" in self.icon.style:
            del self.icon.style["background"]
            del self.icon.style["border"]
            del self.icon.style["border_radius"]

    @property
    def is_highlighted(self):
        return self._is_highlighted

    def update(self):
        if self.highlight_checker is None or not callable(self.highlight_checker) or self._stop_highlight_checker:
            return

        should_highlight = self.highlight_checker()
        self.highlight(should_highlight)
