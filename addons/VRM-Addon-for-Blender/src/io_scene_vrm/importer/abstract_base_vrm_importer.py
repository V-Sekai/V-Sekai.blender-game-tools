# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2018 iCyP

import json
import math
import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Optional, Union

import bpy
from bpy.types import (
    Armature,
    Context,
    Image,
    Material,
    Mesh,
    Object,
    ShaderNodeOutputMaterial,
    SpaceView3D,
)
from mathutils import Matrix, Vector

from ..common import convert, deep, shader
from ..common.deep import Json
from ..common.logging import get_logger
from ..common.preferences import ImportPreferencesProtocol
from ..common.version import addon_version
from ..common.vrm0.human_bone import HumanBoneName, HumanBoneSpecifications
from ..editor import make_armature, migration
from ..editor.make_armature import (
    connect_parent_tail_and_child_head_if_very_close_position,
)
from ..editor.mtoon1.property_group import (
    Mtoon0TexturePropertyGroup,
    Mtoon1MaterialPropertyGroup,
    Mtoon1SamplerPropertyGroup,
    Mtoon1TextureInfoPropertyGroup,
    Mtoon1TexturePropertyGroup,
)
from ..editor.vrm0.property_group import (
    Vrm0BlendShapeGroupPropertyGroup,
    Vrm0BlendShapeMasterPropertyGroup,
    Vrm0FirstPersonPropertyGroup,
    Vrm0HumanoidPropertyGroup,
    Vrm0MeshAnnotationPropertyGroup,
    Vrm0MetaPropertyGroup,
    Vrm0SecondaryAnimationPropertyGroup,
)
from .vrm_parser import ParseResult, Vrm0MaterialProperty

logger = get_logger(__name__)


