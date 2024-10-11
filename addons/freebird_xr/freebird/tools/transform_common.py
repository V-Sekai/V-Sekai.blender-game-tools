import bpy
import bmesh
from bpy.types import Object
from bl_xr import Pose
from bl_xr.consts import VEC_RIGHT, VEC_FORWARD, VEC_ONE
from bl_xr.utils import vec_signed_angle, get_bmesh_elements, quat_diff

from mathutils import Vector, Quaternion, Matrix
from math import isclose

from ..settings_manager import settings

transform_state = {
    "transform_m": None,
    "transform_m_inv": None,
    "transform_elements": None,
    "preselected_elements": None,
    "object_to_transform": None,
    "has_transformed": False,
    "siblings_affected_indirectly": None,
    "allow_transform": True,
    "has_cloned": False,
    "context_override": None,
}


def on_transform_object(self, event_name, event):
    for ob in transform_state["transform_elements"]:
        pose = ob.pose_get()
        pose.transform(event.pose_delta, event.pivot_position)
        ob.pose_set(pose)


def on_transform_edit_mesh(ob, event_name, event):
    tool_settings = bpy.context.scene.tool_settings

    if tool_settings.use_proportional_edit:
        delta_to_apply = event.pose_delta
        axis, angle = delta_to_apply.rotation.to_axis_angle()

        p_size = "proportional_distance" if hasattr(tool_settings, "proportional_distance") else "proportional_size"
        proportional_opts = {
            "use_proportional_edit": tool_settings.use_proportional_edit,
            "proportional_edit_falloff": tool_settings.proportional_edit_falloff,
            "proportional_size": getattr(tool_settings, p_size),
        }

        with transform_state["context_override"]:
            bpy.ops.transform.translate(value=delta_to_apply.position, orient_type="GLOBAL", **proportional_opts)
            bpy.ops.transform.rotate(
                value=-angle,
                center_override=event.pivot_position,
                orient_matrix=create_z_orient(axis),
                **proportional_opts
            )
            bpy.ops.transform.resize(
                value=delta_to_apply.scale_factor * VEC_ONE, orient_type="GLOBAL", **proportional_opts
            )
    else:
        # this block isn't necessary, it's just there until the older unit tests are fixed to work with transform operators
        for v in transform_state["transform_elements"]:
            pose = Pose(transform_state["transform_m"] @ v.co, Quaternion(), 1)
            pose.transform(event.pose_delta, event.pivot_position)
            v.co = transform_state["transform_m_inv"] @ pose.position

        bmesh.update_edit_mesh(ob.data)


def on_transform_edit_curve(ob, event_name, event):
    for v in transform_state["transform_elements"]:
        pose = Pose(transform_state["transform_m"] @ Vector(v.co[:-1]), Quaternion(), 1)
        pose.transform(event.pose_delta, event.pivot_position)
        v.co = (transform_state["transform_m_inv"] @ pose.position).to_tuple() + (v.co[3],)


def on_transform_edit_armature(ob, event_name, event):
    # prepare
    ob = list(event.targets)[0]
    transform_m = ob.matrix_world
    transform_m_inv = transform_m.inverted()
    world_rot = transform_m.decompose()[1]
    delta_to_apply = event.pose_delta

    # record the bone transform info, to avoid a bone's transform interfering with its connected bones
    sub_targets = freeze_positions()

    for bone, el_type, bone_head, bone_tail, bone_rot, bone_length in sub_targets:
        delta = delta_to_apply

        if el_type == "HEAD" and bone in transform_state["siblings_affected_indirectly"]:
            other, other_orig = transform_state["siblings_affected_indirectly"][bone]
            delta = Pose((transform_m @ other.head) - (transform_m @ other_orig))

        is_corner = el_type != "BOTH" and len(sub_targets) == 1  # dealing with a corner
        transform_bone(
            bone,
            el_type,
            transform_m,
            transform_m_inv,
            world_rot,
            bone_head,
            bone_tail,
            bone_rot,
            bone_length,
            delta,
            event.pivot_position,
            is_corner,
            event,
        )


