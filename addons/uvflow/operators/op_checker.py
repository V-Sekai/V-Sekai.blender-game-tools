'''
Copyright (C) 2021-2023 Orange Turbine
https://orangeturbine.com
orangeturbine@cgcookie.com

This file is part of UV Flow.

The code for UV Flow is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <https://www.gnu.org/licenses>.
'''

import bpy, os
from bpy.types import Context, Object, MaterialSlot, Texture, ImageTexture, Mesh
from typing import List

from uvflow.addon_utils import Register, Property

checker_texture_name = 'UV Flow Checker Texture'
mix_shader_name = 'UV Flow Overlay'
attribute_node_name = 'UV Flow Map'


def enable_shading(context: Context, objects: List[Object], auto: bool = False):
    for obj in context.scene.objects:
        if obj.display_type in ['WIRE', 'BOUNDS']:
            pass
        elif obj in objects and obj.type in ['MESH', 'CURVE', 'SURFACE']:
            if not obj.get('prev_display_type'):
                obj['prev_display_type'] = obj.display_type
            obj.display_type = 'TEXTURED'
            if auto and not obj.get('checker_enabled_user'):
                obj['checker_enabled_auto'] = True
            else:
                if obj.get('checker_enabled_auto'):
                    obj.pop('checker_enabled_auto')
                obj['checker_enabled_user'] = True
        elif (obj not in objects and
            not obj.get('checker_enabled_auto') and
            not obj.get('checker_enabled_user') and
            obj.visible_get() and
            obj.type in ['MESH', 'CURVE']):
                if not obj.get('prev_display_type'):
                    obj['prev_display_type'] = obj.display_type
                if context.space_data.shading.color_type != 'TEXTURE':
                    obj.display_type = 'SOLID'
                    
    if hasattr(context.space_data, 'shading'):
        shading = context.space_data.shading.type
        is_wire = shading == 'WIREFRAME'
        color = context.space_data.shading.color_type

        if is_wire: context.space_data.shading.type = 'SOLID'
        if color != 'TEXTURE':
            context.scene['color_type'] = color
            context.space_data.shading.color_type = 'TEXTURE'
        if is_wire: context.space_data.shading.type = 'WIREFRAME'


def disable_shading(context: Context, objects: List[Object], auto: bool = False):
    # revert selected objects
    for obj in objects:
        if ((auto and obj.get('checker_enabled_auto') or not auto and obj.get('checker_enabled_user')) and
            'prev_display_type' in obj.keys()):
                obj.display_type = obj.pop('prev_display_type')

    # revert background objects only if no textured objects still exist
    other_tex_objs = [obj for obj in context.scene.objects if (
        obj not in objects and
        obj.visible_get() and
        (obj.get('checker_enabled_auto') or obj.get('checker_enabled_user'))
    )]
    self_tex_objs = [obj for obj in objects if auto and obj.get('checker_enabled_user')]
    if not other_tex_objs and not self_tex_objs:
        for obj in context.scene.objects:
            if obj not in objects and 'prev_display_type' in obj.keys():
                obj.display_type = obj.pop('prev_display_type')

        if context.space_data and hasattr(context.space_data, 'shading'):
            from uvflow.prefs import UVFLOW_Preferences
            prefs = UVFLOW_Preferences.get_prefs(context)
            if context.mode == 'EDIT_MESH' and prefs.use_overlays and prefs.use_seam_highlight:
                context.space_data.shading.color_type = 'MATERIAL'
            elif 'color_type' in context.scene.keys():
                context.space_data.shading.color_type = context.scene.pop('color_type')


def import_texture(texture_id: str, image_name: str):
    textures = {
        'SIMPLE_LIGHT': 'minimal_light.webp',
        'SIMPLE_DARK': 'minimal_dark.webp',
        'SIMPLE_BLUE': 'minimal_blue.webp',
        'SIMPLE_PINK': 'minimal_pink.webp',
        'SIMPLE_CONTRAST': 'minimal_contrast.webp',
        'CRAFT_STONE': 'craft_stone.webp',
        'CRAFT_GRASS': 'craft_grass.webp',
        'CRAFT_DIAMOND': 'craft_diamond.webp',
    }
    path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'textures', textures[texture_id])
    image = bpy.data.images.load(path, check_existing=True)
    image.name = image_name
    return image


