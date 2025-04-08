import math
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from pathlib import Path
from sys import float_info
from typing import TYPE_CHECKING, Optional

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import (
    Context,
    Event,
    Material,
    Mesh,
    Node,
    NodesModifier,
    Object,
    Operator,
    ShaderNodeMapping,
)
from bpy_extras.io_utils import ImportHelper

from ...common import convert, shader
from ...common.logging import get_logger
from .. import search
from .property_group import (
    Mtoon0ReceiveShadowTexturePropertyGroup,
    Mtoon0ShadingGradeTexturePropertyGroup,
    Mtoon1BaseColorTexturePropertyGroup,
    Mtoon1EmissiveTexturePropertyGroup,
    Mtoon1MatcapTexturePropertyGroup,
    Mtoon1MaterialPropertyGroup,
    Mtoon1NormalTexturePropertyGroup,
    Mtoon1OutlineWidthMultiplyTexturePropertyGroup,
    Mtoon1RimMultiplyTexturePropertyGroup,
    Mtoon1SamplerPropertyGroup,
    Mtoon1ShadeMultiplyTexturePropertyGroup,
    Mtoon1ShadingShiftTexturePropertyGroup,
    Mtoon1TextureInfoPropertyGroup,
    Mtoon1UvAnimationMaskTexturePropertyGroup,
    Mtoon1VrmcMaterialsMtoonPropertyGroup,
    reset_shader_node_group,
)

logger = get_logger(__name__)


