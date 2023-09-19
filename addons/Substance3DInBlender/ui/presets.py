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

# file: ui/presets.py
# brief: Presets UI
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy

from ..ops.presets import SUBSTANCE_OT_ImportPreset, SUBSTANCE_OT_ExportPreset, SUBSTANCE_OT_DeletePreset


class SUBSTANCE_MT_PresetOptions(bpy.types.Menu):
    bl_idname = 'SUBSTANCE_MT_PresetOptions'
    bl_label = ""
    bl_description = 'Additional Preset Options'
    bl_options = {'REGISTER'}

    def draw(self, context):
        _col = self.layout.column()
        _row = _col.row()
        _row.operator(SUBSTANCE_OT_DeletePreset.bl_idname, icon='TRASH')
        _row = _col.row()
        _row.operator(SUBSTANCE_OT_ImportPreset.bl_idname, icon='IMPORT')
        _row = _col.row()
        _row.operator(SUBSTANCE_OT_ExportPreset.bl_idname, icon='EXPORT')
