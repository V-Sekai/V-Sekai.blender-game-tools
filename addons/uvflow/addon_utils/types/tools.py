from typing import Union, Callable
import math

from .event import EventType, EventValue, Mouse
from ..utils.raycast import BVHTreeRaycastInfo

from bpy.types import Context, Event, Operator


class ToolAction:
    _instance = None # singleton

    geo_context: str

    @classmethod
    def get(cls) -> 'ToolAction':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    event_type: EventType
    event_value: EventValue
    alt: bool   = False
    ctrl: bool  = False
    shift: bool = False

    additional_hotkeys: tuple[dict] = None

    # INTERNAL.
    _is_modal = False
    op_poll: Callable = None
    mouse: Mouse
    raycast_info: BVHTreeRaycastInfo

    def poll(self, context: Context, event: Event) -> bool:
        return True

    def check_release(self, event: Event) -> bool:
        if event.type == self.event_type:
            if self.event_value in {'PRESS', 'CLICK_DRAG'}:
                if self.ctrl and event.ctrl:
                    return False
                if self.alt and event.alt:
                    return False
                if self.shift and event.shift:
                    return False
                return event.value == 'RELEASE'
        return False

    def action(self, context: Context, event: Event) -> None:
        return 1

    @classmethod
    def get_keymaps(self) -> list[dict]:
        km = dict(
            type=self.event_type,
            value=self.event_value
        )

        toggle_modifier = []
        if self.alt and isinstance(self.alt, str):
            if self.alt == 'TOGGLE':
                toggle_modifier.append('alt')
            self.alt = False # HACK. To avoid blocking the modal exit.
        if self.ctrl and isinstance(self.ctrl, str):
            if self.ctrl == 'TOGGLE':
                toggle_modifier.append('ctrl')
        if self.shift and isinstance(self.shift, str):
            if self.shift == 'TOGGLE':
                toggle_modifier.append('shift')

        print(self.__class__.__name__, km, ', Toggle Modifier:', toggle_modifier)

        keymaps: list[dict] = []

        if toggle_modifier:
            mod_count: int = len(toggle_modifier)
            for n in range(0, math.factorial(mod_count)*2):
                comb_bin =f'{n:0{mod_count}b}' # "{0:b}".format(n)
                modifier_states = {}
                for i in range(0, len(comb_bin)):
                    state = bool(int(comb_bin[i]))
                    modifier_states[toggle_modifier[i]] = state
                km_cpy = km.copy()
                km_cpy.update(modifier_states)
                if km_cpy in keymaps:
                    continue
                print("\t->", km_cpy)
                keymaps.append(km_cpy)
        else:
            keymaps.append(km)

        if self.additional_hotkeys is not None:
            for hotkey in self.additional_hotkeys:
                keymaps.append(hotkey)

        return keymaps


class ToolActionModal(ToolAction):
    # INTERNAL.
    _is_modal = True

    def timer_poll(self, context: Context) -> bool:
        return False

    def enter(self, context: Context, event: Event) -> int:
        pass

    def update(self, context: Context, event: Event) -> int:
        pass

    def update_timer(self, context: Context, event: Event, mouse: Mouse) -> None:
        pass

    def update_mousemove(self, context: Context) -> None:
        pass

    def finish(self, context: Context, event: Event) -> int:
        pass

    def cancel(self, context: Context, event: Event) -> int:
        pass

    def exit(self, context: Context, event: Event) -> int:
        pass

    def draw_2d(self, context: Context) -> int:
        pass

    def draw_3d(self, context: Context) -> int:
        pass



TOOL_ACTION_TYPES = Union[ToolAction, ToolActionModal]
