from collections.abc import Callable, Sequence
from collections.abc import Set as AbstractSet
from math import radians
from sys import float_info
from typing import TYPE_CHECKING, Optional

import bmesh
import bpy
from bmesh.types import BMesh
from bpy.props import BoolProperty, FloatProperty, StringProperty
from bpy.types import Armature, Bone, Context, EditBone, Mesh, Object, Operator
from mathutils import Matrix, Vector

from ..common.version import addon_version
from ..common.vrm0.human_bone import HumanBoneSpecifications
from . import migration
from .vrm0.property_group import (
    Vrm0BlendShapeGroupPropertyGroup,
    Vrm0HumanoidPropertyGroup,
)

MIN_BONE_LENGTH = 0.00001  # 10μm
AUTO_BONE_CONNECTION_DISTANCE = 0.000001  # 1μm


class ICYP_OT_make_armature(Operator):
    bl_idname = "icyp.make_basic_armature"
    bl_label = "Add VRM Humanoid"
    bl_description = "Create armature along with a simple setup for VRM export"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    skip_heavy_armature_setup: BoolProperty(  # type: ignore[valid-type]
        default=False,
        options={"HIDDEN"},
    )

    #
    WIP_with_template_mesh: BoolProperty(  # type: ignore[valid-type]
        default=False
    )

    # 身長 at meter
    tall: FloatProperty(  # type: ignore[valid-type]
        default=1.70,
        min=0.3,
        step=1,
        name="Bone tall",
    )

    # 頭身
    head_ratio: FloatProperty(  # type: ignore[valid-type]
        default=8.0,
        min=4,
        step=5,
        description="height per heads",
    )

    head_width_ratio: FloatProperty(  # type: ignore[valid-type]
        default=2 / 3,
        min=0.3,
        max=1.2,
        step=5,
        description="height per heads",
    )

    # 足-胴比率:0:子供、1:大人 に近くなる(低等身で有効)
    aging_ratio: FloatProperty(  # type: ignore[valid-type]
        default=0.5, min=0, max=1, step=10
    )

    # 目の奥み
    eye_depth: FloatProperty(  # type: ignore[valid-type]
        default=-0.03, min=-0.1, max=0, step=1
    )

    # 肩幅
    shoulder_in_width: FloatProperty(  # type: ignore[valid-type]
        default=0.05,
        min=0.01,
        step=1,
        description="Inner shoulder position",
    )

    shoulder_width: FloatProperty(  # type: ignore[valid-type]
        default=0.08,
        min=0.01,
        step=1,
        description="shoulder roll position",
    )

    # 腕長さ率
    arm_length_ratio: FloatProperty(  # type: ignore[valid-type]
        default=1, min=0.5, step=1
    )

    # 手
    hand_ratio: FloatProperty(  # type: ignore[valid-type]
        default=1, min=0.5, max=2.0, step=5
    )

    finger_1_2_ratio: FloatProperty(  # type: ignore[valid-type]
        default=0.75,
        min=0.5,
        max=1,
        step=1,
        description="proximal / intermediate",
    )

    finger_2_3_ratio: FloatProperty(  # type: ignore[valid-type]
        default=0.75,
        min=0.5,
        max=1,
        step=1,
        description="intermediate / distal",
    )

    nail_bone: BoolProperty(  # type: ignore[valid-type]
        default=False,
        description="may need for finger collider",
    )  # 指先の当たり判定として必要

    # 足
    leg_length_ratio: FloatProperty(  # type: ignore[valid-type]
        default=0.5,
        min=0.3,
        max=0.6,
        step=1,
        description="upper body/lower body",
    )

    leg_width_ratio: FloatProperty(  # type: ignore[valid-type]
        default=1, min=0.01, step=1
    )

    leg_size: FloatProperty(  # type: ignore[valid-type]
        default=0.26, min=0.05, step=1
    )

    custom_property_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"}
    )

    armature_obj: Optional[Object] = None

    def execute(self, context: Context) -> set[str]:
        if (
            context.view_layer.objects.active is not None
            and context.view_layer.objects.active.mode != "OBJECT"
        ):
            bpy.ops.object.mode_set(mode="OBJECT")
        self.armature_obj, compare_dict = self.make_armature(context)
        self.setup_as_vrm(self.armature_obj, compare_dict)
        if self.custom_property_name:
            self.armature_obj[self.custom_property_name] = True
        if self.WIP_with_template_mesh:
            IcypTemplateMeshMaker(context, self)
        return {"FINISHED"}

    def float_prop(self, name: str) -> float:
        prop = getattr(self, name)
        if not isinstance(prop, float):
            message = f"prop {name} is not float"
            raise TypeError(message)
        return prop

    def head_size(self) -> float:
        return self.float_prop("tall") / self.float_prop("head_ratio")

    def hand_size(self) -> float:
        return self.head_size() * 0.75 * self.float_prop("hand_ratio")

    def make_armature(self, context: Context) -> tuple[Object, dict[str, str]]:
        bpy.ops.object.add(type="ARMATURE", enter_editmode=True, location=(0, 0, 0))
        armature = context.object
        if not armature:
            message = "armature is not created"
            raise ValueError(message)
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            message = "armature data is not an Armature"
            raise TypeError(message)
        armature_data.vrm_addon_extension.addon_version = addon_version()

        bone_dict = {}

        def bone_add(
            name: str,
            head_pos: Vector,
            tail_pos: Vector,
            parent_bone: Optional[EditBone] = None,
            radius: float = 0.1,
            roll: float = 0,
        ) -> EditBone:
            armature_data = armature.data
            if not isinstance(armature_data, Armature):
                message = "armature data is not an Armature"
                raise TypeError(message)
            added_bone = armature_data.edit_bones.new(name)
            added_bone.head = head_pos
            added_bone.tail = tail_pos
            added_bone.head_radius = radius
            added_bone.tail_radius = radius
            added_bone.envelope_distance = 0.01
            added_bone.roll = radians(roll)
            if parent_bone is not None:
                added_bone.parent = parent_bone
            bone_dict.update({name: added_bone})
            return added_bone

        # bone_type = "leg" or "arm" for roll setting
        def x_mirror_bones_add(
            base_name: str,
            right_head_pos: Vector,
            right_tail_pos: Vector,
            parent_bones: tuple[EditBone, EditBone],
            radius: float = 0.1,
            bone_type: str = "other",
        ) -> tuple[EditBone, EditBone]:
            right_roll = 0
            left_roll = 0
            if bone_type == "arm":
                right_roll = 180
            elif bone_type == "leg":
                right_roll = 90
                left_roll = 90
            left_bone = bone_add(
                base_name + ".L",
                right_head_pos,
                right_tail_pos,
                parent_bones[0],
                radius=radius,
                roll=left_roll,
            )

            head_pos = [pos * axis for pos, axis in zip(right_head_pos, (-1, 1, 1))]
            tail_pos = [pos * axis for pos, axis in zip(right_tail_pos, (-1, 1, 1))]
            right_bone = bone_add(
                base_name + ".R",
                Vector((head_pos[0], head_pos[1], head_pos[2])),
                Vector((tail_pos[0], tail_pos[1], tail_pos[2])),
                parent_bones[1],
                radius=radius,
                roll=right_roll,
            )

            return left_bone, right_bone

        def x_add(pos_a: Vector, add_x: float) -> Vector:
            pos = [p_a + _add for p_a, _add in zip(pos_a, [add_x, 0, 0])]
            return Vector((pos[0], pos[1], pos[2]))

        def y_add(pos_a: Vector, add_y: float) -> Vector:
            pos = [p_a + _add for p_a, _add in zip(pos_a, [0, add_y, 0])]
            return Vector((pos[0], pos[1], pos[2]))

        def z_add(pos_a: Vector, add_z: float) -> Vector:
            pos = [p_a + _add for p_a, _add in zip(pos_a, [0, 0, add_z])]
            return Vector((pos[0], pos[1], pos[2]))

        head_size = self.head_size()
        # down side (前は8頭身の時の股上/股下の股下側割合、
        # 後ろは4頭身のときの〃を年齢具合で線形補完)(股上高めにすると破綻する)
        eight_upside_ratio, four_upside_ratio = (
            1 - self.leg_length_ratio,
            (2.5 / 4) * (1 - self.aging_ratio)
            + (1 - self.leg_length_ratio) * self.aging_ratio,
        )
        hip_up_down_ratio = (
            eight_upside_ratio * (1 - (8 - self.head_ratio) / 4)
            + four_upside_ratio * (8 - self.head_ratio) / 4
        )
        # 体幹
        # 股間
        body_separate = self.tall * (1 - hip_up_down_ratio)
        # 首の長さ
        neck_len = head_size * 2 / 3
        # 仙骨(骨盤脊柱基部)
        hips_tall = body_separate + head_size * 3 / 4
        # 胸椎・spineの全長 #首の1/3は顎の後ろに隠れてる
        backbone_len = self.tall - hips_tall - head_size - neck_len / 2
        # TODO: 胸椎と脊椎の割合の確認
        # 脊椎の基部に位置する主となる屈曲点と、胸郭基部に位置するもうひとつの屈曲点
        # by Humanoid Doc
        spine_len = backbone_len * 5 / 17

        root = bone_add("root", Vector((0, 0, 0)), Vector((0, 0, 0.3)))
        # 仙骨基部
        hips = bone_add(
            "hips",
            Vector((0, 0, body_separate)),
            Vector((0, 0, hips_tall)),
            root,
            roll=90,
        )
        # 骨盤基部->胸郭基部
        spine = bone_add(
            "spine", hips.tail, z_add(hips.tail, spine_len), hips, roll=-90
        )
        # 胸郭基部->首元
        chest = bone_add(
            "chest", spine.tail, z_add(hips.tail, backbone_len), spine, roll=-90
        )
        neck = bone_add(
            "neck",
            Vector((0, 0, self.tall - head_size - neck_len / 2)),
            Vector((0, 0, self.tall - head_size + neck_len / 2)),
            chest,
            roll=-90,
        )
        # 首の1/2は顎の後ろに隠れてる
        head = bone_add(
            "head",
            Vector((0, 0, self.tall - head_size + neck_len / 2)),
            Vector((0, 0, self.tall)),
            neck,
            roll=-90,
        )

        # 目
        eye_depth = self.eye_depth
        eyes = x_mirror_bones_add(
            "eye",
            Vector(
                (head_size * self.head_width_ratio / 5, 0, self.tall - head_size / 2)
            ),
            Vector(
                (
                    head_size * self.head_width_ratio / 5,
                    eye_depth,
                    self.tall - head_size / 2,
                )
            ),
            (head, head),
        )
        # 足
        leg_width = head_size / 4 * self.leg_width_ratio
        leg_size = self.leg_size

        leg_bone_length = (body_separate + head_size * 3 / 8 - self.tall * 0.05) / 2
        upside_legs = x_mirror_bones_add(
            "upper_leg",
            x_add(Vector((0, 0, body_separate + head_size * 3 / 8)), leg_width),
            x_add(
                Vector(
                    z_add(
                        Vector((0, 0, body_separate + head_size * 3 / 8)),
                        -leg_bone_length,
                    )
                ),
                leg_width,
            ),
            (hips, hips),
            radius=leg_width * 0.9,
            bone_type="leg",
        )
        lower_legs = x_mirror_bones_add(
            "lower_leg",
            upside_legs[0].tail,
            Vector((leg_width, 0, self.tall * 0.05)),
            upside_legs,
            radius=leg_width * 0.9,
            bone_type="leg",
        )
        foots = x_mirror_bones_add(
            "foot",
            lower_legs[0].tail,
            Vector((leg_width, -leg_size * (2 / 3), 0)),
            lower_legs,
            radius=leg_width * 0.9,
            bone_type="leg",
        )
        toes = x_mirror_bones_add(
            "toes",
            foots[0].tail,
            Vector((leg_width, -leg_size, 0)),
            foots,
            radius=leg_width * 0.5,
            bone_type="leg",
        )

        # 肩~指
        shoulder_in_pos = self.shoulder_in_width / 2

        shoulder_parent = chest
        shoulders = x_mirror_bones_add(
            "shoulder",
            x_add(shoulder_parent.tail, shoulder_in_pos),
            x_add(shoulder_parent.tail, shoulder_in_pos + self.shoulder_width),
            (shoulder_parent, shoulder_parent),
            radius=self.hand_size() * 0.4,
            bone_type="arm",
        )

        arm_length = (
            head_size
            * (1 * (1 - (self.head_ratio - 6) / 2) + 1.5 * ((self.head_ratio - 6) / 2))
            * self.arm_length_ratio
        )
        arms = x_mirror_bones_add(
            "upper_arm",
            shoulders[0].tail,
            x_add(shoulders[0].tail, arm_length),
            shoulders,
            radius=self.hand_size() * 0.4,
            bone_type="arm",
        )

        # グーにするとパーの半分くらいになる、グーのとき手を含む下腕の長さと上腕の長さが
        # 概ね一緒、けど手がでかすぎると破綻する
        forearm_length = max(arm_length - self.hand_size() / 2, arm_length * 0.8)
        forearms = x_mirror_bones_add(
            "lower_arm",
            arms[0].tail,
            x_add(arms[0].tail, forearm_length),
            arms,
            radius=self.hand_size() * 0.4,
            bone_type="arm",
        )
        hands = x_mirror_bones_add(
            "hand",
            forearms[0].tail,
            x_add(forearms[0].tail, self.hand_size() / 2),
            forearms,
            radius=self.hand_size() / 4,
            bone_type="arm",
        )

        def fingers(
            finger_name: str,
            proximal_pos: Vector,
            finger_len_sum: float,
        ) -> tuple[
            tuple[EditBone, EditBone],
            tuple[EditBone, EditBone],
            tuple[EditBone, EditBone],
        ]:
            finger_normalize = 1 / (
                self.finger_1_2_ratio * self.finger_2_3_ratio
                + self.finger_1_2_ratio
                + 1
            )
            proximal_finger_len = finger_len_sum * finger_normalize
            intermediate_finger_len = (
                finger_len_sum * finger_normalize * self.finger_1_2_ratio
            )
            distal_finger_len = (
                finger_len_sum
                * finger_normalize
                * self.finger_1_2_ratio
                * self.finger_2_3_ratio
            )
            proximal_bones = x_mirror_bones_add(
                f"{finger_name}_proximal",
                proximal_pos,
                x_add(proximal_pos, proximal_finger_len),
                hands,
                self.hand_size() / 18,
                bone_type="arm",
            )
            intermediate_bones = x_mirror_bones_add(
                f"{finger_name}_intermediate",
                proximal_bones[0].tail,
                x_add(proximal_bones[0].tail, intermediate_finger_len),
                proximal_bones,
                self.hand_size() / 18,
                bone_type="arm",
            )
            distal_bones = x_mirror_bones_add(
                f"{finger_name}_distal",
                intermediate_bones[0].tail,
                x_add(intermediate_bones[0].tail, distal_finger_len),
                intermediate_bones,
                self.hand_size() / 18,
                bone_type="arm",
            )
            if self.nail_bone:
                x_mirror_bones_add(
                    f"{finger_name}_nail",
                    distal_bones[0].tail,
                    x_add(distal_bones[0].tail, distal_finger_len),
                    distal_bones,
                    self.hand_size() / 20,
                    bone_type="arm",
                )
            return proximal_bones, intermediate_bones, distal_bones

        finger_y_offset = -self.hand_size() / 16
        thumbs = fingers(
            "thumb",
            y_add(hands[0].head, finger_y_offset * 3),
            self.hand_size() / 2,
        )

        mats = [
            Matrix.Translation(vec)
            for vec in [thumbs[0][i].matrix.translation for i in [0, 1]]
        ]
        for j in range(3):
            for n, angle in enumerate([-45, 45]):
                thumbs[j][n].transform(mats[n].inverted(), scale=False, roll=False)
                thumbs[j][n].transform(Matrix.Rotation(radians(angle), 4, "Z"))
                thumbs[j][n].transform(mats[n], scale=False, roll=False)
                thumbs[j][n].roll = [0, radians(180)][n]

        index_fingers = fingers(
            "index",
            y_add(hands[0].tail, finger_y_offset * 3),
            (self.hand_size() / 2) - (1 / 2.3125) * (self.hand_size() / 2) / 3,
        )
        middle_fingers = fingers(
            "middle", y_add(hands[0].tail, finger_y_offset), self.hand_size() / 2
        )
        ring_fingers = fingers(
            "ring",
            y_add(hands[0].tail, -finger_y_offset),
            (self.hand_size() / 2) - (1 / 2.3125) * (self.hand_size() / 2) / 3,
        )
        little_fingers = fingers(
            "little",
            y_add(hands[0].tail, -finger_y_offset * 3),
            ((self.hand_size() / 2) - (1 / 2.3125) * (self.hand_size() / 2) / 3)
            * ((1 / 2.3125) + (1 / 2.3125) * 0.75),
        )

        body_dict = {
            "hips": hips.name,
            "spine": spine.name,
            "chest": chest.name,
            "neck": neck.name,
            "head": head.name,
        }

        left_right_body_dict = {
            f"{left_right}{bone_name}": bones[lr].name
            for bone_name, bones in {
                "Eye": eyes,
                "UpperLeg": upside_legs,
                "LowerLeg": lower_legs,
                "Foot": foots,
                "Toes": toes,
                "Shoulder": shoulders,
                "UpperArm": arms,
                "LowerArm": forearms,
                "Hand": hands,
            }.items()
            for lr, left_right in enumerate(["left", "right"])
        }

        # VRM finger like name key
        fingers_dict = {
            f"{left_right}{finger_name}{position}": finger[i][lr].name
            for finger_name, finger in zip(
                ["Thumb", "Index", "Middle", "Ring", "Little"],
                [thumbs, index_fingers, middle_fingers, ring_fingers, little_fingers],
            )
            for i, position in enumerate(["Proximal", "Intermediate", "Distal"])
            for lr, left_right in enumerate(["left", "right"])
        }

        # VRM bone name : blender bone name
        bone_name_all_dict = {}
        bone_name_all_dict.update(body_dict)
        bone_name_all_dict.update(left_right_body_dict)
        bone_name_all_dict.update(fingers_dict)

        armature_data = armature.data
        if isinstance(armature_data, Armature):
            connect_parent_tail_and_child_head_if_very_close_position(armature_data)

        context.scene.view_layers.update()
        bpy.ops.object.mode_set(mode="OBJECT")
        context.scene.view_layers.update()
        return armature, bone_name_all_dict

    def setup_as_vrm(self, armature: Object, compare_dict: dict[str, str]) -> None:
        Vrm0HumanoidPropertyGroup.fixup_human_bones(armature)
        armature_data = armature.data
        if isinstance(armature_data, Armature) and not self.skip_heavy_armature_setup:
            for vrm_bone_name, bpy_bone_name in compare_dict.items():
                for (
                    human_bone
                ) in armature_data.vrm_addon_extension.vrm0.humanoid.human_bones:
                    if human_bone.bone == vrm_bone_name:
                        human_bone.node.set_bone_name(bpy_bone_name)
                        break
        self.make_extension_setting_and_metas(
            armature,
            offset_from_head_bone=(-self.eye_depth, self.head_size() / 6, 0),
        )
        if not self.skip_heavy_armature_setup:
            migration.migrate(armature.name, defer=False)

    @classmethod
    def make_extension_setting_and_metas(
        cls,
        armature: Object,
        offset_from_head_bone: tuple[float, float, float] = (0, 0, 0),
    ) -> None:
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return
        vrm0 = armature_data.vrm_addon_extension.vrm0
        vrm1 = armature_data.vrm_addon_extension.vrm1
        vrm0.first_person.first_person_bone.set_bone_name("head")
        vrm0.first_person.first_person_bone_offset = (0, 0, 0.06)
        vrm1.look_at.offset_from_head_bone = offset_from_head_bone
        vrm0.first_person.look_at_horizontal_inner.y_range = 8
        vrm0.first_person.look_at_horizontal_outer.y_range = 12
        vrm0.meta.author = "undefined"
        vrm0.meta.contact_information = "undefined"
        vrm0.meta.other_license_url = "undefined"
        vrm0.meta.other_permission_url = "undefined"
        vrm0.meta.reference = "undefined"
        vrm0.meta.title = "undefined"
        vrm0.meta.version = "undefined"
        for preset in Vrm0BlendShapeGroupPropertyGroup.presets:
            if preset.identifier == "unknown":
                continue
            blend_shape_group = vrm0.blend_shape_master.blend_shape_groups.add()
            blend_shape_group.name = preset.default_blend_shape_group_name
            blend_shape_group.preset_name = preset.identifier

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        skip_heavy_armature_setup: bool  # type: ignore[no-redef]
        WIP_with_template_mesh: bool  # type: ignore[no-redef]
        tall: float  # type: ignore[no-redef]
        head_ratio: float  # type: ignore[no-redef]
        head_width_ratio: float  # type: ignore[no-redef]
        aging_ratio: float  # type: ignore[no-redef]
        eye_depth: float  # type: ignore[no-redef]
        shoulder_in_width: float  # type: ignore[no-redef]
        shoulder_width: float  # type: ignore[no-redef]
        arm_length_ratio: float  # type: ignore[no-redef]
        hand_ratio: float  # type: ignore[no-redef]
        finger_1_2_ratio: float  # type: ignore[no-redef]
        finger_2_3_ratio: float  # type: ignore[no-redef]
        nail_bone: bool  # type: ignore[no-redef]
        leg_length_ratio: float  # type: ignore[no-redef]
        leg_width_ratio: float  # type: ignore[no-redef]
        leg_size: float  # type: ignore[no-redef]
        custom_property_name: str  # type: ignore[no-redef]


