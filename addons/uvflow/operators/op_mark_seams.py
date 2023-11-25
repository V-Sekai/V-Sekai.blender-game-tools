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

from uvflow.addon_utils import Register, Property
from uvflow.utils.selection import get_selected_faces, restore_face_selection
from uvflow.utils.transforms import apply_scale, restore_scale

from uvflow.prefs import UVFLOW_Preferences
from uvflow.utils.mode import CM_ModeToggle
from uvflow.utils.decorators import time_it
from uvflow.utils.editor_uv import get_uv_editor
from uvflow.tool.attributes import save_attributes
from bpy.types import Context, Mesh, Object, SpaceImageEditor

from .op_unwrap import split

@Register.OPS.GENERIC
class UVMarkSeams:
    label: str = 'Split'
    bl_description: str = 'Marks split edges as seams'
    bl_options = {'REGISTER', 'UNDO'}

    use_seam: Property.BOOL(
        name = 'Mark Seam',
        default = True
    )

    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'MESH' and context.mode in {'EDIT_MESH'}

    def draw(self, context):
        prefs = UVFLOW_Preferences.get_prefs(context)
        content = self.layout.column()
        content.use_property_split=True
        content.use_property_decorate=False
        content.prop(self, 'use_seam')
        content.separator()
        UVFLOW_Preferences.draw_split_prefs(prefs, content)

    def action(self, context):
        prefs = UVFLOW_Preferences.get_prefs(context)
        if context.mode == 'OBJECT':
            objects = [ob for ob in context.view_layer.objects if ob.select_get()]
        elif context.mode == 'EDIT_MESH':
            objects = context.objects_in_mode
        else:
            objects = []
        split(context, prefs, objects, self.use_seam)


@Register.OPS.GENERIC
class UVSeamsFromIslands:
    label: str = 'Seams From Islands'
    bl_description: str = 'Syncs seams with the current UV layout'
    bl_options = {'REGISTER', 'UNDO'}

    addative: Property.BOOL(default=True)

    def action(self, context: Context):
        with CM_ModeToggle(context, 'EDIT'):
            if not self.addative:
                objects = context.objects_in_mode
                prev_selected = get_selected_faces(objects)
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.mark_seam(clear=True)
                restore_face_selection(objects, prev_selected)

            context.area.type = 'IMAGE_EDITOR'
            context.area.ui_type = 'UV'
            uv_editor = context.area
            space: SpaceImageEditor = uv_editor.spaces[0]
            if space.image is not None and space.image.type not in {'IMAGE', 'UV_TEST'}:
                # Exclude image type of 'COMPOSING' (Viewer Node) and 'RENDER_RESULT' (Render Result).
                space.image = None

            bpy.ops.uv.select_all(action='SELECT')
            bpy.ops.uv.seams_from_islands()

            context.area.type = 'VIEW_3D'

            save_attributes(context, seams=True, selected=True)
