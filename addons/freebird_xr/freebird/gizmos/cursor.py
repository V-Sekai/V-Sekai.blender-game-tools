import bl_xr
from bl_xr import root, xr_session
from bl_xr import Node, Sphere
from bl_xr.utils import lerp, clamp

from mathutils import Vector, Quaternion

from .. import tools
from ..settings_manager import settings


class Cursor(Node):
    CURSOR_DEFAULTS_KEYS = {
        "select": ("select.default_cursor_size", "select.default_cursor_color"),
        "erase": ("erase.default_cursor_size", "erase.default_cursor_color"),
        "draw.stroke": ("stroke.pen.default_cursor_size", "select.default_cursor_color"),
        "draw.shape": ("shape.default_cursor_size", "select.default_cursor_color"),
        "draw.hull": ("shape.default_cursor_size", "select.default_cursor_color"),
        "pen": ("stroke.pen.default_cursor_size", "select.default_cursor_color"),
        "pipe": ("stroke.pipe.default_cursor_size", "select.default_cursor_color"),
        "edit_mesh.loop_cut": ("shape.default_cursor_size", "select.default_cursor_color"),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.sphere = Sphere(radius=1)
        self.sphere.scale = settings["gizmo.cursor.default_size"]
        self.intersects = None

        self.style["fixed_scale"] = True
        self.style["opacity"] = 0.5

        self.append_child(self.sphere)

        root.add_event_listener("joystick_x_main_press", self.on_cursor_resize)
        root.add_event_listener("joystick_x_main_end", self.on_cursor_resize_end)

    @property
    def size(self) -> float:
        "Size (in local scale)"
        return self.sphere.scale.x

    @size.setter
    def size(self, s: float):
        self.sphere.scale = s
        if tools.active_tool in ("select", "erase"):
            bl_xr.selection_size = s * self.scale.x

    @property
    def size_world(self) -> float:
        "Size (in world scale)"
        return self.sphere.scale_world.x

    @size_world.setter
    def size_world(self, s: float):
        self.size = s / self.scale_world.x

    def update(self):
        self.position = Vector(xr_session.controller_main_aim_position)
        self.rotation = Quaternion(xr_session.controller_main_aim_rotation)

    def on_cursor_resize(self, event_name, event):
        from freebird import gizmos

        resize_amt = event.value

        if "joystick_for_keyframe" in gizmos.active_gizmos:  # HACK
            return

        speed = settings["gizmo.cursor.resize_speed"]
        min_size, max_size = settings["gizmo.cursor.min_size"], settings["gizmo.cursor.max_size"]
        speed_thin_mul = settings["gizmo.cursor.resize_speed_small_multiplier"]
        speed_thick_mul = settings["gizmo.cursor.resize_speed_large_multiplier"]

        curr_size_local = self.size

        size_t = (curr_size_local - min_size) / (max_size - min_size)
        size_speedup = lerp(speed_thin_mul, speed_thick_mul, size_t)
        d = resize_amt * speed * size_speedup

        curr_size_local += d
        curr_size_local = clamp(curr_size_local, min_size, max_size)

        self.size = curr_size_local

        # save size
        if tools.active_tool in self.CURSOR_DEFAULTS_KEYS:
            size_key, _ = self.CURSOR_DEFAULTS_KEYS[tools.active_tool]
            settings[size_key] = self.size

    def on_cursor_resize_end(self, event_name, event):
        self._last_resize_frame_time = None

    def set_default_cursor(self, tool_name):
        if tool_name not in self.CURSOR_DEFAULTS_KEYS:
            return

        size_key, color_key = self.CURSOR_DEFAULTS_KEYS[tool_name]
        self.size = settings[size_key]
        self.sphere.style["color"] = settings[color_key]


cursor = Cursor(id="cursor_main")


def enable_gizmo():
    root.append_child(cursor)


def disable_gizmo():
    root.remove_child(cursor)