def generate_texture(pattern: str, resolution: tuple[int, int], image_name: str):
    tex = bpy.data.images.new(image_name, *resolution)
    tex.generated_type = pattern
    return tex


def setup_image(context: Context):
    from uvflow.prefs import UVFLOW_Preferences
    prefs = UVFLOW_Preferences.get_prefs(context)
    pattern = prefs.checker_pattern
    image_name = f"UV Flow Checkers {pattern}"
    if image_name in bpy.data.images:
        tex = bpy.data.images[image_name]
        if pattern == 'UV_GRID' or pattern == 'COLOR_GRID':
            tex.generated_width = prefs.checker_custom_resolution[0]
            tex.generated_height = prefs.checker_custom_resolution[1]
    elif pattern == 'UV_GRID' or pattern == 'COLOR_GRID':
        tex = generate_texture(pattern, prefs.checker_custom_resolution, image_name)
    else:
        tex = import_texture(pattern, image_name)
    return tex


def setup_slots(context: Context, obj):
    if not len(obj.material_slots):
        obj.data.materials.append(bpy.data.materials.new("Material"))
    if not obj.material_slots[0].material:
        obj.material_slots[0].material = bpy.data.materials.new('Material')
    return [x for x in obj.material_slots if x.material]


def setup_nodes(context: Context, obj: Object, slot: MaterialSlot, tex: Texture):
    slot.material.use_nodes = True
    nodes = slot.material.node_tree.nodes
    links = slot.material.node_tree.links

    # Save active node
    if slot.material.node_tree.nodes.active:
        slot.material['uvf_prev_active'] = slot.material.node_tree.nodes.active.name

    # Set up nodes
    output_nodes = [node for node in nodes if node.type == 'OUTPUT_MATERIAL']
    if not output_nodes:
        output_node = nodes.new('ShaderNodeOutputMaterial')
    else:
        for node in output_nodes:
            if node.is_active_output:
                output_node = node

    if any(x.name == mix_shader_name for x in nodes):
        mix = nodes[mix_shader_name]
    else:
        mix = nodes.new('ShaderNodeMixShader')
        mix.name = mix_shader_name
        mix.label = mix_shader_name
        mix.inputs['Fac'].default_value = 0.9
        mix.location = [output_node.location[0], output_node.location[1] + 150]
        if output_node.inputs and output_node.inputs[0].links and output_node.inputs[0].links[0].from_node != mix:
            links.new(output_node.inputs[0].links[0].from_socket, mix.inputs[1])
        links.new(mix.outputs[0], output_node.inputs[0])

    if any(x.name == checker_texture_name for x in nodes):
        image_tex: ImageTexture = nodes[checker_texture_name]
    else:
        image_tex = nodes.new('ShaderNodeTexImage')
        image_tex.name = checker_texture_name
        image_tex.label = checker_texture_name
        image_tex.hide = True
        nodes.active = image_tex
        image_tex.location = [output_node.location[0], output_node.location[1] + 200]
        links.new(image_tex.outputs[0], mix.inputs[2])
    image_tex.image = tex

    if any(x.name == attribute_node_name for x in nodes):
        map = nodes[attribute_node_name]
    else:
        map = nodes.new('ShaderNodeAttribute')
        map.name = attribute_node_name
        map.label = attribute_node_name
        map.hide = True
        map.location = [output_node.location[0], output_node.location[1] + 250]
        links.new(map.outputs['Vector'], image_tex.inputs[0])
    if hasattr(obj.data, 'uv_layers') and obj.data.uv_layers.active:
        map.attribute_name = obj.data.uv_layers.active.name


