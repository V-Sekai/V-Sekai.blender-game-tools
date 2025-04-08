from collections.abc import Set as AbstractSet
from typing import Optional

import bpy
from bpy.app.translations import pgettext
from bpy.types import Armature, Context, Mesh, Object, Panel, UILayout

from ...common.logging import get_logger
from ...common.vrm1.human_bone import HumanBoneSpecifications
from .. import ops, search
from ..extension import VrmAddonSceneExtensionPropertyGroup
from ..migration import migrate
from ..ops import layout_operator
from ..panel import VRM_PT_vrm_armature_object_property
from ..search import active_object_is_vrm1_armature
from . import ops as vrm1_ops
from .property_group import (
    Vrm1CustomExpressionPropertyGroup,
    Vrm1ExpressionPropertyGroup,
    Vrm1ExpressionsPresetPropertyGroup,
    Vrm1ExpressionsPropertyGroup,
    Vrm1FirstPersonPropertyGroup,
    Vrm1HumanBonePropertyGroup,
    Vrm1HumanBonesPropertyGroup,
    Vrm1HumanoidPropertyGroup,
    Vrm1LookAtPropertyGroup,
    Vrm1MaterialColorBindPropertyGroup,
    Vrm1MetaPropertyGroup,
    Vrm1MorphTargetBindPropertyGroup,
    Vrm1TextureTransformBindPropertyGroup,
)
from .ui_list import (
    VRM_UL_vrm1_expression,
    VRM_UL_vrm1_material_color_bind,
    VRM_UL_vrm1_morph_target_bind,
    VRM_UL_vrm1_texture_transform_bind,
)

logger = get_logger(__name__)


def draw_vrm1_bone_prop_search(
    layout: UILayout,
    human_bone: Vrm1HumanBonePropertyGroup,
    icon: str,
) -> None:
    layout.prop_search(
        human_bone.node,
        "bone_name",
        human_bone,
        "node_candidates",
        text="",
        translate=False,
        icon=icon,
    )


def draw_vrm1_humanoid_required_bones_layout(
    human_bones: Vrm1HumanBonesPropertyGroup,
    layout: UILayout,
) -> None:
    split_factor = 0.2

    layout.label(text="VRM Required Bones", icon="ARMATURE_DATA")

    row = layout.row(align=True).split(factor=split_factor, align=True)
    column = row.column(align=True)
    column.label(text=HumanBoneSpecifications.HEAD.label)
    column.label(text=HumanBoneSpecifications.SPINE.label)
    column.label(text=HumanBoneSpecifications.HIPS.label)
    column = row.column(align=True)
    icon = "USER"
    draw_vrm1_bone_prop_search(column, human_bones.head, icon)
    draw_vrm1_bone_prop_search(column, human_bones.spine, icon)
    draw_vrm1_bone_prop_search(column, human_bones.hips, icon)

    row = layout.row(align=True).split(factor=split_factor, align=True)
    column = row.column(align=True)
    column.label(text="")
    column.label(text=HumanBoneSpecifications.LEFT_UPPER_ARM.label_no_left_right)
    column.label(text=HumanBoneSpecifications.LEFT_LOWER_ARM.label_no_left_right)
    column.label(text=HumanBoneSpecifications.LEFT_HAND.label_no_left_right)
    column.separator()
    column.label(text=HumanBoneSpecifications.LEFT_UPPER_LEG.label_no_left_right)
    column.label(text=HumanBoneSpecifications.LEFT_LOWER_LEG.label_no_left_right)
    column.label(text=HumanBoneSpecifications.LEFT_FOOT.label_no_left_right)

    column = row.column(align=True)
    column.label(text="Right")
    icon = "VIEW_PAN"
    draw_vrm1_bone_prop_search(column, human_bones.right_upper_arm, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_lower_arm, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_hand, icon)
    column.separator()
    icon = "MOD_DYNAMICPAINT"
    draw_vrm1_bone_prop_search(column, human_bones.right_upper_leg, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_lower_leg, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_foot, icon)

    column = row.column(align=True)
    column.label(text="Left")
    icon = "VIEW_PAN"
    draw_vrm1_bone_prop_search(column, human_bones.left_upper_arm, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_lower_arm, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_hand, icon)
    column.separator()
    icon = "MOD_DYNAMICPAINT"
    draw_vrm1_bone_prop_search(column, human_bones.left_upper_leg, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_lower_leg, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_foot, icon)