class VRM_OT_convert_material_to_mtoon1(Operator):
    bl_idname = "vrm.convert_material_to_mtoon1"
    bl_label = "Convert Material to MToon 1.0"
    bl_description = "Convert Material to MToon 1.0"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    material_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"}
    )

    def execute(self, context: Context) -> set[str]:
        material = bpy.data.materials.get(self.material_name)
        if not isinstance(material, Material):
            return {"CANCELLED"}
        self.convert_material_to_mtoon1(context, material)
        return {"FINISHED"}

    @staticmethod
    def assign_mtoon_unversioned_image(
        texture_info: Mtoon1TextureInfoPropertyGroup,
        image_name_and_sampler_type: Optional[tuple[str, int, int]],
        uv_offset: tuple[float, float],
        uv_scale: tuple[float, float],
    ) -> None:
        texture_info.extensions.khr_texture_transform.offset = uv_offset
        texture_info.extensions.khr_texture_transform.scale = uv_scale

        if image_name_and_sampler_type is None:
            return

        image_name, wrap_number, filter_number = image_name_and_sampler_type
        image = bpy.data.images.get(image_name)
        if not image:
            return

        texture_info.index.source = image

        mag_filter = Mtoon1SamplerPropertyGroup.MAG_FILTER_NUMBER_TO_ID.get(
            filter_number
        )
        if mag_filter:
            texture_info.index.sampler.mag_filter = mag_filter

        min_filter = Mtoon1SamplerPropertyGroup.MIN_FILTER_NUMBER_TO_ID.get(
            filter_number
        )
        if min_filter:
            texture_info.index.sampler.min_filter = min_filter

        wrap = Mtoon1SamplerPropertyGroup.WRAP_NUMBER_TO_ID.get(wrap_number)
        if wrap:
            texture_info.index.sampler.wrap_s = wrap
            texture_info.index.sampler.wrap_t = wrap

    def convert_material_to_mtoon1(self, context: Context, material: Material) -> None:
        node = search.vrm_shader_node(material)
        if isinstance(node, Node) and node.node_tree["SHADER"] == "MToon_unversioned":
            self.convert_mtoon_unversioned_to_mtoon1(context, material, node)
            return

        addon_version = tuple(material.vrm_addon_extension.mtoon1.addon_version)
        reset_shader_node_group(
            context,
            material,
            reset_node_tree=True,
            overwrite=(addon_version < (2, 20, 8)),
        )

    def convert_mtoon_unversioned_to_mtoon1(
        self,
        context: Context,
        material: Material,
        node: Node,
    ) -> None:
        transparent_with_z_write = False
        alpha_cutoff: Optional[float] = 0.5
        if material.blend_method == "OPAQUE":
            alpha_mode = Mtoon1MaterialPropertyGroup.ALPHA_MODE_OPAQUE
        elif material.blend_method == "CLIP":
            alpha_cutoff = shader.get_float_value(node, "CutoffRate", 0, float_info.max)
            if alpha_cutoff is None:
                alpha_cutoff = 0.5
            alpha_mode = Mtoon1MaterialPropertyGroup.ALPHA_MODE_MASK
        else:
            alpha_mode = Mtoon1MaterialPropertyGroup.ALPHA_MODE_BLEND
            transparent_with_z_write_float = shader.get_float_value(
                node, "TransparentWithZWrite"
            )
            transparent_with_z_write = (
                transparent_with_z_write_float is not None
                and math.fabs(transparent_with_z_write_float) >= float_info.epsilon
            )

        base_color_factor = shader.get_rgba_value(node, "DiffuseColor", 0.0, 1.0) or (
            0,
            0,
            0,
            1,
        )
        base_color_texture = shader.get_image_name_and_sampler_type(
            node,
            "MainTexture",
        )

        uv_offset = (0.0, 0.0)
        uv_scale = (1.0, 1.0)

        main_texture_socket = node.inputs.get("MainTexture")
        if (
            main_texture_socket
            and main_texture_socket.links
            and main_texture_socket.links[0]
            and main_texture_socket.links[0].from_node
            and main_texture_socket.links[0].from_node.inputs
            and main_texture_socket.links[0].from_node.inputs[0]
            and main_texture_socket.links[0].from_node.inputs[0].links
            and main_texture_socket.links[0].from_node.inputs[0].links[0]
            and main_texture_socket.links[0].from_node.inputs[0].links[0].from_node
        ):
            mapping_node = (
                main_texture_socket.links[0].from_node.inputs[0].links[0].from_node
            )
            if isinstance(mapping_node, ShaderNodeMapping):
                location_socket = mapping_node.inputs.get("Location")
                if location_socket and isinstance(
                    location_socket, shader.VECTOR_SOCKET_CLASSES
                ):
                    uv_offset = (
                        float(location_socket.default_value[0]),
                        float(location_socket.default_value[1]),
                    )

                scale_socket = mapping_node.inputs.get("Scale")
                if scale_socket and isinstance(
                    scale_socket, shader.VECTOR_SOCKET_CLASSES
                ):
                    uv_scale = (
                        float(scale_socket.default_value[0]),
                        float(scale_socket.default_value[1]),
                    )

        shade_color_factor = shader.get_rgb_value(node, "ShadeColor", 0.0, 1.0) or (
            0,
            0,
            0,
        )
        shade_multiply_texture = shader.get_image_name_and_sampler_type(
            node,
            "ShadeTexture",
        )
        normal_texture = shader.get_image_name_and_sampler_type(
            node,
            "NormalmapTexture",
        )
        if not normal_texture:
            normal_texture = shader.get_image_name_and_sampler_type(
                node,
                "NomalmapTexture",
            )
        normal_texture_scale = shader.get_float_value(node, "BumpScale")

        shading_shift_0x = shader.get_float_value(node, "ShadeShift")
        if shading_shift_0x is None:
            shading_shift_0x = 0.0

        shading_toony_0x = shader.get_float_value(node, "ShadeToony")
        if shading_toony_0x is None:
            shading_toony_0x = 0.0

        shading_shift_factor = convert.mtoon_shading_shift_0_to_1(
            shading_toony_0x, shading_shift_0x
        )

        shading_toony_factor = convert.mtoon_shading_toony_0_to_1(
            shading_toony_0x, shading_shift_0x
        )

        gi_equalization_0x = shader.get_float_value(node, "IndirectLightIntensity")
        gi_equalization_factor = None
        if gi_equalization_0x is not None:
            gi_equalization_factor = convert.mtoon_intensity_to_gi_equalization(
                gi_equalization_0x
            )

        emissive_factor = shader.get_rgb_value(node, "EmissionColor", 0.0, 1.0) or (
            0,
            0,
            0,
        )
        emissive_texture = shader.get_image_name_and_sampler_type(
            node,
            "Emission_Texture",
        )
        matcap_texture = shader.get_image_name_and_sampler_type(
            node,
            "SphereAddTexture",
        )

        parametric_rim_color_factor = shader.get_rgb_value(node, "RimColor", 0.0, 1.0)
        parametric_rim_fresnel_power_factor = shader.get_float_value(
            node, "RimFresnelPower", 0.0, float_info.max
        )
        parametric_rim_lift_factor = shader.get_float_value(node, "RimLift")

        rim_multiply_texture = shader.get_image_name_and_sampler_type(
            node,
            "RimTexture",
        )

        centimeter_to_meter = 0.01
        one_hundredth = 0.01

        outline_width_mode_float = shader.get_float_value(node, "OutlineWidthMode")
        outline_width = shader.get_float_value(node, "OutlineWidth")
        if outline_width is None:
            outline_width = 0.0
        outline_width_multiply_texture = shader.get_image_name_and_sampler_type(
            node,
            "OutlineWidthTexture",
        )

        outline_color_factor = shader.get_rgb_value(node, "OutlineColor", 0.0, 1.0) or (
            0,
            0,
            0,
        )

        outline_color_mode = shader.get_float_value(node, "OutlineColorMode")
        if outline_color_mode is not None:
            outline_color_mode = int(round(outline_color_mode))
        else:
            outline_color_mode = 0

        outline_lighting_mix_factor = 0.0
        if outline_color_mode == 1:
            outline_lighting_mix_factor = (
                shader.get_float_value(node, "OutlineLightingMix") or 1.0
            )

        uv_animation_mask_texture = shader.get_image_name_and_sampler_type(
            node,
            "UV_Animation_Mask_Texture",
        )
        uv_animation_rotation_speed_factor = shader.get_float_value(
            node, "UV_Scroll_Rotation"
        )
        uv_animation_scroll_x_speed_factor = shader.get_float_value(node, "UV_Scroll_X")
        uv_animation_scroll_y_speed_factor = shader.get_float_value(node, "UV_Scroll_Y")
        if isinstance(uv_animation_scroll_y_speed_factor, float):
            uv_animation_scroll_y_speed_factor *= -1

        shader.load_mtoon1_shader(context, material, overwrite=True)

        gltf = material.vrm_addon_extension.mtoon1
        mtoon = gltf.extensions.vrmc_materials_mtoon

        gltf.alpha_mode = alpha_mode
        gltf.alpha_cutoff = alpha_cutoff
        mtoon.transparent_with_z_write = transparent_with_z_write
        gltf.pbr_metallic_roughness.base_color_factor = base_color_factor
        self.assign_mtoon_unversioned_image(
            gltf.pbr_metallic_roughness.base_color_texture,
            base_color_texture,
            uv_offset,
            uv_scale,
        )
        mtoon.shade_color_factor = shade_color_factor
        self.assign_mtoon_unversioned_image(
            mtoon.shade_multiply_texture,
            shade_multiply_texture,
            uv_offset,
            uv_scale,
        )
        self.assign_mtoon_unversioned_image(
            gltf.normal_texture,
            normal_texture,
            uv_offset,
            uv_scale,
        )
        if normal_texture_scale is not None:
            gltf.normal_texture.scale = normal_texture_scale

        mtoon.shading_shift_factor = shading_shift_factor
        mtoon.shading_toony_factor = shading_toony_factor

        if gi_equalization_factor is not None:
            mtoon.gi_equalization_factor = gi_equalization_factor

        gltf.emissive_factor = emissive_factor
        self.assign_mtoon_unversioned_image(
            gltf.emissive_texture,
            emissive_texture,
            uv_offset,
            uv_scale,
        )
        self.assign_mtoon_unversioned_image(
            mtoon.matcap_texture,
            matcap_texture,
            (0, 0),
            (1, 1),
        )

        if parametric_rim_color_factor is not None:
            mtoon.parametric_rim_color_factor = parametric_rim_color_factor
        if parametric_rim_fresnel_power_factor is not None:
            mtoon.parametric_rim_fresnel_power_factor = (
                parametric_rim_fresnel_power_factor
            )
        if parametric_rim_lift_factor is not None:
            mtoon.parametric_rim_lift_factor = parametric_rim_lift_factor

        self.assign_mtoon_unversioned_image(
            mtoon.rim_multiply_texture,
            rim_multiply_texture,
            uv_offset,
            uv_scale,
        )

        # https://github.com/vrm-c/UniVRM/blob/7c9919ef47a25c04100a2dcbe6a75dff49ef4857/Assets/VRM10/Runtime/Migration/Materials/MigrationMToonMaterial.cs#L287-L290
        mtoon.rim_lighting_mix_factor = 1.0

        centimeter_to_meter = 0.01
        one_hundredth = 0.01

        if outline_width_mode_float is not None:
            outline_width_mode = int(round(outline_width_mode_float))
        else:
            outline_width_mode = 0

        if outline_width_mode == 1:
            mtoon.outline_width_mode = mtoon.OUTLINE_WIDTH_MODE_WORLD_COORDINATES
            mtoon.outline_width_factor = max(0.0, outline_width * centimeter_to_meter)
        elif outline_width_mode == 2:
            mtoon.outline_width_mode = mtoon.OUTLINE_WIDTH_MODE_SCREEN_COORDINATES
            mtoon.outline_width_factor = max(0.0, outline_width * one_hundredth * 0.5)
        else:
            mtoon.outline_width_mode = mtoon.OUTLINE_WIDTH_MODE_NONE

        self.assign_mtoon_unversioned_image(
            mtoon.outline_width_multiply_texture,
            outline_width_multiply_texture,
            uv_offset,
            uv_scale,
        )

        mtoon.outline_color_factor = outline_color_factor
        mtoon.outline_lighting_mix_factor = 0.0
        if outline_color_mode == 1:
            mtoon.outline_lighting_mix_factor = outline_lighting_mix_factor

        self.assign_mtoon_unversioned_image(
            mtoon.uv_animation_mask_texture,
            uv_animation_mask_texture,
            uv_offset,
            uv_scale,
        )

        if uv_animation_rotation_speed_factor is not None:
            mtoon.uv_animation_rotation_speed_factor = (
                uv_animation_rotation_speed_factor
            )
        if uv_animation_scroll_x_speed_factor is not None:
            mtoon.uv_animation_scroll_x_speed_factor = (
                uv_animation_scroll_x_speed_factor
            )
        if uv_animation_scroll_y_speed_factor is not None:
            mtoon.uv_animation_scroll_y_speed_factor = (
                uv_animation_scroll_y_speed_factor
            )

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        material_name: str  # type: ignore[no-redef]


