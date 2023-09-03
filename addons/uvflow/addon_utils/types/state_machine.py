from typing import List, Callable, Set, Dict, Union
from dataclasses import dataclass

from .event import EventType, EventValue

from bpy.types import Context, Event


@dataclass
class EventStateMachineAction:
    idname: str
    event_type: Set[EventType] # to support multiple at once.
    event_value: Set[EventValue] # to support multiple at once.
    callback: Union[str, Callable, None]
    # Trigger this action ONLY in the specified state? None if is a global action.
    state: Union[str, 'EventStateMachineNode', None] = None
    poll: Union[str, Callable, None] = None

    @classmethod
    def annot(cls,
              event_type: EventType, event_value: EventValue,
              callback: Callable,
              state: Union[str, 'EventStateMachineNode', None] = None,
              poll: Callable = None) -> 'EventStateMachineAction':
        return cls('', # Null idname. (will gather the name from the annotation id)
                   event_type if isinstance(event_type, set) else {event_type},
                   event_value if isinstance(event_value, set) else {event_value},
                   callback,
                   state,
                   poll)

    def match_event(self, event: Event) -> bool:
        return event.type in self.event_type and event.value in self.event_value


@dataclass
class EventStateMachineTransition:
    poll: Union[str, Callable, None]
    callback: Union[str, Callable, None]
    from_node: Union[str, 'EventStateMachineNode']
    to_node: Union[str, 'EventStateMachineNode']


@dataclass
class EventStateMachineNode:
    idname: str
    callback: Union[str, Callable, None]
    transitions: List[EventStateMachineTransition]
    detransitions: List[EventStateMachineTransition]
    _flags: Set[str]

    @classmethod
    def annot(cls, callback: Union[str, Callable] = None) -> 'EventStateMachineNode':
        return cls('', callback, [], [], set())

    @property
    def is_head(self) -> bool:
        return 'HEAD' in self._flags

    @property
    def is_tail(self) -> bool:
        return 'TAIL' in self._flags

    def transition(self,
                   to_node: Union[str, 'EventStateMachineNode'],
                   poll: Union[str, Callable] = None,
                   callback: Union[str, Callable] = None,) -> 'EventStateMachineNode':
        self.transitions.append(
            EventStateMachineTransition(poll, callback, self, to_node)
        )
        return self

    def detransition(self,
                     poll: Union[str, Callable] = None,
                     callback: Union[str, Callable] = None) -> 'EventStateMachineNode':
        self.detransitions.append(
            EventStateMachineTransition(poll, callback, None, None)
        )
        return self

    def transition_event(self,
                       to_node: Union[str, 'EventStateMachineNode'],
                       event_type: EventType,
                       event_value: EventValue,
                       modifier: str = '', # {'CTRL', 'ALT', 'SHIFT'}
                       callback: Union[str, Callable] = None,
                       extra_poll: Union[str, Callable, None] = None) -> 'EventStateMachineNode':
        event_type = {event_type} if not isinstance(event_type, set) else event_type
        event_value = {event_value} if not isinstance(event_value, set) else event_value
        if modifier in {'CTRL', 'ALT', 'SHIFT'}:
            ''' To combine a key with a modifier. '''
            if modifier == 'CTRL':
                modifier_poll = lambda evt: evt.ctrl
            elif modifier == 'ALT':
                modifier_poll = lambda evt: evt.alt
            elif modifier == 'SHIFT':
                modifier_poll = lambda evt: evt.shift
        else:
            modifier_poll = lambda evt: True
        if extra_poll is not None and callable(extra_poll):
            poll = lambda ctx, event, *args: event.type in event_type and event.value in event_value and modifier_poll(event) and extra_poll(ctx, event, *args)
        else:
            poll = lambda ctx, event, *args: event.type in event_type and event.value in event_value and modifier_poll(event)
        self.transition(to_node, poll, callback)
        return self

    def detransition_event(self, event_type: EventType, event_value: EventValue, callback: Callable = None) -> 'EventStateMachineNode':
        event_type = {event_type} if not isinstance(event_type, set) else event_type
        event_value = {event_value} if not isinstance(event_value, set) else event_value
        poll = lambda ctx, event, *args: event.type in event_type and event.value in event_value
        self.detransition(poll, callback)
        return self

    def mark_as_head(self, callback: Callable = None) -> 'EventStateMachineNode':
        self._flags.add('HEAD')
        self.executed = False
        self.start_callback = callback
        return self

    def mark_as_tail(self, callback: Callable = None) -> 'EventStateMachineNode':
        self._flags.add('TAIL')
        self.stop_callback = callback
        return self