def draw_vrm1_humanoid_optional_bones_layout(
    human_bones: Vrm1HumanBonesPropertyGroup,
    layout: UILayout,
) -> None:
    split_factor = 0.2

    layout.label(text="VRM Optional Bones", icon="BONE_DATA")

    row = layout.row(align=True).split(factor=split_factor, align=True)
    icon = "HIDE_OFF"
    label_column = row.column(align=True)
    label_column.label(text="")
    label_column.label(text=HumanBoneSpecifications.LEFT_EYE.label_no_left_right)
    label_column.label(text=HumanBoneSpecifications.JAW.label)
    label_column.label(text=HumanBoneSpecifications.NECK.label)
    label_column.label(text=HumanBoneSpecifications.RIGHT_SHOULDER.label_no_left_right)
    label_column.label(text=HumanBoneSpecifications.UPPER_CHEST.label)
    label_column.label(text=HumanBoneSpecifications.CHEST.label)
    label_column.label(text=HumanBoneSpecifications.RIGHT_TOES.label_no_left_right)

    search_column = row.column(align=True)

    right_left_row = search_column.row(align=True)
    right_left_row.label(text="Right")
    right_left_row.label(text="Left")

    right_left_row = search_column.row(align=True)
    draw_vrm1_bone_prop_search(right_left_row, human_bones.right_eye, icon)
    draw_vrm1_bone_prop_search(right_left_row, human_bones.left_eye, icon)

    icon = "USER"
    draw_vrm1_bone_prop_search(search_column, human_bones.jaw, icon)
    draw_vrm1_bone_prop_search(search_column, human_bones.neck, icon)

    icon = "VIEW_PAN"
    right_left_row = search_column.row(align=True)
    draw_vrm1_bone_prop_search(right_left_row, human_bones.right_shoulder, icon)
    draw_vrm1_bone_prop_search(right_left_row, human_bones.left_shoulder, icon)

    icon = "USER"
    draw_vrm1_bone_prop_search(search_column, human_bones.upper_chest, icon)
    draw_vrm1_bone_prop_search(search_column, human_bones.chest, icon)

    icon = "MOD_DYNAMICPAINT"
    right_left_row = search_column.row(align=True)
    draw_vrm1_bone_prop_search(right_left_row, human_bones.right_toes, icon)
    draw_vrm1_bone_prop_search(right_left_row, human_bones.left_toes, icon)

    row = layout.row(align=True).split(factor=split_factor, align=True)
    column = row.column(align=True)
    column.label(text="", translate=False)
    column.label(text="Left Thumb:")
    column.label(text="Left Index:")
    column.label(text="Left Middle:")
    column.label(text="Left Ring:")
    column.label(text="Left Little:")
    column.separator()
    column.label(text="Right Thumb:")
    column.label(text="Right Index:")
    column.label(text="Right Middle:")
    column.label(text="Right Ring:")
    column.label(text="Right Little:")

    icon = "VIEW_PAN"
    column = row.column(align=True)
    column.label(text="Root")
    draw_vrm1_bone_prop_search(column, human_bones.left_thumb_metacarpal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_index_proximal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_middle_proximal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_ring_proximal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_little_proximal, icon)
    column.separator()
    draw_vrm1_bone_prop_search(column, human_bones.right_thumb_metacarpal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_index_proximal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_middle_proximal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_ring_proximal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_little_proximal, icon)

    column = row.column(align=True)
    column.label(text="", translate=False)
    draw_vrm1_bone_prop_search(column, human_bones.left_thumb_proximal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_index_intermediate, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_middle_intermediate, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_ring_intermediate, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_little_intermediate, icon)
    column.separator()
    draw_vrm1_bone_prop_search(column, human_bones.right_thumb_proximal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_index_intermediate, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_middle_intermediate, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_ring_intermediate, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_little_intermediate, icon)

    column = row.column(align=True)
    column.label(text="Tip")
    draw_vrm1_bone_prop_search(column, human_bones.left_thumb_distal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_index_distal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_middle_distal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_ring_distal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.left_little_distal, icon)
    column.separator()
    draw_vrm1_bone_prop_search(column, human_bones.right_thumb_distal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_index_distal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_middle_distal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_ring_distal, icon)
    draw_vrm1_bone_prop_search(column, human_bones.right_little_distal, icon)


def draw_vrm1_humanoid_layout(
    armature: Object,
    layout: UILayout,
    humanoid: Vrm1HumanoidPropertyGroup,
) -> None:
    if migrate(armature.name, defer=True):
        data = armature.data
        if not isinstance(data, Armature):
            return
        Vrm1HumanBonesPropertyGroup.update_all_node_candidates(data.name, defer=True)

    data = armature.data
    if not isinstance(data, Armature):
        return
    human_bones = humanoid.human_bones

    armature_box = layout

    t_pose_box = armature_box.box()
    column = t_pose_box.row().column()
    column.label(text="VRM T-Pose", icon="OUTLINER_OB_ARMATURE")
    if bpy.app.version < (3, 0):
        column.label(text="Pose Library")
    else:
        column.label(text="Pose Asset")
    column.prop_search(
        humanoid, "pose_library", bpy.data, "actions", text="", translate=False
    )
    if humanoid.pose_library and humanoid.pose_library.pose_markers:
        column.label(text="Pose")
        column.prop_search(
            humanoid,
            "pose_marker_name",
            humanoid.pose_library,
            "pose_markers",
            text="",
            translate=False,
        )

    bone_operator_column = layout.column()
    layout_operator(
        bone_operator_column,
        vrm1_ops.VRM_OT_assign_vrm1_humanoid_human_bones_automatically,
        icon="ARMATURE_DATA",
    ).armature_name = armature.name

    if ops.VRM_OT_simplify_vroid_bones.vroid_bones_exist(data):
        simplify_vroid_bones_op = layout_operator(
            armature_box,
            ops.VRM_OT_simplify_vroid_bones,
            text=pgettext(ops.VRM_OT_simplify_vroid_bones.bl_label),
            icon="GREASEPENCIL",
        )
        simplify_vroid_bones_op.armature_name = armature.name

    draw_vrm1_humanoid_required_bones_layout(human_bones, armature_box.box())
    draw_vrm1_humanoid_optional_bones_layout(human_bones, armature_box.box())

    non_humanoid_export_column = layout.column()
    non_humanoid_export_column.prop(human_bones, "allow_non_humanoid_rig")
    if human_bones.allow_non_humanoid_rig:
        non_humanoid_warnings_box = non_humanoid_export_column.box()
        non_humanoid_warnings_column = non_humanoid_warnings_box.column(align=True)
        text = pgettext(
            "VRMs exported as Non-Humanoid\n"
            + "Rigs can not have animations applied\n"
            + "for humanoid avatars."
        )
        for index, message in enumerate(pgettext(text).splitlines()):
            non_humanoid_warnings_column.label(
                text=message,
                translate=False,
                icon="ERROR" if index == 0 else "NONE",
            )


