import bpy

from bpy.types import Object
from freebird.utils import log


def on_transform_end(self, event_name, event):
    if not bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        return  # nothing to do

    if event.sub_targets is None:  # in OBJECT mode
        for ob in event.targets:
            add_object_keyframe(ob)
    else:  # in POSE or EDIT mode
        ob = event.targets[0]  # assuming that we're editing only one object (which is fine for now)
        if ob.type == "MESH":
            pass  # not implemented, not sure how to do this. what are shape keys?
        elif ob.type == "ARMATURE":
            if ob.mode == "EDIT":
                pass  # not implemented
            elif ob.mode == "POSE":
                for bone, bone_corner in event.sub_targets:
                    add_pose_bone_keyframe(bone)
        elif ob.type == "CURVE":
            for spline_point in event.sub_targets:
                add_edit_nurbs_keyframe(spline_point)


def add_object_keyframe(ob):
    ob.keyframe_insert(data_path="location")
    ob.keyframe_insert(data_path="rotation_quaternion")
    ob.keyframe_insert(data_path="rotation_euler")
    ob.keyframe_insert(data_path="scale")


def add_edit_nurbs_keyframe(pt):
    pt.keyframe_insert(data_path="co")


def add_pose_bone_keyframe(bone):
    bone.keyframe_insert(data_path="location")
    bone.keyframe_insert(data_path="rotation_quaternion")
    bone.keyframe_insert(data_path="rotation_euler")
    bone.keyframe_insert(data_path="scale")


def enable_gizmo():
    Object.add_event_listener("fb.transform_end", on_transform_end)


def disable_gizmo():
    Object.remove_event_listener("fb.transform_end", on_transform_end)
