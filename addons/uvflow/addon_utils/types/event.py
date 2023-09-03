from typing import Tuple

from bpy.types import Event, Context

from .math import Vector2i


class EventValue:
    ANY = 'ANY'
    PRESS = 'PRESS'
    RELEASE = 'RELEASE'
    CLICK = 'CLICK'
    DOUBLE_CLICK = 'DOUBLE_CLICK'
    CLICK_DRAG = 'CLICK_DRAG'
    NORTH = 'NORTH'
    NORTH_EAST = 'NORTH_EAST'
    EAST = 'EAST'
    SOUTH_EAST = 'SOUTH_EAST'
    SOUTH = 'SOUTH'
    SOUTH_WEST = 'SOUTH_WEST'
    WEST = 'WEST'
    NORTH_WEST = 'NORTH_WEST'
    NOTHING = 'NOTHING'


class EventType:
    TIMER = 'TIMER'
    RET = 'RET'
    BACKSPACE = 'BACK_SPACE'
    NONE = 'NONE'
    ESC = 'ESC'
    LEFTMOUSE = 'LEFTMOUSE'
    MIDDLEMOUSE = 'MIDDLEMOUSE'
    RIGHTMOUSE = 'RIGHTMOUSE'
    PEN = 'PEN'
    ERASER = 'ERASER'
    MOUSEMOVE = 'MOUSEMOVE'
    INBETWEEN_MOUSEMOVE = 'INBETWEEN_MOUSEMOVE'
    WHEELUPMOUSE = 'WHEELUPMOUSE'
    WHEELDOWNMOUSE = 'WHEELDOWNMOUSE'
    WHEELINMOUSE = 'WHEELINMOUSE'
    WHEELOUTMOUSE = 'WHEELOUTMOUSE'

    LEFT_CTRL = 'LEFT_CTRL'

    U = 'U'
    Z = 'Z'

    NUM_ONE = 'ONE'
    NUM_TWO = 'TWO'
    NUM_THREE = 'THREE'


class Mouse:
    current: Vector2i   # current mouse position.
    prev: Vector2i      # previous mouse position.
    start: Vector2i     # initial mouse position.
    offset: Vector2i    # mouse offset between initial position and current position.
    delta: Vector2i     # difference of mouse position between prev and current.
    dir: Vector2i       # direction of mouse taking into account previous position.
    local: Vector2i     # local space coordinates.
    local_rel: Vector2i # local space coordinates, relative factor between [0, 1].
    enough_movement: bool

    @staticmethod
    def init(event: Event, rect=None) -> 'Mouse':
        mouse = Mouse()
        mouse.start = Vector2i(event.mouse_region_x, event.mouse_region_y)
        mouse.current = mouse.start.copy()
        mouse.prev = mouse.start.copy()
        mouse.offset = Vector2i(0, 0)
        mouse.delta = Vector2i(0, 0)
        mouse.dir = Vector2i(0, 0)
        mouse.enough_movement = True
        if rect:
            mouse.local = mouse.current - Vector2i(*rect.position)
            size = Vector2i(*rect.size)
            size.clamp(1, 10000000)
            mouse.local_rel = mouse.local / size
            mouse.local_rel.clamp(0, 1)
        return mouse

    def update(self, event: Event, rect=None, delta_limit=0) -> None:
        if delta_limit != 0:
            delta_x = self.current.x - self.prev.x
            delta_y = self.current.y - self.prev.y
            if delta_x < delta_limit and delta_y < delta_limit:
                self.enough_movement = False
                return

        self.delta.x = self.current.x - self.prev.x
        self.delta.y = self.current.y - self.prev.y
        self.prev.x = self.current.x
        self.prev.y = self.current.y
        self.current.x = event.mouse_region_x
        self.current.y = event.mouse_region_y
        self.offset.x = self.current.x - self.start.x
        self.offset.y = self.current.y - self.start.y
        
        self.dir.x = 0 if self.delta.x==0 else 1 if self.delta.x > 0 else -1
        self.dir.y = 0 if self.delta.y==0 else 1 if self.delta.y > 0 else -1
        if rect:
            self.local = self.current - Vector2i(*rect.position)
            self.local_rel = self.local / Vector2i(*rect.size)
            self.local_rel.clamp(0, 1)



class Event:
    type: EventType or str = EventType.NONE
    value: EventValue or str = EventValue.NOTHING
    unicode: str = ''
    ascii: str = ''

    alt: bool = False
    ctrl: bool = False
    shift: bool = False
    oskey: bool = False

    tilt: Tuple[float, float] = (0.0, 0.0)
    pressure: float = 0.0

    is_tablet: bool = False
    is_repeat: bool = False
    is_mouse_absolute: bool = False

    mouse_x: Tuple[int, int] = (0, 0)
    mouse_y: Tuple[int, int] = (0, 0)
    mouse_region_x: Tuple[int, int] = (0, 0)
    mouse_region_y: Tuple[int, int] = (0, 0)
    mouse_prev_x: Tuple[int, int] = (0, 0)
    mouse_prev_y: Tuple[int, int] = (0, 0)


class FakeEvent():
    def __init__(self, event: Event = None):
        if event:
            self.update(event)

    def update(self, event: Event):
        self.type = event.type
        self.value = event.value
        self.alt = event.alt
        self.ctrl = event.ctrl
        self.shift = event.shift
        self.unicode = event.unicode
        self.ascii = event.ascii
        self.mouse_region_x = event.mouse_region_x
        self.mouse_region_y = event.mouse_region_y

    def update_partial(self, event: Event):
        self.alt = event.alt
        self.ctrl = event.ctrl
        self.shift = event.shift
        self.mouse_region_x = event.mouse_region_x
        self.mouse_region_y = event.mouse_region_y

    def get_mouse_region_pos(self):
        return Vector2i(self.mouse_region_x, self.mouse_region_y)