class VRM_OT_convert_mtoon1_to_bsdf_principled(Operator):
    bl_idname = "vrm.convert_mtoon1_to_bsdf_principled"
    bl_label = "Convert MToon 1.0 to Principled BSDF"
    bl_description = "Convert MToon 1.0 to Principled BSDF"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    material_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"}
    )

    def execute(self, _context: Context) -> set[str]:
        material = bpy.data.materials.get(self.material_name)
        if not isinstance(material, Material):
            return {"CANCELLED"}
        self.convert_mtoon1_to_bsdf_principled(material)
        return {"FINISHED"}

    def convert_mtoon1_to_bsdf_principled(self, material: Material) -> None:
        if not material.use_nodes:
            material.use_nodes = True
        shader.clear_node_tree(material.node_tree, clear_inputs_outputs=True)
        if not material.node_tree:
            logger.error(f"{material.name}'s node tree is None")
            return
        shader_node = material.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        output_node = material.node_tree.nodes.new("ShaderNodeOutputMaterial")
        material.node_tree.links.new(
            output_node.inputs["Surface"], shader_node.outputs["BSDF"]
        )

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        material_name: str  # type: ignore[no-redef]


class VRM_OT_reset_mtoon1_material_shader_node_tree(Operator):
    bl_idname = "vrm.reset_mtoon1_material_shader_node_group"
    bl_label = "Reset Shader Nodes"
    bl_description = "Reset MToon 1.0 Material Shader Node Tree"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    material_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"}
    )

    def execute(self, context: Context) -> set[str]:
        material = bpy.data.materials.get(self.material_name)
        if not isinstance(material, Material):
            return {"CANCELLED"}
        reset_shader_node_group(context, material, reset_node_tree=True, overwrite=True)
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        material_name: str  # type: ignore[no-redef]


