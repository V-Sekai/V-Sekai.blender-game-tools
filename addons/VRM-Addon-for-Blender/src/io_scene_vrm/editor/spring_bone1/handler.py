import datetime
from dataclasses import dataclass
from sys import float_info
from typing import Optional, Union
import time

import bpy
from bpy.app.handlers import persistent
from bpy.types import Armature, Object, PoseBone
from mathutils import Matrix, Quaternion, Vector

from .property_group import (
    SpringBone1ColliderPropertyGroup,
    SpringBone1JointPropertyGroup,
    SpringBone1SpringPropertyGroup,
)


@dataclass
class State:
    previous_datetime: Optional[datetime.datetime] = None


state = State()


def reset_state() -> None:
    state.previous_datetime = None


@dataclass(frozen=True)
class SphereWorldCollider:
    offset: Vector
    radius: float

    def calculate_collision(
        self, target: Vector, target_radius: float
    ) -> tuple[Vector, float]:
        diff = target - self.offset
        diff_length = diff.length
        if diff_length < float_info.epsilon:
            return Vector((0, 0, -1)), -0.01
        return diff / diff_length, diff_length - target_radius - self.radius


@dataclass(frozen=True)
class CapsuleWorldCollider:
    offset: Vector
    radius: float
    tail: Vector
    offset_to_tail_diff: Vector
    offset_to_tail_diff_length_squared: float

    def calculate_collision(
        self, target: Vector, target_radius: float
    ) -> tuple[Vector, float]:
        fallback_result = (Vector((0, 0, -1)), -0.01)

        if abs(self.offset_to_tail_diff_length_squared) < float_info.epsilon:
            return fallback_result

        offset_to_target_diff = target - self.offset

        # offsetとtailを含む直線上で、targetまでの最短の点を
        # self.offset + (self.tail - self.offset) * offset_to_tail_ratio_for_nearest
        # という式で表すためのoffset_to_tail_ratio_for_nearestを求める
        offset_to_tail_ratio_for_nearest = (
            self.offset_to_tail_diff.dot(offset_to_target_diff)
            / self.offset_to_tail_diff_length_squared
        )

        # offsetからtailまでの線分の始点が0で終点が1なので、範囲外は切り取る
        offset_to_tail_ratio_for_nearest = max(
            0, min(1, offset_to_tail_ratio_for_nearest)
        )

        # targetまでの最短の点を計算し、衝突判定
        nearest = (
            self.offset + self.offset_to_tail_diff * offset_to_tail_ratio_for_nearest
        )
        nearest_to_target_diff = target - nearest
        nearest_to_target_diff_length = nearest_to_target_diff.length
        if nearest_to_target_diff_length < float_info.epsilon:
            return fallback_result
        return (
            nearest_to_target_diff / nearest_to_target_diff_length,
            nearest_to_target_diff_length - target_radius - self.radius,
        )


# https://github.com/vrm-c/vrm-specification/tree/993a90a5bda9025f3d9e2923ad6dea7506f88553/specification/VRMC_springBone-1.0#update-procedure
def update_pose_bone_rotations(delta_time: float) -> None:
    pose_bone_and_rotations: list[tuple[PoseBone, Quaternion]] = []

    for obj in [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]:
        # print(f"Processing object: {obj.name}")
        calculate_object_pose_bone_rotations(delta_time, obj, pose_bone_and_rotations)

    for pose_bone, pose_bone_rotation in pose_bone_and_rotations:
        # print(f"Updating pose bone rotation: {pose_bone.name}")
        if pose_bone.rotation_mode != "QUATERNION":
            pose_bone.rotation_mode = "QUATERNION"

        # pose_bone.rotation_quaternionの代入は負荷が高いのでできるだけ実行しない
        angle_diff = pose_bone_rotation.rotation_difference(
            pose_bone.rotation_quaternion
        ).angle
        if abs(angle_diff) < float_info.epsilon:
            continue
        pose_bone.rotation_quaternion = pose_bone_rotation


