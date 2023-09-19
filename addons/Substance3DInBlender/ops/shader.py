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

# file: ops/shader.py
# brief: Shader Operators
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy

from ..common import ADDON_PACKAGE, Code_Response
from ..api import SUBSTANCE_Api
from ..utils import SUBSTANCE_Utils


class SUBSTANCE_OT_InitializeShaderPresets(bpy.types.Operator):
    bl_idname = 'substance.initialize_shader_presets'
    bl_label = 'Initialize shader preset'
    bl_description = "Initialize the shader presets"

    def execute(self, context):
        _addon_prefs = context.preferences.addons[ADDON_PACKAGE].preferences
        _addon_prefs.shader_presets.clear()

        _result = SUBSTANCE_Api.shader_presets_initialize()

        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data("ERROR", "[{}] Shader presets cannot be initialized...".format(_result))
            return {'FINISHED'}

        for _shader_preset in _result[1]:
            _new_shader = _addon_prefs.shader_presets.add()
            _new_shader.initialize(_shader_preset)

        SUBSTANCE_Utils.log_data("INFO", "Shader Presets initialized...")
        return {'FINISHED'}


class SUBSTANCE_OT_RemoveShaderPresets(bpy.types.Operator):
    bl_idname = 'substance.remove_shader_presets'
    bl_label = 'Remove shader preset'
    bl_description = "Remove the shader presets"

    def execute(self, context):
        _addon_prefs = context.preferences.addons[ADDON_PACKAGE].preferences

        _result = SUBSTANCE_Api.shader_presets_remove(_addon_prefs.shader_presets)
        if _result != Code_Response.success:
            SUBSTANCE_Utils.log_data("ERROR", "Shader Presets could not be removed...")
            _addon_prefs.shader_presets.clear()
            return {'FINISHED'}

        SUBSTANCE_Utils.log_data("INFO", "Shader Presets fully removed...")
        _addon_prefs.shader_presets.clear()
        return {'FINISHED'}


class SUBSTANCE_OT_SaveShaderPresets(bpy.types.Operator):
    bl_idname = 'substance.save_shader_presets'
    bl_label = 'Save shader preset'
    bl_description = "Save the shader presets"

    def execute(self, context):
        _addon_prefs = context.preferences.addons[ADDON_PACKAGE].preferences

        for _shader_preset in _addon_prefs.shader_presets:
            if _shader_preset.modified:
                _parms = getattr(context.scene, _shader_preset.parms_class_name)
                _outputs = getattr(context.scene, _shader_preset.outputs_class_name)
                _obj = {
                    "label": _shader_preset.label,
                    "filename": _shader_preset.filename,
                    "parms": _parms.get(),
                    "outputs": _outputs.get(),
                }

                _result = SUBSTANCE_Api.shader_presets_save(_obj)
                if _result != Code_Response.success:
                    SUBSTANCE_Utils.log_data(
                        "ERROR",
                        "Shader Presets [{}] could not be saved...[{}]".format(_obj["label"], _result))
                SUBSTANCE_Utils.log_data("INFO", "Shader Presets [{}] saved...".format(_obj["label"]))

        return {'FINISHED'}


class SUBSTANCE_OT_ResetShaderPreset(bpy.types.Operator):
    bl_idname = 'substance.reset_shader_preset'
    bl_label = 'Reset shader preset'
    bl_description = "Reset the shader preset"

    @classmethod
    def poll(cls, context):
        _, _selected_preset = SUBSTANCE_Utils.get_selected_shader_preset(context)
        return _selected_preset.modified

    def execute(self, context):
        _, _selected_preset = SUBSTANCE_Utils.get_selected_shader_preset(context)

        _parms = getattr(context.scene, _selected_preset.parms_class_name)
        _parms.reset()
        _outputs = getattr(context.scene, _selected_preset.outputs_class_name)
        _outputs.reset()

        _selected_preset.modified = False

        SUBSTANCE_Utils.log_data(
            "INFO",
            "Shader Presets [{}] is back to default values".format(_selected_preset.label),
            display=True)
        return {'FINISHED'}
