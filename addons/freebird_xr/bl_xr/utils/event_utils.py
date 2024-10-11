# SPDX-License-Identifier: GPL-2.0-or-later

import bl_xr
from mathutils import Vector

from bpy.types import XrEventData


def make_class_event_aware(clazz):
    from bl_xr.events.types import EventAware

    def add_event_listener(event_name, callback, options={}):
        if not isinstance(event_name, str):
            raise Exception("Events can only be added/removed from the class, not on individual objects.")
        EventAware.add_event_listener(clazz, event_name, callback, options)

    def remove_event_listener(event_name, callback=None, options={}):
        if not isinstance(event_name, str):
            raise Exception("Events can only be added/removed from the class, not on individual objects.")
        EventAware.remove_event_listener(clazz, event_name, callback, options)

    def dispatch_event(self, event_name: str, event):
        EventAware.dispatch_event(self, event_name, event)

    setattr(clazz, "event_listeners", {})
    setattr(clazz, "add_event_listener", add_event_listener)
    setattr(clazz, "remove_event_listener", remove_event_listener)
    setattr(clazz, "dispatch_event", dispatch_event)


def filter_event_by_buttons(button_names):
    return lambda self, event_name, event: event.button_name in button_names


def filter_event_by_attr(**kwargs):
    def filter_fn(self, event_name, event):
        for attr, val in kwargs.items():
            if getattr(self, attr, None) != val:
                return False
        return True

    return filter_fn


def translate_event_hands(xr_event: XrEventData) -> tuple[str]:
    """
    Returns a pair of strings denoting the hands in the event.

    For e.g.
    * `("main", None)` or `("alt", None)` for a single-hand event.
    * `("main", "alt")` or `("alt", "main")` for a bi-manual event.
    """
    from bl_xr import xr_session

    left_hand = "alt" if bl_xr.main_hand == "right" else "main"
    right_hand = "main" if bl_xr.main_hand == "right" else "alt"

    if hasattr(xr_event, "user_path"):  # introduced in Blender 3.3
        hand, hand_other = xr_event.user_path, xr_event.user_path_other
        hand = hand.replace("/user/hand/left", left_hand).replace("/user/hand/right", right_hand)
        hand_other = hand_other.replace("/user/hand/left", left_hand).replace("/user/hand/right", right_hand)
        hand_other = None if hand_other.strip() == "" else hand_other
        return hand, hand_other

    # guess the hand by checking the controller distances from the event location
    main_loc = xr_session.controller_main_aim_position
    alt_loc = xr_session.controller_alt_aim_position
    event_loc, event_loc_other = Vector(xr_event.controller_location), Vector(xr_event.controller_location_other)

    hand = "main" if (event_loc - main_loc).length < (event_loc - alt_loc).length else "alt"
    if xr_event.bimanual:
        hand_other = "main" if (event_loc_other - main_loc).length < (event_loc_other - alt_loc).length else "alt"
    else:
        hand_other = None

    return hand, hand_other