def calculate_object_pose_bone_rotations(
    delta_time: float,
    obj: Object,
    pose_bone_and_rotations: list[tuple[PoseBone, Quaternion]],
) -> None:
    if obj.type != "ARMATURE":
        # print(f"Skipping non-armature object: {obj.name}")
        return
    armature_data = obj.data
    if not isinstance(armature_data, Armature):
        # print(f"Invalid armature data for object: {obj.name}")
        return
    ext = armature_data.vrm_addon_extension
    if not ext.is_vrm1():
        # print(f"Skipping non-VRM1 armature: {obj.name}")
        return
    spring_bone1 = ext.spring_bone1
    if not spring_bone1.enable_animation:
        # print(f"Spring bone animation disabled for armature: {obj.name}")
        return

    collider_uuid_to_world_collider: dict[
        str, Union[SphereWorldCollider, CapsuleWorldCollider]
    ] = {}
    for collider in spring_bone1.colliders:
        pose_bone = obj.pose.bones.get(collider.node.bone_name)
        if not pose_bone:
            # print(f"Collider pose bone not found: {collider.node.bone_name}")
            continue
        pose_bone_world_matrix = obj.matrix_world @ pose_bone.matrix

        if collider.shape_type == SpringBone1ColliderPropertyGroup.SHAPE_TYPE_SPHERE:
            offset = pose_bone_world_matrix @ Vector(collider.shape.sphere.offset)
            radius = collider.shape.sphere.radius
            collider_uuid_to_world_collider[collider.uuid] = SphereWorldCollider(
                offset=offset,
                radius=radius,
            )
        elif collider.shape_type == SpringBone1ColliderPropertyGroup.SHAPE_TYPE_CAPSULE:
            offset = pose_bone_world_matrix @ Vector(collider.shape.capsule.offset)
            tail = pose_bone_world_matrix @ Vector(collider.shape.capsule.tail)
            radius = collider.shape.sphere.radius
            offset_to_tail_diff = tail - offset
            collider_uuid_to_world_collider[collider.uuid] = CapsuleWorldCollider(
                offset=offset,
                radius=radius,
                tail=tail,
                offset_to_tail_diff=offset_to_tail_diff,
                offset_to_tail_diff_length_squared=offset_to_tail_diff.length_squared,
            )

    collider_group_uuid_to_world_colliders: dict[
        str, list[Union[SphereWorldCollider, CapsuleWorldCollider]]
    ] = {}
    for collider_group in spring_bone1.collider_groups:
        for collider_reference in collider_group.colliders:
            world_collider = collider_uuid_to_world_collider.get(
                collider_reference.collider_uuid
            )
            if world_collider is None:
                # print(f"Collider reference not found: {collider_reference.collider_uuid}")
                continue
            world_colliders = collider_group_uuid_to_world_colliders.get(
                collider_group.uuid
            )
            if world_colliders is None:
                world_colliders = []
                collider_group_uuid_to_world_colliders[collider_group.uuid] = (
                    world_colliders
                )
            world_colliders.append(world_collider)

    for spring in spring_bone1.springs:
        # print(f"Processing spring: {spring.name}")
        joints = spring.joints
        if not joints:
            # print("No joints found for spring")
            continue
        first_joint = joints[0]
        first_pose_bone = obj.pose.bones.get(first_joint.node.bone_name)
        if not first_pose_bone:
            # print(f"First joint pose bone not found: {first_joint.node.bone_name}")
            continue

        center_pose_bone = obj.pose.bones.get(spring.center.bone_name)

        # https://github.com/vrm-c/vrm-specification/blob/7279e169ac0dcf37e7d81b2adcad9107101d7e25/specification/VRMC_springBone-1.0/README.md#center-space
        center_pose_bone_is_ancestor_of_first_pose_bone = False
        ancestor_of_first_pose_bone: Optional[PoseBone] = first_pose_bone
        while ancestor_of_first_pose_bone:
            if center_pose_bone == ancestor_of_first_pose_bone:
                center_pose_bone_is_ancestor_of_first_pose_bone = True
                break
            ancestor_of_first_pose_bone = ancestor_of_first_pose_bone.parent
        if not center_pose_bone_is_ancestor_of_first_pose_bone:
            # print("Center pose bone is not an ancestor of the first joint pose bone")
            center_pose_bone = None

        if center_pose_bone:
            current_center_world_translation = (
                obj.matrix_world @ center_pose_bone.matrix
            ).to_translation()
            previous_center_world_translation = Vector(
                spring.animation_state.previous_center_world_translation
            )
            previous_to_current_center_world_translation = (
                current_center_world_translation - previous_center_world_translation
            )
            if not spring.animation_state.use_center_space:
                spring.animation_state.previous_center_world_translation = (
                    current_center_world_translation.copy()
                )
                spring.animation_state.use_center_space = True
        else:
            current_center_world_translation = Vector((0, 0, 0))
            previous_to_current_center_world_translation = Vector((0, 0, 0))
            if spring.animation_state.use_center_space:
                spring.animation_state.use_center_space = False

        calculate_spring_pose_bone_rotations(
            delta_time,
            obj,
            spring,
            pose_bone_and_rotations,
            collider_group_uuid_to_world_colliders,
            previous_to_current_center_world_translation,
        )

        spring.animation_state.previous_center_world_translation = (
            current_center_world_translation
        )