class EventStateMachine:
    active_node: EventStateMachineNode
    nodes: Dict[str, EventStateMachineNode]

    @property
    def state_name(self) -> str:
        return self.active_node.idname if self.active_node is not None else 'NONE'

    def __init__(self, nodes: List[EventStateMachineNode] = [], actions: List[EventStateMachineAction] = []) -> None:
        self.active_node = None
        self.state_log: List[str] = []
        self.nodes = {node.idname: node for node in nodes}
        self.actions = actions

        # Load start node.
        for node in nodes:
            if node.is_head:
                # Should only be 1 only head node.
                self.set_active_node(node)
                break

        # Convert transition Node IDs to Node references.
        for node in nodes:
            for transition in node.transitions:
                if isinstance(transition.from_node, str):
                    transition.from_node = node
                if isinstance(transition.to_node, str):
                    transition.to_node = self.nodes[transition.to_node]

        for action in actions:
            if isinstance(action.state, str):
                action.state = self.nodes[action.state]

        print(f"[StateMachine] ENTER")

    def init_callbacks_from_operator(self, operator) -> None:
        # Convert callback and poll IDs to actual callables from the target Modal Operator.
        for node in self.nodes.values():
            if isinstance(node.callback, str):
                if callback := getattr(operator, node.callback):
                    node.callback = callback
            for transition in node.transitions:
                if isinstance(transition.callback, str):
                    if callback := getattr(operator, transition.callback):
                        transition.callback = callback
                if isinstance(transition.poll, str):
                    if poll := getattr(operator, transition.poll):
                        transition.poll = poll

        for action in self.actions:
            if isinstance(action.callback, str):
                if callback := getattr(operator, action.callback):
                    action.callback = callback
            if isinstance(action.poll, str):
                if poll := getattr(operator, action.poll):
                    action.poll = poll

    def set_active_node(self, idname: Union[str, EventStateMachineNode]) -> None:
        if isinstance(idname, str):
            for node in self.nodes.values():
                if node.idname == idname:
                    self.state_log.append(node.idname)
                    self.active_node = node
                    break
        elif isinstance(idname, EventStateMachineNode):
            self.state_log.append(idname)
            self.active_node = idname

    def detransition(self) -> None:
        self.state_log.pop(-1) # remove current state from the pile.
        detransit_to = self.state_log.pop(-1)
        print(f"[StateMachine] Detransition: Node['{self.active_node.idname}'] ---> Node['{detransit_to}']")
        self.set_active_node(detransit_to)

    def process_event(self, context: Context, event: Event, *args) -> int:
        ''' Return values:
             0 -> Finished. (reached the tail Node)
             1 -> Running + Catch Event.
             2 -> Running + Pass Event.
            -1 -> Cancelled. (some error or invalid node) '''
        print(f"[StateMachine] EventType['{event.type}'], EventValue['{event.value}']")
        # Process actions...
        for action in self.actions:
            if action.state is None or action.state == self.active_node:
                if action.match_event(event):
                    if action.poll is None or action.poll(context, *args):
                        print(f"[StateMachine] Action['{action.idname}'].run()")
                        if action.callback is not None:
                            action.callback(context, *args)
                        return 1

        if self.active_node is None:
            print("[StateMachine] No active Node!")
            return -1

        for detransition in self.active_node.detransitions:
            if detransition.poll(context, event, *args):
                if detransition.callback is not None:
                    detransition.callback(context, event, *args)
                self.detransition()
                return 1

        for transition in self.active_node.transitions:
            if transition.poll(context, event, *args):
                print(f"[StateMachine] Transition: Node['{self.active_node.idname}'] ---> Node['{transition.to_node.idname}']")

                print(f"[StateMachine] Node['{self.active_node.idname}'].exit()")
                print(f"[StateMachine] Node['{transition.to_node.idname}'].enter()")

                if transition.callback is not None:
                    if transition.callback(context, event, *args) == -1:
                        print("\t -> Transition to Node was cancelled !")
                        self.detransition()
                        return 1

                if transition.to_node.is_tail:
                    print(f"[StateMachine] Tail['{self.active_node.idname}'].stop()")
                    if transition.to_node.stop_callback is not None:
                        transition.to_node.stop_callback(context, *args)
                    print(f"[StateMachine] EXIT")
                    return 0

                self.set_active_node(transition.to_node)
                return 1

        if self.active_node.callback is not None:
            if self.active_node.is_head:
                if not self.active_node.executed:
                    print(f"[StateMachine] Head['{self.active_node.idname}'].start()")
                    if self.active_node.start_callback:
                        self.active_node.start_callback(context, *args)
                    self.active_node.executed = True
                    return 1

            print(f"[StateMachine] Node['{self.active_node.idname}'].update()")
            if res := self.active_node.callback(context, event, *args):
                if res == 1:
                    print("\t-> Catch Event!")
                elif res == 2:
                    print("\t-> Pass Event!")
                else:
                    print("\t-> WTF Event!?")
                    return 1
                return res
        return 2

    def destroy(self):
        self.active_node = None
        self.nodes.clear()
        self.actions.clear()
        self.state_log.clear()
        del self