class VRM_PT_vrm1_humanoid_armature_object_property(Panel):
    bl_idname = "VRM_PT_vrm1_humanoid_armature_object_property"
    bl_label = "Humanoid"
    bl_translation_context = "VRM"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options: AbstractSet[str] = {"DEFAULT_CLOSED"}
    bl_parent_id = VRM_PT_vrm_armature_object_property.bl_idname

    @classmethod
    def poll(cls, context: Context) -> bool:
        return active_object_is_vrm1_armature(context)

    def draw_header(self, _context: Context) -> None:
        self.layout.label(icon="ARMATURE_DATA")

    def draw(self, context: Context) -> None:
        active_object = context.active_object
        if not active_object:
            return
        if active_object.type != "ARMATURE":
            return
        armature_data = active_object.data
        if not isinstance(armature_data, Armature):
            return
        draw_vrm1_humanoid_layout(
            active_object,
            self.layout,
            armature_data.vrm_addon_extension.vrm1.humanoid,
        )


class VRM_PT_vrm1_humanoid_ui(Panel):
    bl_idname = "VRM_PT_vrm1_humanoid_ui"
    bl_label = "Humanoid"
    bl_translation_context = "VRM"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VRM"
    bl_options: AbstractSet[str] = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return search.current_armature_is_vrm1(context)

    def draw_header(self, _context: Context) -> None:
        self.layout.label(icon="ARMATURE_DATA")

    def draw(self, context: Context) -> None:
        armature = search.current_armature(context)
        if not armature:
            return
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return
        draw_vrm1_humanoid_layout(
            armature, self.layout, armature_data.vrm_addon_extension.vrm1.humanoid
        )


def draw_vrm1_first_person_layout(
    armature: Object,
    context: Context,
    layout: UILayout,
    first_person: Vrm1FirstPersonPropertyGroup,
) -> None:
    if migrate(armature.name, defer=True):
        VrmAddonSceneExtensionPropertyGroup.check_mesh_object_names_and_update(
            context.scene.name
        )
    box = layout.box()
    column = box.column()
    column.label(text="Mesh Annotations", icon="FULLSCREEN_EXIT")
    for mesh_annotation_index, mesh_annotation in enumerate(
        first_person.mesh_annotations
    ):
        row = column.row(align=True)
        row.prop_search(
            mesh_annotation.node,
            "mesh_object_name",
            context.scene.vrm_addon_extension,
            "mesh_object_names",
            text="",
            translate=False,
            icon="OUTLINER_OB_MESH",
        )
        row.prop(mesh_annotation, "type", text="", translate=False)
        remove_mesh_annotation_op = layout_operator(
            row,
            vrm1_ops.VRM_OT_remove_vrm1_first_person_mesh_annotation,
            text="Remove",
            icon="REMOVE",
        )
        remove_mesh_annotation_op.armature_name = armature.name
        remove_mesh_annotation_op.mesh_annotation_index = mesh_annotation_index
    add_mesh_annotation_op = layout_operator(
        column, vrm1_ops.VRM_OT_add_vrm1_first_person_mesh_annotation
    )
    add_mesh_annotation_op.armature_name = armature.name


class VRM_PT_vrm1_first_person_armature_object_property(Panel):
    bl_idname = "VRM_PT_vrm1_first_person_armature_object_property"
    bl_label = "First Person"
    bl_translation_context = "VRM"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options: AbstractSet[str] = {"DEFAULT_CLOSED"}
    bl_parent_id = VRM_PT_vrm_armature_object_property.bl_idname

    @classmethod
    def poll(cls, context: Context) -> bool:
        return active_object_is_vrm1_armature(context)

    def draw_header(self, _context: Context) -> None:
        self.layout.label(icon="HIDE_OFF")

    def draw(self, context: Context) -> None:
        active_object = context.active_object
        if not active_object:
            return
        if active_object.type != "ARMATURE":
            return
        armature_data = active_object.data
        if not isinstance(armature_data, Armature):
            return
        draw_vrm1_first_person_layout(
            active_object,
            context,
            self.layout,
            armature_data.vrm_addon_extension.vrm1.first_person,
        )


class VRM_PT_vrm1_first_person_ui(Panel):
    bl_idname = "VRM_PT_vrm1_first_person_ui"
    bl_label = "First Person"
    bl_translation_context = "VRM"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VRM"
    bl_options: AbstractSet[str] = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return search.current_armature_is_vrm1(context)

    def draw_header(self, _context: Context) -> None:
        self.layout.label(icon="USER")

    def draw(self, context: Context) -> None:
        armature = search.current_armature(context)
        if not armature:
            return
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return
        draw_vrm1_first_person_layout(
            armature,
            context,
            self.layout,
            armature_data.vrm_addon_extension.vrm1.first_person,
        )


def draw_vrm1_look_at_layout(
    armature: Object,
    _context: Context,
    layout: UILayout,
    look_at: Vrm1LookAtPropertyGroup,
) -> None:
    migrate(armature.name, defer=True)

    layout.prop(look_at, "enable_preview")

    label_input_split = layout.split(factor=0.4)
    label_column = label_input_split.column()
    label_column.label(text="Preview Target:")
    label_column.label(text="Type:")
    input_column = label_input_split.column()
    input_column.prop(look_at, "preview_target_bpy_object", text="", translate=False)
    input_column.prop(look_at, "type", text="", translate=False)

    offset_from_head_bone_column = layout.column()
    offset_from_head_bone_column.label(text="Offset from Head Bone:")
    offset_from_head_bone_column.row().prop(
        look_at, "offset_from_head_bone", icon="BONE_DATA", text="", translate=False
    )

    column = layout.box().column(align=True)
    column.label(text="Range Map Horizontal Inner", icon="FULLSCREEN_EXIT")
    column.prop(look_at.range_map_horizontal_inner, "input_max_value")
    column.prop(look_at.range_map_horizontal_inner, "output_scale")
    column = layout.box().column(align=True)
    column.label(text="Range Map Horizontal Outer", icon="FULLSCREEN_ENTER")
    column.prop(look_at.range_map_horizontal_outer, "input_max_value")
    column.prop(look_at.range_map_horizontal_outer, "output_scale")
    column = layout.box().column(align=True)
    column.label(text="Range Map Vertical Up", icon="TRIA_UP")
    column.prop(look_at.range_map_vertical_up, "input_max_value")
    column.prop(look_at.range_map_vertical_up, "output_scale")
    column = layout.box().column(align=True)
    column.label(text="Range Map Vertical Down", icon="TRIA_DOWN")
    column.prop(look_at.range_map_vertical_down, "input_max_value")
    column.prop(look_at.range_map_vertical_down, "output_scale")