def calculate_spring_pose_bone_rotations(
    delta_time: float,
    obj: Object,
    spring: SpringBone1SpringPropertyGroup,
    pose_bone_and_rotations: list[tuple[PoseBone, Quaternion]],
    collider_group_uuid_to_world_colliders: dict[
        str, list[Union[SphereWorldCollider, CapsuleWorldCollider]]
    ],
    previous_to_current_center_world_translation: Optional[Vector],
) -> None:
    inputs: list[
        tuple[
            SpringBone1JointPropertyGroup,
            PoseBone,
            Matrix,
            SpringBone1JointPropertyGroup,
            PoseBone,
            Matrix,
        ]
    ] = []

    joints: list[
        tuple[
            SpringBone1JointPropertyGroup,
            PoseBone,
            Matrix,
        ]
    ] = []
    for joint in spring.joints:
        bone_name = joint.node.bone_name
        pose_bone = obj.pose.bones.get(bone_name)
        if not pose_bone:
            continue
        rest_object_matrix = pose_bone.bone.convert_local_to_pose(
            Matrix(), pose_bone.bone.matrix_local
        )
        joints.append((joint, pose_bone, rest_object_matrix))

    for (head_joint, head_pose_bone, head_rest_object_matrix), (
        tail_joint,
        tail_pose_bone,
        tail_rest_object_matrix,
    ) in zip(joints, joints[1:]):
        inputs.append(
            (
                head_joint,
                head_pose_bone,
                head_rest_object_matrix,
                tail_joint,
                tail_pose_bone,
                tail_rest_object_matrix,
            )
        )

    world_colliders: list[Union[SphereWorldCollider, CapsuleWorldCollider]] = []
    for collider_group_reference in spring.collider_groups:
        collider_group_world_colliders = collider_group_uuid_to_world_colliders.get(
            collider_group_reference.collider_group_uuid
        )
        if not collider_group_world_colliders:
            continue
        world_colliders.extend(collider_group_world_colliders)

    center_pose_bone = obj.pose.bones.get(spring.center.bone_name)
    center_world_matrix = None
    if center_pose_bone:
        center_world_matrix = obj.matrix_world @ center_pose_bone.matrix

    next_head_pose_bone_before_rotation_matrix = None
    for (
        head_joint,
        head_pose_bone,
        head_rest_object_matrix,
        tail_joint,
        tail_pose_bone,
        tail_rest_object_matrix,
    ) in inputs:
        is_center_pose_bone_ancestor = False
        if center_pose_bone:
            current_pose_bone = head_pose_bone
            while current_pose_bone:
                if current_pose_bone == center_pose_bone:
                    is_center_pose_bone_ancestor = True
                    break
                current_pose_bone = current_pose_bone.parent

        (
            head_pose_bone_rotation,
            next_head_pose_bone_before_rotation_matrix,
        ) = calculate_joint_pair_head_pose_bone_rotations(
            delta_time,
            obj,
            head_joint,
            head_pose_bone,
            head_rest_object_matrix,
            tail_joint,
            tail_pose_bone,
            tail_rest_object_matrix,
            next_head_pose_bone_before_rotation_matrix,
            world_colliders,
            center_world_matrix if is_center_pose_bone_ancestor else None,
            previous_to_current_center_world_translation if is_center_pose_bone_ancestor else None,
        )
        pose_bone_and_rotations.append((head_pose_bone, head_pose_bone_rotation))


