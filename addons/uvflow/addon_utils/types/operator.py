from dataclasses import dataclass
from typing import Tuple, Union
from time import time

import bpy
from bpy.types import Operator, OperatorProperties, UILayout, Context, Event

from uvflow.globals import print_debug
from .event import EventType, EventValue, Mouse
from .tools import TOOL_ACTION_TYPES
from ...utils.raycast import RaycastInfo, BVHTreeRaycastInfo
from ...utils.cursor import Cursor
from .state_machine import EventStateMachine, EventStateMachineNode, EventStateMachineAction


class OpsReturn:
    FINISH = {'FINISHED'}
    CANCEL = {'CANCELLED'}
    PASS = {'PASS_THROUGH'}
    RUN = {'RUNNING_MODAL'}
    UI = {'INTERFACE'}


####################################
####################################
####################################


@dataclass
class _ModalTrigger:
    type: EventType
    value: EventValue
    poll: callable

    def match_event(self, context: Context, event: Event) -> bool:
        if event.type == self.type and event.value == self.value:
            if self.poll:
                res = self.poll(context, event)
                return res
            return True
        return False

class ModalTrigger:
    start_trigger: _ModalTrigger
    finish_triggers: list[_ModalTrigger]
    cancel_triggers: list[_ModalTrigger]
    modal_callback: callable

    def __init__(self, modal_state: str, start_type: EventType, start_value: EventValue, poll: callable = None, modal_callback: callable = None) -> None:
        self.start_trigger = _ModalTrigger(start_type, start_value, poll=poll)
        self.finish_triggers = []
        self.cancel_triggers = []
        self.modal_state = modal_state
        self.poll = poll
        self.modal_callback = modal_callback
        self.cursor: Cursor = None

    def set_cursor(self, cursor: Cursor) -> 'ModalTrigger':
        self.cursor = cursor
        return self

    def has_started(self, context: Context, event: Event) -> bool:
        return self.start_trigger.match_event(context, event)

    def has_finished(self, context: Context, event: Event) -> tuple[bool, bool]:
        for finish_trigger in self.finish_triggers:
            if finish_trigger.match_event(context, event):
                return True, False
        for cancel_trigger in self.cancel_triggers:
            if cancel_trigger.match_event(context, event):
                return True, True
        return False, False

    def finish_trigger(self, event_type: EventType, event_value: EventValue, poll: callable = None) -> 'ModalTrigger':
        self.finish_triggers.append(_ModalTrigger(event_type, event_value, poll))
        return self

    def cancel_trigger(self, event_type: EventType, event_value: EventValue, poll: callable = None) -> 'ModalTrigger':
        self.cancel_triggers.append(_ModalTrigger(event_type, event_value, poll))
        return self


####################################
####################################
####################################


class BaseOperator: # (Operator):
    label: str

    @classmethod
    def run(cls, **operator_properties: dict) -> None:
        eval('bpy.ops.'+cls.bl_idname)(**operator_properties)

    @classmethod
    def run_invoke(cls, **operator_properties: dict) -> None:
        eval('bpy.ops.'+cls.bl_idname)('INVOKE_DEFAULT', **operator_properties)

    @classmethod
    def draw_in_layout(cls,
                       layout: UILayout,
                       label: str = None,
                       op_props: dict = {},
                       **draw_kwargs: dict) -> OperatorProperties:
        op = layout.operator(cls.bl_idname, text=label if label is not None else cls.label, **draw_kwargs)
        if op_props:
            for key, value in op_props.items():
                setattr(op, key, value)
        return op

    def invoke(self, context: Context, event: Event) -> OpsReturn:
        # print("BaseOperator::invoke() -> ", self.bl_idname)
        return self.execute(context)

    def action(self, context: 'Context') -> None:
        # print("BaseOperator::action() -> ", self.bl_idname)
        pass

    def execute(self, context: 'Context') -> OpsReturn:
        print_debug("\n* OPS - " + self.ori_cls.__name__ + "::execute()::PRE")
        start_time = time()
        self.action(context)
        print_debug("\n* OPS - " + self.ori_cls.__name__ + "::execute()::POST" + "-> %.4f seconds" % (time()-start_time))
        return OpsReturn.FINISH


class InvokePropsOperator(BaseOperator):
    bl_options: set[str] = {'REGISTER', 'UNDO'}

    def invoke(self, context: Context, event: Event) -> OpsReturn:
        return context.window_manager.invoke_props_popup(self, event)


###### BASE MODAL OPERATOR ######