class VRM_PT_vrm1_look_at_armature_object_property(Panel):
    bl_idname = "VRM_PT_vrm1_look_at_armature_object_property"
    bl_label = "Look At"
    bl_translation_context = "VRM"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options: AbstractSet[str] = {"DEFAULT_CLOSED"}
    bl_parent_id = VRM_PT_vrm_armature_object_property.bl_idname

    @classmethod
    def poll(cls, context: Context) -> bool:
        return active_object_is_vrm1_armature(context)

    def draw_header(self, _context: Context) -> None:
        self.layout.label(icon="HIDE_OFF")

    def draw(self, context: Context) -> None:
        active_object = context.active_object
        if not active_object:
            return
        if active_object.type != "ARMATURE":
            return
        armature_data = active_object.data
        if not isinstance(armature_data, Armature):
            return
        draw_vrm1_look_at_layout(
            active_object,
            context,
            self.layout,
            armature_data.vrm_addon_extension.vrm1.look_at,
        )


class VRM_PT_vrm1_look_at_ui(Panel):
    bl_idname = "VRM_PT_vrm1_look_at_ui"
    bl_label = "Look At"
    bl_translation_context = "VRM"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VRM"
    bl_options: AbstractSet[str] = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return search.current_armature_is_vrm1(context)

    def draw_header(self, _context: Context) -> None:
        self.layout.label(icon="HIDE_OFF")

    def draw(self, context: Context) -> None:
        armature = search.current_armature(context)
        if not armature:
            return
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return
        draw_vrm1_look_at_layout(
            armature,
            context,
            self.layout,
            armature_data.vrm_addon_extension.vrm1.look_at,
        )


def draw_vrm1_expression_layout(
    armature: Object,
    context: Context,
    layout: UILayout,
    name: str,
    expression: Vrm1ExpressionPropertyGroup,
    custom_expression: Optional[Vrm1CustomExpressionPropertyGroup],
) -> None:
    blend_data = context.blend_data

    row = layout.row()
    row.alignment = "LEFT"
    row.prop(
        expression,
        "show_expanded",
        icon="TRIA_DOWN" if expression.show_expanded else "TRIA_RIGHT",
        emboss=False,
        text=name,
        translate=False,
    )
    if not expression.show_expanded:
        return

    box = layout.box().column()

    if custom_expression:
        box.row().prop(custom_expression, "custom_name")

    row = box.row()
    row.alignment = "LEFT"
    row.prop(
        expression,
        "show_expanded_morph_target_binds",
        icon="TRIA_DOWN"
        if expression.show_expanded_morph_target_binds
        else "TRIA_RIGHT",
        emboss=False,
    )
    if expression.show_expanded_morph_target_binds:
        VrmAddonSceneExtensionPropertyGroup.check_mesh_object_names_and_update(
            context.scene.name
        )
        for bind_index, bind in enumerate(expression.morph_target_binds):
            bind_box = box.box().column()
            bind_box.prop_search(
                bind.node,
                "mesh_object_name",
                context.scene.vrm_addon_extension,
                "mesh_object_names",
                text="Mesh",
                icon="OUTLINER_OB_MESH",
            )
            mesh_object = blend_data.objects.get(bind.node.mesh_object_name)
            if mesh_object:
                mesh_data = mesh_object.data
                if isinstance(mesh_data, Mesh):
                    shape_keys = mesh_data.shape_keys
                    if shape_keys:
                        bind_box.prop_search(
                            bind,
                            "index",
                            shape_keys,
                            "key_blocks",
                            text="Shape key",
                        )
            bind_box.prop(bind, "weight", slider=True)

            remove_morph_target_bind_op = layout_operator(
                bind_box,
                vrm1_ops.VRM_OT_remove_vrm1_expression_morph_target_bind,
                icon="REMOVE",
            )
            remove_morph_target_bind_op.armature_name = armature.name
            remove_morph_target_bind_op.expression_name = name
            remove_morph_target_bind_op.bind_index = bind_index

        add_morph_target_bind_op = layout_operator(
            box,
            vrm1_ops.VRM_OT_add_vrm1_expression_morph_target_bind,
            icon="ADD",
        )
        add_morph_target_bind_op.armature_name = armature.name
        add_morph_target_bind_op.expression_name = name

    row = box.row()
    row.alignment = "LEFT"
    row.prop(
        expression,
        "show_expanded_material_color_binds",
        icon="TRIA_DOWN"
        if expression.show_expanded_material_color_binds
        else "TRIA_RIGHT",
        emboss=False,
    )
    if expression.show_expanded_material_color_binds:
        for bind_index, bind in enumerate(expression.material_color_binds):
            bind_box = box.box().column()
            bind_box.prop_search(bind, "material", blend_data, "materials")
            bind_box.prop(bind, "type")
            target_value_split = bind_box.split(factor=0.5)
            target_value_split.label(text="Target Value:")
            if bind.type == "color":
                target_value_split.prop(bind, "target_value", text="", translate=False)
            else:
                target_value_split.prop(
                    bind, "target_value_as_rgb", text="", translate=False
                )

            remove_material_color_bind_op = layout_operator(
                bind_box,
                vrm1_ops.VRM_OT_remove_vrm1_expression_material_color_bind,
                icon="REMOVE",
            )
            remove_material_color_bind_op.armature_name = armature.name
            remove_material_color_bind_op.expression_name = name
            remove_material_color_bind_op.bind_index = bind_index
        add_material_color_bind_op = layout_operator(
            box,
            vrm1_ops.VRM_OT_add_vrm1_expression_material_color_bind,
            icon="ADD",
        )
        add_material_color_bind_op.armature_name = armature.name
        add_material_color_bind_op.expression_name = name

    row = box.row()
    row.alignment = "LEFT"
    row.prop(
        expression,
        "show_expanded_texture_transform_binds",
        icon="TRIA_DOWN"
        if expression.show_expanded_texture_transform_binds
        else "TRIA_RIGHT",
        emboss=False,
    )
    if expression.show_expanded_texture_transform_binds:
        for bind_index, bind in enumerate(expression.texture_transform_binds):
            bind_box = box.box().column()
            bind_box.prop_search(bind, "material", blend_data, "materials")
            bind_box.prop(bind, "scale")
            bind_box.prop(bind, "offset")

            remove_texture_transform_bind_op = layout_operator(
                bind_box,
                vrm1_ops.VRM_OT_remove_vrm1_expression_texture_transform_bind,
                icon="REMOVE",
            )
            remove_texture_transform_bind_op.armature_name = armature.name
            remove_texture_transform_bind_op.expression_name = name
            remove_texture_transform_bind_op.bind_index = bind_index
        add_texture_transform_bind_op = layout_operator(
            box,
            vrm1_ops.VRM_OT_add_vrm1_expression_texture_transform_bind,
            icon="ADD",
        )
        add_texture_transform_bind_op.armature_name = armature.name
        add_texture_transform_bind_op.expression_name = name

    box.prop(expression, "is_binary", icon="IPO_CONSTANT")
    box.prop(expression, "override_blink")
    box.prop(expression, "override_look_at")
    box.prop(expression, "override_mouth")

    if custom_expression:
        remove_custom_expression_op = layout_operator(
            box,
            vrm1_ops.VRM_OT_remove_vrm1_expressions_custom_expression,
            icon="REMOVE",
        )
        remove_custom_expression_op.armature_name = armature.name
        remove_custom_expression_op.custom_expression_name = name


