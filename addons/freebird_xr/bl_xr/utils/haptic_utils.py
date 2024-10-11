# SPDX-License-Identifier: GPL-2.0-or-later

from bl_input import apply_haptic_feedback as _apply_haptic_feedback
from .xr_session_utils import xr_session


def apply_haptic_feedback(hand="main", duration=200, strength=1, type="TINY_LIGHT"):
    """
    * hand: "main" or "alt"
    * type: preset type of haptic feedback (`TINY_LIGHT`, `TINY_STRONG`, `SHORT_LIGHT`, `SHORT_STRONG`).
    * duration: custom duration of feedback (in milliseconds)
    * strength: custom feedback strength (0 to 1, where 1 is strongest)

    Note: `duration` and `strength` will be ignored if `type` is set.
    """

    hand_raw = xr_session.get_actual_hand_name(hand)

    return _apply_haptic_feedback(hand_raw, duration=duration, strength=strength, type=type)
