"""
Copyright (C) 2022 Adobe.
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# file: ui/shortcut.py
# brief: Shortcuts UI
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy

from ..utils import SUBSTANCE_Utils
from ..common import SHORTCUT_CLASS_NAME
from ..ops.sbsar import (
    SUBSTANCE_OT_LoadSBSAR,
    SUBSTANCE_OT_ApplySBSAR,
    SUBSTANCE_OT_DuplicateSBSAR,
    SUBSTANCE_OT_ReloadSBSAR,
    SUBSTANCE_OT_RemoveSBSAR
)


def SubstanceShortcutMenuFactory(space):

    class SUBSTANCE_MT_Main(bpy.types.Menu):
        bl_idname = SHORTCUT_CLASS_NAME.format(space)
        bl_label = 'Substance 3D Menu'

        def draw(self, context):
            self.layout.operator_context = 'INVOKE_REGION_WIN'

            _row = self.layout.row(align=True)
            _row.operator(SUBSTANCE_OT_LoadSBSAR.bl_idname, text="Load New Substance File(s)")

            _row = self.layout.row()
            _row.separator()

            if len(context.scene.loaded_sbsars) > 0:
                _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
                _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)

                _sbsar_name = _selected_sbsar.name + " - " + _selected_graph.name

                _row = self.layout.row()
                _row.operator(
                    SUBSTANCE_OT_ApplySBSAR.bl_idname,
                    text="Apply " + _sbsar_name,
                    icon='MATERIAL')

                _row = self.layout.row()
                _row.operator(
                    SUBSTANCE_OT_DuplicateSBSAR.bl_idname,
                    text="Duplicate " + _selected_sbsar.name,
                    icon='DUPLICATE')

                _row = self.layout.row()
                _row.operator(
                    SUBSTANCE_OT_ReloadSBSAR.bl_idname,
                    text="Refresh " + _selected_sbsar.name,
                    icon='FILE_REFRESH')

                _row = self.layout.row()
                _row.operator(SUBSTANCE_OT_RemoveSBSAR.bl_idname, text="Remove " + _selected_sbsar.name, icon='TRASH')

    return SUBSTANCE_MT_Main
