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
from uvflow.utils.selection import get_selected_faces, restore_face_selection
from uvflow.utils.transforms import apply_scale, restore_scale

from uvflow.prefs import UVFLOW_Preferences
from uvflow.utils.mode import CM_ModeToggle
from uvflow.utils.decorators import time_it
from uvflow.utils.editor_uv import get_uv_editor
from uvflow.utils.enums import Alignment
from bl_operators.uvcalc_transform import align_uv_rotation_bmesh

import bpy, bmesh
from bmesh.types import BMEdge, BMFace, BMVert, BMLoop, BMesh, BMLoopUV
from bpy.types import Context, Mesh, Object, SpaceImageEditor
from bpy_extras import bmesh_utils

from typing import List


@time_it
def split(context: Context, prefs: UVFLOW_Preferences, objects: list[Object], use_seam: bool = True) -> None:
    bpy.ops.object.mode_set(False, mode='OBJECT')

    temp_edge_seams = {}
    edge_bevel_weight: float = prefs.edge_bevel_weight
    edge_crease_weight: float = prefs.edge_crease_weight
    edge_angle: float = prefs.edge_angle
    use_edge_sharp: bool = prefs.use_sharp
    use_edge_bevel: bool = prefs.use_bevel
    use_edge_angle: bool = prefs.use_angle and prefs.edge_angle != 0
    use_edge_crease: bool = prefs.use_crease
    use_freestyle_mark: bool = prefs.use_freestyle_mark


    for obj in objects:
        mesh: Mesh = obj.data
        temp_edge_seams[obj.name]: set[int] = set()
        bm = None

        if use_edge_angle:
            bm: BMesh = bmesh.new(use_operators=False)
            bm.from_mesh(mesh)
            bm.edges.index_update()
            bm.edges.ensure_lookup_table()

        def _mark_edge(edge: bpy.types.MeshEdge):
            temp_edge_seams[obj.name].add(edge.index)
            edge.use_seam = use_seam

        for edge in mesh.edges:
            if not edge.select:
                continue

            if (use_seam and edge.use_seam) or (not use_seam and not edge.use_seam):
                # Only mark edges that are not seams or clear edges that are seams
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
                bm_edge: BMEdge = bm.edges[edge.index]
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

    return temp_edge_seams

@time_it
def split_restore_seams(objects: list[Object], temp_seams: Object) -> None:
    bpy.ops.object.mode_set(False, mode='OBJECT')
    for obj in objects:
        mesh: Mesh = obj.data
        for edge_idx in temp_seams[obj.name]:
            mesh.edges[edge_idx].use_seam = False

    bpy.ops.object.mode_set(False, mode='EDIT')
    del temp_seams


