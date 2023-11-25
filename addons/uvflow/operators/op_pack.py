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
from bpy.types import Context, Material, Object, Mesh

from uvflow.addon_utils import Register, Property
from uvflow.utils.mode import CM_ModeToggle
from uvflow.utils.enums import PackIncludes, PackTogether
from uvflow.utils.selection import get_selected_faces, restore_face_selection
from uvflow.utils.transforms import apply_scale, restore_scale
from uvflow.utils.decorators import time_it
from uvflow.prefs import UVFLOW_Preferences


@time_it
def setup_uv_editor(context: Context):
    context.area.type = 'IMAGE_EDITOR'
    if context.area.spaces[0].image is not None and context.area.spaces[0].image.type not in {'IMAGE', 'UV_TEST'}:
      # Exclude image type of 'COMPOSING' (Viewer Node) and 'RENDER_RESULT' (Render Result).
      context.area.spaces[0].image = None
    context.area.ui_type = 'UV'
    bpy.ops.uv.select_mode(False, type='FACE')

@time_it
def get_selected_materials(context: Context, pack_includes: PackIncludes):
    materials = set()
    if pack_includes == PackIncludes.SELECT_MATERIAL:
        for ob in context.objects_in_mode:
            mesh: Mesh = ob.data
            if mesh.total_face_sel == 0:
                continue
            added_materials_indices = set()
            added_material_count: int = 0
            tot_materials = len(mesh.materials)
            bm = bmesh.from_edit_mesh(ob.data)
            for face in bm.faces:
                if face.select and face.material_index not in added_materials_indices:
                    added_materials_indices.add(face.material_index)
                    materials.add(mesh.materials[face.material_index])
                    added_material_count += 1
                    if tot_materials == added_material_count:
                        break
            bm.free()
    elif pack_includes == PackIncludes.OBJECT_MATERIAL:
        for ob in context.selected_objects:
            for slot in ob.material_slots:
                if slot.material:
                    materials.add(slot.material)
    elif pack_includes == PackIncludes.ACTIVE_MATERIAL:
        materials.add(context.active_object.active_material)
    return materials

@time_it
def filter_objects(context: Context, pack_includes: PackIncludes, materials: set[Material]) -> list[Object]:
    if pack_includes in [PackIncludes.OBJECT_MATERIAL, PackIncludes.ACTIVE_MATERIAL, PackIncludes.SELECT_MATERIAL]:
        objects = [ob
            for ob in context.view_layer.objects\
                if 'uvflow_overlay' not in ob.name\
                    for slot in ob.material_slots\
                        if slot.material in materials]
    elif pack_includes == PackIncludes.FACES:
        objects = context.objects_in_mode
    else:
        objects = context.selected_objects

    if len(objects) == 0:
        return []

    if objects and context.active_object not in objects:
        context.view_layer.objects.active = objects[0]

    return objects


def is_face_included(pack_includes: PackIncludes, face, obj: Object, materials: set[Material]):
    if pack_includes == PackIncludes.FACES:
        return face.select
    elif pack_includes in [PackIncludes.OBJECT_MATERIAL, PackIncludes.ACTIVE_MATERIAL, PackIncludes.SELECT_MATERIAL]:
        return obj.material_slots[face.material_index].material in materials
    else:
        return True


@time_it
def group_faces(pack_includes: PackIncludes,
                pack_together: PackTogether,
                objects: list[Object],
                materials: set[Material]):
    grouped_faces = {}
    for obj in objects:
        if obj.data.uv_layers:
            bm = bmesh.from_edit_mesh(obj.data)
            for face in bm.faces:
                if is_face_included(pack_includes, face, obj, materials):
                    if pack_together == PackTogether.MATERIAL and obj.material_slots:
                        material = obj.material_slots[face.material_index].material
                        if material:
                            if material.name not in grouped_faces:
                                grouped_faces[material.name] = {}
                            if obj.name not in grouped_faces[material.name]:
                                grouped_faces[material.name][obj.name] = []
                            grouped_faces[material.name][obj.name].append(face.index)
                    elif pack_together == PackTogether.OBJECT:
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


@time_it
def pack_islands(prefs: UVFLOW_Preferences, context: Context, grouped_faces):
        prev_area_type = context.area.type
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

        context.area.type = prev_area_type
        if select_sync:
            context.scene.tool_settings.use_uv_select_sync = True


@Register.OPS.GENERIC
class UVPack:
    label: str = 'UV Pack'
    bl_description: str = 'Pack UV islands'
    bl_options = {'REGISTER', 'UNDO'}

    pack_active_material: Property.BOOL(default=False)

    @classmethod
    def poll(cls, context: Context):
        return context.object and context.object.type == 'MESH' and context.mode in {'EDIT_MESH', 'OBJECT'}
    
    def draw(self, context):
        prefs = UVFLOW_Preferences.get_prefs(context)
        content = self.layout.column()
        UVFLOW_Preferences.draw_packing_prefs(prefs, content, context)

    def action(self, context: Context):
        prefs = UVFLOW_Preferences.get_prefs(context)
        active_object: Object = context.active_object
        selected_objects: list[Object] = [ob for ob in context.view_layer.objects if ob.select_get()]

        if self.pack_active_material:
            pack_includes = PackIncludes.ACTIVE_MATERIAL 
            pack_together = PackTogether.MATERIAL
        elif context.mode == 'OBJECT':
            pack_includes: PackIncludes = getattr(PackIncludes, prefs.object_pack_includes)
            pack_together: PackTogether = getattr(PackTogether, prefs.pack_together)
        else:
            pack_includes: PackIncludes = getattr(PackIncludes, prefs.edit_pack_includes)
            pack_together: PackTogether = getattr(PackTogether, prefs.pack_together)
            
        materials = get_selected_materials(context, pack_includes)
        objects = filter_objects(context, pack_includes, materials)

        # All objects needed in the unwrap need to be in Edit Mode
        with CM_ModeToggle(context, 'OBJECT'):
            bpy.ops.object.select_all(action='DESELECT')
            for ob in objects:
                ob.select_set(True)
            if objects and active_object not in objects:
                context.view_layer.objects.active = objects[0]
        
        with CM_ModeToggle(context, 'EDIT'):      
            prev_selection = get_selected_faces(objects)
            if prefs.average_scale:
                prev_scale = apply_scale(objects)

            faces = group_faces(pack_includes, pack_together, objects, materials)
            pack_islands(prefs, context, faces)

            restore_face_selection(objects, prev_selection)
            if prefs.average_scale:
                restore_scale(objects, prev_scale)

        with CM_ModeToggle(context, 'OBJECT'):
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = active_object
            for ob in selected_objects:
                ob.select_set(True)