def draw_vrm1_expressions_morph_target_bind_layout(
    context: Context,
    layout: UILayout,
    bind: Vrm1MorphTargetBindPropertyGroup,
) -> None:
    VrmAddonSceneExtensionPropertyGroup.check_mesh_object_names_and_update(
        context.scene.name
    )

    blend_data = context.blend_data

    bind_column = layout.column()
    bind_column.prop_search(
        bind.node,
        "mesh_object_name",
        context.scene.vrm_addon_extension,
        "mesh_object_names",
        text="Mesh",
        icon="OUTLINER_OB_MESH",
    )
    mesh_object = blend_data.objects.get(bind.node.mesh_object_name)
    if not mesh_object:
        return
    mesh = mesh_object.data
    if not isinstance(mesh, Mesh):
        return
    shape_keys = mesh.shape_keys
    if not shape_keys:
        return
    key_blocks = shape_keys.key_blocks
    if not key_blocks:
        return

    bind_column.prop_search(
        bind,
        "index",
        shape_keys,
        "key_blocks",
        text="Shape key",
    )
    bind_column.prop(bind, "weight", slider=True)


def draw_vrm1_expressions_material_color_bind_layout(
    context: Context,
    layout: UILayout,
    bind: Vrm1MaterialColorBindPropertyGroup,
) -> None:
    blend_data = context.blend_data

    bind_column = layout.column()
    bind_column.prop_search(bind, "material", blend_data, "materials")
    bind_column.prop(bind, "type")
    target_value_split = bind_column.split(factor=0.5)
    target_value_split.label(text="Target Value:")
    if bind.type == "color":
        target_value_split.prop(bind, "target_value", text="", translate=False)
    else:
        target_value_split.prop(bind, "target_value_as_rgb", text="", translate=False)


def draw_vrm1_expressions_texture_transform_bind_layout(
    context: Context,
    layout: UILayout,
    bind: Vrm1TextureTransformBindPropertyGroup,
) -> None:
    blend_data = context.blend_data

    bind_column = layout.column()
    bind_column.prop_search(bind, "material", blend_data, "materials")
    bind_column.prop(bind, "scale")
    bind_column.prop(bind, "offset")


