import bl_xr
from bl_xr import xr_session, Node, Sphere, Pyramid, Cube, Cone, Line
from bl_xr.utils import sign, get_mesh_mode, apply_haptic_feedback, filter_event_by_buttons
from bl_xr.consts import VEC_FORWARD
from mathutils import Vector, Quaternion
from math import radians

from ...settings_manager import settings
from ...utils import log


class PullPushHandle(Node):
    "A handle with a knob that can be pulled or pushed (and dispatches handle drag events to itself)"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        length = kwargs.get("length", settings["gizmo.edit_handle.length"])
        knob_radius = kwargs.get("knob_radius", settings["gizmo.edit_handle.knob_radius"])

        self._color = (1, 0.77, 0.25, 1)
        self.highlight_color = (1, 0.92, 0.61, 1)

        knob_type = kwargs.get("knob_type", "SPHERE")
        if knob_type == "SPHERE":
            self.knob = Sphere(radius=knob_radius)
        elif knob_type == "PYRAMID":
            self.knob = Pyramid(size=knob_radius)
            self.knob.rotation = Quaternion((1, 0, 0), radians(-90))
        elif knob_type == "CONE":
            self.knob = Cone(radius=knob_radius * 0.5, height=knob_radius * 1.5)
            self.knob.rotation = Quaternion((1, 0, 0), radians(-90))
        elif knob_type == "CUBE":
            self.knob = Cube(size=knob_radius)

        self.knob.position = Vector((0, length, 0))
        self.knob.style.update({"color": self._color, "opacity": 0.8})

        self.rod = Line(length=length, style={"color": self._color})
        self.style["fixed_scale"] = True
        self.knob.style["depth_test"] = False
        self.rod.style["depth_test"] = False
        self.haptic_feedback = kwargs.get("haptic_feedback", True)

        self.apply_total_offset = kwargs.get("apply_total_offset", True)

        self.contents = Node(child_nodes=[self.knob, self.rod])
        self.intersects = "bounds"

        self._is_pressing = False
        self._is_highlighted = False
        self._is_dragging = False
        self.direction = None
        self.total_drag_amt = 0

        self.append_child(self.contents)

        self.knob.add_event_listener("drag_start", self.on_knob_drag)
        self.knob.add_event_listener("drag", self.on_knob_drag)
        self.knob.add_event_listener("drag_end", self.on_knob_drag_end)

        # absorb trigger events, we don't want them to go to the root
        self.knob.add_event_listener("trigger_main_start", self.absorb_trigger_press_event)
        self.knob.add_event_listener("trigger_main_press", self.absorb_trigger_press_event)
        self.knob.add_event_listener("trigger_main_end", self.absorb_trigger_press_event)
        self.knob.add_event_listener("squeeze_main_start", self.absorb_trigger_press_event)
        self.knob.add_event_listener("squeeze_main_press", self.absorb_trigger_press_event)
        self.knob.add_event_listener("squeeze_main_end", self.absorb_trigger_press_event)

    def highlight(self, state: bool, haptic=True):
        self._is_highlighted = state
        self.knob.style["color"] = self.highlight_color if state else self._color
        self.rod.style["color"] = self.highlight_color if state else self._color

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

    def on_knob_drag(self, event_name, event):
        expected_button_name = "trigger_main" if settings["transform.grab_button"] == "trigger" else "squeeze_main"
        if event.button_name != expected_button_name:
            return

        # if self.direction is None:
        #     log.error(
        #         "Can't move the edit handle, as it no longer is anchored to anything. Origin and direction are None. Are any elements selected?"
        #     )
        #     return

        event.stop_propagation = True
        event.stop_propagation_immediate = True

        d = event.pose_delta.position
        direction = self.rotation_world @ VEC_FORWARD
        along = d.project(direction)
        drag_amt = along.length * sign(d.dot(direction))
        self.total_drag_amt += drag_amt

        if abs(drag_amt) > 0:
            self._is_dragging = True

            if get_mesh_mode() in self.mesh_modes_allowed:
                amt = self.total_drag_amt if self.apply_total_offset else drag_amt

                if event_name == "drag_start":
                    self.dispatch_event("handle_drag_start", amt)

                self.dispatch_event("handle_drag", amt)

            if self.apply_total_offset:
                self.knob.position_world += along
                self.rod.length = self.knob.position.y

            # it isn't obvious why knob's position_world is set. atleast not to me. but there's a reason for it.
            # knob's position_world is set because the expectation is that the knob moves along with
            # the controller in the "user frame of reference". event.pose_delta is in the user frame of reference,
            # and knob is at fixed_scale. the explanation may not make much sense, but it's the right thing to do.

    def on_knob_drag_end(self, event_name, event):
        expected_button_name = "trigger_main" if settings["transform.grab_button"] == "trigger" else "squeeze_main"
        if event.button_name != expected_button_name:
            return

        event.stop_propagation = True

        self.rod.length = settings["gizmo.edit_handle.length"]
        self.knob.position = Vector((0, self.rod.length, 0))
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
        should_highlight = self.knob.intersect(
            controller_p, bl_xr.selection_shape, bl_xr.selection_size * xr_session.viewer_scale
        )
        if should_highlight:
            if not self._is_highlighted:
                self.highlight(True)
        elif self._is_highlighted:
            self.highlight(False)
