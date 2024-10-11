# SPDX-License-Identifier: GPL-2.0-or-later


from .. import intersections
from .make_events import (
    make_xr_action_events,
    make_xr_action_base_event,
    make_intersection_transition_events,
    make_high_level_event,
    make_pointer_press_event,
    make_xr_controller_move_event,
    make_pointer_move_event,
    make_mouse_move_event,
)
from .bind_and_dispatch import bind_and_dispatch, bind_objects, dispatch_events

from bpy.types import Event as Bl_Event


prevent_trigger_events_on_raycast = False
prevent_pointer_events_on_raycast = False


def on_event(event_type, event_data):
    if event_type == "XR_ACTION":
        on_xr_action(event_data)
    elif event_type == "XR_CONTROLLER_MOVE":
        on_xr_controller_move(event_data)
    elif event_type == "MOUSEMOVE":
        on_mouse_move(event_data)


def on_xr_action(bl_event: Bl_Event):
    global prevent_trigger_events_on_raycast, prevent_pointer_events_on_raycast

    base_event = make_xr_action_base_event(bl_event)
    if base_event is None:
        return

    events = make_xr_action_events(base_event)
    for e in events:
        if e.type == "trigger_main_start":
            prevent_trigger_events_on_raycast = any(
                node.prevent_trigger_events_on_raycast for node in intersections.curr["raycast"].keys()
            )
            prevent_pointer_events_on_raycast = len(intersections.curr["raycast"]) == 0

        if e.type.endswith("_start") and e.hand == "main":  # don't miss intersections when a 'press' starts
            intersections.refresh_intersections(e)
            break

    if not prevent_trigger_events_on_raycast:
        bind_and_dispatch(events)

    pointer_press_event = None
    if base_event.button_name == "trigger" and not prevent_pointer_events_on_raycast:
        pointer_press_event = make_pointer_press_event(events)
        bind_and_dispatch(pointer_press_event)

    if base_event.button_name in ("trigger", "squeeze") and not prevent_trigger_events_on_raycast:
        high_level_event = make_high_level_event(events)
        bind_and_dispatch(high_level_event)

    if any(e.type == "trigger_main_end" for e in events):
        prevent_trigger_events_on_raycast = False
        prevent_pointer_events_on_raycast = False


def on_xr_controller_move(event_data):
    hand_bl, position, rotation_bl, _ = event_data
    base_event = make_xr_controller_move_event(hand_bl, position, rotation_bl)

    # update intersection cache
    intersections.refresh_intersections(base_event)

    # bounds
    bounds_transition_events = make_intersection_transition_events("bounds", base_event)
    bind_and_dispatch(bounds_transition_events)

    # raycast
    raycast_transition_events = []
    if not prevent_pointer_events_on_raycast:
        raycast_transition_events = make_intersection_transition_events("raycast", base_event)
        bind_and_dispatch(raycast_transition_events)

    if len(raycast_transition_events) == 0 and not prevent_pointer_events_on_raycast:
        event = make_pointer_move_event(base_event.hand, base_event.position)
        bind_and_dispatch(event)

    # controller move event
    bind_objects(base_event)

    if len(bounds_transition_events) > 0 and base_event.targets:
        # remove targets with bounds_transition events
        for e in bounds_transition_events:
            for o in e.targets:
                if o in base_event.targets:
                    base_event.targets.remove(o)

        if not base_event.targets:
            base_event.targets = None

    dispatch_events(base_event)


def on_mouse_move(bl_event: Bl_Event):
    event = make_mouse_move_event(bl_event)
    bind_and_dispatch(event)