class VRM_OT_import_mtoon1_texture_image_file(Operator, ImportHelper):
    bl_idname = "vrm.import_mtoon1_texture_image_file"
    bl_label = "Open"
    bl_description = "Import Texture Image File"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    filepath: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        default="",
    )

    filter_glob: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        # https://docs.blender.org/api/2.83/Image.html#Image.file_format
        default=(
            "*.bmp"
            ";*.sgi"
            ";*.bw"
            ";*.rgb"
            ";*.rgba"
            ";*.png"
            ";*.jpg"
            ";*.jpeg"
            ";*.jp2"
            ";*.tga"
            ";*.cin"
            ";*.dpx"
            ";*.exr"
            ";*.hdr"
            ";*.tif"
            ";*.tiff"
        ),
    )

    material_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )

    target_texture_items = (
        (Mtoon1BaseColorTexturePropertyGroup.__name__, "", "", "NONE", 0),
        (Mtoon1ShadeMultiplyTexturePropertyGroup.__name__, "", "", "NONE", 1),
        (Mtoon1NormalTexturePropertyGroup.__name__, "", "", "NONE", 2),
        (Mtoon1ShadingShiftTexturePropertyGroup.__name__, "", "", "NONE", 3),
        (Mtoon1EmissiveTexturePropertyGroup.__name__, "", "", "NONE", 4),
        (Mtoon1RimMultiplyTexturePropertyGroup.__name__, "", "", "NONE", 5),
        (Mtoon1MatcapTexturePropertyGroup.__name__, "", "", "NONE", 6),
        (
            Mtoon1OutlineWidthMultiplyTexturePropertyGroup.__name__,
            "",
            "",
            "NONE",
            7,
        ),
        (Mtoon1UvAnimationMaskTexturePropertyGroup.__name__, "", "", "NONE", 8),
        (Mtoon0ReceiveShadowTexturePropertyGroup.__name__, "", "", "NONE", 9),
        (Mtoon0ShadingGradeTexturePropertyGroup.__name__, "", "", "NONE", 10),
    )

    target_texture: EnumProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        items=target_texture_items,
        name="Target Texture",
    )

    def execute(self, _context: Context) -> set[str]:
        filepath = self.filepath
        if not filepath or not Path(filepath).exists():
            return {"CANCELLED"}

        last_images_len = len(bpy.data.images)
        image = bpy.data.images.load(filepath, check_existing=True)
        created = last_images_len < len(bpy.data.images)

        material = bpy.data.materials.get(self.material_name)
        if not isinstance(material, Material):
            return {"FINISHED"}

        gltf = material.vrm_addon_extension.mtoon1
        mtoon = gltf.extensions.vrmc_materials_mtoon

        for texture in [
            gltf.pbr_metallic_roughness.base_color_texture.index,
            mtoon.shade_multiply_texture.index,
            gltf.normal_texture.index,
            mtoon.shading_shift_texture.index,
            gltf.emissive_texture.index,
            mtoon.rim_multiply_texture.index,
            mtoon.matcap_texture.index,
            mtoon.outline_width_multiply_texture.index,
            mtoon.uv_animation_mask_texture.index,
            gltf.mtoon0_receive_shadow_texture,
            gltf.mtoon0_shading_grade_texture,
        ]:
            if self.target_texture != type(texture).__name__:
                continue
            texture.source = image
            if created:
                image.colorspace_settings.name = type(texture).colorspace
            return {"FINISHED"}

        return {"CANCELLED"}

    def invoke(self, context: Context, event: Event) -> set[str]:
        self.filepath = ""
        return ImportHelper.invoke(self, context, event)

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        filepath: str  # type: ignore[no-redef]
        filter_glob: str  # type: ignore[no-redef]
        material_name: str  # type: ignore[no-redef]
        target_texture: str  # type: ignore[no-redef]


