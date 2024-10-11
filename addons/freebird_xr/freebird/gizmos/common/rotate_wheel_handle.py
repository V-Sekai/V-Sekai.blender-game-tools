import bl_xr
from bl_xr import xr_session, Node, Sphere, Ring, Line
from bl_xr.consts import VEC_UP
from bl_xr.utils import sign, get_mesh_mode, apply_haptic_feedback, vec_signed_angle
from mathutils import Vector
from math import atan2

from ...settings_manager import settings
from ...utils import log


class RotateWheelHandle(Node):
    "A circular handle that can be rotated (and dispatches handle drag events to itself)"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        radius = kwargs.get("radius", settings["gizmo.edit_handle.length"])
        thickness = kwargs.get("thickness", settings["gizmo.transform_handles.ring_thickness"])

        self._color = (1, 0.77, 0.25, 1)
        self.highlight_color = (1, 0.92, 0.61, 1)

        self.ring = Ring(
            radius=radius,
            thickness=thickness * 0.5,
            width=thickness,
            segments=16,
            style={"color": self._color, "opacity": 0.8},
        )
        self.style["fixed_scale"] = True
        self.ring.style["depth_test"] = False
        self.haptic_feedback = kwargs.get("haptic_feedback", True)

        self.contents = Node(child_nodes=[self.ring])
        self.intersects = "bounds"

        self._is_pressing = False
        self._is_highlighted = False
        self._is_dragging = False
        self.total_drag_amt = 0

        self.append_child(self.contents)

        self.ring.add_event_listener("drag_start", self.on_ring_drag)
        self.ring.add_event_listener("drag", self.on_ring_drag)
        self.ring.add_event_listener("drag_end", self.on_ring_drag_end)

        # absorb trigger events, we don't want them to go to the root
        self.ring.add_event_listener("trigger_main_start", self.absorb_trigger_press_event)
        self.ring.add_event_listener("trigger_main_press", self.absorb_trigger_press_event)
        self.ring.add_event_listener("trigger_main_end", self.absorb_trigger_press_event)
        self.ring.add_event_listener("squeeze_main_start", self.absorb_trigger_press_event)
        self.ring.add_event_listener("squeeze_main_press", self.absorb_trigger_press_event)
        self.ring.add_event_listener("squeeze_main_end", self.absorb_trigger_press_event)

    def highlight(self, state: bool, haptic=True):
        self._is_highlighted = state
        self.ring.style["color"] = self.highlight_color if state else self._color

        if state and haptic and self.haptic_feedback:
            apply_haptic_feedback()

    @property
    def is_highlighted(self):
        return self._is_highlighted

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, c):
        self._color = c
        self.highlight(self._is_highlighted, haptic=False)

    def on_ring_drag(self, event_name, event):
        expected_button_name = "trigger_main" if settings["transform.grab_button"] == "trigger" else "squeeze_main"
        if event.button_name != expected_button_name:
            return

        event.stop_propagation = True
        event.stop_propagation_immediate = True

        d = event.pose_delta.position
        curr_pt = xr_session.controller_main_aim_position
        prev_pt = curr_pt - d

        a = self.ring.world_to_local_point(prev_pt)
        b = self.ring.world_to_local_point(curr_pt)

        a.z = b.z = 0

        drag_amt = vec_signed_angle(b, a, VEC_UP)

        self.total_drag_amt += drag_amt

        if abs(drag_amt) > 0:
            self._is_dragging = True

            if event_name == "drag_start":
                self.dispatch_event("handle_drag_start", drag_amt)

            self.dispatch_event("handle_drag", drag_amt)

    def on_ring_drag_end(self, event_name, event):
        expected_button_name = "trigger_main" if settings["transform.grab_button"] == "trigger" else "squeeze_main"
        if event.button_name != expected_button_name:
            return

        event.stop_propagation = True

        self.total_drag_amt = 0
        self._is_dragging = False
        self._is_pressing = False

        self.dispatch_event("handle_drag_end", event)

    def absorb_trigger_press_event(self, event_name, event):
        expected_button_name = settings["transform.grab_button"]

        if event_name == f"{expected_button_name}_main_start" and not self._is_pressing:
            self._is_pressing = True

        if self._is_pressing:
            event.stop_propagation = True

    def update(self):
        controller_p = xr_session.controller_main_aim_position
        should_highlight = self.ring.intersect(
            controller_p, bl_xr.selection_shape, bl_xr.selection_size * xr_session.viewer_scale
        )
        if should_highlight:
            if not self._is_highlighted:
                self.highlight(True)
        elif self._is_highlighted:
            self.highlight(False)
