import bpy
from bpy.types import SpaceView3D

from .tool_state import ToolState


# Global reference to the draw handler.
_draw_handler = None


# ----- DRAWING ------------------------------------

def tool_draw_3d():
    ToolState.get().draw_batch(bpy.context)


# ----- REGISTERING --------------------------------

def register_draw_handler():
    global _draw_handler
    if _draw_handler is not None:
        return
    _draw_handler = SpaceView3D.draw_handler_add(
        tool_draw_3d,
        (),
        'WINDOW',
        'POST_VIEW'
    )

def unregister_draw_handler():
    global _draw_handler
    if _draw_handler is None:
        return
    SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
    _draw_handler = None
