import bpy

from bl_xr import root, xr_session
from bl_xr import Node, Sphere
from bl_xr.consts import VEC_ONE, BLACK

from mathutils import Vector, Quaternion


class ProportionalEditSphere(Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.sphere = Sphere(style={"opacity": 0.2, "color": BLACK, "depth_test": None}, intersects=None)

        self.append_child(self.sphere)

    def update(self):
        ob = bpy.context.view_layer.objects.active
        if not ob:
            return

        tool_settings = bpy.context.scene.tool_settings

        self.sphere.style["visible"] = ob.mode == "EDIT" and ob.type == "MESH" and tool_settings.use_proportional_edit

        if tool_settings.use_proportional_edit:
            p_size = "proportional_distance" if hasattr(tool_settings, "proportional_distance") else "proportional_size"
            self.sphere.scale = VEC_ONE * getattr(tool_settings, p_size)

            self.position = Vector(xr_session.controller_main_aim_position)
            self.rotation = Quaternion(xr_session.controller_main_aim_rotation)


proportional_edit_sphere = ProportionalEditSphere(id="proportional_edit_sphere", intersects=None)


def enable_gizmo():
    root.append_child(proportional_edit_sphere)


def disable_gizmo():
    root.remove_child(proportional_edit_sphere)