def on_transform_pose_armature(ob, event_name, event):
    # prepare
    ob = list(event.targets)[0]
    transform_m = ob.matrix_world
    transform_m_inv = transform_m.inverted()
    world_rot = transform_m.decompose()[1]
    delta_to_apply = event.pose_delta

    bones_with_constraints, bones_without_constraints = [], []

    for b, _ in transform_state["transform_elements"]:
        if len(b.constraints) > 0:
            bones_with_constraints.append(b)
        else:
            bones_without_constraints.append(b)

    if bones_with_constraints:
        transform_bones_with_constraints(
            bones_with_constraints, transform_m, transform_m_inv, world_rot, event, delta_to_apply
        )

    if bones_without_constraints:
        transform_bones_without_constraints(
            bones_without_constraints, transform_m, transform_m_inv, world_rot, event, delta_to_apply
        )


def transform_bones_with_constraints(bones, transform_m, transform_m_inv, world_rot, event, delta_to_apply):
    """
    Slower performance, since it uses operators.
    Should use matrix_basis and pose_bone.bone.matrix_local, but I couldn't figure out a way that works in every situation
    """

    def transform_movable_bones(movable_bones, transform_m, transform_m_inv, world_rot, event, delta_to_apply):
        for bone in movable_bones:
            bone.bone.select = True

        axis, angle = delta_to_apply.rotation.to_axis_angle()

        # print(delta_to_apply.position)

        with transform_state["context_override"]:
            bpy.ops.transform.translate(value=delta_to_apply.position, orient_type="GLOBAL")
            bpy.ops.transform.rotate(
                value=-angle, center_override=event.pivot_position, orient_matrix=create_z_orient(axis)
            )
            bpy.ops.transform.resize(value=delta_to_apply.scale_factor * VEC_ONE, orient_type="GLOBAL")

        for bone in movable_bones:
            bone.bone.select = False

    def transform_rotate_only_bones(rotate_only_bones, transform_m, transform_m_inv, world_rot, event, delta_to_apply):
        for bone in rotate_only_bones:
            bone.bone.select = True

            bone_head = transform_m @ bone.head
            bone_rot = bone.matrix.decompose()[1]
            bone_rot.rotate(world_rot)
            bone_rot_orig = Quaternion(bone_rot)

            # apply controller twist, if any
            twist_rot = get_twist(delta_to_apply.rotation, bone_rot)
            bone_rot.rotate(twist_rot)

            # calculate the bone orientation for representing the new leaf position
            new_pivot_pos = event.pivot_position
            base_pos = bone_head

            prev_pivot_pos = new_pivot_pos - delta_to_apply.position
            a = prev_pivot_pos - base_pos
            b = new_pivot_pos - base_pos
            norm = a.cross(b)
            angle = vec_signed_angle(a, b, norm)
            bone_rot.rotate(Quaternion(norm, -angle))

            # back to local space
            bone_rot.rotate(world_rot.inverted())

            bone_rot_to_apply = quat_diff(bone_rot, bone_rot_orig)
            twist_axis, twist_angle = bone_rot_to_apply.to_axis_angle()

            with transform_state["context_override"]:
                bpy.ops.transform.rotate(
                    value=-twist_angle, center_override=event.pivot_position, orient_matrix=create_z_orient(twist_axis)
                )
                bpy.ops.transform.resize(value=delta_to_apply.scale_factor * VEC_ONE, orient_type="GLOBAL")

            bone.bone.select = False

    # separate into movable and rotate-only bones
    is_gizmo_event = getattr(event, "handle_type", None) is not None  # i.e. is from transform handles/gizmo
    movable_bones, rotate_only_bones = [], []
    for bone in bones:
        if is_gizmo_event or (
            (bone.parent is None or not bone.bone.use_connect) and not settings["transform.lock_pose_bone_position"]
        ):
            movable_bones.append(bone)
        else:
            rotate_only_bones.append(bone)

    # clear initial selection
    for bone in bones:
        bone.bone.select = False

    # transform movable bones first
    if movable_bones:
        transform_movable_bones(movable_bones, transform_m, transform_m_inv, world_rot, event, delta_to_apply)

    # transform rotate-only bones next
    if rotate_only_bones:
        transform_rotate_only_bones(rotate_only_bones, transform_m, transform_m_inv, world_rot, event, delta_to_apply)

    # restore initial selection
    for bone in bones:
        bone.bone.select = True


