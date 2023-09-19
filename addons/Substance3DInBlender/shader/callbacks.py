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

# file: shader/callbacks.py
# brief: Callbacks for shader presets parameters and outputs
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2


from ..utils import SUBSTANCE_Utils


class SUBSTANCE_ShaderCallbacks():
    @staticmethod
    def on_shader_changed(self, context):
        _, _selected_preset = SUBSTANCE_Utils.get_selected_shader_preset(context)
        _selected_preset.modified = True

    @staticmethod
    def on_parm_changed(self, context):
        SUBSTANCE_ShaderCallbacks.on_shader_changed(self, context)

    @staticmethod
    def on_output_changed(self, context):
        SUBSTANCE_ShaderCallbacks.on_shader_changed(self, context)
