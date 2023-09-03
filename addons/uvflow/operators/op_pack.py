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
import bpy, bmesh
from bpy.types import Context

from uvflow.addon_utils import Register, Property
from uvflow.addon_utils.utils.mode import CM_ModeToggle
from uvflow.addon_utils.utils.selection import get_selected_materials, get_selected_polys, restore_selection
from uvflow.prefs import UVFLOW_Preferences

def setup_uv_editor(context: Context):
    context.area.type = 'IMAGE_EDITOR'
    if context.area.spaces[0].image is not None and context.area.spaces[0].image.type not in {'IMAGE', 'UV_TEST'}:
      # Exclude image type of 'COMPOSING' (Viewer Node) and 'RENDER_RESULT' (Render Result).
      context.area.spaces[0].image = None
    context.area.ui_type = 'UV'
    bpy.ops.uv.select_mode(False, type='FACE')

def filter_objects(context: Context, prefs: UVFLOW_Preferences, materials):
    if prefs.pack_includes == 'MATERIAL':
        objects = []
        for obj in context.view_layer.objects:
            if 'uvflow_overlay' not in obj.name:
                for slot in obj.material_slots:
                    if slot.material in materials:
                        objects.append(obj)
        return objects
    elif prefs.pack_includes == 'SELECTED' and context.mode == 'EDIT':
          objects = [x for x in context.view_layer.objects if x.mode == 'EDIT']
    else:
        objects = context.selected_objects

    if context.active_object not in objects:
        context.view_layer.objects.active = objects[0]
        
    return objects

def is_face_included(prefs: UVFLOW_Preferences, face, obj, materials):
    if prefs.pack_includes == 'SELECTED':
        return face.select
    if prefs.pack_includes == 'MATERIAL':
        return obj.material_slots[face.material_index].material in materials
    else:
        return True

def group_faces(prefs: UVFLOW_Preferences, objects, materials):
    grouped_faces = {}
    for obj in objects:
        bm = bmesh.from_edit_mesh(obj.data)
        for face in bm.faces:
            if is_face_included(prefs, face, obj, materials):
                if prefs.pack_together == 'MATERIAL' and obj.material_slots:
                    material = obj.material_slots[face.material_index].material
                    if material:
                        if material.name not in grouped_faces:
                            grouped_faces[material.name] = {}
                        if obj.name not in grouped_faces[material.name]:
                            grouped_faces[material.name][obj.name] = []
                        grouped_faces[material.name][obj.name].append(face.index)
                elif prefs.pack_together == 'OBJECT':
                    if obj.name not in grouped_faces:
                        grouped_faces[obj.name] = {}
                    if obj.name not in grouped_faces[obj.name]:
                        grouped_faces[obj.name][obj.name] = []
                    grouped_faces[obj.name][obj.name].append(face.index)
                else:
                    if 'all' not in grouped_faces:
                        grouped_faces['all'] = {}
                    if obj.name not in grouped_faces['all']:
                        grouped_faces['all'][obj.name] = []
                    grouped_faces['all'][obj.name].append(face.index)
        bm.free()
    return grouped_faces

def pack_islands(prefs: UVFLOW_Preferences, context: Context, grouped_faces):
        select_sync = int(context.scene.tool_settings.use_uv_select_sync)
        if select_sync:
           context.scene.tool_settings.use_uv_select_sync = False

        for group in grouped_faces.keys():
            bpy.ops.mesh.select_all(False, action='DESELECT')
            for obj_name in grouped_faces[group].keys():
                bm = bmesh.from_edit_mesh(bpy.data.objects[obj_name].data)
                bm.faces.ensure_lookup_table()
                for face_idx in grouped_faces[group][obj_name]:
                    bm.faces[face_idx].select_set(True)
                bm.free()
            setup_uv_editor(context)
            bpy.ops.uv.select_all(False, action='SELECT')
            if prefs.average_scale:
                bpy.ops.uv.average_islands_scale(False)
            bpy.ops.uv.pack_islands(False,
                shape_method=prefs.pack_method,
                udim_source=prefs.pack_to,
                rotate=False if prefs.rotation == "NONE" else True,
                rotate_method='ANY' if prefs.rotation == "NONE" else prefs.rotation,
                margin_method=prefs.margin_method,
                margin=prefs.margin/100,
                merge_overlap=prefs.merge_overlapping,
                pin=False if prefs.lock_pinned == "NONE" else True,
                pin_method="LOCKED" if prefs.lock_pinned == "NONE" else prefs.lock_pinned
            )

        context.area.type = 'VIEW_3D'
        if select_sync:
            context.scene.tool_settings.use_uv_select_sync = True


@Register.OPS.GENERIC
class UVPack:
    label: str = 'UV Pack'
    pack_all: Property.BOOL(default = False)

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH' and context.mode in {'EDIT_MESH', 'OBJECT'}

    def action(self, context: Context):
        prefs = UVFLOW_Preferences.get_prefs(context)

        with CM_ModeToggle(context, 'EDIT'):
            bpy.ops.mesh.select_all(False, action='SELECT')

            materials = get_selected_materials(context, prefs)
            objects = filter_objects(context, prefs, materials)
            prev_selection = get_selected_polys(objects)
            faces = group_faces(prefs, objects, materials)

            pack_islands(prefs, context, faces)

            restore_selection(objects, prev_selection)


@Register.OPS.GENERIC
class UVPackFromObject:
    label: str = 'UV Pack Objects'
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        prefs = UVFLOW_Preferences.get_prefs(context)
        content = self.layout.column()
        UVFLOW_Preferences.draw_packing_prefs(prefs, content)

    def action(self, context):
        UVPack.run()
