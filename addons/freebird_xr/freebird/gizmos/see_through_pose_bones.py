import bpy
from bpy.types import Object

from bl_xr import root
from bl_xr import Line

from mathutils import Vector, Matrix

import time

PASSIVE_UPDATE_INTERVAL = 0.3  # seconds
ACTIVE_UPDATE_INTERVAL = 1.0 / 60  # 60 Hz

prev_depth_test = -1
prev_show_in_front = -1
next_update_time = 0  # seconds
update_interval = PASSIVE_UPDATE_INTERVAL

bone_line_group = Line(id="bone_lines", style={"depth_test": None})


def on_transform_bones_start(self, event_name, event):
    global update_interval

    update_interval = ACTIVE_UPDATE_INTERVAL


def on_transform_bones_end(self, event_name, event):
    global update_interval

    update_interval = PASSIVE_UPDATE_INTERVAL


def update_bone_lines(self):
    global next_update_time

    ob = bpy.context.view_layer.objects.active
    if ob is None or ob.mode != "POSE":
        return

    if time.time() < next_update_time:
        return

    next_update_time = time.time() + update_interval

    m = ob.matrix_world

    bone_line_group.mesh.vertices.clear()

    has_custom_shapes = any(bone.custom_shape is not None for bone in ob.pose.bones)

    for bone in ob.pose.bones:
        if bone.bone.hide:
            continue

        if bone.custom_shape:
            continue

        if not has_custom_shapes:
            bone_line_group.mesh.vertices.append(m @ bone.head)
            bone_line_group.mesh.vertices.append(m @ bone.tail)

    if hasattr(bone_line_group, "_batch"):
        delattr(bone_line_group, "_batch")


def on_mode_change(self, event_name, new_mode):
    global prev_depth_test, prev_show_in_front

    ob = bpy.context.view_layer.objects.active
    if ob.type == "ARMATURE":
        if new_mode == "POSE":
            has_custom_shapes = any(bone.custom_shape is not None for bone in ob.pose.bones)
            if has_custom_shapes:
                ob.data["prev_display_type"] = ob.display_type
                ob.display_type = "SOLID"
            elif "prev_display_type" in ob.data:
                ob.display_type = ob.data["prev_display_type"]
        elif new_mode == "EDIT":
            ob.data["prev_display_type"] = ob.display_type
            ob.display_type = "SOLID"
        elif "prev_display_type" in ob.data:
            ob.display_type = ob.data["prev_display_type"]

    cursor = root.q("#cursor_main")
    if cursor is None:
        return

    if new_mode == "POSE" and prev_depth_test == -1:
        prev_depth_test = cursor.sphere.get_computed_style("depth_test", True)
        cursor.sphere.style["depth_test"] = None

        Object.add_event_listener("fb.transform_start", on_transform_bones_start)
        Object.add_event_listener("fb.transform_end", on_transform_bones_end)

        root.append_child(bone_line_group)
    elif prev_depth_test != -1:
        cursor.sphere.style["depth_test"] = prev_depth_test
        prev_depth_test = -1

        Object.remove_event_listener("fb.transform_start", on_transform_bones_start)
        Object.remove_event_listener("fb.transform_end", on_transform_bones_end)

        root.remove_child(bone_line_group)


def on_xr_start(self, event_name, event):
    "Check if we're already in the POSE mode when XR starts"

    ob = bpy.context.view_layer.objects.active
    if ob and ob.type == "ARMATURE" and ob.mode in ("EDIT", "POSE"):
        on_mode_change(root, "bl.mode_change", ob.mode)


bone_line_group.update = update_bone_lines.__get__(bone_line_group)


def enable_gizmo():
    root.add_event_listener("bl.mode_change", on_mode_change)
    root.add_event_listener("fb.xr_start", on_xr_start)


def disable_gizmo():
    root.remove_event_listener("bl.mode_change", on_mode_change)
    root.remove_event_listener("fb.xr_start", on_xr_start)