class BaseModalOperator(BaseOperator):
    bl_label: str
    bl_idname: str

    use_raycast_info: bool = False
    raycast_type: str = 'OBJECT' # 'BVHTREE' # 'SCENE'
    mouse_delta_limit = 0

    modal_triggers: Tuple[ModalTrigger] = ()

    ######

    raycast_info: Union[RaycastInfo, BVHTreeRaycastInfo]


    _modal_instance: Operator = None
    @classmethod
    def get_modal_instance(cls) -> Operator:
        return cls._modal_instance

    def invoke(self, context: Context, event: Event) -> OpsReturn:
        for modal_trigger in self.modal_triggers:
            if modal_trigger.start_trigger.match_event(context, event):
                if not context.window_manager.modal_handler_add(self):
                    return OpsReturn.CANCEL
                self.active_modal_trigger = modal_trigger
                self._modal_start(context, event)
                return OpsReturn.RUN
        if not self.modal_triggers:
            self.active_modal_trigger = None
            self._modal_start(context, event)
            return OpsReturn.RUN
        return OpsReturn.CANCEL

    def _modal_start(self, context: Context, event: Event) -> None:
        self.__class__._modal_instance = self
        self.mouse = Mouse.init(event)
        if self.use_raycast_info:
            if self.raycast_type in {'SCENE', 'OBJECT'}:
                self.raycast_info = RaycastInfo()
                self.raycast_info.update(context, event, target_object=context.object if self.raycast_type == 'OBJECT' else None)
            else:
                self.raycast_info = BVHTreeRaycastInfo(context)
                self.raycast_info.update(context, event)
        self._modal_timer = None
        self.modal_start(context, event)

    def start_modal_timer(self, context: Context, time_step: float = 0.001):
        if self._modal_timer:
            return
        # self.stop_modal_timer(context)
        self._modal_timer = context.window_manager.event_timer_add(time_step, window=context.window)

    def stop_modal_timer(self, context: Context):
        if self._modal_timer is None:
            return
        context.window_manager.event_timer_remove(self._modal_timer)
        self._modal_timer = None

    def update_raycast_info(self, context, event):
        if self.use_raycast_info:
            if self.raycast_type in {'SCENE', 'OBJECT'}:
                self.raycast_info.update(context, event, target_object=context.object if self.raycast_type == 'OBJECT' else None)
            else:
                self.raycast_info.update(context, event)

    def modal_start(self, context: Context, event: Event) -> None:
        pass

    def modal(self, context: 'Context', event: 'Event') -> OpsReturn:
        if event.type in {EventType.TIMER}:
            self.update_mouse(event)
            self.update_raycast_info(context, event)
            res = self.modal__timer(context, event, self.mouse)
            if res is not None:
                if res == OpsReturn.CANCEL or res == OpsReturn.FINISH:
                    self._modal_exit(context, event, cancel=res==OpsReturn.CANCEL)
                    return res
            return OpsReturn.RUN

        if hasattr(self, 'active_modal_trigger') and self.active_modal_trigger:
            for cancel_trigger in self.active_modal_trigger.cancel_triggers:
                if cancel_trigger.match_event(context, event):
                    self._modal_exit(context, event, cancel=True)
                    return OpsReturn.CANCEL
            for finish_trigger in self.active_modal_trigger.finish_triggers:
                if finish_trigger.match_event(context, event):
                    self._modal_exit(context, event, cancel=False)
                    return OpsReturn.FINISH

        if event.type in {EventType.MOUSEMOVE, EventType.INBETWEEN_MOUSEMOVE}:
            self.update_mouse(event)
            self.update_raycast_info(context, event)
            self.modal__mousemove(context, self.mouse)

        res = self.modal_update(context, event, self.mouse)
        if res is not None:
            if res == OpsReturn.CANCEL or res == OpsReturn.FINISH:
                self._modal_exit(context, event, cancel=res==OpsReturn.CANCEL)
            return res
        return OpsReturn.RUN

    def update_mouse(self, event: Event):
        self.mouse.update(event, delta_limit=self.mouse_delta_limit)

    def modal__timer(self, context: Context, event: Event, mouse: Mouse) -> OpsReturn:
        pass

    def modal__mousemove(self, context: Context, mouse: Mouse) -> None:
        pass

    def modal_update(self, context: Context, event: Event, mouse: Mouse) -> OpsReturn or None:
        pass

    def _modal_exit(self, context: Context, event: Event, cancel: bool) -> None:
        self.stop_modal_timer(context)
        if cancel:
            self.modal_cancel(context, event)
        else:
            self.modal_finish(context, event)
        self.modal_exit(context, event)
        del self.mouse
        if self.use_raycast_info:
            if self.raycast_type == 'BVHTREE':
                if self.raycast_info.bm and self.raycast_info.bm.is_valid:
                    self.raycast_info.bm.free()
                del self.raycast_info.bm
            del self.raycast_info
        self.__class__._modal_instance = None

    def modal_finish(self, context: Context, event: Event) -> None:
        pass

    def modal_cancel(self, context: Context, event: Event) -> None:
        pass

    def modal_exit(self, context: Context, event: Event) -> None:
        pass