class AbstractBaseVrmImporter(ABC):
    def __init__(
        self,
        context: Context,
        parse_result: ParseResult,
        preferences: ImportPreferencesProtocol,
    ) -> None:
        self.context = context
        self.parse_result = parse_result
        self.preferences = preferences

        self.meshes: dict[int, Object] = {}
        self.images: dict[int, Image] = {}
        self.armature: Optional[Object] = None
        self.bone_names: dict[int, str] = {}
        self.materials: dict[int, Material] = {}
        self.primitive_obj_dict: Optional[dict[Optional[int], list[float]]] = None
        self.mesh_joined_objects = None
        self.bone_child_object_world_matrices: dict[str, Matrix] = {}

    @abstractmethod
    def import_vrm(self) -> None:
        pass

    @staticmethod
    def axis_glb_to_blender(vec3: Sequence[float]) -> list[float]:
        return [vec3[i] * t for i, t in zip([0, 2, 1], [-1, 1, 1])]

    @property
    def armature_data(self) -> Armature:
        if not self.armature:
            message = "armature is not set"
            raise AssertionError(message)
        armature_data = self.armature.data
        if not isinstance(armature_data, Armature):
            message = f"{type(armature_data)} is not an Armature"
            raise TypeError(message)
        return armature_data

    def save_bone_child_object_world_matrices(self, armature: Object) -> None:
        for obj in bpy.data.objects:
            if (
                obj.parent_type == "BONE"
                and obj.parent == armature
                and obj.parent_bone in self.armature_data.bones
            ):
                self.bone_child_object_world_matrices[obj.name] = (
                    obj.matrix_world.copy()
                )

    def load_bone_child_object_world_matrices(self, armature: Object) -> None:
        for obj in bpy.data.objects:
            if (
                obj.parent_type == "BONE"
                and obj.parent == armature
                and obj.parent_bone in self.armature_data.bones
                and obj.name in self.bone_child_object_world_matrices
            ):
                obj.matrix_world = self.bone_child_object_world_matrices[
                    obj.name
                ].copy()

    def setup_vrm0_humanoid_bones(self) -> None:
        armature = self.armature
        if not armature:
            return
        addon_extension = self.armature_data.vrm_addon_extension

        Vrm0HumanoidPropertyGroup.fixup_human_bones(armature)
        Vrm0HumanoidPropertyGroup.update_all_node_candidates(
            self.armature_data.name,
            force=True,
        )

        human_bones = addon_extension.vrm0.humanoid.human_bones
        for human_bone in human_bones:
            if (
                human_bone.node.bone_name
                and human_bone.node.bone_name not in human_bone.node_candidates
            ):
                # has error
                return

        for humanoid_name in HumanBoneSpecifications.required_names:
            if not any(
                human_bone.bone == humanoid_name and human_bone.node.bone_name
                for human_bone in human_bones
            ):
                # has error
                return

        previous_active = self.context.view_layer.objects.active
        try:
            self.context.view_layer.objects.active = armature

            bone_name_to_human_bone_name: dict[str, HumanBoneName] = {}
            for human_bone in human_bones:
                if not human_bone.node.bone_name:
                    continue
                name = HumanBoneName.from_str(human_bone.bone)
                if not name:
                    continue
                bone_name_to_human_bone_name[human_bone.node.bone_name] = name

            bpy.ops.object.mode_set(mode="EDIT")

            for bone_name in bone_name_to_human_bone_name:
                bone = self.armature_data.edit_bones.get(bone_name)
                while bone:
                    bone.roll = 0.0
                    bone = bone.parent

            for (
                bone_name,
                human_bone_name,
            ) in bone_name_to_human_bone_name.items():
                # 現在のアルゴリズムでは
                #
                #   head ---- node ---- leftEye
                #                   \
                #                    -- rightEye
                #
                # を上手く扱えないので、leftEyeとrightEyeは処理しない
                if human_bone_name in [HumanBoneName.RIGHT_EYE, HumanBoneName.LEFT_EYE]:
                    continue

                bone = self.armature_data.edit_bones.get(bone_name)
                if not bone:
                    continue
                last_human_bone_name = human_bone_name
                while True:
                    parent = bone.parent
                    if not parent:
                        break
                    parent_human_bone_name = bone_name_to_human_bone_name.get(
                        parent.name
                    )

                    if parent_human_bone_name in [
                        HumanBoneName.RIGHT_HAND,
                        HumanBoneName.LEFT_HAND,
                    ]:
                        break

                    if (
                        parent_human_bone_name == HumanBoneName.UPPER_CHEST
                        and last_human_bone_name
                        not in [HumanBoneName.HEAD, HumanBoneName.NECK]
                    ):
                        break

                    if (
                        parent_human_bone_name == HumanBoneName.CHEST
                        and last_human_bone_name
                        not in [
                            HumanBoneName.HEAD,
                            HumanBoneName.NECK,
                            HumanBoneName.UPPER_CHEST,
                        ]
                    ):
                        break

                    if (
                        parent_human_bone_name == HumanBoneName.SPINE
                        and last_human_bone_name
                        not in [
                            HumanBoneName.HEAD,
                            HumanBoneName.NECK,
                            HumanBoneName.UPPER_CHEST,
                            HumanBoneName.CHEST,
                        ]
                    ):
                        break

                    if (
                        parent_human_bone_name == HumanBoneName.HIPS
                        and last_human_bone_name != HumanBoneName.SPINE
                    ):
                        break

                    if parent_human_bone_name:
                        last_human_bone_name = parent_human_bone_name

                    if (
                        parent.head - bone.head
                    ).length >= make_armature.MIN_BONE_LENGTH:
                        parent.tail = bone.head

                    bone = parent

            for human_bone in human_bones:
                if (
                    human_bone.bone
                    not in [HumanBoneName.LEFT_EYE.value, HumanBoneName.RIGHT_EYE.value]
                    or not human_bone.node.bone_name
                ):
                    continue

                bone = self.armature_data.edit_bones.get(human_bone.node.bone_name)
                if not bone or bone.children:
                    continue

                world_head = (
                    armature.matrix_world @ Matrix.Translation(bone.head)
                ).to_translation()

                world_tail = list(world_head)
                world_tail[1] -= 0.03125

                world_inv = armature.matrix_world.inverted()
                if not world_inv:
                    continue
                bone.tail = (
                    Matrix.Translation(world_tail) @ world_inv
                ).to_translation()

            connect_parent_tail_and_child_head_if_very_close_position(
                self.armature_data
            )
            bpy.ops.object.mode_set(mode="OBJECT")
        finally:
            active = self.context.view_layer.objects.active
            if active and active.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            self.context.view_layer.objects.active = previous_active

        self.load_bone_child_object_world_matrices(armature)

    def scene_init(self) -> Optional[Object]:
        # active_objectがhideだとbpy.ops.object.mode_set.poll()に失敗してエラーが出るの
        # でその回避と、それを元に戻す
        affected_object = None
        if self.context.active_object is not None:
            if (
                hasattr(self.context.active_object, "hide_viewport")
                and self.context.active_object.hide_viewport
            ):
                self.context.active_object.hide_viewport = False
                affected_object = self.context.active_object
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
        return affected_object

    def finishing(self, affected_object: Optional[Object]) -> None:
        # initで弄ったやつを戻す
        if affected_object is not None:
            affected_object.hide_viewport = True

        for obj in self.context.selected_objects:
            obj.select_set(False)

        # image_path_to Texture

    def use_fake_user_for_thumbnail(self) -> None:
        # サムネイルはVRMの仕様ではimageのインデックスとあるが、UniVRMの実装ではtexture
        # のインデックスになっている
        # https://github.com/vrm-c/UniVRM/blob/v0.67.0/Assets/VRM/Runtime/IO/VRMImporterContext.cs#L308
        json_texture_index = deep.get(
            self.parse_result.vrm0_extension, ["meta", "texture"]
        )
        if not isinstance(json_texture_index, int):
            return
        json_textures = self.parse_result.json_dict.get("textures", [])
        if not isinstance(json_textures, list):
            logger.warning('json["textures"] is not list')
            return
        if json_texture_index not in (-1, None) and (
            "textures" in self.parse_result.json_dict
            and len(json_textures) > json_texture_index
        ):
            json_texture = json_textures[json_texture_index]
            if isinstance(json_texture, dict):
                image_index = json_texture.get("source")
                if isinstance(image_index, int) and image_index in self.images:
                    self.images[image_index].use_fake_user = True

    # material
    @staticmethod
    def find_material_output_node(
        material: Material,
    ) -> ShaderNodeOutputMaterial:
        if material.node_tree:
            for node in material.node_tree.nodes:
                if not isinstance(node, ShaderNodeOutputMaterial):
                    continue
                return node
        message = f'No "ShaderNodeOutputMaterial" node in {material}'
        raise ValueError(message)

    @staticmethod
    def reset_material(material: Material) -> None:
        if not material.use_nodes:
            material.use_nodes = True
        shader.clear_node_tree(material.node_tree)
        if material.alpha_threshold != 0.5:
            material.alpha_threshold = 0.5
        if material.blend_method != "OPAQUE":
            material.blend_method = "OPAQUE"
        if material.shadow_method != "OPAQUE":
            material.shadow_method = "OPAQUE"
        if material.use_backface_culling:
            material.use_backface_culling = False
        if material.show_transparent_back:
            material.show_transparent_back = False
        if material.node_tree:
            material.node_tree.nodes.new("ShaderNodeOutputMaterial")
        else:
            logger.error(f"No node tree for material {material.name}")

    def make_material(self) -> None:
        shader_to_build_method = {
            "VRM/MToon": self.build_material_from_mtoon0,
            "VRM/UnlitTransparentZWrite": self.build_material_from_transparent_z_write,
        }

        for index, material_property in enumerate(
            self.parse_result.vrm0_material_properties
        ):
            build_method = shader_to_build_method.get(material_property.shader)
            if not build_method:
                continue

            material = self.materials.get(index)
            if not material:
                material = bpy.data.materials.new(material_property.name)
                self.materials[index] = material

            self.reset_material(material)
            build_method(material, material_property)

    def assign_mtoon0_texture(
        self,
        texture: Union[Mtoon0TexturePropertyGroup, Mtoon1TexturePropertyGroup],
        texture_index: Optional[int],
    ) -> bool:
        if texture_index is None:
            return False
        texture_dicts = self.parse_result.json_dict.get("textures")
        if not isinstance(texture_dicts, list):
            return False
        if not 0 <= texture_index < len(texture_dicts):
            return False
        texture_dict = texture_dicts[texture_index]
        if not isinstance(texture_dict, dict):
            return False

        source = texture_dict.get("source")
        if isinstance(source, int):
            image = self.images.get(source)
            if image:
                image.colorspace_settings.name = texture.colorspace
                texture.source = image

        sampler = texture_dict.get("sampler")
        samplers = self.parse_result.json_dict.get("samplers")
        if not isinstance(sampler, int) or not isinstance(samplers, list):
            return True
        if not 0 <= sampler < len(samplers):
            return True

        sampler_dict = samplers[sampler]
        if not isinstance(sampler_dict, dict):
            return True

        mag_filter = sampler_dict.get("magFilter")
        if isinstance(mag_filter, int):
            mag_filter_id = Mtoon1SamplerPropertyGroup.MAG_FILTER_NUMBER_TO_ID.get(
                mag_filter
            )
            if isinstance(mag_filter_id, str):
                texture.sampler.mag_filter = mag_filter_id

        min_filter = sampler_dict.get("minFilter")
        if isinstance(min_filter, int):
            min_filter_id = Mtoon1SamplerPropertyGroup.MIN_FILTER_NUMBER_TO_ID.get(
                min_filter
            )
            if isinstance(min_filter_id, str):
                texture.sampler.min_filter = min_filter_id

        wrap_s = sampler_dict.get("wrapS")
        if isinstance(wrap_s, int):
            wrap_s_id = Mtoon1SamplerPropertyGroup.WRAP_NUMBER_TO_ID.get(wrap_s)
            if isinstance(wrap_s_id, str):
                texture.sampler.wrap_s = wrap_s_id

        wrap_t = sampler_dict.get("wrapT")
        if isinstance(wrap_t, int):
            wrap_t_id = Mtoon1SamplerPropertyGroup.WRAP_NUMBER_TO_ID.get(wrap_t)
            if isinstance(wrap_t_id, str):
                texture.sampler.wrap_t = wrap_t_id

        return True

    def assign_mtoon0_texture_info(
        self,
        texture_info: Mtoon1TextureInfoPropertyGroup,
        texture_index: Optional[int],
        uv_transform: tuple[float, float, float, float],
    ) -> None:
        if not self.assign_mtoon0_texture(texture_info.index, texture_index):
            return

        texture_info.extensions.khr_texture_transform.offset = (
            uv_transform[0],
            uv_transform[1],
        )
        texture_info.extensions.khr_texture_transform.scale = (
            uv_transform[2],
            uv_transform[3],
        )

    def build_material_from_mtoon0(
        self, material: Material, vrm0_material_property: Vrm0MaterialProperty
    ) -> None:
        # https://github.com/saturday06/VRM-Addon-for-Blender/blob/2_15_26/io_scene_vrm/editor/mtoon1/ops.py#L98
        material.use_backface_culling = True

        gltf = material.vrm_addon_extension.mtoon1
        gltf.addon_version = addon_version()
        gltf.enabled = True
        gltf.show_expanded_mtoon0 = True
        mtoon = gltf.extensions.vrmc_materials_mtoon

        gltf.alpha_mode = gltf.ALPHA_MODE_OPAQUE
        blend_mode = vrm0_material_property.float_properties.get("_BlendMode")
        if blend_mode is not None:
            if math.fabs(blend_mode - 1) < 0.001:
                gltf.alpha_mode = gltf.ALPHA_MODE_MASK
            elif math.fabs(blend_mode - 2) < 0.001:
                gltf.alpha_mode = gltf.ALPHA_MODE_BLEND
            elif math.fabs(blend_mode - 3) < 0.001:
                gltf.alpha_mode = gltf.ALPHA_MODE_BLEND
                mtoon.transparent_with_z_write = True

        cutoff = vrm0_material_property.float_properties.get("_Cutoff")
        if cutoff is not None:
            gltf.alpha_cutoff = cutoff

        gltf.double_sided = True
        cull_mode = vrm0_material_property.float_properties.get("_CullMode")
        if cull_mode is not None:
            if math.fabs(cull_mode - 1) < 0.001:
                gltf.mtoon0_front_cull_mode = True
            elif math.fabs(cull_mode - 2) < 0.001:
                gltf.double_sided = False

        base_color_factor = shader.rgba_or_none(
            vrm0_material_property.vector_properties.get("_Color")
        )
        if base_color_factor:
            gltf.pbr_metallic_roughness.base_color_factor = base_color_factor

        raw_uv_transform = vrm0_material_property.vector_properties.get("_MainTex")
        if raw_uv_transform is None or len(raw_uv_transform) != 4:
            uv_transform = (0.0, 0.0, 1.0, 1.0)
        else:
            uv_transform = (
                raw_uv_transform[0],
                raw_uv_transform[1],
                raw_uv_transform[2],
                raw_uv_transform[3],
            )

        self.assign_mtoon0_texture_info(
            gltf.pbr_metallic_roughness.base_color_texture,
            vrm0_material_property.texture_properties.get("_MainTex"),
            uv_transform,
        )

        shade_color_factor = shader.rgb_or_none(
            vrm0_material_property.vector_properties.get("_ShadeColor")
        )
        if shade_color_factor:
            mtoon.shade_color_factor = shade_color_factor

        self.assign_mtoon0_texture_info(
            mtoon.shade_multiply_texture,
            vrm0_material_property.texture_properties.get("_ShadeTexture"),
            uv_transform,
        )

        self.assign_mtoon0_texture_info(
            gltf.normal_texture,
            vrm0_material_property.texture_properties.get("_BumpMap"),
            uv_transform,
        )
        normal_texture_scale = vrm0_material_property.float_properties.get("_BumpScale")
        if isinstance(normal_texture_scale, (float, int)):
            gltf.normal_texture.scale = float(normal_texture_scale)

        shading_shift_0x = vrm0_material_property.float_properties.get("_ShadeShift")
        if shading_shift_0x is None:
            shading_shift_0x = 0

        shading_toony_0x = vrm0_material_property.float_properties.get("_ShadeToony")
        if shading_toony_0x is None:
            shading_toony_0x = 0

        mtoon.shading_shift_factor = convert.mtoon_shading_shift_0_to_1(
            shading_toony_0x, shading_shift_0x
        )

        mtoon.shading_toony_factor = convert.mtoon_shading_toony_0_to_1(
            shading_toony_0x, shading_shift_0x
        )

        indirect_light_intensity = vrm0_material_property.float_properties.get(
            "_IndirectLightIntensity"
        )
        if indirect_light_intensity is not None:
            mtoon.gi_equalization_factor = convert.mtoon_intensity_to_gi_equalization(
                indirect_light_intensity
            )
        else:
            mtoon.gi_equalization_factor = 0.5

        raw_emissive_factor = shader.rgb_or_none(
            vrm0_material_property.vector_properties.get("_EmissionColor")
        ) or (0, 0, 0)
        max_color_component_value = max(raw_emissive_factor)
        if max_color_component_value > 1:
            gltf.emissive_factor = list(
                Vector(raw_emissive_factor) / max_color_component_value
            )
            gltf.extensions.khr_materials_emissive_strength.emissive_strength = (
                max_color_component_value
            )
        else:
            gltf.emissive_factor = raw_emissive_factor

        self.assign_mtoon0_texture_info(
            gltf.emissive_texture,
            vrm0_material_property.texture_properties.get("_EmissionMap"),
            uv_transform,
        )

        self.assign_mtoon0_texture_info(
            mtoon.matcap_texture,
            vrm0_material_property.texture_properties.get("_SphereAdd"),
            (0, 0, 1, 1),
        )

        parametric_rim_color_factor = shader.rgb_or_none(
            vrm0_material_property.vector_properties.get("_RimColor")
        )
        if parametric_rim_color_factor:
            mtoon.parametric_rim_color_factor = parametric_rim_color_factor

        parametric_rim_fresnel_power_factor = (
            vrm0_material_property.float_properties.get("_RimFresnelPower")
        )
        if isinstance(parametric_rim_fresnel_power_factor, (float, int)):
            mtoon.parametric_rim_fresnel_power_factor = (
                parametric_rim_fresnel_power_factor
            )

        mtoon.parametric_rim_lift_factor = vrm0_material_property.float_properties.get(
            "_RimLift", 0
        )

        self.assign_mtoon0_texture_info(
            mtoon.rim_multiply_texture,
            vrm0_material_property.texture_properties.get("_RimTexture"),
            uv_transform,
        )

        # https://github.com/vrm-c/UniVRM/blob/7c9919ef47a25c04100a2dcbe6a75dff49ef4857/Assets/VRM10/Runtime/Migration/Materials/MigrationMToonMaterial.cs#L287-L290
        mtoon.rim_lighting_mix_factor = 1.0
        rim_lighting_mix = vrm0_material_property.float_properties.get(
            "_RimLightingMix"
        )
        if rim_lighting_mix is not None:
            gltf.mtoon0_rim_lighting_mix = rim_lighting_mix

        centimeter_to_meter = 0.01
        one_hundredth = 0.01

        outline_width_mode = int(
            round(vrm0_material_property.float_properties.get("_OutlineWidthMode", 0))
        )

        outline_width = vrm0_material_property.float_properties.get("_OutlineWidth")
        if outline_width is None:
            outline_width = 0.0

        if outline_width_mode == 0:
            mtoon.outline_width_mode = mtoon.OUTLINE_WIDTH_MODE_NONE
        elif outline_width_mode == 1:
            mtoon.outline_width_mode = mtoon.OUTLINE_WIDTH_MODE_WORLD_COORDINATES
            mtoon.outline_width_factor = max(0.0, outline_width * centimeter_to_meter)
        else:
            mtoon.outline_width_mode = mtoon.OUTLINE_WIDTH_MODE_SCREEN_COORDINATES
            mtoon.outline_width_factor = max(0.0, outline_width * one_hundredth * 0.5)
            outline_scaled_max_distance = vrm0_material_property.float_properties.get(
                "_OutlineScaledMaxDistance"
            )
            if outline_scaled_max_distance is not None:
                gltf.mtoon0_outline_scaled_max_distance = outline_scaled_max_distance

        self.assign_mtoon0_texture_info(
            mtoon.outline_width_multiply_texture,
            vrm0_material_property.texture_properties.get("_OutlineWidthTexture"),
            uv_transform,
        )

        outline_color_factor = shader.rgb_or_none(
            vrm0_material_property.vector_properties.get("_OutlineColor")
        )
        if outline_color_factor:
            mtoon.outline_color_factor = outline_color_factor

        outline_color_mode = vrm0_material_property.float_properties.get(
            "_OutlineColorMode"
        )
        if (
            outline_color_mode is not None
            and math.fabs(outline_color_mode - 1) < 0.00001
        ):
            mtoon.outline_lighting_mix_factor = (
                vrm0_material_property.float_properties.get("_OutlineLightingMix") or 1
            )
        else:
            mtoon.outline_lighting_mix_factor = 0  # Fixed Color

        self.assign_mtoon0_texture_info(
            mtoon.uv_animation_mask_texture,
            vrm0_material_property.texture_properties.get("_UvAnimMaskTexture"),
            uv_transform,
        )

        uv_animation_rotation_speed_factor = (
            vrm0_material_property.float_properties.get("_UvAnimRotation")
        )
        if isinstance(uv_animation_rotation_speed_factor, (float, int)):
            mtoon.uv_animation_rotation_speed_factor = (
                uv_animation_rotation_speed_factor
            )

        uv_animation_scroll_x_speed_factor = (
            vrm0_material_property.float_properties.get("_UvAnimScrollX")
        )
        if isinstance(uv_animation_scroll_x_speed_factor, (float, int)):
            mtoon.uv_animation_scroll_x_speed_factor = (
                uv_animation_scroll_x_speed_factor
            )

        uv_animation_scroll_y_speed_factor = (
            vrm0_material_property.float_properties.get("_UvAnimScrollY")
        )
        if isinstance(uv_animation_scroll_y_speed_factor, (float, int)):
            mtoon.uv_animation_scroll_y_speed_factor = (
                -uv_animation_scroll_y_speed_factor
            )

        light_color_attenuation = vrm0_material_property.float_properties.get(
            "_LightColorAttenuation"
        )
        if light_color_attenuation is not None:
            gltf.mtoon0_light_color_attenuation = light_color_attenuation

        self.assign_mtoon0_texture(
            gltf.mtoon0_receive_shadow_texture,
            vrm0_material_property.texture_properties.get("_ReceiveShadowTexture"),
        )

        gltf.mtoon0_receive_shadow_rate = vrm0_material_property.float_properties.get(
            "_ReceiveShadowRate", 0.5
        )

        self.assign_mtoon0_texture(
            gltf.mtoon0_shading_grade_texture,
            vrm0_material_property.texture_properties.get("_ShadingGradeTexture"),
        )

        gltf.mtoon0_shading_grade_rate = vrm0_material_property.float_properties.get(
            "_ShadingGradeRate", 0.5
        )

        if vrm0_material_property.render_queue is not None:
            gltf.mtoon0_render_queue = vrm0_material_property.render_queue

    def build_material_from_transparent_z_write(
        self,
        material: Material,
        vrm0_material_property: Vrm0MaterialProperty,
    ) -> None:
        gltf = material.vrm_addon_extension.mtoon1
        gltf.enabled = True
        mtoon = gltf.extensions.vrmc_materials_mtoon

        main_texture_index = vrm0_material_property.texture_properties.get("_MainTex")
        main_texture_image = None
        if isinstance(main_texture_index, int):
            texture_dicts = self.parse_result.json_dict.get("textures")
            if isinstance(texture_dicts, list) and 0 <= main_texture_index < len(
                texture_dicts
            ):
                texture_dict = texture_dicts[main_texture_index]
                if isinstance(texture_dict, dict):
                    image_index = texture_dict.get("source")
                    if isinstance(image_index, int):
                        main_texture_image = self.images.get(image_index)
        if main_texture_image:
            gltf.pbr_metallic_roughness.base_color_texture.index.source = (
                main_texture_image
            )
            gltf.emissive_texture.index.source = main_texture_image
            mtoon.shade_multiply_texture.index.source = main_texture_image

        gltf.pbr_metallic_roughness.base_color_factor = (0, 0, 0, 1)
        gltf.emissive_factor = (1, 1, 1)

        gltf.alpha_mode = Mtoon1MaterialPropertyGroup.ALPHA_MODE_BLEND
        gltf.alpha_cutoff = 0.5
        gltf.double_sided = False
        mtoon.transparent_with_z_write = True
        mtoon.shade_color_factor = (0, 0, 0)
        mtoon.shading_toony_factor = 0.95
        mtoon.shading_shift_factor = -0.05
        mtoon.rim_lighting_mix_factor = 1
        mtoon.parametric_rim_fresnel_power_factor = 5
        mtoon.parametric_rim_lift_factor = 0

    def load_vrm0_extensions(self) -> None:
        armature = self.armature
        if not armature:
            return
        addon_extension = self.armature_data.vrm_addon_extension
        addon_extension.spec_version = addon_extension.SPEC_VERSION_VRM0
        vrm0 = addon_extension.vrm0

        if self.parse_result.spec_version_number >= (1, 0):
            return

        vrm0_extension = self.parse_result.vrm0_extension

        addon_extension.addon_version = addon_version()

        textblock = bpy.data.texts.new(name="vrm.json")
        textblock.write(json.dumps(self.parse_result.json_dict, indent=4))

        self.load_vrm0_meta(vrm0.meta, vrm0_extension.get("meta"))
        self.load_vrm0_humanoid(vrm0.humanoid, vrm0_extension.get("humanoid"))
        self.setup_vrm0_humanoid_bones()
        self.load_vrm0_first_person(
            vrm0.first_person, vrm0_extension.get("firstPerson")
        )
        self.load_vrm0_blend_shape_master(
            vrm0.blend_shape_master, vrm0_extension.get("blendShapeMaster")
        )
        self.load_vrm0_secondary_animation(
            vrm0.secondary_animation, vrm0_extension.get("secondaryAnimation")
        )
        migration.migrate(armature.name, defer=False)

    def load_vrm0_meta(self, meta: Vrm0MetaPropertyGroup, meta_dict: Json) -> None:
        if not isinstance(meta_dict, dict):
            return

        title = meta_dict.get("title")
        if isinstance(title, str):
            meta.title = title

        version = meta_dict.get("version")
        if isinstance(version, str):
            meta.version = version

        author = meta_dict.get("author")
        if isinstance(author, str):
            meta.author = author

        contact_information = meta_dict.get("contactInformation")
        if isinstance(contact_information, str):
            meta.contact_information = contact_information

        reference = meta_dict.get("reference")
        if isinstance(reference, str):
            meta.reference = reference

        allowed_user_name = meta_dict.get("allowedUserName")
        if (
            isinstance(allowed_user_name, str)
            and allowed_user_name in Vrm0MetaPropertyGroup.ALLOWED_USER_NAME_VALUES
        ):
            meta.allowed_user_name = allowed_user_name

        violent_ussage_name = meta_dict.get("violentUssageName")
        if (
            isinstance(violent_ussage_name, str)
            and violent_ussage_name in Vrm0MetaPropertyGroup.VIOLENT_USSAGE_NAME_VALUES
        ):
            meta.violent_ussage_name = violent_ussage_name

        sexual_ussage_name = meta_dict.get("sexualUssageName")
        if (
            isinstance(sexual_ussage_name, str)
            and sexual_ussage_name in Vrm0MetaPropertyGroup.SEXUAL_USSAGE_NAME_VALUES
        ):
            meta.sexual_ussage_name = sexual_ussage_name

        commercial_ussage_name = meta_dict.get("commercialUssageName")
        if (
            isinstance(commercial_ussage_name, str)
            and commercial_ussage_name
            in Vrm0MetaPropertyGroup.COMMERCIAL_USSAGE_NAME_VALUES
        ):
            meta.commercial_ussage_name = commercial_ussage_name

        other_permission_url = meta_dict.get("otherPermissionUrl")
        if isinstance(other_permission_url, str):
            meta.other_permission_url = other_permission_url

        license_name = meta_dict.get("licenseName")
        if (
            isinstance(license_name, str)
            and license_name in Vrm0MetaPropertyGroup.LICENSE_NAME_VALUES
        ):
            meta.license_name = license_name

        other_license_url = meta_dict.get("otherLicenseUrl")
        if isinstance(other_license_url, str):
            meta.other_license_url = other_license_url

        texture = meta_dict.get("texture")
        texture_dicts = self.parse_result.json_dict.get("textures")
        if (
            isinstance(texture, int)
            and isinstance(texture_dicts, list)
            # extensions.VRM.meta.texture could be -1
            # https://github.com/vrm-c/UniVRM/issues/91#issuecomment-454284964
            and 0 <= texture < len(texture_dicts)
        ):
            texture_dict = texture_dicts[texture]
            if isinstance(texture_dict, dict):
                image_index = texture_dict.get("source")
                if isinstance(image_index, int) and image_index in self.images:
                    meta.texture = self.images[image_index]

    def load_vrm0_humanoid(
        self, humanoid: Vrm0HumanoidPropertyGroup, humanoid_dict: Json
    ) -> None:
        if not isinstance(humanoid_dict, dict):
            return
        human_bone_dicts = humanoid_dict.get("humanBones")
        if isinstance(human_bone_dicts, list):
            for human_bone_dict in human_bone_dicts:
                if not isinstance(human_bone_dict, dict):
                    continue

                bone = human_bone_dict.get("bone")
                if bone not in HumanBoneSpecifications.all_names:
                    continue

                node = human_bone_dict.get("node")
                if not isinstance(node, int) or node not in self.bone_names:
                    continue

                human_bone = next(
                    (
                        human_bone
                        for human_bone in humanoid.human_bones
                        if human_bone.bone == bone
                    ),
                    None,
                )
                if human_bone:
                    logger.warning(f'Duplicated bone: "{bone}"')
                else:
                    human_bone = humanoid.human_bones.add()
                human_bone.bone = bone
                human_bone.node.set_bone_name(self.bone_names[node])

                use_default_values = human_bone_dict.get("useDefaultValues")
                if isinstance(use_default_values, bool):
                    human_bone.use_default_values = use_default_values

                min_ = convert.vrm_json_vector3_to_tuple(human_bone_dict.get("min"))
                if min_ is not None:
                    human_bone.min = min_

                max_ = convert.vrm_json_vector3_to_tuple(human_bone_dict.get("max"))
                if max_ is not None:
                    human_bone.max = max_

                center = convert.vrm_json_vector3_to_tuple(
                    human_bone_dict.get("center")
                )
                if center is not None:
                    human_bone.center = center

                axis_length = human_bone_dict.get("axisLength")
                if isinstance(axis_length, (int, float)):
                    human_bone.axis_length = axis_length

        arm_stretch = humanoid_dict.get("armStretch")
        if isinstance(arm_stretch, (int, float)):
            humanoid.arm_stretch = arm_stretch

        leg_stretch = humanoid_dict.get("legStretch")
        if isinstance(leg_stretch, (int, float)):
            humanoid.leg_stretch = leg_stretch

        upper_arm_twist = humanoid_dict.get("upperArmTwist")
        if isinstance(upper_arm_twist, (int, float)):
            humanoid.upper_arm_twist = upper_arm_twist

        lower_arm_twist = humanoid_dict.get("lowerArmTwist")
        if isinstance(lower_arm_twist, (int, float)):
            humanoid.lower_arm_twist = lower_arm_twist

        upper_leg_twist = humanoid_dict.get("upperLegTwist")
        if isinstance(upper_leg_twist, (int, float)):
            humanoid.upper_leg_twist = upper_leg_twist

        lower_leg_twist = humanoid_dict.get("lowerLegTwist")
        if isinstance(lower_leg_twist, (int, float)):
            humanoid.lower_leg_twist = lower_leg_twist

        feet_spacing = humanoid_dict.get("feetSpacing")
        if isinstance(feet_spacing, (int, float)):
            humanoid.feet_spacing = feet_spacing

        has_translation_dof = humanoid_dict.get("hasTranslationDoF")
        if isinstance(has_translation_dof, bool):
            humanoid.has_translation_dof = has_translation_dof

    def load_vrm0_first_person(
        self,
        first_person: Vrm0FirstPersonPropertyGroup,
        first_person_dict: Json,
    ) -> None:
        if not isinstance(first_person_dict, dict):
            return

        first_person_bone = first_person_dict.get("firstPersonBone")
        if isinstance(first_person_bone, int) and first_person_bone in self.bone_names:
            first_person.first_person_bone.set_bone_name(
                self.bone_names[first_person_bone]
            )

        first_person_bone_offset = convert.vrm_json_vector3_to_tuple(
            first_person_dict.get("firstPersonBoneOffset")
        )
        if first_person_bone_offset is not None:
            # Axis confusing
            (x, y, z) = first_person_bone_offset
            first_person.first_person_bone_offset = (x, z, y)

        mesh_annotation_dicts = first_person_dict.get("meshAnnotations")
        if isinstance(mesh_annotation_dicts, list):
            for mesh_annotation_dict in mesh_annotation_dicts:
                mesh_annotation = first_person.mesh_annotations.add()

                if not isinstance(mesh_annotation_dict, dict):
                    continue

                mesh = mesh_annotation_dict.get("mesh")
                if isinstance(mesh, int) and mesh in self.meshes:
                    mesh_annotation.mesh.mesh_object_name = self.meshes[mesh].name

                first_person_flag = mesh_annotation_dict.get("firstPersonFlag")
                if (
                    isinstance(first_person_flag, str)
                    and first_person_flag
                    in Vrm0MeshAnnotationPropertyGroup.FIRST_PERSON_FLAG_VALUES
                ):
                    mesh_annotation.first_person_flag = first_person_flag

        look_at_type_name = first_person_dict.get("lookAtTypeName")
        if (
            isinstance(look_at_type_name, str)
            and look_at_type_name
            in Vrm0FirstPersonPropertyGroup.LOOK_AT_TYPE_NAME_VALUES
        ):
            first_person.look_at_type_name = look_at_type_name

        for look_at, look_at_dict in [
            (
                first_person.look_at_horizontal_inner,
                first_person_dict.get("lookAtHorizontalInner"),
            ),
            (
                first_person.look_at_horizontal_outer,
                first_person_dict.get("lookAtHorizontalOuter"),
            ),
            (
                first_person.look_at_vertical_down,
                first_person_dict.get("lookAtVerticalDown"),
            ),
            (
                first_person.look_at_vertical_up,
                first_person_dict.get("lookAtVerticalUp"),
            ),
        ]:
            if not isinstance(look_at_dict, dict):
                continue

            curve = convert.vrm_json_curve_to_list(look_at_dict.get("curve"))
            if curve is not None:
                look_at.curve = curve

            x_range = look_at_dict.get("xRange")
            if isinstance(x_range, (float, int)):
                look_at.x_range = x_range

            y_range = look_at_dict.get("yRange")
            if isinstance(y_range, (float, int)):
                look_at.y_range = y_range

    def load_vrm0_blend_shape_master(
        self,
        blend_shape_master: Vrm0BlendShapeMasterPropertyGroup,
        blend_shape_master_dict: Json,
    ) -> None:
        if not isinstance(blend_shape_master_dict, dict):
            return
        blend_shape_group_dicts = blend_shape_master_dict.get("blendShapeGroups")
        if not isinstance(blend_shape_group_dicts, list):
            return

        for blend_shape_group_dict in blend_shape_group_dicts:
            blend_shape_group = blend_shape_master.blend_shape_groups.add()

            if not isinstance(blend_shape_group_dict, dict):
                continue

            name = blend_shape_group_dict.get("name")
            if isinstance(name, str):
                blend_shape_group.name = name

            preset_name = blend_shape_group_dict.get("presetName")
            if (
                isinstance(preset_name, str)
                and preset_name in Vrm0BlendShapeGroupPropertyGroup.PRESET_NAME_VALUES
            ):
                blend_shape_group.preset_name = preset_name

            bind_dicts = blend_shape_group_dict.get("binds")
            if isinstance(bind_dicts, list):
                for bind_dict in bind_dicts:
                    if not isinstance(bind_dict, dict):
                        continue

                    mesh_index = bind_dict.get("mesh")
                    if not isinstance(mesh_index, int):
                        continue

                    mesh_object = self.meshes.get(mesh_index)
                    if not mesh_object:
                        continue

                    bind = blend_shape_group.binds.add()
                    bind.mesh.mesh_object_name = mesh_object.name
                    mesh_data = mesh_object.data
                    if isinstance(mesh_data, Mesh):
                        shape_keys = mesh_data.shape_keys
                        if shape_keys:
                            index = bind_dict.get("index")
                            if isinstance(index, int) and (
                                1 <= (index + 1) < len(shape_keys.key_blocks)
                            ):
                                bind.index = list(shape_keys.key_blocks.keys())[
                                    index + 1
                                ]
                    weight = bind_dict.get("weight")
                    if not isinstance(weight, (int, float)):
                        weight = 0
                    bind.weight = min(max(weight / 100.0, 0), 1)

            material_value_dicts = blend_shape_group_dict.get("materialValues")
            if isinstance(material_value_dicts, list):
                for material_value_dict in material_value_dicts:
                    material_value = blend_shape_group.material_values.add()

                    if not isinstance(material_value_dict, dict):
                        continue

                    material_name = material_value_dict.get("materialName")
                    if (
                        isinstance(material_name, str)
                        and material_name in bpy.data.materials
                    ):
                        material_value.material = bpy.data.materials[material_name]

                    property_name = material_value_dict.get("propertyName")
                    if isinstance(property_name, str):
                        material_value.property_name = property_name

                    target_value_vector = material_value_dict.get("targetValue")
                    if isinstance(target_value_vector, list):
                        for v in target_value_vector:
                            material_value.target_value.add().value = (
                                v if isinstance(v, (int, float)) else 0
                            )

            is_binary = blend_shape_group_dict.get("isBinary")
            if isinstance(is_binary, bool):
                blend_shape_group.is_binary = is_binary

    def load_vrm0_secondary_animation(
        self,
        secondary_animation: Vrm0SecondaryAnimationPropertyGroup,
        secondary_animation_dict: Json,
    ) -> None:
        if not isinstance(secondary_animation_dict, dict):
            return
        armature = self.armature
        if armature is None:
            message = "armature is None"
            raise ValueError(message)

        collider_group_dicts = secondary_animation_dict.get("colliderGroups")
        if not isinstance(collider_group_dicts, list):
            collider_group_dicts = []

        self.context.view_layer.depsgraph.update()
        self.context.scene.view_layers.update()
        collider_objs = []
        for collider_group_dict in collider_group_dicts:
            collider_group = secondary_animation.collider_groups.add()
            collider_group.uuid = uuid.uuid4().hex
            collider_group.refresh(armature)

            if not isinstance(collider_group_dict, dict):
                continue

            node = collider_group_dict.get("node")
            if not isinstance(node, int) or node not in self.bone_names:
                continue

            bone_name = self.bone_names[node]
            collider_group.node.set_bone_name(bone_name)
            collider_dicts = collider_group_dict.get("colliders")
            if not isinstance(collider_dicts, list):
                continue

            for collider_index, collider_dict in enumerate(collider_dicts):
                collider = collider_group.colliders.add()

                if not isinstance(collider_dict, dict):
                    continue

                offset = convert.vrm_json_vector3_to_tuple(collider_dict.get("offset"))
                if offset is None:
                    offset = (0, 0, 0)

                radius = collider_dict.get("radius")
                if not isinstance(radius, (int, float)):
                    radius = 0

                collider_name = f"{bone_name}_collider_{collider_index}"
                obj = bpy.data.objects.new(name=collider_name, object_data=None)
                collider.bpy_object = obj
                obj.parent = self.armature
                obj.parent_type = "BONE"
                obj.parent_bone = bone_name
                fixed_offset = [
                    offset[axis] * inv for axis, inv in zip([0, 2, 1], [-1, -1, 1])
                ]  # TODO: Y軸反転はUniVRMのシリアライズに合わせてる

                # boneのtail側にparentされるので、根元からのpositionに動かしなおす
                obj.matrix_world = Matrix.Translation(
                    [
                        armature.matrix_world.to_translation()[i]
                        + self.armature_data.bones[
                            bone_name
                        ].matrix_local.to_translation()[i]
                        + fixed_offset[i]
                        for i in range(3)
                    ]
                )

                obj.empty_display_size = radius
                obj.empty_display_type = "SPHERE"
                collider_objs.append(obj)
        if collider_objs:
            colliders_collection = bpy.data.collections.new("Colliders")
            self.context.scene.collection.children.link(colliders_collection)
            for collider_obj in collider_objs:
                colliders_collection.objects.link(collider_obj)

        for collider_group in secondary_animation.collider_groups:
            collider_group.refresh(armature)

        bone_group_dicts = secondary_animation_dict.get("boneGroups")
        if not isinstance(bone_group_dicts, list):
            bone_group_dicts = []

        for bone_group_dict in bone_group_dicts:
            bone_group = secondary_animation.bone_groups.add()

            if not isinstance(bone_group_dict, dict):
                bone_group.refresh(armature)
                continue

            comment = bone_group_dict.get("comment")
            if isinstance(comment, str):
                bone_group.comment = comment

            stiffiness = bone_group_dict.get("stiffiness")
            if isinstance(stiffiness, (int, float)):
                bone_group.stiffiness = stiffiness

            gravity_power = bone_group_dict.get("gravityPower")
            if isinstance(gravity_power, (int, float)):
                bone_group.gravity_power = gravity_power

            gravity_dir = convert.vrm_json_vector3_to_tuple(
                bone_group_dict.get("gravityDir")
            )
            if gravity_dir is not None:
                # Axis confusing
                (x, y, z) = gravity_dir
                bone_group.gravity_dir = (x, z, y)

            drag_force = bone_group_dict.get("dragForce")
            if isinstance(drag_force, (int, float)):
                bone_group.drag_force = drag_force

            center = bone_group_dict.get("center")
            if isinstance(center, int) and center in self.bone_names:
                bone_group.center.set_bone_name(self.bone_names[center])

            hit_radius = bone_group_dict.get("hitRadius")
            if isinstance(hit_radius, (int, float)):
                bone_group.hit_radius = hit_radius

            bones = bone_group_dict.get("bones")
            if isinstance(bones, list):
                for bone in bones:
                    bone_prop = bone_group.bones.add()
                    if not isinstance(bone, int) or bone not in self.bone_names:
                        continue

                    bone_prop.set_bone_name(self.bone_names[bone])

            collider_group_dicts = bone_group_dict.get("colliderGroups")
            if isinstance(collider_group_dicts, list):
                for collider_group in collider_group_dicts:
                    if not isinstance(collider_group, int) or not (
                        0 <= collider_group < len(secondary_animation.collider_groups)
                    ):
                        continue
                    collider_group_uuid = bone_group.collider_groups.add()
                    collider_group_uuid.value = secondary_animation.collider_groups[
                        collider_group
                    ].uuid

        for bone_group in secondary_animation.bone_groups:
            bone_group.refresh(armature)

    def viewport_setup(self) -> None:
        if self.armature:
            if self.preferences.set_armature_display_to_wire:
                self.armature.display_type = "WIRE"
            if self.preferences.set_armature_display_to_show_in_front:
                self.armature.show_in_front = True
            if self.preferences.set_armature_bone_shape_to_default:
                for bone in self.armature.pose.bones:
                    bone.custom_shape = None

        if self.preferences.set_view_transform_to_standard_on_import:
            # https://github.com/saturday06/VRM-Addon-for-Blender/issues/336#issuecomment-1760729404
            view_settings = self.context.scene.view_settings
            try:
                view_settings.view_transform = "Standard"
            except TypeError:
                logger.exception(
                    "scene.view_settings.view_transform"
                    + ' doesn\'t support "Standard".'
                )

        if self.preferences.set_shading_type_to_material_on_import:
            screen = self.context.screen
            for area in screen.areas:
                for space in area.spaces:
                    if space.type == "VIEW_3D" and isinstance(space, SpaceView3D):
                        space.shading.type = "MATERIAL"