@dataclass(frozen=True)
class NodesModifierInputKey:
    geometry_key: str
    material_key: str
    outline_material_key: str
    outline_width_mode_key: str
    outline_width_factor_key: str
    outline_width_multiply_texture_key: str
    outline_width_multiply_texture_exists_key: str
    outline_width_multiply_texture_uv_key: str
    outline_width_multiply_texture_uv_offset_x_key: str
    outline_width_multiply_texture_uv_offset_y_key: str
    outline_width_multiply_texture_uv_scale_x_key: str
    outline_width_multiply_texture_uv_scale_y_key: str
    extrude_mesh_individual_key: str
    object_key: str
    enabled_key: str

    @staticmethod
    def keys_len() -> int:
        return 15

    def outline_width_multiply_texture_uv_use_attribute_key(self) -> str:
        return self.outline_width_multiply_texture_uv_key + "_use_attribute"

    def outline_width_multiply_texture_uv_attribute_name_key(self) -> str:
        return self.outline_width_multiply_texture_uv_key + "_attribute_name"


def get_nodes_modifier_input_key(
    modifier: NodesModifier,
) -> Optional[NodesModifierInputKey]:
    node_group = modifier.node_group
    if not node_group:
        return None
    if bpy.app.version < (4, 0):
        keys = [i.identifier for i in node_group.inputs]
    else:
        from bpy.types import NodeTreeInterfaceSocket

        keys = [
            item.identifier
            for item in node_group.interface.items_tree
            if item.item_type == "SOCKET"
            and isinstance(item, NodeTreeInterfaceSocket)
            and item.in_out == "INPUT"
        ]
    keys_len = NodesModifierInputKey.keys_len()
    if len(keys) < keys_len:
        return None
    return NodesModifierInputKey(*keys[:keys_len])


