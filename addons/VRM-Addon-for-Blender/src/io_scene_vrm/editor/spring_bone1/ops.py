import uuid
from collections.abc import Set as AbstractSet
from sys import float_info
from typing import TYPE_CHECKING

import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import Armature, Context, Operator

from .handler import reset_state, update_pose_bone_rotations


class VRM_OT_add_spring_bone1_collider(Operator):
    bl_idname = "vrm.add_spring_bone1_collider"
    bl_label = "Add Collider"
    bl_description = "Add VRM 1.0 Collider"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )

    def execute(self, context: Context) -> set[str]:
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}
        collider = armature_data.vrm_addon_extension.spring_bone1.colliders.add()
        collider.uuid = uuid.uuid4().hex
        collider.shape.sphere.radius = 0.125
        collider.reset_bpy_object(context, armature)
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        armature_name: str  # type: ignore[no-redef]


class VRM_OT_remove_spring_bone1_collider(Operator):
    bl_idname = "vrm.remove_spring_bone1_collider"
    bl_label = "Remove Collider"
    bl_description = "Remove VRM 0.x Collider"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )
    collider_index: IntProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        min=0,
    )

    def execute(self, _context: Context) -> set[str]:
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}
        spring_bone = armature_data.vrm_addon_extension.spring_bone1
        colliders = spring_bone.colliders
        if len(colliders) <= self.collider_index:
            return {"CANCELLED"}
        bpy_object = colliders[self.collider_index].bpy_object
        if bpy_object:
            remove_objects = [*bpy_object.children, bpy_object]
            for collection in bpy.data.collections:
                for remove_object in remove_objects:
                    remove_object.parent = None
                    if remove_object.name in collection.objects:
                        collection.objects.unlink(remove_object)
            for remove_object in remove_objects:
                if remove_object.users <= 1:
                    bpy.data.objects.remove(remove_object, do_unlink=True)

        collider_uuid = colliders[self.collider_index].uuid
        colliders.remove(self.collider_index)
        for collider_group in spring_bone.collider_groups:
            while True:
                removed = False
                for index, collider in enumerate(list(collider_group.colliders)):
                    if collider.collider_uuid != collider_uuid:
                        continue
                    collider_group.colliders.remove(index)
                    removed = True
                    break
                if not removed:
                    break

        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        armature_name: str  # type: ignore[no-redef]
        collider_index: int  # type: ignore[no-redef]


class VRM_OT_add_spring_bone1_spring(Operator):
    bl_idname = "vrm.add_spring_bone1_spring"
    bl_label = "Add Spring"
    bl_description = "Add VRM 1.0 Spring"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )

    def execute(self, _context: Context) -> set[str]:
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}
        spring = armature_data.vrm_addon_extension.spring_bone1.springs.add()
        spring.vrm_name = "Spring"
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        armature_name: str  # type: ignore[no-redef]


class VRM_OT_remove_spring_bone1_spring(Operator):
    bl_idname = "vrm.remove_spring_bone1_spring"
    bl_label = "Remove Spring"
    bl_description = "Remove VRM 1.0 Spring"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )
    spring_index: IntProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        min=0,
    )

    def execute(self, _context: Context) -> set[str]:
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}
        springs = armature_data.vrm_addon_extension.spring_bone1.springs
        if len(springs) <= self.spring_index:
            return {"CANCELLED"}
        springs.remove(self.spring_index)
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        armature_name: str  # type: ignore[no-redef]
        spring_index: int  # type: ignore[no-redef]


class VRM_OT_add_spring_bone1_collider_group(Operator):
    bl_idname = "vrm.add_spring_bone1_collider_group"
    bl_label = "Add Collider Group"
    bl_description = "Add VRM 1.0 Spring Bone Collider Group"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )

    def execute(self, _context: Context) -> set[str]:
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}
        collider_group = (
            armature_data.vrm_addon_extension.spring_bone1.collider_groups.add()
        )
        collider_group.vrm_name = "Collider Group"
        collider_group.uuid = uuid.uuid4().hex
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        armature_name: str  # type: ignore[no-redef]


