# SPDX-License-Identifier: GPL-2.0-or-later

import bpy

from bl_xr import Node, Event, ControllerEvent, UIEvent, DragEvent, TwoHandedControllerEvent
from bl_xr import root
from bl_xr import intersections

from bl_xr.utils import make_class_event_aware, make_class_posable, log

import logging

make_class_event_aware(bpy.types.Object)
make_class_posable(bpy.types.Object)


def bind_and_dispatch(events):
    bind_objects(events)
    dispatch_events(events)


def bind_objects(events: Event | list[Event]):
    if not events:
        return

    events = events if isinstance(events, list) else [events]

    for event in events:
        if isinstance(event, ControllerEvent) and intersections.curr["bounds"]:
            hand_allowed = event.hand != "alt" or isinstance(event, TwoHandedControllerEvent)
            if hand_allowed and event.button_name.startswith(("trigger_", "squeeze_", "pose")):
                event.targets = list(intersections.curr["bounds"].keys())
        elif isinstance(event, DragEvent):
            event.targets = remove_dead_targets(event.targets)
            if event.targets:
                event.sub_targets = remove_dead_subtargets(event.targets[0], event.sub_targets)

            continue  # drag_event's binding is handled by `click_drag`, since the binding works in a different way for drag
        elif isinstance(event, UIEvent) and event.hand == "main":
            type = "bounds" if event.type.startswith("controller_") else "raycast"

            curr, prev = intersections.curr[type].keys(), intersections.prev[type].keys()
            curr, prev = set(curr), set(prev)

            if event.type.endswith("_enter"):
                diff = curr.difference(prev)
                event.targets = list(diff)
            elif event.type.endswith("_leave"):
                diff = prev.difference(curr)
                event.targets = list(diff)
            elif curr:
                event.targets = list(curr)

        event.targets = remove_dead_targets(event.targets)
        if event.targets:
            event.sub_targets = intersections.sub_targets
            event.sub_targets = remove_dead_subtargets(event.targets[0], event.sub_targets)


def dispatch_events(events: Event | list[Event]):
    if not events:
        return

    events = events if isinstance(events, list) else [events]

    for event in events:
        if log.isEnabledFor(logging.DEBUG):
            log.debug(str(event))

        targets = list(event.targets) if event.targets else []
        appended_root = False
        if not isinstance(event, UIEvent):
            targets.append(root)
            appended_root = True

        for target in targets:
            if event.stop_propagation_immediate or (target == root and event.stop_propagation):
                continue

            if target != root and isinstance(target, Node):
                x = target
                while x:
                    x.dispatch_event(event.type, event)
                    x = x.parent

                    if (
                        event.stop_propagation
                        or event.stop_propagation_immediate
                        or (x == root and (appended_root or isinstance(event, UIEvent)))
                    ):
                        break
            else:
                target.dispatch_event(event.type, event)


def remove_dead_targets(targets):
    if targets is None:
        return

    new_targets = []
    for t in targets:
        try:
            t.__class__  # skip invalid references (e.g. deleted targets)
            if hasattr(t, "name"):
                t.name
        except:
            continue

        new_targets.append(t)

    return new_targets


def remove_dead_subtargets(ob, sub_targets):
    if not sub_targets:
        return

    new_sub_targets = set()
    for t in sub_targets:
        if not isinstance(ob, bpy.types.Object):
            continue
        if ob.type == "MESH" and not t.is_valid:
            continue
        elif ob.type == "CURVE" and (len(ob.data.splines) == 0 or not any(t == pt for pt in ob.data.splines[0].points)):
            continue
        elif ob.type == "ARMATURE" and ob.mode == "EDIT" and t[0] not in ob.data.edit_bones:
            continue
        new_sub_targets.add(t)
    return new_sub_targets if len(new_sub_targets) else None