def draw_vrm1_expressions_layout(
    armature: Object,
    context: Context,
    layout: UILayout,
    expressions: Vrm1ExpressionsPropertyGroup,
) -> None:
    if migrate(armature.name, defer=True):
        VrmAddonSceneExtensionPropertyGroup.check_mesh_object_names_and_update(
            context.scene.name
        )

    row = layout.row()
    row.template_list(
        VRM_UL_vrm1_expression.bl_idname,
        "",
        expressions,
        "expression_ui_list_elements",
        expressions,
        "active_expression_ui_list_element_index",
    )
    active_index = expressions.active_expression_ui_list_element_index

    list_side_column = row.column(align=True)

    add_custom_expression_op = layout_operator(
        list_side_column,
        vrm1_ops.VRM_OT_add_vrm1_expressions_custom_expression,
        icon="ADD",
        text="",
    )
    add_custom_expression_op.armature_name = armature.name
    add_custom_expression_op.custom_expression_name = "custom"

    preset_expressions = list(expressions.preset.name_to_expression_dict().values())
    custom_index = active_index - len(preset_expressions)

    if 0 <= active_index < len(preset_expressions):
        expression = preset_expressions[active_index]
        custom = False
    elif 0 <= custom_index < len(expressions.custom):
        custom = True
        expression = expressions.custom[custom_index]
        remove_custom_expression_op = layout_operator(
            list_side_column,
            vrm1_ops.VRM_OT_remove_vrm1_expressions_custom_expression,
            icon="REMOVE",
            text="",
        )
        remove_custom_expression_op.armature_name = armature.name
        remove_custom_expression_op.custom_expression_name = expression.custom_name

        list_side_column.separator()
        move_up_custom_expression_op = layout_operator(
            list_side_column,
            vrm1_ops.VRM_OT_move_up_vrm1_expressions_custom_expression,
            icon="TRIA_UP",
            text="",
        )
        move_up_custom_expression_op.armature_name = armature.name
        move_up_custom_expression_op.custom_expression_name = expression.custom_name

        move_down_custom_expression_op = layout_operator(
            list_side_column,
            vrm1_ops.VRM_OT_move_down_vrm1_expressions_custom_expression,
            icon="TRIA_DOWN",
            text="",
        )
        move_down_custom_expression_op.armature_name = armature.name
        move_down_custom_expression_op.custom_expression_name = expression.custom_name
    else:
        return

    box = layout.box()
    if custom:
        box.prop(expression, "custom_name")
    else:
        preset_icon = Vrm1ExpressionsPresetPropertyGroup.NAME_TO_ICON_DICT.get(
            expression.name
        )
        if not preset_icon:
            logger.error(f"Unknown preset expression: {expression.name}")
            preset_icon = "SHAPEKEY_DATA"
        box.label(text=expression.name, translate=False, icon=preset_icon)
    column = box.column()
    column.prop(expression, "preview", icon="PLAY", text="Preview")
    column.prop(expression, "is_binary", icon="IPO_CONSTANT")
    column.prop(expression, "override_blink")
    column.prop(expression, "override_look_at")
    column.prop(expression, "override_mouth")
    column.separator(factor=0.5)

    morph_target_binds_box = column.box()
    morph_target_binds_box.label(text="Morph Target Binds", icon="MESH_DATA")
    morph_target_binds_row = morph_target_binds_box.row()
    morph_target_binds_row.template_list(
        VRM_UL_vrm1_morph_target_bind.bl_idname,
        "",
        expression,
        "morph_target_binds",
        expression,
        "active_morph_target_bind_index",
    )

    active_morph_target_bind_index = expression.active_morph_target_bind_index
    morph_target_binds_side_column = morph_target_binds_row.column(align=True)

    add_morph_target_bind_op = layout_operator(
        morph_target_binds_side_column,
        vrm1_ops.VRM_OT_add_vrm1_expression_morph_target_bind,
        icon="ADD",
        text="",
    )
    add_morph_target_bind_op.armature_name = armature.name
    add_morph_target_bind_op.expression_name = expression.name

    if expression.morph_target_binds:
        remove_morph_target_bind_op = layout_operator(
            morph_target_binds_side_column,
            vrm1_ops.VRM_OT_remove_vrm1_expression_morph_target_bind,
            icon="REMOVE",
            text="",
        )
        remove_morph_target_bind_op.armature_name = armature.name
        remove_morph_target_bind_op.expression_name = expression.name
        remove_morph_target_bind_op.bind_index = active_morph_target_bind_index

        morph_target_binds_side_column.separator()

        move_up_morph_target_bind_op = layout_operator(
            morph_target_binds_side_column,
            vrm1_ops.VRM_OT_move_up_vrm1_expression_morph_target_bind,
            icon="TRIA_UP",
            text="",
        )
        move_up_morph_target_bind_op.armature_name = armature.name
        move_up_morph_target_bind_op.expression_name = expression.name
        move_up_morph_target_bind_op.bind_index = (
            expression.active_morph_target_bind_index
        )

        move_down_morph_target_bind_op = layout_operator(
            morph_target_binds_side_column,
            vrm1_ops.VRM_OT_move_down_vrm1_expression_morph_target_bind,
            icon="TRIA_DOWN",
            text="",
        )
        move_down_morph_target_bind_op.armature_name = armature.name
        move_down_morph_target_bind_op.expression_name = expression.name
        move_down_morph_target_bind_op.bind_index = (
            expression.active_morph_target_bind_index
        )

    if 0 <= active_morph_target_bind_index < len(expression.morph_target_binds):
        draw_vrm1_expressions_morph_target_bind_layout(
            context,
            morph_target_binds_box,
            expression.morph_target_binds[active_morph_target_bind_index],
        )

    column.separator(factor=0.2)

    material_color_binds_box = column.box()
    material_color_binds_box.label(text="Material Color Binds", icon="MATERIAL")
    material_color_binds_row = material_color_binds_box.row()
    material_color_binds_row.template_list(
        VRM_UL_vrm1_material_color_bind.bl_idname,
        "",
        expression,
        "material_color_binds",
        expression,
        "active_material_color_bind_index",
    )
    active_material_color_bind_index = expression.active_material_color_bind_index
    material_color_binds_side_column = material_color_binds_row.column(align=True)

    add_material_color_bind_op = layout_operator(
        material_color_binds_side_column,
        vrm1_ops.VRM_OT_add_vrm1_expression_material_color_bind,
        icon="ADD",
        text="",
    )
    add_material_color_bind_op.armature_name = armature.name
    add_material_color_bind_op.expression_name = expression.name

    if expression.material_color_binds:
        remove_material_color_bind_op = layout_operator(
            material_color_binds_side_column,
            vrm1_ops.VRM_OT_remove_vrm1_expression_material_color_bind,
            icon="REMOVE",
            text="",
        )
        remove_material_color_bind_op.armature_name = armature.name
        remove_material_color_bind_op.expression_name = expression.name
        remove_material_color_bind_op.bind_index = active_material_color_bind_index

        material_color_binds_side_column.separator()

        move_up_material_color_bind_op = layout_operator(
            material_color_binds_side_column,
            vrm1_ops.VRM_OT_move_up_vrm1_expression_material_color_bind,
            icon="TRIA_UP",
            text="",
        )
        move_up_material_color_bind_op.armature_name = armature.name
        move_up_material_color_bind_op.expression_name = expression.name
        move_up_material_color_bind_op.bind_index = (
            expression.active_material_color_bind_index
        )

        move_down_material_color_bind_op = layout_operator(
            material_color_binds_side_column,
            vrm1_ops.VRM_OT_move_down_vrm1_expression_material_color_bind,
            icon="TRIA_DOWN",
            text="",
        )
        move_down_material_color_bind_op.armature_name = armature.name
        move_down_material_color_bind_op.expression_name = expression.name
        move_down_material_color_bind_op.bind_index = (
            expression.active_material_color_bind_index
        )

    if 0 <= active_material_color_bind_index < len(expression.material_color_binds):
        draw_vrm1_expressions_material_color_bind_layout(
            context,
            material_color_binds_box,
            expression.material_color_binds[active_material_color_bind_index],
        )
    column.separator(factor=0.2)

    texture_transform_binds_box = column.box()
    texture_transform_binds_box.label(text="Texture Transform Binds", icon="MATERIAL")
    texture_transform_binds_row = texture_transform_binds_box.row()
    texture_transform_binds_row.template_list(
        VRM_UL_vrm1_texture_transform_bind.bl_idname,
        "",
        expression,
        "texture_transform_binds",
        expression,
        "active_texture_transform_bind_index",
    )
    active_texture_transform_bind_index = expression.active_texture_transform_bind_index
    texture_transform_binds_side_column = texture_transform_binds_row.column(align=True)

    add_texture_transform_bind_op = layout_operator(
        texture_transform_binds_side_column,
        vrm1_ops.VRM_OT_add_vrm1_expression_texture_transform_bind,
        icon="ADD",
        text="",
    )
    add_texture_transform_bind_op.armature_name = armature.name
    add_texture_transform_bind_op.expression_name = expression.name

    if expression.texture_transform_binds:
        remove_texture_transform_bind_op = layout_operator(
            texture_transform_binds_side_column,
            vrm1_ops.VRM_OT_remove_vrm1_expression_texture_transform_bind,
            icon="REMOVE",
            text="",
        )
        remove_texture_transform_bind_op.armature_name = armature.name
        remove_texture_transform_bind_op.expression_name = expression.name
        remove_texture_transform_bind_op.bind_index = (
            active_texture_transform_bind_index
        )

        texture_transform_binds_side_column.separator()

        move_up_texture_transform_bind_op = layout_operator(
            texture_transform_binds_side_column,
            vrm1_ops.VRM_OT_move_up_vrm1_expression_texture_transform_bind,
            icon="TRIA_UP",
            text="",
        )
        move_up_texture_transform_bind_op.armature_name = armature.name
        move_up_texture_transform_bind_op.expression_name = expression.name
        move_up_texture_transform_bind_op.bind_index = (
            expression.active_texture_transform_bind_index
        )

        move_down_texture_transform_bind_op = layout_operator(
            texture_transform_binds_side_column,
            vrm1_ops.VRM_OT_move_down_vrm1_expression_texture_transform_bind,
            icon="TRIA_DOWN",
            text="",
        )
        move_down_texture_transform_bind_op.armature_name = armature.name
        move_down_texture_transform_bind_op.expression_name = expression.name
        move_down_texture_transform_bind_op.bind_index = (
            expression.active_texture_transform_bind_index
        )

    if (
        0
        <= active_texture_transform_bind_index
        < len(expression.texture_transform_binds)
    ):
        draw_vrm1_expressions_texture_transform_bind_layout(
            context,
            texture_transform_binds_box,
            expression.texture_transform_binds[active_texture_transform_bind_index],
        )


