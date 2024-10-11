# SPDX-License-Identifier: GPL-2.0-or-later

from ..types import ControllerEvent, UIEvent

from bl_xr import intersections


def make_intersection_transition_events(intersection_type, base_event: ControllerEvent) -> list[UIEvent]:
    """
    Creates `enter` and `leave` events for UI and bpy objects.

    Makes `pointer_main_enter` or `pointer_main_leave` events for `"raycast"` intersection_type, and
    `controller_main_enter` or `controller_main_leave` events for `"bounds"` intersection_type.

    Only accepts an event created by `make_xr_controller_move_event()`.
    """
    events = []

    if not base_event or base_event.hand != "main":
        return events

    device = "controller" if intersection_type == "bounds" else "pointer"
    curr, prev = intersections.curr[intersection_type].keys(), intersections.prev[intersection_type].keys()
    curr, prev = set(curr), set(prev)

    entering = curr.difference(prev)
    leaving = prev.difference(curr)

    if leaving:
        events.append((f"{device}_main_leave", None))
    if entering:
        point = list(intersections.curr[intersection_type].values())[0] if intersection_type == "raycast" else None
        events.append((f"{device}_main_enter", point))

    events = list(map(lambda e: UIEvent(type=e[0], hand=base_event.hand, position=e[1]), events))

    return events
