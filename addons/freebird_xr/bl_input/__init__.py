# SPDX-License-Identifier: GPL-2.0-or-later

import bpy

event_callback = None
send_movement_events = False


def start_input_tracking():
    # don't remove these imports. required for registering the operator
    from . import move_timer, actionset

    _start_tracking_xr_actions()

    if send_movement_events:
        bpy.ops.bl_input.start_xr_move_timer()
        bpy.ops.bl_input.mouse_event_op()


def _start_tracking_xr_actions():
    from . import bindings
    from .actionset import make_actions, ACTION_SET_NAME

    xr_session_state = bpy.context.window_manager.xr_session_state

    if not xr_session_state:
        return

    # generate the mappings
    print("number of actionsets", len(xr_session_state.actionmaps))  # maybe skip if already bound
    actionset = xr_session_state.actionmaps.new(xr_session_state, ACTION_SET_NAME, True)
    make_actions(actionset)

    # bind the mappings
    if not xr_session_state.action_set_create(bpy.context, actionset):
        raise RuntimeError("Could not make actionset!")

    for action in actionset.actionmap_items:
        if not xr_session_state.action_create(bpy.context, actionset, action):
            raise RuntimeError(f"Could not make action: {action.name}")

        for binding in action.bindings:
            if binding.name in bindings.DISABLED_PROFILES:
                continue

            if not xr_session_state.action_binding_create(bpy.context, actionset, action, binding):
                raise RuntimeError(f"Could not make action binding: {action.name} to {binding.name}")

    # bind the pose tracking
    xr_session_state.controller_pose_actions_set(bpy.context, ACTION_SET_NAME, "controller_grip", "controller_aim")

    # start tracking!
    if not xr_session_state.active_action_set_set(bpy.context, ACTION_SET_NAME):
        raise RuntimeError("Could not activate actionset!")


def apply_haptic_feedback(hand="right", duration=200, strength=1, type="TINY_LIGHT"):
    """
    * hand: "right" or "left"
    * type: preset type of haptic feedback (`TINY_LIGHT`, `TINY_STRONG`, `SHORT_LIGHT`, `SHORT_STRONG`).
    * duration: custom duration of feedback (in milliseconds)
    * strength: custom feedback strength (0 to 1, where 1 is strongest)

    Note: `duration` and `strength` will be ignored if `type` is set.
    """

    from .actionset import ACTION_SET_NAME

    xr_session_state = bpy.context.window_manager.xr_session_state

    if not xr_session_state:
        return

    user_path = "/user/hand/" + hand.lower()

    if type == "TINY_LIGHT":
        duration = 20000
        strength = 0.35
    elif type == "TINY_STRONG":
        duration = 20000
        strength = 0.6
    elif type == "SHORT_LIGHT":
        duration = 40000
        strength = 0.4
    elif type == "SHORT_STRONG":
        duration = 40000
        strength = 1

    frequency = 0

    applied = xr_session_state.haptic_action_apply(
        bpy.context, ACTION_SET_NAME, "haptic", user_path, duration, frequency, strength
    )
    return applied
