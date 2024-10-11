# SPDX-License-Identifier: GPL-2.0-or-later

from ..types import Event, ControllerEvent

from mathutils import Quaternion

from bl_xr import xr_session
from bl_xr import Event, ControllerEvent, TwoHandedControllerEvent, DragEvent, Pose
from bl_xr.consts import VEC_FORWARD
from bl_xr.utils import quat_diff, log
from bl_xr import intersections

from mathutils import Quaternion, Matrix
from math import radians
from dataclasses import dataclass
from typing import Dict
import logging


@dataclass
class HighLevelEvent:
    start_pose: Pose
    prev_frame_pose: Pose
    is_dragging: bool
    start_intersection_targets: set
    start_intersection_sub_targets: set


_events_tracking: Dict[str, HighLevelEvent] = {}

TRANSLATION_SNAP_THRESHOLD = 0.006
ROTATION_SNAP_THRESHOLD = radians(3.5)
SCALE_SNAP_THRESHOLD = 0.05  # 5% increase/decrease
MIN_DISTANCE_FROM_PIVOT_AXIS = 0.05


def make_high_level_event(events: list[ControllerEvent]) -> Event:
    events = list(filter(lambda e: e.type.startswith(("trigger_", "squeeze_")) and "touch" not in e.type, events))
    output = None
    if len(events) == 0:
        return output

    def end_event(event: ControllerEvent, delete_entry=True):
        nonlocal output

        event_pose_data = _events_tracking[event.button_name]
        # print("** ENDING EVENT", event.button_name, event_pose_data.is_dragging)
        if event_pose_data.is_dragging:
            drag_event = DragEvent()
            drag_event.type = "drag_end"
            drag_event.button_name = event.button_name
            drag_event.targets = event_pose_data.start_intersection_targets
            drag_event.sub_targets = event_pose_data.start_intersection_sub_targets

            output = drag_event
        elif event.button_name == "trigger_main":
            # dispatch the 'click' event to the tracked objects
            click_event = ControllerEvent()
            click_event.type = "click"
            click_event.button_name = event.button_name
            click_event.hand = event.hand
            click_event.position = event.position
            click_event.rotation = event.rotation
            click_event.value = 1.0
            output = click_event

        # clear the tracked objects list, and recorded pointer pose
        if delete_entry:
            del _events_tracking[event.button_name]

    if len(events) == 3:
        event_main, event_alt, event_both = events

        curr_pointer_pose = get_relative_pointer_pose(event_both)

        if event_both.button_name in _events_tracking:
            if "_end" in event_main.type and "_end" in event_alt.type and "_end" in event_both.type:
                end_event(event_both)
            elif "_end" in event_both.type:
                # transitioning to single-handed tracking
                event = event_main if "_press" in event_main.type else event_alt

                event_pose_data = _events_tracking[event_both.button_name]
                if "_end" in event_main.type and event_main.button_name == "trigger_main":
                    if event_pose_data.is_dragging:
                        end_event(
                            event_both, delete_entry=False
                        )  # won't transition drag to trigger_alt, that's the behavior I've decided upon
                        event_pose_data.is_dragging = False
                    else:
                        # dispatch the 'click' event to the tracked objects
                        click_event = ControllerEvent()
                        click_event.type = "click"
                        click_event.button_name = event_main.button_name
                        click_event.hand = event_main.hand
                        click_event.position = event_main.position
                        click_event.rotation = event_main.rotation
                        click_event.value = 1.0
                        output = click_event

                curr_pointer_pose = get_relative_pointer_pose(event)

                _events_tracking[event.button_name] = HighLevelEvent(
                    curr_pointer_pose,
                    curr_pointer_pose,
                    False,
                    list(intersections.curr["bounds"].keys()) if intersections.curr["bounds"] else None,
                    intersections.sub_targets,
                )

                _events_tracking[event.button_name].is_dragging = event_pose_data.is_dragging
                del _events_tracking[event_both.button_name]
            else:
                # already tracking two-handed
                event = event_both
                event_pose_data = _events_tracking[event.button_name]

                pose_delta_from_start = curr_pointer_pose.difference(event_pose_data.start_pose)
                if event_pose_data.is_dragging or not is_within_threshold(pose_delta_from_start):
                    # dispatch the 'drag_start' or 'drag' event (if 'drag_start' already sent)
                    # to the tracked objects, along with the pose_change data
                    drag_event = DragEvent()
                    drag_event.type = "drag" if event_pose_data.is_dragging else "drag_start"
                    _events_tracking[event.button_name].is_dragging = True

                    nav_pose = xr_session.viewer_pose
                    m_local_to_world = Matrix.LocRotScale(
                        nav_pose.position, nav_pose.rotation, (nav_pose.scale_factor,) * 3
                    )

                    if drag_event.type == "drag_start":
                        pose_delta = pose_delta_from_start.clone()
                    else:
                        pose_delta = curr_pointer_pose.difference(event_pose_data.prev_frame_pose)
                        if log.isEnabledFor(logging.DEBUG):
                            log.debug(f"NOW: {curr_pointer_pose}")
                            log.debug(f"PREV: {event_pose_data.prev_frame_pose}")
                            log.debug(f"DELTA: {pose_delta}")

                    pose_delta.position = m_local_to_world @ pose_delta.position - nav_pose.position

                    # convert the rotation from a user-centric to world-centric frame of reference
                    r1 = Quaternion(pose_delta.rotation)
                    r1.rotate(nav_pose.rotation)
                    pose_delta.rotation = quat_diff(r1, nav_pose.rotation)

                    # prevent gimbal lock when the controllers are very close to the pivot axis
                    p0 = event_alt.position / nav_pose.scale_factor
                    p1 = event_main.position / nav_pose.scale_factor
                    p0.z = p1.z = 0
                    if (p0 - p1).length < MIN_DISTANCE_FROM_PIVOT_AXIS:
                        pose_delta.rotation = Quaternion()

                    drag_event.button_name = event.button_name
                    drag_event.pose_delta = pose_delta
                    drag_event.pivot_position = m_local_to_world @ curr_pointer_pose.position
                    drag_event.targets = event_pose_data.start_intersection_targets
                    drag_event.sub_targets = event_pose_data.start_intersection_sub_targets

                    output = drag_event

                event_pose_data.prev_frame_pose = curr_pointer_pose
        else:
            # tracking start for two-handed
            event = event_both
            _events_tracking[event.button_name] = HighLevelEvent(
                curr_pointer_pose,
                curr_pointer_pose,
                False,
                list(intersections.curr["bounds"].keys()) if intersections.curr["bounds"] else None,
                intersections.sub_targets,
            )

            # check for transition from single-handed to two-handed
            if event_main.button_name in _events_tracking:
                _events_tracking[event.button_name].is_dragging = _events_tracking[event_main.button_name].is_dragging
                del _events_tracking[event_main.button_name]
            elif event_alt.button_name in _events_tracking:
                _events_tracking[event.button_name].is_dragging = _events_tracking[event_alt.button_name].is_dragging
                del _events_tracking[event_alt.button_name]
    elif len(events) == 1:
        event = events[0]
        curr_pointer_pose = get_relative_pointer_pose(event)

        # print("****", event.type, _events_tracking)

        if event.type.endswith("_press") and event.button_name not in _events_tracking:
            return output

        if event.type.endswith("_start"):
            # start tracking `intersecting_elements`, and record the pointer pose
            _events_tracking[event.button_name] = HighLevelEvent(
                curr_pointer_pose,
                curr_pointer_pose,
                False,
                list(intersections.curr["bounds"].keys()) if intersections.curr["bounds"] else None,
                intersections.sub_targets,
            )
        elif event.type.endswith("_press"):
            event_pose_data = _events_tracking[event.button_name]

            pose_delta_from_start = curr_pointer_pose.difference(event_pose_data.start_pose)
            if event_pose_data.is_dragging or (
                event.button_name != "trigger_alt" and not is_within_threshold(pose_delta_from_start)
            ):
                # dispatch the 'drag_start' or 'drag' event (if 'drag_start' already sent)
                # to the tracked objects, along with the pose_change data
                drag_event = DragEvent()
                drag_event.type = "drag" if event_pose_data.is_dragging else "drag_start"
                _events_tracking[event.button_name].is_dragging = True

                nav_pose = xr_session.viewer_pose
                m_local_to_world = Matrix.LocRotScale(
                    nav_pose.position, nav_pose.rotation, (nav_pose.scale_factor,) * 3
                )

                if drag_event.type == "drag_start":
                    pose_delta = pose_delta_from_start.clone()
                else:
                    pose_delta = curr_pointer_pose.difference(event_pose_data.prev_frame_pose)
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug(f"NOW: {curr_pointer_pose}")
                        log.debug(f"PREV: {event_pose_data.prev_frame_pose}")
                        log.debug(f"DELTA: {pose_delta}")

                pose_delta.position = m_local_to_world @ pose_delta.position - nav_pose.position

                # convert the rotation from a user-centric to world-centric frame of reference
                r1 = Quaternion(pose_delta.rotation)
                r1.rotate(nav_pose.rotation)
                pose_delta.rotation = quat_diff(r1, nav_pose.rotation)

                drag_event.button_name = event.button_name
                drag_event.pose_delta = pose_delta
                drag_event.pivot_position = m_local_to_world @ curr_pointer_pose.position
                drag_event.targets = event_pose_data.start_intersection_targets
                drag_event.sub_targets = event_pose_data.start_intersection_sub_targets

                output = drag_event

            event_pose_data.prev_frame_pose = curr_pointer_pose
        elif event.type.endswith("_end") and event.button_name in _events_tracking:
            end_event(event)

    return output