def connect_parent_tail_and_child_head_if_very_close_position(
    armature: Armature,
) -> None:
    bones = [bone for bone in armature.edit_bones if not bone.parent]
    while bones:
        bone = bones.pop()

        children_by_distance = sorted(
            bone.children,
            key=lambda child: (child.parent.tail - child.head).length_squared
            if child.parent
            else 0.0,
        )
        for child in children_by_distance:
            if (bone.tail - child.head).length < AUTO_BONE_CONNECTION_DISTANCE and (
                bone.head - child.head
            ).length >= MIN_BONE_LENGTH:
                bone.tail = child.head
            break

        bones.extend(bone.children)

    bones = [bone for bone in armature.edit_bones if not bone.parent]
    while bones:
        bone = bones.pop()
        for child in bone.children:
            if (bone.tail - child.head).length < float_info.epsilon:
                child.use_connect = True
            bones.append(child)


class IcypTemplateMeshMaker:
    def make_mesh_obj(
        self, context: Context, name: str, method: Callable[[Mesh], None]
    ) -> Object:
        mesh = bpy.data.meshes.new(name)
        method(mesh)
        obj = bpy.data.objects.new(name, mesh)
        scene = context.scene
        scene.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        bpy.ops.object.modifier_add(type="MIRROR")
        return obj

    def __init__(self, context: Context, args: ICYP_OT_make_armature) -> None:
        self.args = args
        self.head_size = args.tall / args.head_ratio
        self.make_mesh_obj(context, "Head", self.make_head)
        self.make_mesh_obj(context, "Body", self.make_humanoid)

    def get_humanoid_bone(self, bone: str) -> Bone:
        armature_obj = self.args.armature_obj
        if armature_obj is None:
            message = "armature obj is None"
            raise AssertionError(message)
        armature_data = armature_obj.data
        if not isinstance(armature_data, Armature):
            message = f"{type(armature_data)} is not a Armature"
            raise TypeError(message)

        tmp_dict = {
            v.bone: i
            for i, v in enumerate(
                armature_data.vrm_addon_extension.vrm0.humanoid.human_bones
            )
        }

        bone_name: str = armature_data.vrm_addon_extension.vrm0.humanoid.human_bones[
            tmp_dict[bone]
        ].node.bone_name
        humanoid_bone = armature_data.bones[bone_name]
        return humanoid_bone

    # ボーンマトリックスからY軸移動を打ち消して、あらためて欲しい高さ(上底が身長の高さ)
    # にする変換(matrixはYupだけど、bone座標系はZup)
    @staticmethod
    def head_bone_to_head_matrix(
        head_bone: Bone, head_tall_size: float, neck_depth_offset: float
    ) -> Matrix:
        return (
            head_bone.matrix_local
            @ Matrix(
                [
                    [1, 0, 0, 0],
                    [0, 1, 0, -head_bone.head_local[2]],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1],
                ]
            )
            @ Matrix.Translation(
                Vector([head_tall_size / 16, neck_depth_offset - head_tall_size, 0])
            )
        )

    def make_head(self, mesh: Mesh) -> None:
        args = self.args
        bm = bmesh.new()
        head_size = self.head_size

        head_bone = self.get_humanoid_bone("head")
        head_matrix = self.head_bone_to_head_matrix(head_bone, head_size, args.tall)
        self.make_half_trapezoid(
            bm,
            [head_size * 7 / 8, head_size * args.head_width_ratio],
            [head_size * 7 / 8, head_size * args.head_width_ratio],
            head_size,
            head_matrix,
        )
        bm.to_mesh(mesh)
        bm.free()

    def make_humanoid(self, mesh: Mesh) -> None:
        args = self.args
        armature_obj = args.armature_obj
        if armature_obj is None:
            message = "armature obj is None"
            raise AssertionError(message)
        armature_data = armature_obj.data
        if not isinstance(armature_data, Armature):
            message = f"{type(armature_data)} is not a Armature"
            raise TypeError(message)

        bm = bmesh.new()
        head_size = self.head_size
        # body

        # make neck
        neck_bone = self.get_humanoid_bone("neck")
        self.make_half_cube(
            bm, [head_size / 2, head_size / 2, neck_bone.length], neck_bone.head_local
        )
        # make chest - upper and lower (肋骨の幅の最大値で分割)
        chest_bone = self.get_humanoid_bone("chest")
        shoulder_in = args.shoulder_in_width
        left_upper_arm_bone = self.get_humanoid_bone("leftUpperArm")
        # upper chest shell
        self.make_half_trapezoid(
            bm,
            [head_size * 3 / 4, left_upper_arm_bone.head_local[0] * 2],
            [head_size * 3 / 4, shoulder_in],
            chest_bone.length,
            chest_bone.matrix_local,
        )
        # lower chest shell
        spine_bone = self.get_humanoid_bone("spine")
        self.make_half_trapezoid(
            bm,
            [head_size * 3 / 4, (left_upper_arm_bone.head_local[0] - shoulder_in) * 2],
            [head_size * 3 / 4, left_upper_arm_bone.head_local[0] * 2],
            spine_bone.length * 3 / 5,
            spine_bone.matrix_local
            @ Matrix.Translation(Vector([0, spine_bone.length * 2 / 5, 0])),
        )

        # make spine
        # make hips
        hips_bone = self.get_humanoid_bone("hips")
        hips_size = left_upper_arm_bone.head_local[0] * 2 * 1.2
        self.make_half_cube(
            bm, [hips_size, head_size * 3 / 4, hips_bone.length], hips_bone.head_local
        )

        # arm
        left_arm_bones = [
            self.get_humanoid_bone(v)
            for v in HumanBoneSpecifications.left_arm_req
            + HumanBoneSpecifications.left_arm_def
        ]
        left_hand_bone = self.get_humanoid_bone("leftHand")
        for b in left_arm_bones:
            base_xz = [
                b.head_radius if b != left_hand_bone else args.hand_size() / 2,
                b.head_radius,
            ]
            top_xz = [
                b.tail_radius if b != left_hand_bone else args.hand_size() / 2,
                b.tail_radius,
            ]
            self.make_trapezoid(
                bm, base_xz, top_xz, b.length, [0, 0, 0], b.matrix_local
            )
        # TODO: Thumb rotation

        # leg
        # TODO: ?
        left_leg_bones = [
            self.get_humanoid_bone(v)
            for v in HumanBoneSpecifications.left_leg_req
            + HumanBoneSpecifications.left_leg_def
        ]
        for b in left_leg_bones:
            bone_name = ""
            for k, v in armature_data.items():
                if v == b.name:
                    bone_name = k
                    break
            if bone_name == "":
                head_x = b.head_radius
                head_z = b.head_radius
                tail_x = b.head_radius
                tail_z = b.head_radius
            elif "UpperLeg" in bone_name:
                head_x = hips_size / 2
                head_z = hips_size / 2
                tail_x = 0.71 * hips_size / 2
                tail_z = 0.71 * hips_size / 2
            elif "LowerLeg" in bone_name:
                head_x = 0.71 * hips_size / 2
                head_z = 0.71 * hips_size / 2
                tail_x = 0.54 * hips_size / 2
                tail_z = 0.6 * hips_size / 2
            elif "Foot" in bone_name:
                head_x = 0.54 * hips_size / 2
                head_z = 0.6 * hips_size / 2
                tail_x = 0.81 * hips_size / 2
                tail_z = 0.81 * hips_size / 2
            elif "Toes" in bone_name:
                head_x = 0.81 * hips_size / 2
                head_z = 0.81 * hips_size / 2
                tail_x = 0.81 * hips_size / 2
                tail_z = 0.81 * hips_size / 2
            else:
                continue
            self.make_trapezoid(
                bm,
                [head_x, head_z],
                [tail_x, tail_z],
                b.length,
                [0, 0, 0],
                b.matrix_local,
            )

        bm.to_mesh(mesh)
        bm.free()

    def make_cube(
        self,
        bm: BMesh,
        xyz: list[float],
        translation: Optional[list[float]] = None,
        rot_matrix: Optional[Matrix] = None,
    ) -> None:
        points = self.cubic_points(xyz, translation, rot_matrix)
        verts = [bm.verts.new(p) for p in points]
        for poly in self.cube_loop:
            bm.faces.new([verts[i] for i in poly])

    def make_half_cube(
        self, bm: BMesh, xyz: Sequence[float], translation: Sequence[float]
    ) -> None:
        points = self.half_cubic_points(xyz, translation)
        verts = [bm.verts.new(p) for p in points]
        for poly in self.cube_loop_half:
            bm.faces.new([verts[i] for i in poly])

    def cubic_points(
        self,
        xyz: list[float],
        translation: Optional[list[float]] = None,
        rot_matrix: Optional[Matrix] = None,
    ) -> list[Vector]:
        if translation is None:
            translation = [0, 0, 0]
        if rot_matrix is None:
            rot_matrix = Matrix.Identity(4)
        x = xyz[0]
        y = xyz[1]
        z = xyz[2]
        tx = translation[0]
        ty = translation[1]
        tz = translation[2]
        points = (
            (-x / 2 + tx, -y / 2 + ty, 0 + tz),
            (-x / 2 + tx, y / 2 + ty, 0 + tz),
            (x / 2 + tx, y / 2 + ty, 0 + tz),
            (x / 2 + tx, -y / 2 + ty, 0 + tz),
            (-x / 2 + tx, -y / 2 + ty, z + tz),
            (-x / 2 + tx, y / 2 + ty, z + tz),
            (x / 2 + tx, y / 2 + ty, z + tz),
            (x / 2 + tx, -y / 2 + ty, z + tz),
        )

        return [rot_matrix @ Vector(p) for p in points]

    cube_loop = (
        [0, 1, 2, 3],
        [7, 6, 5, 4],
        [4, 5, 1, 0],
        [5, 6, 2, 1],
        [6, 7, 3, 2],
        [7, 4, 0, 3],
    )

    def half_cubic_points(
        self, xyz: Sequence[float], translation: Sequence[float]
    ) -> tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]:
        x = xyz[0]
        y = xyz[1]
        z = xyz[2]
        tx = translation[0]
        ty = translation[1]
        tz = translation[2]
        return (
            (0, -y / 2 + ty, 0 + tz),
            (0, y / 2 + ty, 0 + tz),
            (x / 2 + tx, y / 2 + ty, 0 + tz),
            (x / 2 + tx, -y / 2 + ty, 0 + tz),
            (0, -y / 2 + ty, z + tz),
            (0, y / 2 + ty, z + tz),
            (x / 2 + tx, y / 2 + ty, z + tz),
            (x / 2 + tx, -y / 2 + ty, z + tz),
        )

    cube_loop_half = (
        [0, 1, 2, 3],
        [7, 6, 5, 4],
        [5, 6, 2, 1],
        [6, 7, 3, 2],
        [7, 4, 0, 3],
    )

    def make_half_trapezoid(
        self,
        bm: BMesh,
        head_xz: list[float],
        tail_xz: list[float],
        height: float,
        matrix: Matrix,
    ) -> None:
        points = self.half_trapezoid_points(head_xz, tail_xz, height, matrix)
        verts = [bm.verts.new(p) for p in points]
        for poly in self.half_trapezoid_loop:
            bm.faces.new([verts[i] for i in poly])

    def half_trapezoid_points(
        self,
        head_xz: list[float],
        tail_xz: list[float],
        height: float,
        matrix: Optional[Matrix],
    ) -> list[Vector]:
        if matrix is None:
            matrix = Matrix.Identity(4)
        hx = head_xz[0]
        hz = head_xz[1]
        tx = tail_xz[0]
        tz = tail_xz[1]

        points = (
            (-hx / 2, 0, 0),  # 0
            (-hx / 2, 0, -hz / 2),  # 1
            (-tx / 2, height, -tz / 2),  # 2
            (-tx / 2, height, 0),  # 3
            (hx / 2, 0, -hz / 2),  # 4
            (hx / 2, 0, 0),  # 5
            (tx / 2, height, 0),  # 6
            (tx / 2, height, -tz / 2),  # 7
        )
        return [matrix @ Vector(p) for p in points]

    half_trapezoid_loop = (
        [3, 2, 1, 0],
        [7, 2, 3, 6],
        [6, 5, 4, 7],
        [7, 4, 1, 2],
        [5, 4, 1, 0],
    )

    def make_trapezoid(
        self,
        bm: BMesh,
        head_xz: list[float],
        tail_xz: list[float],
        height: float,
        translation: Optional[list[float]] = None,
        rot_matrix: Optional[Matrix] = None,
    ) -> None:
        points = self.trapezoid_points(
            head_xz, tail_xz, height, translation, rot_matrix
        )
        verts = [bm.verts.new(p) for p in points]
        for poly in self.trapezoid_poly_indices:
            bm.faces.new([verts[i] for i in poly])

    # 台形 軸方向高さ
    def trapezoid_points(
        self,
        head_xz: list[float],
        tail_xz: list[float],
        height: float,
        translation: Optional[list[float]] = None,
        rot_matrix: Optional[Matrix] = None,
    ) -> list[Vector]:
        if translation is None:
            translation = [0, 0, 0]
        if rot_matrix is None:
            rot_matrix = Matrix.Identity(4)
        hx = head_xz[0]
        hz = head_xz[1]
        tx = tail_xz[0]
        tz = tail_xz[1]

        tlx = translation[0]
        tly = translation[1]
        tlz = translation[2]
        points = (
            (-hx / 2 + tlx, tly, -hz / 2 + tlz),
            (hx / 2 + tlx, tly, -hz / 2 + tlz),
            (hx / 2 + tlx, tly, hz / 2 + tlz),
            (-hx / 2 + tlx, tly, hz / 2 + tlz),
            (-tx / 2 + tlx, height + tly, -tz / 2 + tlz),
            (tx / 2 + tlx, height + tly, -tz / 2 + tlz),
            (tx / 2 + tlx, height + tly, tz / 2 + tlz),
            (-tx / 2 + tlx, height + tly, tz / 2 + tlz),
        )

        return [rot_matrix @ Vector(p) for p in points]

    trapezoid_poly_indices = (
        [3, 2, 1, 0],
        [6, 5, 4, 7],
        [5, 1, 0, 4],
        [6, 2, 1, 5],
        [7, 3, 2, 6],
        [4, 0, 3, 7],
    )
