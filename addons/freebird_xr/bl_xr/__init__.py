# SPDX-License-Identifier: GPL-2.0-or-later

from .utils.xr_session_utils import xr_session

from .events.types import (
    Event,
    MouseEvent,
    ControllerEvent,
    TwoHandedControllerEvent,
    DragEvent,
    UIEvent,
    EventAware,
)

from .utils.geometry_utils import Pose, Bounds

from .ui.components import (
    Mesh,
    Sphere,
    Ring,
    Pyramid,
    Cube,
    Cone,
    Image,
    Text,
    Button,
    Line,
    Grid2D,
)

from .dom import Node, root

import bpy
from bpy.app.handlers import persistent

# config
main_hand: str = "right"  # or "left"
selection_shape: str = "SPHERE"
selection_size: float = 0.01
"In local scale, i.e. not factoring in xr_session.viewer_scale"
intersection_checks: set = {"RAYCAST_UI", "BOUNDS_ON_MAIN_TRIGGER"}
"One or more of 'BOUNDS_ON_MAIN_TRIGGER', 'RAYCAST_UI', 'ALL'"
raise_exception_on_listener_error: bool = True
"Only logs the exception, if set to False. Otherwise raises the exception thrown by the listener (useful while testing)."


def init():
    from .events import init as init_events
    from .ui import init as init_ui

    init_events()
    init_ui()


@persistent
def on_xr_start(context):
    root.dispatch_event("xr_start", bpy.context)


def register_controllers():
    bpy.app.handlers.xr_session_start_pre.append(on_xr_start)


def unregister_controllers():
    if on_xr_start in bpy.app.handlers.xr_session_start_pre:
        bpy.app.handlers.xr_session_start_pre.remove(on_xr_start)


init()
