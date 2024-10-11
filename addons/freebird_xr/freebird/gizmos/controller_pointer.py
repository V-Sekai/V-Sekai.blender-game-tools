from bl_xr import root, xr_session, intersections
from bl_xr import Line, Node


def on_controller_update(self):
    self.position = xr_session.controller_main_aim_position
    self.rotation = xr_session.controller_main_aim_rotation

    controller_pointer_line.style["visible"] = len(intersections.curr["raycast"]) > 0


controller_pointer_line = Line(length=1)
controller_pointer = Node(
    id="controller_main_pointer",
    child_nodes=[controller_pointer_line],
    intersects=None,
    style={"fixed_scale": True},
)
controller_pointer.update = on_controller_update.__get__(controller_pointer)


def enable_gizmo():
    root.append_child(controller_pointer)


def disable_gizmo():
    root.remove_child(controller_pointer)