class VRM_OT_remove_spring_bone1_collider_group(Operator):
    bl_idname = "vrm.remove_spring_bone1_collider_group"
    bl_label = "Remove Collider Group"
    bl_description = "Remove VRM 1.0 Spring Bone Collider Group"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )
    collider_group_index: IntProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        min=0,
    )

    def execute(self, _context: Context) -> set[str]:
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}
        spring_bone = armature_data.vrm_addon_extension.spring_bone1
        collider_groups = spring_bone.collider_groups
        if len(collider_groups) <= self.collider_group_index:
            return {"CANCELLED"}
        collider_group_uuid = collider_groups[self.collider_group_index].uuid
        collider_groups.remove(self.collider_group_index)
        for spring in spring_bone.springs:
            while True:
                removed = False
                for index, collider_group in enumerate(list(spring.collider_groups)):
                    if collider_group.collider_group_uuid != collider_group_uuid:
                        continue
                    spring.collider_groups.remove(index)
                    removed = True
                    break
                if not removed:
                    break
        for collider_group in collider_groups:
            collider_group.fix_index()

        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        armature_name: str  # type: ignore[no-redef]
        collider_group_index: int  # type: ignore[no-redef]


class VRM_OT_add_spring_bone1_collider_group_collider(Operator):
    bl_idname = "vrm.add_spring_bone1_collider_group_collider"
    bl_label = "Add Collider"
    bl_description = "Add VRM 1.0 Spring Bone Collider Group Collider"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )
    collider_group_index: IntProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        min=0,
    )

    def execute(self, _context: Context) -> set[str]:
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}
        collider_groups = armature_data.vrm_addon_extension.spring_bone1.collider_groups
        if len(collider_groups) <= self.collider_group_index:
            return {"CANCELLED"}
        collider_groups[self.collider_group_index].colliders.add()
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        armature_name: str  # type: ignore[no-redef]
        collider_group_index: int  # type: ignore[no-redef]


class VRM_OT_remove_spring_bone1_collider_group_collider(Operator):
    bl_idname = "vrm.remove_spring_bone1_collider_group_collider"
    bl_label = "Remove Collider"
    bl_description = "Remove VRM 1.0 Spring Bone Collider Group Collider"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )
    collider_group_index: IntProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        min=0,
    )
    collider_index: IntProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        min=0,
    )

    def execute(self, _context: Context) -> set[str]:
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}
        collider_groups = armature_data.vrm_addon_extension.spring_bone1.collider_groups
        if len(collider_groups) <= self.collider_group_index:
            return {"CANCELLED"}
        colliders = collider_groups[self.collider_group_index].colliders
        if len(colliders) <= self.collider_index:
            return {"CANCELLED"}
        colliders.remove(self.collider_index)
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        armature_name: str  # type: ignore[no-redef]
        collider_group_index: int  # type: ignore[no-redef]
        collider_index: int  # type: ignore[no-redef]


class VRM_OT_add_spring_bone1_spring_collider_group(Operator):
    bl_idname = "vrm.add_spring_bone1_spring_collider_group"
    bl_label = "Add Collider Group"
    bl_description = "Add VRM 1.0 Spring Bone Spring Collider Group"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )
    spring_index: IntProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        min=0,
    )

    def execute(self, _context: Context) -> set[str]:
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}
        springs = armature_data.vrm_addon_extension.spring_bone1.springs
        if len(springs) <= self.spring_index:
            return {"CANCELLED"}
        springs[self.spring_index].collider_groups.add()
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        armature_name: str  # type: ignore[no-redef]
        spring_index: int  # type: ignore[no-redef]


