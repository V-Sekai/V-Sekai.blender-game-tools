# SPDX-License-Identifier: GPL-2.0-or-later

from ..types import ControllerEvent

from bpy.types import Event as Bl_Event
from mathutils import Vector, Quaternion

from bl_input.bindings import THRESHOLD
import bl_xr
from bl_xr import ControllerEvent, TwoHandedControllerEvent
from bl_xr.utils import translate_event_hands, to_blender_axis_system

input_state = {}


def make_xr_action_base_event(bl_event: Bl_Event) -> ControllerEvent:
    """
    Creates a `ControllerEvent` after performing the following conversions:
    1. Converts the hand from right/left to main/alt (depending on user config).
    2. Pitches the rotation by 90 degrees, to follow Blender's axis style (instead of OpenXR's style).
    3. The XR action name will be copied to `event.type` and `event.button_name`, after removing the hand name in it (if any).

    The PRESS/RELEASE state will be appended to `event.type` (in lower case). E.g. `trigger_press`.

    The `position` and `value` will be copied from the original event without modification.

    A `TwoHandedControllerEvent` will be created for bimanual events.
    """

    q = Quaternion(bl_event.xr.controller_rotation)
    if q.x == 0 and q.y == 0 and q.z == 0 and q.w == 0:
        return

    action = bl_event.xr.action.replace("_lefthand", "").replace("_righthand", "")
    bimanual = bl_event.xr.bimanual if action in ("trigger", "squeeze") else False

    event = TwoHandedControllerEvent() if bimanual else ControllerEvent()
    event.type = f"{action}_{bl_event.value.lower()}"
    event.button_name = action
    event.position = Vector(bl_event.xr.controller_location)
    event.rotation = to_blender_axis_system(bl_event.xr.controller_rotation)
    event.value = bl_event.xr.state[0]
    event.hand, event.hand_other = translate_event_hands(bl_event.xr)

    if bimanual:
        event.position_other = Vector(bl_event.xr.controller_location_other)
        event.rotation_other = to_blender_axis_system(bl_event.xr.controller_rotation_other)
        event.value_other = bl_event.xr.state_other[0]

    return event