def calculate_joint_pair_head_pose_bone_rotations(
    delta_time: float,
    obj: Object,
    head_joint: SpringBone1JointPropertyGroup,
    head_pose_bone: PoseBone,
    current_head_rest_object_matrix: Matrix,
    tail_joint: SpringBone1JointPropertyGroup,
    tail_pose_bone: PoseBone,
    current_tail_rest_object_matrix: Matrix,
    next_head_pose_bone_before_rotation_matrix: Optional[Matrix],
    world_colliders: list[Union[SphereWorldCollider, CapsuleWorldCollider]],
    center_world_matrix: Optional[Matrix],
    previous_to_current_center_world_translation: Optional[Vector],
) -> tuple[Quaternion, Matrix]:
    current_head_pose_bone_matrix = head_pose_bone.matrix
    current_tail_pose_bone_matrix = tail_pose_bone.matrix

    if next_head_pose_bone_before_rotation_matrix is None:
        if head_pose_bone.parent:
            current_head_parent_matrix = head_pose_bone.parent.matrix
            current_head_parent_rest_object_matrix = head_pose_bone.parent.bone.convert_local_to_pose(Matrix(), head_pose_bone.parent.bone.matrix_local)
        else:
            current_head_parent_matrix = Matrix()
            current_head_parent_rest_object_matrix = Matrix()
        next_head_pose_bone_before_rotation_matrix = current_head_parent_matrix @ (current_head_parent_rest_object_matrix.inverted_safe() @ current_head_rest_object_matrix)

    next_head_world_translation = (obj.matrix_world @ next_head_pose_bone_before_rotation_matrix.to_translation())

    if not tail_joint.animation_state.initialized_as_tail:
        initial_tail_world_translation = (obj.matrix_world @ current_tail_pose_bone_matrix).to_translation()
        tail_joint.animation_state.initialized_as_tail = True
        tail_joint.animation_state.previous_world_translation = initial_tail_world_translation
        tail_joint.animation_state.current_world_translation = initial_tail_world_translation

    previous_tail_world_translation = Vector(tail_joint.animation_state.previous_world_translation)
    current_tail_world_translation = Vector(tail_joint.animation_state.current_world_translation)

    if center_world_matrix is not None:
        if previous_to_current_center_world_translation is not None:
            previous_tail_world_translation += previous_to_current_center_world_translation
            current_tail_world_translation += previous_to_current_center_world_translation
        else:
            previous_tail_world_translation = center_world_matrix.inverted_safe() @ previous_tail_world_translation
            current_tail_world_translation = center_world_matrix.inverted_safe() @ current_tail_world_translation

    inertia = (current_tail_world_translation - previous_tail_world_translation) * (1.0 - head_joint.drag_force)

    parent_rotation = head_pose_bone.parent.matrix.to_quaternion() if head_pose_bone.parent else Quaternion()
    stiffness_direction = (current_head_rest_object_matrix.inverted_safe() @ current_tail_rest_object_matrix.to_translation())
    stiffness = (obj.matrix_world.to_quaternion() @ next_head_pose_bone_before_rotation_matrix.to_quaternion() @ stiffness_direction).normalized() * head_joint.stiffness * delta_time

    external = Vector(head_joint.gravity_dir) * head_joint.gravity_power * delta_time

    next_tail_world_translation = current_tail_world_translation + inertia + stiffness + external

    head_to_tail_world_distance = (obj.matrix_world @ current_head_pose_bone_matrix.to_translation() - (obj.matrix_world @ current_tail_pose_bone_matrix.to_translation())).length
    next_tail_world_translation = next_head_world_translation + (next_tail_world_translation - next_head_world_translation).normalized() * head_to_tail_world_distance

    for world_collider in world_colliders:
        direction, distance = world_collider.calculate_collision(next_tail_world_translation, head_joint.hit_radius)
        if distance >= 0:
            continue
        next_tail_world_translation = next_tail_world_translation - direction * distance
        next_tail_world_translation = next_head_world_translation + (next_tail_world_translation - next_head_world_translation).normalized() * head_to_tail_world_distance

    next_head_rotation_start_target_local_translation = current_head_rest_object_matrix.inverted_safe() @ current_tail_rest_object_matrix.to_translation()
    next_head_rotation_end_target_local_translation = next_head_pose_bone_before_rotation_matrix.inverted_safe() @ (obj.matrix_world.inverted_safe() @ next_tail_world_translation)
    next_head_pose_bone_rotation = Quaternion(
        next_head_rotation_start_target_local_translation.cross(next_head_rotation_end_target_local_translation),
        next_head_rotation_start_target_local_translation.angle(next_head_rotation_end_target_local_translation, 0)
    )

    (next_head_pose_bone_translation, next_head_parent_pose_bone_object_rotation, next_head_pose_bone_scale) = next_head_pose_bone_before_rotation_matrix.decompose()
    next_head_pose_bone_object_rotation = next_head_parent_pose_bone_object_rotation @ next_head_pose_bone_rotation
    next_head_pose_bone_matrix = Matrix.Translation(next_head_pose_bone_translation) @ next_head_pose_bone_object_rotation.to_matrix().to_4x4() @ Matrix.Diagonal(next_head_pose_bone_scale).to_4x4()

    next_tail_pose_bone_before_rotation_matrix = next_head_pose_bone_matrix @ current_head_rest_object_matrix.inverted_safe() @ current_tail_rest_object_matrix

    if center_world_matrix is not None:
        tail_joint.animation_state.previous_world_translation = center_world_matrix @ current_tail_world_translation
        tail_joint.animation_state.current_world_translation = center_world_matrix @ next_tail_world_translation
    else:
        tail_joint.animation_state.previous_world_translation = current_tail_world_translation
        tail_joint.animation_state.current_world_translation = next_tail_world_translation

    return (
        next_head_pose_bone_rotation if head_pose_bone.bone.use_inherit_rotation else next_head_pose_bone_object_rotation,
        next_tail_pose_bone_before_rotation_matrix,
    )


