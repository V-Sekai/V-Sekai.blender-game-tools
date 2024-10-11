# SPDX-License-Identifier: GPL-2.0-or-later


def init():
    import bl_input

    from ..dom import root

    from .event_manager import on_event

    bl_input.event_callback = on_event
    bl_input.send_movement_events = True

    root.add_event_listener("xr_start", lambda self, event, c: bl_input.start_input_tracking())