class VRM_OT_refresh_mtoon1_outline(Operator):
    bl_idname = "vrm.refresh_mtoon1_outline"
    bl_label = "Refresh MToon 1.0 Outline Width Mode"
    bl_description = "Import Texture Image File"
    bl_options: AbstractSet[str] = {"UNDO"}

    material_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"}
    )
    create_modifier: BoolProperty(  # type: ignore[valid-type]
        options={"HIDDEN"}
    )

    @staticmethod
    def assign(
        context: Context,
        material: Material,
        obj: Object,
        create_modifier: bool,
    ) -> None:
        shader.load_mtoon1_outline_geometry_node_group(context, overwrite=False)
        node_group = context.blend_data.node_groups.get(
            shader.OUTLINE_GEOMETRY_GROUP_NAME
        )
        if not node_group:
            return
        mtoon = material.vrm_addon_extension.mtoon1.extensions.vrmc_materials_mtoon
        outline_width_mode_value = next(
            (
                value
                for mode, _, _, _, value in (
                    Mtoon1VrmcMaterialsMtoonPropertyGroup.outline_width_mode_items
                )
                if mode == mtoon.outline_width_mode
            ),
            None,
        )
        if not isinstance(outline_width_mode_value, int):
            return

        no_outline = (
            mtoon.outline_width_mode
            == Mtoon1VrmcMaterialsMtoonPropertyGroup.OUTLINE_WIDTH_MODE_NONE
            or mtoon.outline_width_factor < float_info.epsilon
        )
        cleanup = no_outline
        modifier = None

        for search_modifier_name in list(obj.modifiers.keys()):
            search_modifier = obj.modifiers.get(search_modifier_name)
            if not search_modifier:
                continue
            if search_modifier.type != "NODES":
                continue
            if not isinstance(search_modifier, NodesModifier):
                continue
            if not search_modifier.node_group:
                continue
            if search_modifier.node_group.name != shader.OUTLINE_GEOMETRY_GROUP_NAME:
                continue
            input_key = get_nodes_modifier_input_key(search_modifier)
            if input_key is None:
                continue
            search_material = search_modifier.get(input_key.material_key)
            if not isinstance(search_material, Material):
                continue
            if search_material.name != material.name:
                continue
            if cleanup:
                obj.modifiers.remove(search_modifier)
                continue
            modifier = search_modifier
            cleanup = True

        if no_outline:
            return

        if not modifier and not create_modifier:
            if not no_outline:
                mtoon.outline_width_mode = (
                    Mtoon1VrmcMaterialsMtoonPropertyGroup.OUTLINE_WIDTH_MODE_NONE
                )
            return

        outline_material_name = f"MToon Outline ({material.name})"
        modifier_name = f"MToon Outline ({material.name})"

        outline_material = material.vrm_addon_extension.mtoon1.outline_material
        reset_outline_material = not outline_material
        if reset_outline_material:
            outline_material = context.blend_data.materials.new(
                name=outline_material_name
            )
            if not outline_material.use_nodes:
                outline_material.use_nodes = True
            if outline_material.diffuse_color[3] != 0.25:
                outline_material.diffuse_color[3] = 0.25
            if outline_material.roughness != 0:
                outline_material.roughness = 0
            shader.load_mtoon1_shader(context, outline_material, overwrite=False)
            outline_material.vrm_addon_extension.mtoon1.is_outline_material = True
            material.vrm_addon_extension.mtoon1.outline_material = outline_material
        if outline_material.name != outline_material_name:
            outline_material.name = outline_material_name
        if not outline_material.use_nodes:
            outline_material.use_nodes = True
        if not outline_material.vrm_addon_extension.mtoon1.is_outline_material:
            outline_material.vrm_addon_extension.mtoon1.is_outline_material = True
        if (
            outline_material.vrm_addon_extension.mtoon1.alpha_cutoff
            != material.vrm_addon_extension.mtoon1.alpha_cutoff
        ):
            outline_material.vrm_addon_extension.mtoon1.alpha_cutoff = (
                material.vrm_addon_extension.mtoon1.alpha_cutoff
            )
        if (
            outline_material.vrm_addon_extension.mtoon1.alpha_mode
            != material.vrm_addon_extension.mtoon1.alpha_mode
        ):
            outline_material.vrm_addon_extension.mtoon1.alpha_mode = (
                material.vrm_addon_extension.mtoon1.alpha_mode
            )
        if outline_material.shadow_method != "NONE":
            outline_material.shadow_method = "NONE"
        if not outline_material.use_backface_culling:
            outline_material.use_backface_culling = True
        if outline_material.show_transparent_back:
            outline_material.show_transparent_back = False

        if not modifier:
            new_modifier = obj.modifiers.new(modifier_name, "NODES")
            if not isinstance(new_modifier, NodesModifier):
                message = f"{type(new_modifier)} is not a NodesModifier"
                raise AssertionError(message)
            modifier = new_modifier
            modifier.show_expanded = False
            modifier.show_in_editmode = False

        if modifier.name != modifier_name:
            modifier.name = modifier_name
        if modifier.node_group != node_group:
            modifier.node_group = node_group

        input_key = get_nodes_modifier_input_key(modifier)
        if input_key is None:
            return

        modifier_input_changed = False

        (
            outline_width_multiply_texture_uv_offset_x,
            outline_width_multiply_texture_uv_offset_y,
        ) = mtoon.outline_width_multiply_texture.extensions.khr_texture_transform.offset
        (
            outline_width_multiply_texture_uv_scale_x,
            outline_width_multiply_texture_uv_scale_y,
        ) = mtoon.outline_width_multiply_texture.extensions.khr_texture_transform.scale

        uv_layer_name = None
        if isinstance(obj.data, Mesh):
            uv_layer_name = next(
                (
                    uv_layer.name
                    for uv_layer in obj.data.uv_layers
                    if uv_layer and uv_layer.active_render
                ),
                None,
            )
        if uv_layer_name is None:
            uv_layer_name = "UVMap"

        has_auto_smooth = tuple(bpy.app.version) < (4, 1)
        for k, v in [
            (input_key.material_key, material),
            (input_key.outline_material_key, outline_material),
            (input_key.outline_width_mode_key, outline_width_mode_value),
            (input_key.outline_width_factor_key, mtoon.outline_width_factor),
            (
                input_key.outline_width_multiply_texture_key,
                mtoon.outline_width_multiply_texture.index.source,
            ),
            (
                input_key.outline_width_multiply_texture_exists_key,
                bool(mtoon.outline_width_multiply_texture.index.source),
            ),
            (input_key.outline_width_multiply_texture_uv_use_attribute_key(), 1),
            (
                input_key.outline_width_multiply_texture_uv_attribute_name_key(),
                uv_layer_name,
            ),
            (
                input_key.outline_width_multiply_texture_uv_offset_x_key,
                outline_width_multiply_texture_uv_offset_x,
            ),
            (
                input_key.outline_width_multiply_texture_uv_offset_y_key,
                outline_width_multiply_texture_uv_offset_y,
            ),
            (
                input_key.outline_width_multiply_texture_uv_scale_x_key,
                outline_width_multiply_texture_uv_scale_x,
            ),
            (
                input_key.outline_width_multiply_texture_uv_scale_y_key,
                outline_width_multiply_texture_uv_scale_y,
            ),
            (
                input_key.extrude_mesh_individual_key,
                (
                    obj.type == "MESH"
                    and isinstance(obj.data, Mesh)
                    and not (has_auto_smooth and obj.data.use_auto_smooth)
                    and not any(polygon.use_smooth for polygon in obj.data.polygons)
                ),
            ),
            (input_key.object_key, obj),
            (
                input_key.enabled_key,
                obj.mode
                not in ["VERTEX_PAINT", "TEXTURE_PAINT", "WEIGHT_PAINT", "SCULPT"],
            ),
        ]:
            if modifier.get(k) != v:
                modifier[k] = v
                modifier_input_changed = True

        # Apply input values
        if modifier_input_changed:
            modifier.show_viewport = not modifier.show_viewport
            modifier.show_viewport = not modifier.show_viewport

        if reset_outline_material:
            reset_shader_node_group(
                context, material, reset_node_tree=False, overwrite=False
            )

    @staticmethod
    def refresh_object(context: Context, obj: Object) -> None:
        if bpy.app.version < (3, 3):
            return
        for material_slot in obj.material_slots:
            if not material_slot.material:
                continue
            material = context.blend_data.materials.get(material_slot.material.name)
            if not material:
                continue
            if not material.vrm_addon_extension.mtoon1.enabled:
                continue
            if material.vrm_addon_extension.mtoon1.is_outline_material:
                continue

            VRM_OT_refresh_mtoon1_outline.assign(
                context, material, obj, create_modifier=False
            )

    @staticmethod
    def refresh(
        context: Context,
        create_modifier: bool,
        material_name: Optional[str] = None,
    ) -> None:
        if bpy.app.version < (3, 3):
            return
        for obj in context.blend_data.objects:
            if obj.type != "MESH":
                continue
            outline_material_names = []
            for material_slot in obj.material_slots:
                if not material_slot.material:
                    continue
                if (
                    material_name is not None
                    and material_name != material_slot.material.name
                ):
                    continue
                material = context.blend_data.materials.get(material_slot.material.name)
                if not material:
                    continue
                if not material.vrm_addon_extension.mtoon1.enabled:
                    continue
                if material.vrm_addon_extension.mtoon1.is_outline_material:
                    continue

                VRM_OT_refresh_mtoon1_outline.assign(
                    context, material, obj, create_modifier
                )
                outline_material_names.append(material.name)
            if material_name is not None:
                continue

            # マテリアル名が指定されなかった場合は、
            # 不要なアウトラインのモディファイアを削除する
            for search_modifier_name in list(obj.modifiers.keys()):
                search_modifier = obj.modifiers.get(search_modifier_name)
                if not search_modifier:
                    continue
                if search_modifier.type != "NODES":
                    continue
                if not isinstance(search_modifier, NodesModifier):
                    continue
                node_group = search_modifier.node_group
                if not node_group:
                    continue
                if node_group.name != shader.OUTLINE_GEOMETRY_GROUP_NAME:
                    continue
                input_key = get_nodes_modifier_input_key(search_modifier)
                if input_key is None:
                    continue
                search_material = search_modifier.get(input_key.material_key)
                if (
                    isinstance(search_material, Material)
                    and search_material.name in outline_material_names
                ):
                    continue
                obj.modifiers.remove(search_modifier)

    def execute(self, context: Context) -> set[str]:
        self.refresh(context, self.create_modifier, self.material_name)
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        material_name: str  # type: ignore[no-redef]
        create_modifier: bool  # type: ignore[no-redef]
