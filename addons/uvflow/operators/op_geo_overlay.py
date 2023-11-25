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

from uvflow.addon_utils import Register, Property
from uvflow.utils.append import append_path
from uvflow.utils.mode import CM_ModeToggle

import bpy
from bpy.types import Context, Object
from bpy.app import timers

import functools
from typing import List, Tuple


viewer_node_timer_state = 0
viewer_node_timer_area_memaddress = 0

collection_name = 'UV Flow Overlays'
geo_modifier_name = 'UV Flow Geometry Overlays'
face_modifier_name = 'UV Flow Face Overlays'
seam_node_group_name = 'UV Flow Seam Overlay'
pin_node_group_name = 'UV Flow Pin Overlay'
angle_node_group_name = 'UV Flow Angle Stretch Overlay'
area_node_group_name = 'UV Flow Area Stretch Overlay'
udim_node_group_name = 'UV Flow UDIM Overlay'
overlay_suffix = '_uvflow_overlay'
wire_suffix = '_uvflow_wire'
seam_material_name = 'uvflow_seam'
selected_material_name = 'uvflow_selected'
pin_material_name = 'uvflow_pin'
geo_overlay_names = [seam_node_group_name, pin_node_group_name]
face_overlay_names = [angle_node_group_name, area_node_group_name, udim_node_group_name]

def setup_collection(context: Context):
    if collection_name not in [x.name for x in bpy.data.collections]:
        new_collection = bpy.data.collections.new(collection_name)
        new_collection.hide_select = True
        new_collection.hide_render = True
        new_collection.color_tag = 'COLOR_01'
        context.scene.collection.children.link(new_collection)
        return new_collection
    else:
        collection = bpy.data.collections[collection_name]
        if collection.name not in context.scene.collection.children:
            context.scene.collection.children.link(collection)
        return collection

def remove_collection():
    if collection_name in [x.name for x in bpy.data.collections]:
        bpy.data.collections.remove(bpy.data.collections[collection_name])

def setup_geo_objects(collection, objects: List[Object]):
    new_objects = []
    for obj in objects:
        name = obj.name + overlay_suffix
        overlay_obj = bpy.data.objects.get(name, None)
        if overlay_obj is None:
            overlay_obj = bpy.data.objects.new(name, obj.data)
        overlay_obj.matrix_world = obj.matrix_world
        if overlay_obj.name not in collection.objects:
            collection.objects.link(overlay_obj)
        new_objects.append(overlay_obj)
    return new_objects

def setup_wire_objects(collection, objects: List[Object]):
    new_objects = []
    for obj in objects:
        name = obj.name + wire_suffix
        wire_ob = bpy.data.objects.get(name, None)
        if wire_ob is None:
            wire_ob = bpy.data.objects.new(name, obj.data)
        wire_ob.matrix_world = obj.matrix_world
        wire_ob.display_type = 'WIRE'
        if wire_ob.name not in collection.objects:
            collection.objects.link(wire_ob)
        new_objects.append(wire_ob)
    return objects

def remove_overlay_objects(objects: List[Object] = [], geo=False, wire=False):
    for obj in objects:
        geo_name = obj.name + overlay_suffix
        wire_name = obj.name + wire_suffix
        if geo and (geo_ob := bpy.data.objects.get(geo_name, None)):
            bpy.data.objects.remove(geo_ob)
        if wire and (wire_ob := bpy.data.objects.get(wire_name, None)):
            bpy.data.objects.remove(wire_ob)

def setup_nodes(context: Context, objects: List[Object] = [], enable_geo=False, enable_face=False):
    with CM_ModeToggle(context, 'OBJECT'):
        modifier_name = geo_modifier_name if enable_geo else face_modifier_name
        node_tree = bpy.data.node_groups.get(modifier_name, None)
        if node_tree is None:
            bpy.ops.wm.append(filename=modifier_name, directory=append_path('NodeTree'))
            node_tree = bpy.data.node_groups[modifier_name]

            if seam_node := node_tree.nodes.get(seam_node_group_name, None):
                if seam_node.node_tree is not None:
                    seam_node.node_tree.nodes['Set Material'].inputs[2].default_value = bpy.data.materials[seam_material_name]
                    seam_node.node_tree.nodes['Set Material.001'].inputs[2].default_value = bpy.data.materials[selected_material_name]

        for obj in objects:
            modifier = obj.modifiers.get(modifier_name, None)
            if modifier is None:
                modifier = obj.modifiers.new(modifier_name, 'NODES')
            modifier.node_group = node_tree

        return node_tree

def remove_modifier(objects: List[Object] = [], geo=False, face=False):
    modifier_name = geo_modifier_name if geo else face_modifier_name
    for obj in objects:
        if modifier := obj.modifiers.get(modifier_name, None):
            obj.modifiers.remove(modifier)