def remove_nodes(context: Context, obj: Object, slot: MaterialSlot, auto: bool = False):
    if (auto and obj.get('checker_enabled_auto') or not auto and obj.get('checker_enabled_user')) and slot.material.use_nodes:
        nodes = slot.material.node_tree.nodes
        links = slot.material.node_tree.links
        # Remove nodes
        if any(x.name == mix_shader_name for x in nodes):
            mix = nodes[mix_shader_name]
            if mix.inputs[1].links and mix.outputs[0].links:
                links.new(mix.inputs[1].links[0].from_socket, mix.outputs[0].links[0].to_socket)
            nodes.remove(mix)
        if any(x.name == checker_texture_name for x in nodes):
            if nodes.active == nodes[checker_texture_name] and slot.material.get('uvf_prev_active'):
                nodes.active = nodes[slot.material.pop('uvf_prev_active')]
            nodes.remove(nodes[checker_texture_name])
        if any(x.name == attribute_node_name for x in nodes):
            nodes.remove(nodes[attribute_node_name])


def update_material_uvmap(context: Context, uv_layer_id: str | None = None):
    objects = [ob for ob in context.view_layer.objects if ob.mode == 'EDIT' or ob.select_get() or context.active_object == ob]
    for obj in objects:
        mesh: Mesh = obj.data
        if mesh.uv_layers.active is None:
            continue
        for slot in obj.material_slots:
            if slot.material is None:
                continue
            nodes = slot.material.node_tree.nodes
            if node := nodes.get(attribute_node_name, None):
                if uv_layer_id is None:
                    uv_layer_id = mesh.uv_layers.active.name
                node.attribute_name = uv_layer_id


def enable_checker_material(context: Context, objects: List[Object], auto: bool = False):
    enable_shading(context, objects, auto)
    tex = setup_image(context)
    for obj in objects:
        slots = setup_slots(context, obj)
        for slot in slots:
            setup_nodes(context, obj, slot, tex)


def disable_checker_material(context: Context, objects: List[Object], auto: bool = False):
    disable_shading(context, objects, auto)
    for obj in objects:
        slots = [x for x in obj.material_slots if x.material]
        for slot in slots:
            remove_nodes(context, obj, slot, auto)
        if obj.get('checker_enabled_auto'):
            obj.pop('checker_enabled_auto')
        elif auto == False and obj.get('checker_enabled_user'):
            obj.pop('checker_enabled_user')


def refresh_checker(context: Context):
    from uvflow.prefs import UVFLOW_Preferences
    prefs = UVFLOW_Preferences.get_prefs(context)

    objects = [ob for ob in context.view_layer.objects if ob.mode == 'EDIT']

    if prefs.use_overlays and prefs.checker_pattern != 'NONE':
        enable_checker_material(context, objects, auto=True)
    else:
        disable_checker_material(context, objects, auto=True)


@Register.OPS.GENERIC
class ToggleUvCheckerMaterial:
    label: str = 'Toggle UV Checkers'
    bl_description: str = 'Toggle a UV checker texture on the selected objects. This also sets the viewport color and display of other objects, so toggle the checker off when finished to revert to previous settings'
    bl_options = {'REGISTER', 'UNDO'}

    enable: Property.BOOL(name="Enabled")
    auto: Property.BOOL()

    def draw(self, context: Context):
        from uvflow.prefs import UVFLOW_Preferences
        prefs = UVFLOW_Preferences.get_prefs(context)
        self.layout.use_property_split=True
        self.layout.use_property_decorate=False
        self.layout.prop(prefs, 'checker_pattern')
        if prefs.checker_pattern in ['UV_GRID', 'COLOR_GRID']:
            self.layout.prop(prefs, 'checker_custom_resolution')
        self.layout.prop(self, 'enable')

    def action(self, context: Context):
        objects = [ob for ob in context.view_layer.objects if (
            ob.type in ['MESH', 'CURVE', 'SURFACE'] and
            (ob.mode == 'EDIT' or ob.select_get() == True or (self.auto and context.active_object == ob))
        )]
        if objects:
            if context.active_object not in objects:
                context.view_layer.objects.active = objects[0]
            if self.enable:
                enable_checker_material(context, objects, self.auto)
            else:
                disable_checker_material(context, objects, self.auto)