@persistent
def depsgraph_update_pre(_dummy: object) -> None:
    state.previous_datetime = None


@persistent
def frame_change_pre(_dummy: object) -> None:
    state.previous_datetime = datetime.datetime.now(datetime.timezone.utc)
    delta_time = bpy.context.scene.render.fps_base / float(bpy.context.scene.render.fps)
    update_pose_bone_rotations(delta_time)

@persistent
def sixtyFPS(dummy: object) -> None:
    state.previous_datetime = datetime.datetime.now(datetime.timezone.utc)
    bpy.ops.wm.spring_bone_physics_operator('INVOKE_DEFAULT')
    

class SpringBonePhysicsModalOperator(bpy.types.Operator):
    """Operator which runs itself from a timer to update spring bone physics"""
    bl_idname = "wm.spring_bone_physics_operator"
    bl_label = "Spring Bone Physics Operator"

    _timer = None
    _last_time = None

    @persistent
    def modal(self, context, event):
        if event.type in {'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            current_time = time.time()
            if self._last_time is None:
                self._last_time = current_time
            delta_time = current_time - self._last_time
            if delta_time >= 0.0167:  # Update physics at 60 FPS
                self._last_time = current_time
                update_pose_bone_rotations(delta_time)

        return {'PASS_THROUGH'}

    def execute(self, context):
        self._last_time = None
        self._timer = context.window_manager.event_timer_add(0.0167, window=context.window) # 60 FPS
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        context.window_manager.event_timer_remove(self._timer)