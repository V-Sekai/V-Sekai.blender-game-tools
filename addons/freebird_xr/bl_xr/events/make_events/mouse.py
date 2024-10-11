# SPDX-License-Identifier: GPL-2.0-or-later

from ..types import MouseEvent

from bpy.types import Event as Bl_Event

from mathutils import Vector


def make_mouse_move_event(bl_event: Bl_Event) -> MouseEvent:
    event = MouseEvent()
    event.type = "mouse_move"
    event.mouse_position = Vector((bl_event.mouse_x, bl_event.mouse_y, 0))
    return event
