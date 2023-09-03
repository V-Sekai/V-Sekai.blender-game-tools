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

import bpy
from bpy.types import Context, Mesh, BoolAttribute, bpy_prop_collection

from uvflow.addon_utils.utils.mode import CM_ModeToggle
from uvflow.globals import CM_SkipMeshUpdates, print_debug



def _apply_attribute(mesh: Mesh,
                    mesh_seq: bpy_prop_collection,
                    mesh_seq_attr: str,
                    layer_id: str,
                    layer_domain: str,
                    layer_data_type: str,
                    layer_default_value: bool | int | float) -> None:
    if layer := mesh.attributes.get(layer_id, None):
        data = [layer_default_value] * len(mesh_seq)
        layer.data.foreach_get('value', data)
        mesh.edges.foreach_set(mesh_seq_attr, data)
        del data
    else:
        layer: BoolAttribute = mesh.attributes.new(layer_id, layer_data_type, layer_domain)
        data = [layer_default_value] * len(mesh_seq)
        layer.data.foreach_set('value', data)
        mesh_seq.foreach_set(mesh_seq_attr, data)

        del data
        # raise ValueError("Could not find the attribute layer named %s" % layer_id)
    
    print_debug("ATTR| Applying attributes to Mesh from Layer '%s'" % layer_id)


def _save_attribute(mesh: Mesh,
                     mesh_seq: bpy_prop_collection,
                     mesh_seq_attr: str,
                     layer_id: str,
                     layer_domain: str,
                     layer_data_type: str,
                     layer_default_value: int | int | float) -> None:
    layer: BoolAttribute = mesh.attributes.get(layer_id, None)
    if layer is None:
        layer: BoolAttribute = mesh.attributes.new(layer_id, layer_data_type, layer_domain)

    data = [layer_default_value] * len(mesh_seq)
    mesh_seq.foreach_get(mesh_seq_attr, data)
    layer.data.foreach_set('value', data)
    del data
    
    print_debug("ATTR| Saving Mesh attributes to Attribute Layer '%s'" % layer_id)


def _remove_attribute(mesh: Mesh, layer_id: str) -> None:
    if layer := mesh.attributes.get(layer_id, None):
        mesh.attributes.remove(layer)
        print_debug("ATTR| Removing Attribute Layer '%s'" % layer_id)
    else:
        raise ValueError(f"Could not find the attribute layer named {layer_id}")


def remove_attributes(context: Context,
                      seams: bool = False,
                      seam_layer_id: str | None = None,
                      hidden: bool = False,
                      pinned: bool = False,
                      selected: bool = False):
    if context.mode not in {'EDIT_MESH', 'OBJECT'}:
        raise Exception("Invalid context.mode! remove_attributes expects EDIT_MESH mode!")

    with CM_SkipMeshUpdates(), CM_ModeToggle(context, 'OBJECT'):
        mesh: Mesh = context.object.data

        if seams:
            if seam_layer_id is None:
                seam_layer_id = mesh.uv_layers.active.name
            _remove_attribute(mesh, layer_id=seam_layer_id + '_seams')
        if hidden:
            _remove_attribute(mesh, layer_id='uvflow_hidden')
        if pinned:
            _remove_attribute(mesh, layer_id='uvflow_pinned')
        if selected:
            _remove_attribute(mesh, layer_id='uvflow_selected')


def save_attributes(context: Context,
                      seams: bool = False,
                      seam_layer_id: str | None = None,
                      hidden: bool = False,
                      pinned: bool = False,
                      selected: bool = False):
    if context.mode not in {'EDIT_MESH', 'OBJECT'}:
        raise Exception("Invalid context.mode! remove_attributes expects EDIT_MESH mode!")

    with CM_SkipMeshUpdates(), CM_ModeToggle(context, 'OBJECT'):

        from uvflow.prefs import UVFLOW_Preferences
        prefs = UVFLOW_Preferences.get_prefs(context)
        mesh: Mesh = context.object.data

        if seams and prefs.use_seam_layers and mesh.uv_layers.active:
            if seam_layer_id is None:
                seam_layer_id = mesh.uv_layers.active.name
            _save_attribute(
                mesh,
                mesh_seq=mesh.edges,
                mesh_seq_attr='use_seam',
                layer_id=seam_layer_id + '_seams',
                layer_domain='EDGE',
                layer_data_type='BOOLEAN',
                layer_default_value=False
            )
        if hidden:
            _save_attribute(
                mesh,
                mesh_seq=mesh.polygons,
                mesh_seq_attr='hide',
                layer_id='uvflow_hidden',
                layer_domain='FACE',
                layer_data_type='BOOLEAN',
                layer_default_value=False
            )
        if pinned:
            pass # Not Implemented yet.
        if selected:
            _save_attribute(
                mesh,
                mesh_seq=mesh.edges,
                mesh_seq_attr='select',
                layer_id='uvflow_selected',
                layer_domain='EDGE',
                layer_data_type='BOOLEAN',
                layer_default_value=False
            )


def apply_attributes(context: Context,
                     seams: bool = False,
                     seam_layer_id: str | None = None,
                     hidden: bool = False,
                     pinned: bool = False,
                     selected: bool = False):
    if context.mode not in {'EDIT_MESH', 'OBJECT'}:
        raise Exception("Invalid context.mode! remove_attributes expects EDIT_MESH mode!")

    with CM_SkipMeshUpdates(), CM_ModeToggle(context, 'OBJECT'):
        from uvflow.prefs import UVFLOW_Preferences
        prefs = UVFLOW_Preferences.get_prefs(context)
        mesh: Mesh = context.object.data

        if seams and prefs.use_seam_layers:
            if seam_layer_id is None:
                seam_layer_id = mesh.uv_layers.active.name
            _apply_attribute(
                mesh,
                mesh_seq=mesh.edges,
                mesh_seq_attr='use_seam',
                layer_id=seam_layer_id + '_seams',
                layer_domain='EDGE',
                layer_data_type='BOOLEAN',
                layer_default_value=False
            )
        if hidden:
            _apply_attribute(
                mesh,
                mesh_seq=mesh.polygons,
                mesh_seq_attr='hide',
                layer_id='uvflow_hidden',
                layer_domain='FACE',
                layer_data_type='BOOLEAN',
                layer_default_value=False
            )
        if pinned:
            pass # Not Implemented yet.
        if selected:
            _apply_attribute(
                mesh,
                mesh_seq=mesh.edges,
                mesh_seq_attr='select',
                layer_id='uvflow_selected',
                layer_domain='EDGE',
                layer_data_type='BOOLEAN',
                layer_default_value=False
            )