###### STATE MACHINE MODAL OPERATOR ######

state_machine_result_to_ops_return: dict[int, OpsReturn] = {
    -1: OpsReturn.CANCEL,
    0: OpsReturn.FINISH,
    1: OpsReturn.RUN,
    2: OpsReturn.PASS
}

class StateMachineModalOperator(BaseModalOperator):
    # Internal.
    tool_event_state_machine: EventStateMachine

    # You have to fill up this one in any subclass.
    tool_event_state_machine_nodes: Tuple[EventStateMachineNode] = ()
    tool_event_state_machine_actions: Tuple[EventStateMachineAction] = ()

    @property
    def active_node(self) -> EventStateMachineNode:
        return self.tool_event_state_machine.active_node

    def invoke(self, context: Context, event: Event) -> OpsReturn:
        if not context.window_manager.modal_handler_add(self):
            return OpsReturn.CANCEL
        self._modal_start(context, event)
        return OpsReturn.RUN

    def _modal_start(self, context: Context, event: Event) -> None:
        super()._modal_start(context, event)
        self.tool_event_state_machine = EventStateMachine(self.tool_event_state_machine_nodes, self.tool_event_state_machine_actions)
        self.tool_event_state_machine.init_callbacks_from_operator(self)
        head = self.tool_event_state_machine.active_node
        if head.start_callback is not None:
            head.start_callback(context, self) # Head should be called once.
            head.executed = True

    def modal_update(self, context: Context, event: Event, mouse: Mouse) -> OpsReturn or None:
        sm_result = self.tool_event_state_machine.process_event(context, event, self)
        return state_machine_result_to_ops_return[sm_result]

    def modal_exit(self, context: Context, event: Event) -> None:
        self.tool_event_state_machine.destroy()
        self.tool_event_state_machine = None
        return super().modal_exit(context, event)


class ToolActionModalOperator(BaseModalOperator):
    use_raycast_info = True
    raycast_type = 'BVHTREE'
    tool_action: TOOL_ACTION_TYPES

    def timer_poll(self, context: Context) -> bool:
        return self.tool_action.timer_poll(context)

    def update_tool_action(self):
        # Update tool action props.
        self.tool_action.mouse = self.mouse
        self.tool_action.raycast_info = self.raycast_info

    def invoke(self, context: Context, event: Event) -> OpsReturn:
        # We may require the raycast_info and Mouse data for the poll.
        self.invoke_prepare(context, event)
        if not self.tool_action.poll(context, event):
            return OpsReturn.PASS
        if not self.tool_action._is_modal:
            self.tool_action.action(context, event)
            return OpsReturn.FINISH
        if res := self._modal_start(context, event):
            if res == -1:
                return OpsReturn.CANCEL
            if isinstance(res, set):
                return res
        if not context.window_manager.modal_handler_add(self):
            return OpsReturn.CANCEL
        return OpsReturn.RUN

    def invoke_prepare(self, context: Context, event: Event) -> None:
        super()._modal_start(context, event)
        self.update_tool_action()

    def modal_update(self, context: Context, event: Event, mouse: Mouse) -> OpsReturn or None: 
        def _modal():
            if event.type in {EventType.ESC, EventType.RIGHTMOUSE}:
                return OpsReturn.CANCEL
            if self.tool_action.check_release(event):
                return OpsReturn.FINISH
            if res := self.tool_action.update(context, event):
                return res
            return OpsReturn.RUN
        
        res = _modal()
        if self.timer_poll(context):
            self.start_modal_timer(context, time_step=0.001)
        else:
            self.stop_modal_timer(context)
        return res

    def modal__mousemove(self, context: Context, mouse: Mouse) -> None:
        self.update_tool_action()
        if not self.mouse.enough_movement:
            return
        self.tool_action.update_mousemove(context)

    def modal__timer(self, context: Context, event: Event, mouse: Mouse) -> OpsReturn:
        return self.tool_action.update_timer(context, event, mouse)

    def _modal_start(self, context: Context, event: Event) -> int:
        return self.tool_action.enter(context, event)

    def _modal_exit(self, context: Context, event: Event, cancel: bool) -> None:
        super()._modal_exit(context, event, cancel)
        self.tool_action.exit(context, event)
        del self.tool_action.mouse
        del self.tool_action.raycast_info

    def modal_cancel(self, context: Context, event: Event) -> None:
        self.tool_action.cancel(context, event)

    def modal_finish(self, context: Context, event: Event) -> None:
        self.tool_action.finish(context, event)

    def draw_2d(self, context: Context) -> None:
        self.tool_action.draw_2d(context)

    def draw_3d(self, context: Context) -> None:
        self.tool_action.draw_3d(context)


class MacroOperator__AfterModal(BaseOperator):
    def action(self, context: 'Context') -> None:
        return super().action(context)
