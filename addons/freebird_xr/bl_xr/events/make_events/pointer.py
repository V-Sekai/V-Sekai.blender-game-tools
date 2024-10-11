# SPDX-License-Identifier: GPL-2.0-or-later

from ..types import ControllerEvent, UIEvent

from bl_xr import intersections

from mathutils import Vector


def make_pointer_press_event(events: list[ControllerEvent]) -> UIEvent:
    """
    Creates one of `pointer_main_press_start`, `pointer_main_press` and `pointer_main_press_end` events from
    the trigger_main state.

    Only accepts the list of events created by `make_xr_action_events()`.
    """

    if events is None or not isinstance(events, list):
        return

    trigger_main_event = next((e for e in events if e.type.startswith("trigger_main_")), None)
    if not trigger_main_event:
        return

    if not intersections.curr["raycast"]:
        return

    event = UIEvent()
    event.type = f"pointer_main_press"
    event.position = list(intersections.curr["raycast"].values())[0]
    event.hand = trigger_main_event.hand

    if "_start" in trigger_main_event.type:
        event.type += "_start"
    elif "_end" in trigger_main_event.type:
        event.type += "_end"

    return event


def make_pointer_move_event(hand: str, position: Vector):
    if hand != "main" or not intersections.curr["raycast"]:
        return None

    event = UIEvent()
    event.type = "pointer_main_move"
    event.position = list(intersections.curr["raycast"].values())[0]
    event.hand = hand

    return event