@Register.OPS.GENERIC
class UVUnwrap:
    label: str = 'UV Unwrap'
    bl_description: str = 'Unwraps the selected mesh'
    bl_options = {'REGISTER', 'UNDO'}

    unwrap_all: Property.BOOL()

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH' and context.mode in {'EDIT_MESH', 'OBJECT'}

    def draw(self, context):
        prefs = UVFLOW_Preferences.get_prefs(context)
        content = self.layout.column()
        UVFLOW_Preferences.draw_unwrap_prefs(prefs, content, context)
        UVFLOW_Preferences.draw_split_prefs(prefs, content)
        UVFLOW_Preferences.draw_unwrap_apply_prefs(prefs, content)

    @time_it
    def action(self, context: Context):
        prefs = UVFLOW_Preferences.get_prefs(context)

        if context.mode == 'OBJECT':
            prev_mode = 'OBJECT'
            self.unwrap_all = True
            objects = [ob for ob in context.view_layer.objects if ob.select_get()]
            if objects and context.active_object not in objects:
                context.view_layer.objects.active = objects[0]
        elif context.mode == 'EDIT_MESH':
            prev_mode = 'EDIT_MESH'
            objects = context.objects_in_mode
        else:
            return -1

        if len(objects) == 0:
            return -1

        with CM_ModeToggle(context, 'EDIT'):
            prev_selected = get_selected_faces(objects)

            if self.unwrap_all:
                bpy.ops.mesh.select_all(False, action='SELECT')
            else:
                # USE SELECTION FOR THE UNWRAP.
                pass

            ''' Apply Scale? '''
            if prefs.correct_scale:
                prev_scale = apply_scale(objects)

            ''' SPLIT. '''
            use_temp_seams = prefs.use_split
            if use_temp_seams:
                temp_seams = split(context, prefs, objects)

            ''' UNWRAP. '''
            self.unwrap(prefs)

            ''' Apply Scale? (Restore) '''
            if prefs.correct_scale:
                restore_scale(objects, prev_scale)

            ''' Align UVs '''
            if prev_mode == 'OBJECT' and prefs.alignment_obj:
                self.align_uvs(context, objects, Alignment.BOUNDS)
            elif prefs.alignment_edit != Alignment.NONE:
                self.align_uvs(context, objects, prefs.alignment_edit)

            if self.unwrap_all:
                bpy.ops.mesh.select_all(False, action='DESELECT')

            ''' SPLIT (RESTORE SEAMS). '''
            if use_temp_seams and temp_seams and not prefs.create_seams:
                split_restore_seams(objects, temp_seams)

            restore_face_selection(objects, prev_selected)

    @time_it
    def unwrap(self, prefs: UVFLOW_Preferences) -> None:
        bpy.ops.uv.unwrap(False,
            method=prefs.unwrap_method,
            fill_holes=prefs.fill_holes,
            correct_aspect=prefs.correct_aspect,
            use_subsurf_data=prefs.use_subdiv,
            margin_method='SCALED',
            margin=prefs.margin/100
        )

    @time_it
    def align_uvs(self, context: Context, objects: list[Object], alignment: Alignment) -> None:
        context.area.type = 'IMAGE_EDITOR'
        context.area.ui_type = 'UV'
        uv_editor = context.area
        space: SpaceImageEditor = uv_editor.spaces[0]
        if space.image is not None and space.image.type not in {'IMAGE', 'UV_TEST'}:
            # Exclude image type of 'COMPOSING' (Viewer Node) and 'RENDER_RESULT' (Render Result).
            space.image = None

        if alignment == 'BOUNDS':
            bpy.ops.uv.select_mode(False, type='FACE')
            bpy.ops.uv.select_all(False, action='SELECT')
            bpy.ops.uv.align_rotation(False, method='AUTO')
        elif alignment == 'EDGE':
            ob = context.active_object
            bm = bmesh.from_edit_mesh(ob.data)
            active_edge: BMEdge = None
            if bm.select_history:
                active = bm.select_history[-1]
                if type(active) == BMEdge:
                    active_edge = active
                elif type(active) == BMFace:
                    active_edge = active.loops[0].edge
                else:
                    self.report({'INFO'}, 'Island not aligned. Active element must be a face or edge.')
            else:
                for edge in bm.edges:
                    if edge.select:
                        active_edge = edge
                        break
            if bm and active_edge and bm.loops.layers.uv:
                uv_layer = bm.loops.layers.uv.active
                active_loops = []
                for face in bm.faces:
                    for loop in face.loops:
                        loop[uv_layer].select_edge = False
                        if loop.edge == active_edge:
                            print('match!')
                            active_loops.append(loop)
                #TODO: Check if the edges are part of the same island. If not, align both
                if active_loops:
                    active_loops[0][uv_layer].select_edge = True
                    align_uv_rotation_bmesh(ob.data, bm, method='EDGE', axis='X')
                    bmesh.update_edit_mesh(ob.data)

        context.area.type = 'VIEW_3D'

        #The context override here causes occasional crashes
        '''
        uv_editor = get_uv_editor(context.window)
        if uv_editor is None:
            context.area.type = 'IMAGE_EDITOR'
            context.area.ui_type = 'UV'
            uv_editor = context.area
            changed_editor_type = True
        else:
            changed_editor_type = False
        space: SpaceImageEditor = uv_editor.spaces[0]
        if space.image is not None and space.image.type not in {'IMAGE', 'UV_TEST'}:
            # Exclude image type of 'COMPOSING' (Viewer Node) and 'RENDER_RESULT' (Render Result).
            space.image = None

        region = None
        for reg in uv_editor.regions:
            if reg.type == 'WINDOW':
                region = reg
                break

        with context.temp_override(window=context.window, area=uv_editor, region=region):
            bpy.ops.uv.select_mode(False, type='FACE')
            bpy.ops.uv.select_all(False, action='SELECT')
            bpy.ops.uv.align_rotation(False, method='AUTO')

        if changed_editor_type:
            context.area.type = 'VIEW_3D'
        '''