def transform_bones_without_constraints(bones, transform_m, transform_m_inv, world_rot, event, delta_to_apply):
    for bone in bones:
        # preprocess ensures that the bone under the cursor is the first bone in transform_elements

        bone_head = transform_m @ bone.head
        _, bone_rot, bone_scale = bone.matrix.decompose()
        bone_rot.rotate(world_rot)

        if getattr(event, "handle_type", None) is not None or (  # i.e. is from transform handles/gizmo
            (bone.parent is None or not bone.bone.use_connect) and not settings["transform.lock_pose_bone_position"]
        ):
            bone_pose = Pose(bone_head, bone_rot, 1)
            bone_pose.transform(delta_to_apply, event.pivot_position)

            # back to local space
            bone_pose.position = transform_m_inv @ bone_pose.position
            bone_pose.rotation.rotate(world_rot.inverted())

            # apply
            bone_scale *= bone_pose.scale_factor
            bone.matrix = Matrix.LocRotScale(bone_pose.position, bone_pose.rotation, bone_scale)
            continue

        # apply controller twist, if any
        twist_rot = get_twist(delta_to_apply.rotation, bone_rot)
        bone_rot.rotate(twist_rot)

        # calculate the bone orientation for representing the new leaf position
        new_pivot_pos = event.pivot_position
        base_pos = bone_head

        prev_pivot_pos = new_pivot_pos - delta_to_apply.position
        a = prev_pivot_pos - base_pos
        b = new_pivot_pos - base_pos
        norm = a.cross(b)
        angle = vec_signed_angle(a, b, norm)
        bone_rot.rotate(Quaternion(norm, -angle))

        # back to local space
        bone_rot.rotate(world_rot.inverted())

        bone_rot_to_apply = bone_rot

        bone_scale = bone.matrix.decompose()[2]
        bone_scale *= delta_to_apply.scale_factor

        bone.matrix = Matrix.LocRotScale(bone.head, bone_rot_to_apply, bone_scale)


def pre_process_edit_bones(ob, sub_targets: set):
    sub_targets = [(ob.data.edit_bones[bone_name], e) for bone_name, e in sub_targets]
    siblings_affected_indirectly = {}

    if len(sub_targets) > 1:
        # scenario 0: de-duplicate
        both_bones = [bone for bone, el_type in sub_targets if el_type == "BOTH"]
        for bone in both_bones:
            if (bone, "HEAD") in sub_targets:
                sub_targets.remove((bone, "HEAD"))
            if (bone, "TAIL") in sub_targets:
                sub_targets.remove((bone, "TAIL"))

        # scenario 1: only transforming a joint. move only the parent bone's tail
        tail_only_bone = next((bone for bone, el_type in sub_targets if el_type == "TAIL" and bone.children), None)
        if tail_only_bone:
            for child in tail_only_bone.children:
                if (child, "HEAD") in sub_targets:
                    sub_targets.remove((child, "HEAD"))

        # scenario 2a: don't move a parent's tail if moving a full bone
        parents_to_remove = [
            bone.parent for bone, el_type in sub_targets if el_type == "BOTH" and (bone.parent, "TAIL") in sub_targets
        ]
        for bone in parents_to_remove:
            if (bone, "TAIL") in sub_targets:
                sub_targets.remove((bone, "TAIL"))

        # scenario 2b: don't move a child's head if moving a full bone
        children_to_remove = [c for bone, el_type in sub_targets if el_type == "BOTH" for c in bone.children]
        for bone in children_to_remove:
            if (bone, "HEAD") in sub_targets:
                sub_targets.remove((bone, "HEAD"))

    # scenario 3: moving a full bone should move sibling heads, if that bone is at a fork and is connected
    fork_child_bones = [
        (bone, el_type)
        for bone, el_type in sub_targets
        if bone.parent and len(bone.parent.children) > 1 and bone.use_connect
    ]
    for bone, el_type in fork_child_bones:
        if el_type == "TAIL":
            continue

        for sibling in bone.parent.children:
            if sibling == bone or sibling in siblings_affected_indirectly or (sibling, "BOTH") in sub_targets:
                continue

            siblings_affected_indirectly[sibling] = (bone, Vector(bone.head).freeze())
            sub_targets.append((sibling, "HEAD"))

    return sub_targets, siblings_affected_indirectly


