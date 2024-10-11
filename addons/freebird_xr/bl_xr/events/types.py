# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from ..utils.geometry_utils import Pose
from mathutils import Vector, Quaternion

from dataclasses import dataclass
from ..utils import log

import logging
from copy import deepcopy


class EventAware:
    def add_event_listener(self, event_name: str, callback, options={}):
        if not hasattr(self, "event_listeners"):
            setattr(self, "event_listeners", {})

        event_listeners = getattr(self, "event_listeners")
        event_listeners[event_name] = event_listeners.get(event_name, [])
        if (callback, options) not in event_listeners[event_name]:
            event_listeners[event_name].append((callback, options))

    def remove_event_listener(self, event_name: str, callback=None, options={}):
        if not hasattr(self, "event_listeners"):
            setattr(self, "event_listeners", {})

        event_listeners = getattr(self, "event_listeners")
        if event_name not in event_listeners:
            return

        listeners = event_listeners[event_name]

        if callback:
            idx = -1
            for i, (l, opts) in enumerate(listeners):
                if l == callback:
                    idx = i
                    break

            if idx != -1:
                del listeners[idx]

        if len(listeners) == 0 or callback is None:
            del event_listeners[event_name]

    def dispatch_event(self, event_name: str, event: Event):
        if not hasattr(self, "event_listeners"):
            setattr(self, "event_listeners", {})

        event_listeners = getattr(self, "event_listeners")
        event_listeners = event_listeners.get(event_name, []) + event_listeners.get("*", [])

        if log.isEnabledFor(logging.DEBUG):
            from ..dom import root

            self_name = "root" if self == root else str(self)
            log.debug(f"dispatching: {event_name} to {len(event_listeners)} listeners on {self_name}")

        for listener, opts in event_listeners:
            try:
                self.__class__  # skip invalid references (e.g. deleted targets
            except:
                continue

            try:
                if "filter_fn" in opts and not opts["filter_fn"](self, event_name, event):
                    continue
            except Exception as e:
                log.exception(f"Error while running the filter function for event: {event_name}: {e}")
                continue

            if log.isEnabledFor(logging.DEBUG):
                log.debug(
                    f"Calling LISTENER for {event_name}: {listener.__module__}.{listener.__name__} (hash: {id(listener)}) ON {self_name}"
                )

            try:
                if hasattr(listener, "__self__"):
                    listener(event_name, event)
                else:
                    listener(self, event_name, event)
            except Exception as e:
                log.exception(f"Error in listener function for event: {event_name}, function: {listener}: {e}")
                import bl_xr

                if bl_xr.raise_exception_on_listener_error:
                    raise e


@dataclass(repr=False)
class Event:
    type: str = ""
    stop_propagation: bool = False
    stop_propagation_immediate: bool = False
    targets: list = None
    sub_targets: set = None

    def __repr__(self) -> str:
        fields = list(
            filter(
                lambda v: not v.startswith("__") and not callable(getattr(self, v)),
                dir(self),
            )
        )
        fields = [f"{v}={getattr(self, v)}" for v in fields]
        fields = ", ".join(fields)
        return f"{type(self).__name__}({fields})"

    def clone(self) -> Event:
        targets = self.targets
        sub_targets = self.sub_targets

        # temporarily delete these attributes, to prevent deepcopying them
        del self.targets
        del self.sub_targets

        try:
            clone = deepcopy(self)
        finally:  # put back the attributes in the original
            self.targets = targets
            self.sub_targets = sub_targets

        clone.targets = None if targets is None else list(targets)
        clone.sub_targets = None if sub_targets is None else set(sub_targets)
        return clone

    @property
    def _fields(self):
        return


@dataclass(repr=False)
class MouseEvent(Event):
    mouse_position: Vector = None


@dataclass(repr=False)
class ControllerEvent(Event):
    button_name: str = ""
    position: Vector = None
    rotation: Quaternion = None
    value: float = 0.0
    hand: str = None
    "'main' or 'alt'"


@dataclass(repr=False)
class TwoHandedControllerEvent(ControllerEvent):
    position_other: Vector = None
    rotation_other: Quaternion = None
    value_other: float = 0.0
    hand_other: str = None
    "'main' or 'alt'"


@dataclass(repr=False)
class DragEvent(Event):
    button_name: str = ""
    pose_delta: Pose = None
    pivot_position: Vector = None


@dataclass(repr=False)
class UIEvent(Event):
    position: Vector = None
    "World position where the pointer intersected with the target"
    hand: str = None
    "'main' or 'alt'"