class VRM_PT_vrm1_expressions_armature_object_property(Panel):
    bl_idname = "VRM_PT_vrm1_expressions_armature_object_property"
    bl_label = "Expressions"
    bl_translation_context = "VRM"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options: AbstractSet[str] = {"DEFAULT_CLOSED"}
    bl_parent_id = VRM_PT_vrm_armature_object_property.bl_idname

    @classmethod
    def poll(cls, context: Context) -> bool:
        return active_object_is_vrm1_armature(context)

    def draw_header(self, _context: Context) -> None:
        self.layout.label(icon="SHAPEKEY_DATA")

    def draw(self, context: Context) -> None:
        active_object = context.active_object
        if not active_object:
            return
        if active_object.type != "ARMATURE":
            return
        armature_data = active_object.data
        if not isinstance(armature_data, Armature):
            return
        draw_vrm1_expressions_layout(
            active_object,
            context,
            self.layout,
            armature_data.vrm_addon_extension.vrm1.expressions,
        )


class VRM_PT_vrm1_expressions_ui(Panel):
    bl_idname = "VRM_PT_vrm1_expressions_ui"
    bl_label = "Expressions"
    bl_translation_context = "VRM"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VRM"
    bl_options: AbstractSet[str] = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return search.current_armature_is_vrm1(context)

    def draw_header(self, _context: Context) -> None:
        self.layout.label(icon="SHAPEKEY_DATA")

    def draw(self, context: Context) -> None:
        armature = search.current_armature(context)
        if not armature:
            return
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return
        draw_vrm1_expressions_layout(
            armature,
            context,
            self.layout,
            armature_data.vrm_addon_extension.vrm1.expressions,
        )