def pre_process_pose_bones(ob, sub_targets: set, orig_sub_targets):
    sub_targets = [(ob.pose.bones[bone_name], e) for bone_name, e in sub_targets]
    orig_sub_targets = [(ob.pose.bones[bone_name], e) for bone_name, e in orig_sub_targets]

    if len(sub_targets) > 1:
        # scenario 1: de-duplicate
        both_bones = [bone for bone, el_type in sub_targets if el_type == "BOTH"]
        for bone in both_bones:
            if (bone, "HEAD") in sub_targets:
                sub_targets.remove((bone, "HEAD"))
            if (bone, "TAIL") in sub_targets:
                sub_targets.remove((bone, "TAIL"))

        # scenario 1: remove children if a parent bone is being transformed
        def remove_children(bone):
            for child in bone.children:
                if (child, "BOTH") in sub_targets:
                    sub_targets.remove((child, "BOTH"))
                if (child, "HEAD") in sub_targets:
                    sub_targets.remove((child, "HEAD"))
                if (child, "TAIL") in sub_targets:
                    sub_targets.remove((child, "TAIL"))
                remove_children(child)

        bones_with_children = [bone for bone, el_type in sub_targets if el_type == "BOTH" and bone.children]
        for bone in bones_with_children:
            remove_children(bone)

    # POSE mode only works with full bones
    sub_targets = [(bone, el_type) for bone, el_type in sub_targets if el_type == "BOTH"]

    # make the bone under the cursor the first entry in the list
    bones_under_cursor = [bone for bone, _ in orig_sub_targets]
    bone_under_cursor = next((bone for bone, _ in sub_targets if bone in bones_under_cursor), None)
    if bone_under_cursor is None:
        return []

    sub_targets.remove((bone_under_cursor, "BOTH"))
    sub_targets.insert(0, (bone_under_cursor, "BOTH"))

    return sub_targets


def freeze_positions():
    sub_targets = [
        (
            bone,
            el_type,
            Vector(bone.head).freeze(),
            Vector(bone.tail).freeze(),
            Quaternion(bone.matrix.decompose()[1]).freeze(),
            bone.length,
        )
        for bone, el_type in transform_state["transform_elements"]
    ]
    for sibling, other_data in transform_state["siblings_affected_indirectly"].items():
        other = other_data[0]
        transform_state["siblings_affected_indirectly"][sibling] = (other, Vector(other.head).freeze())

    return sub_targets