def get_relative_pointer_pose(event: ControllerEvent) -> Pose:
    "Returns the pointer pose, relative to the user's real-world frame of reference. Adjusts for scene transforms."

    nav_pose = xr_session.viewer_pose
    m_local_to_world = Matrix.LocRotScale(nav_pose.position, nav_pose.rotation, (nav_pose.scale_factor,) * 3)
    m_world_to_local = m_local_to_world.inverted()

    if not isinstance(event, TwoHandedControllerEvent):  # single handed
        rot = Quaternion(event.rotation)
        rot.rotate(nav_pose.rotation.inverted())
        return Pose(m_world_to_local @ event.position, rot, 1)

    p0 = event.position_other
    p1 = event.position

    length = (p1 - p0).length / xr_session.viewer_scale

    p0 = m_world_to_local @ p0
    p1 = m_world_to_local @ p1
    mid = (p0 + p1) / 2
    d = p1 - p0
    d.z = 0
    rot = VEC_FORWARD.rotation_difference(d)

    return Pose(mid, rot, length)


def is_within_threshold(pose_delta: Pose) -> bool:
    rot_diff = pose_delta.rotation.to_euler()

    return (
        pose_delta.position.magnitude <= TRANSLATION_SNAP_THRESHOLD
        and abs(rot_diff.x) <= ROTATION_SNAP_THRESHOLD
        and abs(rot_diff.y) <= ROTATION_SNAP_THRESHOLD
        and abs(rot_diff.z) <= ROTATION_SNAP_THRESHOLD
        and abs(pose_delta.scale_factor - 1) <= SCALE_SNAP_THRESHOLD
    )