def make_xr_action_events(base_event: ControllerEvent) -> list[ControllerEvent]:
    events = []

    bimanual = isinstance(base_event, TwoHandedControllerEvent)
    is_pressed = "_press" in base_event.type
    event_type = base_event.button_name

    if bimanual and not is_pressed and f"{event_type}_both_press" not in input_state:
        bimanual = False  # workaround a Blender bug
        # don't trust the hand order in this event
        if f"{event_type}_main_press" in input_state:
            base_event.hand = "main"
        elif f"{event_type}_alt_press" in input_state:
            base_event.hand = "alt"

    if bimanual:
        button_threshold = THRESHOLD[event_type]
        if base_event.hand == "main":
            event_main = _make_xr_button_event(
                base_event.value > button_threshold,
                event_type,
                f"{event_type}_main",
                Vector(base_event.position),
                None,
                Quaternion(base_event.rotation),
                None,
                base_event.hand,
                None,
                base_event.value if base_event.value > button_threshold else 0.0,
                None,
            )
            event_alt = _make_xr_button_event(
                base_event.value_other > button_threshold,
                event_type,
                f"{event_type}_alt",
                Vector(base_event.position_other),
                None,
                Quaternion(base_event.rotation_other),
                None,
                base_event.hand_other,
                None,
                base_event.value_other if base_event.value_other > button_threshold else 0.0,
                None,
            )
        else:
            event_main = _make_xr_button_event(
                base_event.value_other > button_threshold,
                event_type,
                f"{event_type}_main",
                Vector(base_event.position_other),
                None,
                Quaternion(base_event.rotation_other),
                None,
                base_event.hand_other,
                None,
                base_event.value_other if base_event.value_other > button_threshold else 0.0,
                None,
            )
            event_alt = _make_xr_button_event(
                base_event.value > button_threshold,
                event_type,
                f"{event_type}_alt",
                Vector(base_event.position),
                None,
                Quaternion(base_event.rotation),
                None,
                base_event.hand,
                None,
                base_event.value if base_event.value > button_threshold else 0.0,
                None,
            )
        event_both = _make_xr_button_event(
            is_pressed,
            event_type,
            f"{event_type}_both",
            Vector(base_event.position),
            Vector(base_event.position_other),
            Quaternion(base_event.rotation),
            Quaternion(base_event.rotation_other),
            base_event.hand,
            base_event.hand_other,
            base_event.value if is_pressed else 0.0,
            base_event.value_other if is_pressed else 0.0,
        )
        events.append(event_main)
        events.append(event_alt)
        events.append(event_both)
    else:
        if f"{event_type}_both_press" in input_state:  # was bimanual in the previous frame
            prev_main_position = input_state[f"{event_type}_main_position"]
            prev_alt_position = input_state[f"{event_type}_alt_position"]
            prev_main_rotation = input_state[f"{event_type}_main_rotation"]
            prev_alt_rotation = input_state[f"{event_type}_alt_rotation"]
            if not is_pressed:
                event_main = _make_xr_button_event(
                    is_pressed,
                    event_type,
                    f"{event_type}_main",
                    prev_main_position,
                    None,
                    prev_main_rotation,
                    None,
                    "main",
                    None,
                    0,
                    None,
                )
                event_alt = _make_xr_button_event(
                    is_pressed,
                    event_type,
                    f"{event_type}_alt",
                    prev_alt_position,
                    None,
                    prev_alt_rotation,
                    None,
                    "alt",
                    None,
                    0,
                    None,
                )
                event_both = _make_xr_button_event(
                    is_pressed,
                    event_type,
                    f"{event_type}_both",
                    prev_main_position,
                    prev_alt_position,
                    prev_main_rotation,
                    prev_alt_rotation,
                    "main",
                    "alt",
                    0,
                    0,
                )
                events.append(event_main)
                events.append(event_alt)
                events.append(event_both)
            else:
                event = _make_xr_button_event(
                    is_pressed,
                    event_type,
                    f"{event_type}_{base_event.hand.lower()}",
                    Vector(base_event.position),
                    None,
                    Quaternion(base_event.rotation),
                    None,
                    base_event.hand,
                    None,
                    base_event.value if is_pressed else 0.0,
                    None,
                )
                if base_event.hand == "main":
                    event_main = event
                    event_alt = _make_xr_button_event(
                        False,
                        event_type,
                        f"{event_type}_alt",
                        prev_alt_position,
                        None,
                        prev_alt_rotation,
                        None,
                        "alt",
                        None,
                        0,
                        None,
                    )
                else:
                    event_main = _make_xr_button_event(
                        False,
                        event_type,
                        f"{event_type}_main",
                        prev_main_position,
                        None,
                        prev_main_rotation,
                        None,
                        "main",
                        None,
                        0,
                        None,
                    )
                    event_alt = event

                event_both = _make_xr_button_event(
                    False,
                    event_type,
                    f"{event_type}_both",
                    prev_main_position,
                    prev_alt_position,
                    prev_main_rotation,
                    prev_alt_rotation,
                    "main",
                    "alt",
                    0,
                    0,
                )
                events.append(event_main)
                events.append(event_alt)
                events.append(event_both)
        elif not is_pressed and f"{event_type}_{base_event.hand.lower()}_press" not in input_state:
            pass
        else:
            event = _make_xr_button_event(
                is_pressed,
                event_type,
                f"{event_type}_{base_event.hand.lower()}",
                Vector(base_event.position),
                None,
                Quaternion(base_event.rotation),
                None,
                base_event.hand,
                None,
                base_event.value if is_pressed else 0.0,
                None,
            )
            events.append(event)

    return events


def _make_xr_button_event(
    is_pressed, event_type, action, loc, loc_other, rot, rot_other, hand, hand_other, state, state_other
) -> ControllerEvent:
    event = TwoHandedControllerEvent() if hand_other else ControllerEvent()
    event.type = event_type
    event.position = loc
    event.rotation = rot
    event.hand = hand
    event.value = state

    if hand_other:
        event.position_other = loc_other
        event.rotation_other = rot_other
        event.hand_other = hand_other
        event.value_other = state_other

    if is_pressed:
        if f"{action}_press" in input_state:
            event.type = f"{action}_press"
        else:
            event.type = f"{action}_start"

        input_state[f"{action}_press"] = True

        input_state[f"{action}_position"] = loc
        input_state[f"{action}_position_other"] = loc_other
        input_state[f"{action}_rotation"] = rot
        input_state[f"{action}_rotation_other"] = rot_other
    elif f"{action}_press" in input_state:
        event.type = f"{action}_end"
        del input_state[f"{action}_press"]

        del input_state[f"{action}_position"]
        del input_state[f"{action}_position_other"]
        del input_state[f"{action}_rotation"]
        del input_state[f"{action}_rotation_other"]

    event.button_name = event.type.replace("_start", "").replace("_press", "").replace("_end", "")

    return event


def make_xr_controller_move_event(hand_bl: str, position: Vector, rotation_bl: Quaternion) -> ControllerEvent:
    """
    * `hand_bl` - "right" or "left"
    * `position` - Vector
    * `rotation_bl` - Quaternion in OpenXR axis style

    Returns `ControllerEvent` with `event.type` as `controller_main_move` or `controller_alt_move`.
    `event.button_name` will be `pose`.
    """

    hand = "main" if hand_bl == bl_xr.main_hand else "alt"

    event = ControllerEvent()
    event.type = f"controller_{hand}_move"
    event.button_name = "pose"
    event.position = position
    event.rotation = to_blender_axis_system(rotation_bl)
    event.hand = hand
    event.value = None

    return event