def transform_bone(
    bone,
    el_type,
    transform_m,
    transform_m_inv,
    world_rot,
    bone_head,
    bone_tail,
    bone_rot,
    bone_length,
    delta_to_apply,
    pivot_position,
    is_corner,
    event,
):
    # local to world space
    head = transform_m @ bone_head
    tail = transform_m @ bone_tail

    bone_rot = Quaternion(bone_rot)
    bone_rot.rotate(world_rot)

    # apply the rotation
    if el_type == "BOTH":
        if getattr(event, "handle_type", None) == "SCALE":
            head_pose = Pose(head, bone_rot, 1)
            tail_pose = Pose(tail, bone_rot, 1)
            head_pose.transform(delta_to_apply, pivot_position)
            tail_pose.transform(delta_to_apply, pivot_position)
            new_corner_pos, bone_rot = head_pose.position, head_pose.rotation
            bone_length = (head_pose.position - tail_pose.position).length
        else:
            bone_pose = Pose(head, bone_rot, bone_length)
            bone_pose.transform(delta_to_apply, pivot_position)
            new_corner_pos, bone_rot, bone_length = bone_pose.position, bone_pose.rotation, bone_pose.scale_factor
    else:
        if is_corner:
            twist_rot = get_twist(delta_to_apply.rotation, bone_rot)
            bone_rot.rotate(twist_rot)

        # calculate the bone orientation for representing the new leaf position
        prev_leaf_pos = head if el_type == "HEAD" else tail
        other_pos = tail if el_type == "HEAD" else head

        new_corner_pos = prev_leaf_pos + delta_to_apply.position
        a = prev_leaf_pos - other_pos
        b = new_corner_pos - other_pos
        norm = a.cross(b)
        angle = vec_signed_angle(a, b, norm)
        bone_rot.rotate(Quaternion(norm, -angle))

    # back to local space
    bone_rot.rotate(world_rot.inverted())
    new_corner_pos_local = transform_m_inv @ new_corner_pos
    new_head_local = bone_head if el_type == "TAIL" else new_corner_pos_local

    # apply the changes
    if el_type == "BOTH":
        bone.length = bone_length
    else:
        other_orig_local = Vector(bone_tail if el_type == "HEAD" else bone_head)
        bone.length = (new_corner_pos_local - other_orig_local).length

    bone.matrix = Matrix.LocRotScale(new_head_local, bone_rot, None)

    # hack to refresh the UI
    bone.tail = bone.tail


def get_twist(rot_to_apply, bone_rot):
    fwd = bone_rot @ VEC_FORWARD
    right = bone_rot @ VEC_RIGHT
    tr = rot_to_apply @ right

    sqr_mag = fwd.dot(fwd)
    dot = tr.dot(fwd)
    projected_right = tr - fwd * dot / sqr_mag
    return right.rotation_difference(projected_right)


def on_joystick_vertical(self, event_name, event):
    tool_settings = bpy.context.scene.tool_settings
    if not tool_settings.use_proportional_edit:
        return

    p_size = "proportional_distance" if hasattr(tool_settings, "proportional_distance") else "proportional_size"

    proportional_size = getattr(tool_settings, p_size)
    proportional_size += event.value * 0.01
    setattr(tool_settings, p_size, proportional_size)


def get_selected_elements(elements=None):
    ob = bpy.context.view_layer.objects.active
    if elements is None:
        if ob is None:
            return set()

        if ob.mode == "OBJECT":
            if hasattr(bpy.context, "selected_objects"):
                return set(bpy.context.selected_objects)

            return set(o for o in bpy.context.scene.objects if o.select_get(view_layer=bpy.context.view_layer))
        elif ob.mode in ("EDIT", "POSE"):
            if ob.type == "MESH":
                elements = get_bmesh_elements(ob)
            elif ob.type == "CURVE":
                curve = ob.data
                if len(curve.splines) == 0:
                    return set()

                elements = curve.splines[0].points
            elif ob.type == "ARMATURE":
                elements = ob.data.edit_bones if ob.mode == "EDIT" else ob.pose.bones
                elements = set((bone.name, "") for bone in elements)

    el_list = list(elements)
    if isinstance(el_list[0], Object):
        return {e for e in elements if e.select_get()}

    if ob.type == "ARMATURE" and ob.mode in ("EDIT", "POSE"):
        selected_bones = set()
        for bone_name, el_type in elements:
            main_bone = ob.pose.bones[bone_name].bone if ob.mode == "POSE" else ob.data.edit_bones[bone_name]
            if el_type in ("", "BOTH") and (main_bone.select or (main_bone.select_head and main_bone.select_tail)):
                selected_bones.add((bone_name, "BOTH"))
            elif el_type in ("", "HEAD") and main_bone.select_head:
                selected_bones.add((bone_name, "HEAD"))
            elif el_type in ("", "TAIL") and main_bone.select_tail:
                selected_bones.add((bone_name, "TAIL"))
        return selected_bones

    return {e for e in elements if e.select}


