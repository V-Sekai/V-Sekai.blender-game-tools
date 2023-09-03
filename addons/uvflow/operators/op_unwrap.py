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
from uvflow.addon_utils.utils.selection import get_selected_polys, restore_selection
from uvflow.addon_utils.utils.transforms import apply_scale, restore_scale
from uvflow.prefs import UVFLOW_Preferences
from uvflow.addon_utils.utils.mode import CM_ModeToggle

import bpy
from bpy.types import Context, Mesh
import bmesh


@Register.OPS.GENERIC
class UVUnwrap:
    label: str = 'UV Unwrap'
    unwrap_all: Property.BOOL()

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH' and context.mode in {'EDIT_MESH', 'OBJECT'}

    def action(self, context: Context):
        prefs = UVFLOW_Preferences.get_prefs(context)

        if context.mode == 'OBJECT':
            self.unwrap_all = True
            objects = [x for x in context.view_layer.objects if x.select_get() == True]
            if context.active_object not in objects:
                context.view_layer.objects.active = objects[0]
        else:
            objects = [x for x in context.view_layer.objects if x.mode == 'EDIT']

        with CM_ModeToggle(context, 'EDIT'):
            prev_selected = get_selected_polys(objects)

            if self.unwrap_all:
                bpy.ops.mesh.select_all(False, action='SELECT')
            else:
                # USE SELECTION FOR THE UNWRAP.
                pass

            ''' Apply Scale? '''
            should_apply_scale = prefs.correct_scale and context.object.scale != (1, 1, 1)
            if should_apply_scale:
                prev_scale = apply_scale(objects)

            ''' SPLIT. '''
            use_temp_seams = prefs.use_split
            if use_temp_seams:
                self.split(context, prefs, objects)

            ''' UNWRAP. '''
            bpy.ops.uv.unwrap(False,
                method=prefs.unwrap_method,
                fill_holes=prefs.fill_holes,
                correct_aspect=prefs.correct_aspect,
                use_subsurf_data=prefs.use_subdiv,
                margin_method='FRACTION',
                margin=prefs.margin/100
            )

            ''' Apply Scale? (Restore) '''
            if should_apply_scale:
                restore_scale(objects, prev_scale)

            ''' Align UVs '''
            if prefs.alignment:
                context.area.type = 'IMAGE_EDITOR'
                context.area.ui_type = 'UV'
                space = context.space_data
                if space.image is not None and space.image.type not in {'IMAGE', 'UV_TEST'}:
                    # Exclude image type of 'COMPOSING' (Viewer Node) and 'RENDER_RESULT' (Render Result).
                    space.image = None
                bpy.ops.uv.select_mode(False, type='FACE')
                bpy.ops.uv.select_all(False, action='SELECT')
                bpy.ops.uv.align_rotation(False, method='AUTO')
                context.area.type = 'VIEW_3D'

            if self.unwrap_all:
                bpy.ops.mesh.select_all(False, action='DESELECT')


            ''' SPLIT (RESTORE SEAMS). '''
            if use_temp_seams and not prefs.create_seams:
                self.split_restore_seams(objects)

            restore_selection(objects, prev_selected)


    def split(self, context: Context, prefs, objects):
        bpy.ops.object.mode_set(False, mode='OBJECT')

        temp_edge_seams = {}

        for obj in objects:
            mesh: Mesh = obj.data
            temp_edge_seams[obj.name]: set[int] = set()
            bm = None

            use_edge_sharp: bool = prefs.use_sharp
            use_edge_bevel: bool = prefs.use_bevel
            use_edge_angle: bool = prefs.use_angle and prefs.edge_angle != 0
            use_edge_crease: bool = prefs.use_crease
            use_freestyle_mark: bool = prefs.use_freestyle_mark

            if use_edge_bevel:
                edge_bevel_weight: float = prefs.edge_bevel_weight
            if use_edge_crease:
                edge_crease_weight: float = prefs.edge_crease_weight
            if use_edge_angle:
                edge_angle: float = prefs.edge_angle
                print(f'Edge angle: {edge_angle}')

                bm: bmesh.types.BMesh = bmesh.new(use_operators=False)
                bm.from_mesh(mesh)
                bm.edges.index_update()
                bm.edges.ensure_lookup_table()

            def _mark_edge(edge: bpy.types.MeshEdge):
                temp_edge_seams[obj.name].add(edge.index)
                edge.use_seam = True

            for edge in mesh.edges:
                if edge.use_seam:
                    # Only mark edges that are not seams.
                    continue

                if use_edge_sharp and edge.use_edge_sharp:
                    _mark_edge(edge)
                    continue

                if use_freestyle_mark and edge.use_freestyle_mark:
                    _mark_edge(edge)
                    continue

                if use_edge_bevel and edge.bevel_weight > edge_bevel_weight:
                    _mark_edge(edge)
                    continue

                if use_edge_crease and edge.crease > edge_crease_weight:
                    _mark_edge(edge)
                    continue

                if use_edge_angle:
                    bm_edge: bmesh.types.BMEdge = bm.edges[edge.index]
                    if bm_edge.is_wire or bm_edge.is_boundary or len(bm_edge.link_faces) < 2:
                        # Cases where the edge won't have an angle.
                        continue
                    angle = bm_edge.calc_face_angle_signed()
                    if edge_angle > 0 and angle > edge_angle:
                        _mark_edge(edge)
                    elif edge_angle < 0 and angle < edge_angle:
                        _mark_edge(edge)

            if bm is not None:
                bm.free()
                del bm

        bpy.ops.object.editmode_toggle(False) # EDIT_MESH.

        self.temp_edge_seams = temp_edge_seams

    def split_restore_seams(self, objects):
        bpy.ops.object.editmode_toggle(False) # OBJECT.
        for obj in objects:
            mesh: Mesh = obj.data
            for edge_idx in self.temp_edge_seams[obj.name]:
                mesh.edges[edge_idx].use_seam = False

        bpy.ops.object.editmode_toggle(False) # EDIT_MESH.
        del self.temp_edge_seams


@Register.OPS.GENERIC
class UVUnwrapFromObject:
    label: str = 'UV Unwrap Objects'
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        prefs = UVFLOW_Preferences.get_prefs(context)
        content = self.layout.column()
        UVFLOW_Preferences.draw_unwrap_prefs(prefs, content)

    def action(self, context):
        UVUnwrap.run()