class VRM_OT_remove_spring_bone1_spring_collider_group(Operator):
    bl_idname = "vrm.remove_spring_bone1_spring_collider_group"
    bl_label = "Remove Collider Group"
    bl_description = "Remove VRM 1.0 Spring Bone Spring Collider Group"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )
    spring_index: IntProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        min=0,
    )
    collider_group_index: IntProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        min=0,
    )

    def execute(self, _context: Context) -> set[str]:
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}
        springs = armature_data.vrm_addon_extension.spring_bone1.springs
        if len(springs) <= self.spring_index:
            return {"CANCELLED"}
        collider_groups = springs[self.spring_index].collider_groups
        if len(collider_groups) <= self.collider_group_index:
            return {"CANCELLED"}
        collider_groups.remove(self.collider_group_index)
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        armature_name: str  # type: ignore[no-redef]
        spring_index: int  # type: ignore[no-redef]
        collider_group_index: int  # type: ignore[no-redef]


class VRM_OT_add_spring_bone1_spring_joint(Operator):
    bl_idname = "vrm.add_spring_bone1_spring_joint"
    bl_label = "Add Joint"
    bl_description = "Add VRM 1.0 Spring Bone Spring Joint"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )
    spring_index: IntProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        min=0,
    )
    guess_properties: BoolProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )

    def execute(self, _context: Context) -> set[str]:
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}
        springs = armature_data.vrm_addon_extension.spring_bone1.springs
        if len(springs) <= self.spring_index:
            return {"CANCELLED"}
        joints = springs[self.spring_index].joints
        joints.add()
        if not self.guess_properties:
            return {"FINISHED"}

        if len(joints) < 2:
            return {"FINISHED"}
        parent_joint, joint = joints[-2:]
        parent_bone = armature_data.bones.get(parent_joint.node.bone_name)
        if parent_bone and parent_bone.children:
            joint.node.set_bone_name(parent_bone.children[0].name)
        joint.hit_radius = parent_joint.hit_radius
        joint.stiffness = parent_joint.stiffness
        joint.gravity_power = parent_joint.gravity_power
        joint.gravity_dir = list(parent_joint.gravity_dir)
        joint.drag_force = parent_joint.drag_force
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        armature_name: str  # type: ignore[no-redef]
        spring_index: int  # type: ignore[no-redef]
        guess_properties: bool  # type: ignore[no-redef]


class VRM_OT_remove_spring_bone1_spring_joint(Operator):
    bl_idname = "vrm.remove_spring_bone1_spring_joint"
    bl_label = "Remove Joint"
    bl_description = "Remove VRM 1.0 Spring Bone Spring Joint"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )
    spring_index: IntProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        min=0,
    )
    joint_index: IntProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        min=0,
    )

    def execute(self, _context: Context) -> set[str]:
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}
        springs = armature_data.vrm_addon_extension.spring_bone1.springs
        if len(springs) <= self.spring_index:
            return {"CANCELLED"}
        joints = springs[self.spring_index].joints
        if len(joints) <= self.joint_index:
            return {"CANCELLED"}
        joints.remove(self.joint_index)
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        armature_name: str  # type: ignore[no-redef]
        spring_index: int  # type: ignore[no-redef]
        joint_index: int  # type: ignore[no-redef]


class VRM_OT_reset_spring_bone1_animation_state(Operator):
    bl_idname = "vrm.reset_spring_bone1_animation_state"
    bl_label = "Reset SpringBone Animation State"
    bl_description = "Reset SpringBone Animation State"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )

    def execute(self, _context: Context) -> set[str]:
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}
        for spring in armature_data.vrm_addon_extension.spring_bone1.springs:
            for joint in spring.joints:
                joint.animation_state.initialized_as_tail = False
        reset_state()
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        armature_name: str  # type: ignore[no-redef]


class VRM_OT_update_spring_bone1_animation(Operator):
    bl_idname = "vrm.update_spring_bone1_animation"
    bl_label = "Update SpringBone Animation"
    bl_description = "Update SpringBone Animation"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    delta_time: FloatProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )

    def execute(self, context: Context) -> set[str]:
        delta_time = self.delta_time
        if abs(delta_time) < float_info.epsilon:
            delta_time = context.scene.render.fps_base / float(context.scene.render.fps)
        update_pose_bone_rotations(delta_time)
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        delta_time: float  # type: ignore[no-redef]