def dispatch_event(self, event_name, event):
    event = event.clone()
    event.type = event_name

    if self.mode == "OBJECT":
        event.targets = list(transform_state["transform_elements"])
        event.sub_targets = None
    elif self.mode == "EDIT" and self.type == "ARMATURE":
        sub_targets = set()
        for bone, el_type in transform_state["transform_elements"]:
            sub_targets.add((bone.name, el_type))
            if el_type in ("BOTH", "HEAD") and bone.use_connect:
                if bone.parent:
                    if (bone.parent.name, "BOTH") not in sub_targets:
                        sub_targets.add((bone.parent.name, "TAIL"))

                    for sibling in bone.parent.children:
                        if (sibling.name, "BOTH") not in sub_targets:
                            sub_targets.add((sibling.name, "HEAD"))

            if el_type in ("BOTH", "TAIL"):
                for child in bone.children:
                    if (child.name, "BOTH") not in sub_targets and child.use_connect:
                        sub_targets.add((child.name, "HEAD"))

        sub_targets = [(self.data.edit_bones[bone_name], e) for bone_name, e in sub_targets]

        # de-duplicate
        both_bones = [bone for bone, el_type in sub_targets if el_type == "BOTH"]
        for bone in both_bones:
            if (bone, "HEAD") in sub_targets:
                sub_targets.remove((bone, "HEAD"))
            if (bone, "TAIL") in sub_targets:
                sub_targets.remove((bone, "TAIL"))

        event.sub_targets = sub_targets
    else:
        event.sub_targets = transform_state["transform_elements"]

    for target in event.targets:
        target.dispatch_event(event_name, event)


def allow_transform(event):
    return settings["gizmo.transform_handles.type"] is None or getattr(event, "is_handle_drag", False)


# https://devtalk.blender.org/t/bpy-ops-transform-rotate-option-axis/6235/9
def create_z_orient(rot_vec):
    x_dir_p = Vector((1.0, 0.0, 0.0))
    y_dir_p = Vector((0.0, 1.0, 0.0))
    z_dir_p = Vector((0.0, 0.0, 1.0))
    tol = 0.001
    rx, ry, rz = rot_vec
    if isclose(rx, 0.0, abs_tol=tol) and isclose(ry, 0.0, abs_tol=tol):
        if isclose(rz, 0.0, abs_tol=tol) or isclose(rz, 1.0, abs_tol=tol):
            return Matrix((x_dir_p, y_dir_p, z_dir_p))  # 3x3 identity
    new_z = rot_vec.copy()  # rot_vec already normalized
    new_y = new_z.cross(z_dir_p)
    new_y_eq_0_0_0 = True
    for v in new_y:
        if not isclose(v, 0.0, abs_tol=tol):
            new_y_eq_0_0_0 = False
            break
    if new_y_eq_0_0_0:
        new_y = y_dir_p
    new_x = new_y.cross(new_z)
    new_x.normalize()
    new_y.normalize()
    return Matrix(((new_x.x, new_y.x, new_z.x), (new_x.y, new_y.y, new_z.y), (new_x.z, new_y.z, new_z.z)))