def set_seam_color(context: Context):
    from uvflow.prefs import UVFLOW_Preferences
    prefs = UVFLOW_Preferences.get_prefs(context)
    theme = context.preferences.themes[0]

    theme.view_3d.edge_seam = prefs.seam_color

    seam_mat = bpy.data.materials.get(seam_material_name, None)
    if seam_mat is None:
        print('Appending seam material')
        bpy.ops.wm.append(filename=seam_material_name, directory=append_path('Material'))
        seam_mat = bpy.data.materials[seam_material_name]
    seam_rgba = [prefs.seam_color[0], prefs.seam_color[1], prefs.seam_color[2], 1]
    seam_mat.node_tree.nodes['Emission'].inputs['Color'].default_value = seam_rgba
    seam_mat.node_tree.nodes['Emission'].inputs['Strength'].default_value = prefs.seam_brightness
    seam_mat.diffuse_color = [prefs.seam_brightness * x for x in seam_rgba]
    seam_mat.diffuse_color[3] = 1

    select_mat = bpy.data.materials.get(selected_material_name, None)
    if select_mat is None:
        bpy.ops.wm.append(filename=selected_material_name, directory=append_path('Material'))
        select_mat = bpy.data.materials[selected_material_name]
    select_rgba = [theme.view_3d.edge_select[0], theme.view_3d.edge_select[1], theme.view_3d.edge_select[2], 1]
    select_mat.node_tree.nodes['Emission'].inputs['Color'].default_value = select_rgba
    select_mat.node_tree.nodes['Emission'].inputs['Strength'].default_value = prefs.seam_brightness
    select_mat.diffuse_color = [prefs.seam_brightness * x for x in select_rgba]
    select_mat.diffuse_color[3] = 1

def set_seam_props(context: Context, uv_layer_id: str | None = None):
    from uvflow.prefs import UVFLOW_Preferences
    prefs = UVFLOW_Preferences.get_prefs(context)
    theme = context.preferences.themes[0]

    set_seam_color(context)

    if prefs.use_overlays and prefs.use_seam_highlight:
        geo_node_group = bpy.data.node_groups.get(geo_modifier_name, None)
        if geo_node_group is None:
            return
        nodes = geo_node_group.nodes['UV Flow Seam Overlay'].node_tree.nodes
        nodes['Radius'].outputs[0].default_value = prefs.seam_size

        if uv_layer_id is None:
            if context.active_object.data.uv_layers.active is None:
                return
            uv_layer_id = context.active_object.data.uv_layers.active.name
        nodes['Seams'].inputs['Name'].default_value = f'{uv_layer_id}_seams'

def set_uvmap(context: Context, node_tree, uv_layer_id: str | None = None):
    if uv_layer_id is None:
        mesh = context.active_object.data
        if mesh.uv_layers.active is None:
            return
        uv_layer_id = mesh.uv_layers.active.name
    node_tree.nodes['UV Map'].inputs['Name'].default_value = uv_layer_id

def set_udim_props(context: Context):
    from uvflow.prefs import UVFLOW_Preferences
    prefs = UVFLOW_Preferences.get_prefs(context)
    nodes =  bpy.data.node_groups['UV Flow UDIM Overlay'].nodes
    nodes['Random Value'].inputs['Seed'].default_value = prefs.udim_seed

def connect_viewer(context: Context, node_tree, group_name):
    nodes = node_tree.nodes
    links = node_tree.links

    if 'Viewer' not in [x.name for x in nodes]:
        viewer = nodes.new('GeometryNodeViewer')
        viewer.location = [750, -100]
        viewer.data_type = 'FLOAT_COLOR'
    else:
        viewer = nodes['Viewer']

    links.new(nodes['Group Input'].outputs[0], viewer.inputs[0])
    links.new(nodes[group_name].outputs[0], viewer.inputs[3])

    if group_name == angle_node_group_name:
        viewer.domain = 'CORNER'
    else:
        viewer.domain = 'FACE'


@Register.OPS.INVOKE_PROPS
class UpdateGeoOverlays:
    label: str = 'Toggle Geometry Overlays'

    enable: Property.BOOL(default=True)

    def action(self, context: Context):
        from uvflow.prefs import UVFLOW_Preferences
        prefs = UVFLOW_Preferences.get_prefs(context)
        enable_seams = prefs.use_seam_highlight
        enable_pins = prefs.use_pin_highlight
        enable_area = prefs.face_highlight == 'AREA'
        enable_angle = prefs.face_highlight == 'ANGLE'
        enable_udims = prefs.face_highlight == 'UDIM'
        enable_geo = prefs.use_overlays and (enable_seams or enable_pins)
        enable_face = prefs.use_overlays and (enable_angle or enable_area or enable_udims)

        objects = [ob for ob in context.view_layer.objects if (
            ob.mode == 'EDIT' or 
            ob.select_get() == True or 
            context.active_object == ob
        )]

        if self.enable and (enable_geo or enable_face):
            collection = setup_collection(context)

            if enable_geo:
                geo_objs = setup_geo_objects(collection, objects)
                node_tree = setup_nodes(context, objects=geo_objs, enable_geo=True)
                if enable_seams:
                    set_seam_props(context)
            else:
                remove_overlay_objects(objects=objects, geo=True)
            if enable_face:
                setup_wire_objects(collection, objects)
                node_tree = setup_nodes(context, objects=objects, enable_face=True)
                set_uvmap(context, node_tree)
                if enable_udims:
                    set_udim_props(context)
                    connect_viewer(context, node_tree, udim_node_group_name)
                elif enable_angle:
                    connect_viewer(context, node_tree, angle_node_group_name)
                elif enable_area:
                    connect_viewer(context, node_tree, area_node_group_name)
            else:
                remove_modifier(objects, face=True)
                remove_overlay_objects(objects=objects, wire=True)
        else:
            remove_overlay_objects(objects=objects, geo=True, wire=True)
            remove_collection()
            remove_modifier(objects, face=True)