def draw_vrm1_meta_layout(
    armature: Object,
    _context: Context,
    layout: UILayout,
    meta: Vrm1MetaPropertyGroup,
) -> None:
    migrate(armature.name, defer=True)

    thumbnail_column = layout.column()
    thumbnail_column.label(text="Thumbnail:")
    thumbnail_column.template_ID_preview(meta, "thumbnail_image")

    layout.prop(meta, "vrm_name", icon="FILE_BLEND")
    layout.prop(meta, "version", icon="LINENUMBERS_ON")

    authors_box = layout.box()
    authors_column = authors_box.column()
    authors_column.label(text="Authors:")
    if meta.authors:
        for author_index, author in enumerate(meta.authors):
            author_row = authors_column.split(align=True, factor=0.7)
            author_row.prop(author, "value", text="", translate=False, icon="USER")
            remove_author_op = layout_operator(
                author_row,
                vrm1_ops.VRM_OT_remove_vrm1_meta_author,
                text="Remove",
                icon="REMOVE",
            )
            remove_author_op.armature_name = armature.name
            remove_author_op.author_index = author_index

    add_author_op = layout_operator(
        authors_column, vrm1_ops.VRM_OT_add_vrm1_meta_author
    )
    add_author_op.armature_name = armature.name

    layout.prop(meta, "copyright_information")
    layout.prop(meta, "contact_information")

    references_box = layout.box()
    references_column = references_box.column()
    references_column.label(text="References:")
    if meta.references:
        for reference_index, reference in enumerate(meta.references):
            reference_row = references_column.split(align=True, factor=0.7)
            reference_row.prop(
                reference, "value", text="", translate=False, icon="USER"
            )
            remove_reference_op = layout_operator(
                reference_row,
                vrm1_ops.VRM_OT_remove_vrm1_meta_reference,
                text="Remove",
                icon="REMOVE",
            )
            remove_reference_op.armature_name = armature.name
            remove_reference_op.reference_index = reference_index
    add_reference_op = layout_operator(
        references_column, vrm1_ops.VRM_OT_add_vrm1_meta_reference
    )
    add_reference_op.armature_name = armature.name

    layout.prop(meta, "third_party_licenses")
    # layout.prop(meta, "license_url", icon="URL")
    layout.prop(meta, "avatar_permission", icon="MATCLOTH")
    layout.prop(meta, "commercial_usage", icon="SOLO_OFF")
    layout.prop(meta, "credit_notation")
    layout.prop(meta, "modification")
    layout.prop(meta, "allow_excessively_violent_usage")
    layout.prop(meta, "allow_excessively_sexual_usage")
    layout.prop(meta, "allow_political_or_religious_usage")
    layout.prop(meta, "allow_antisocial_or_hate_usage")
    layout.prop(meta, "allow_redistribution")
    layout.prop(meta, "other_license_url", icon="URL")


class VRM_PT_vrm1_meta_armature_object_property(Panel):
    bl_idname = "VRM_PT_vrm1_meta_armature_object_property"
    bl_label = "Meta"
    bl_translation_context = "VRM"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options: AbstractSet[str] = {"DEFAULT_CLOSED"}
    bl_parent_id = VRM_PT_vrm_armature_object_property.bl_idname

    @classmethod
    def poll(cls, context: Context) -> bool:
        return active_object_is_vrm1_armature(context)

    def draw_header(self, _context: Context) -> None:
        self.layout.label(icon="FILE_BLEND")

    def draw(self, context: Context) -> None:
        active_object = context.active_object
        if not active_object:
            return
        if active_object.type != "ARMATURE":
            return
        armature_data = active_object.data
        if not isinstance(armature_data, Armature):
            return
        ext = armature_data.vrm_addon_extension
        draw_vrm1_meta_layout(active_object, context, self.layout, ext.vrm1.meta)


class VRM_PT_vrm1_meta_ui(Panel):
    bl_idname = "VRM_PT_vrm1_meta_ui"
    bl_label = "Meta"
    bl_translation_context = "VRM"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VRM"
    bl_options: AbstractSet[str] = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return search.current_armature_is_vrm1(context)

    def draw_header(self, _context: Context) -> None:
        self.layout.label(icon="FILE_BLEND")

    def draw(self, context: Context) -> None:
        armature = search.current_armature(context)
        if not armature:
            return
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return
        draw_vrm1_meta_layout(
            armature,
            context,
            self.layout,
            armature_data.vrm_addon_extension.vrm1.meta,
        )


class VRM_PT_vrm1_bone_property(Panel):
    bl_idname = "VRM_PT_vrm1_bone_property"
    bl_label = "VRM"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "bone"

    @classmethod
    def poll(cls, context: Context) -> bool:
        active_object = context.active_object
        if not active_object:
            return False
        if active_object.type != "ARMATURE":
            return False
        armature_data = active_object.data
        if not isinstance(armature_data, Armature):
            return False
        if not armature_data.bones.active:
            return False
        return search.current_armature_is_vrm1(context)

    def draw(self, context: Context) -> None:
        active_object = context.active_object
        if not active_object:
            return
        if active_object.type != "ARMATURE":
            return
        armature_data = active_object.data
        if not isinstance(armature_data, Armature):
            return
        # context.active_bone is a EditBone
        bone = armature_data.bones.active
        if not bone:
            return
        ext = bone.vrm_addon_extension
        layout = self.layout
        layout.prop(ext, "axis_translation")
