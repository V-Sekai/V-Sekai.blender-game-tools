import bpy

from bl_xr import root, xr_session
from bl_xr import Node, Image, Sphere, Mesh, Bounds
from bl_xr.consts import BLACK, VEC_FORWARD, VEC_RIGHT


from freebird import settings
from freebird.utils import get_freebird_collection

from math import radians
from mathutils import Vector, Quaternion

actual_cursor_obj = None


class MirrorGizmo(Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.planes = MirrorPlanes()
        self.cursors = MirrorCursors()

        self.append_child(self.planes)
        self.append_child(self.cursors)


class Square(Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if "direction" in kwargs:
            self.direction = kwargs["direction"]

        verts = [
            # outer
            [(0, 0, 0), (0, 1, 0)],
            [(0, 1, 0), (1, 1, 0)],
            [(1, 1, 0), (1, 0, 0)],
            [(1, 0, 0), (0, 0, 0)],
            # inner
            [(0.02, 0.02, 0), (0.02, 0.98, 0)],
            [(0.02, 0.98, 0), (0.98, 0.98, 0)],
            [(0.98, 0.98, 0), (0.98, 0, 0)],
            [(0.98, 0.02, 0), (0.02, 0.02, 0)],
        ]

        self.mesh = Mesh(vertices=[v for line in verts for v in line])

    @property
    def bounds_local(self) -> Bounds:
        return Bounds(Vector(), Vector((1, 1, 0)))


class MirrorPlanes(Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.planes = {}
        for axis in ("x", "y", "z"):
            self.planes[axis] = Square(intersects=None, style={"color": BLACK})
            self.append_child(self.planes[axis])

        self.planes["x"].position = Vector((0, -0.5, -0.5))
        self.planes["y"].position = Vector((-0.5, 0, -0.5))
        self.planes["z"].position = Vector((-0.5, -0.5, 0))

        self.planes["x"].rotation = Quaternion(VEC_FORWARD, radians(-90))
        self.planes["y"].rotation = Quaternion(VEC_RIGHT, radians(90))
        self.planes["z"].rotation = Quaternion()

    def update(self):
        for axis, plane in self.planes.items():
            plane.style["visible"] = settings.get(f"gizmo.mirror.axis_{axis}")


class MirrorCursors(Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cursors = {}
        for x_axis in ("+x", "-x"):
            for y_axis in ("+y", "-y"):
                for z_axis in ("+z", "-z"):
                    key = (x_axis, y_axis, z_axis)
                    if key == ("+x", "+y", "+z"):  # skip the original cursor
                        continue

                    cursor = Sphere(intersects=None, style={"color": BLACK, "visible": False, "depth_test": None})

                    self.cursors[key] = cursor
                    self.append_child(cursor)

    def update(self):
        axes_needed = {}
        for axis in ("x", "y", "z"):
            axes_needed[axis] = [f"+{axis}", f"-{axis}"] if settings[f"gizmo.mirror.axis_{axis}"] else [f"+{axis}"]

        cursors_needed = []
        for x_key in axes_needed["x"]:
            for y_key in axes_needed["y"]:
                for z_key in axes_needed["z"]:
                    cursors_needed.append((x_key, y_key, z_key))

        actual_pos_local = self.world_to_local_point(xr_session.controller_main_aim_position)
        actual_cursor_size = actual_cursor_obj.size

        for key, cursor in self.cursors.items():
            cursor.style["visible"] = key in cursors_needed

            if cursor.style["visible"]:
                cursor_pos_local = Vector(actual_pos_local)
                for sign, axis in key:
                    factor = int(f"{sign}1")
                    new_val = factor * getattr(cursor_pos_local, axis)
                    setattr(cursor_pos_local, axis, new_val)

                cursor.position = cursor_pos_local
                cursor.style["scale"] = actual_cursor_size


mirror_origin = MirrorGizmo(id="mirror_plane", style={"fixed_scale": True})


def make_mirror():
    coll = get_freebird_collection()
    if "freebird_mirror_global" not in coll.objects:
        mirror_mesh_data = bpy.data.meshes.new("freebird_mirror_mesh_data")
        mirror_obj_global = bpy.data.objects.new("freebird_mirror_global", mirror_mesh_data)
        coll.objects.link(mirror_obj_global)


def enable_gizmo():
    global actual_cursor_obj

    root.append_child(mirror_origin)

    actual_cursor_obj = root.q("#cursor_main")

    make_mirror()


def disable_gizmo():
    root.remove_child(mirror_origin)
