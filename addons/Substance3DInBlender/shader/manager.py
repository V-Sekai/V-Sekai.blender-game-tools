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

# file: shader/manager.py
# brief: Shader presets operation manager
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import os
import traceback

from .shader import ShaderPreset
from ..utils import SUBSTANCE_Utils
from ..factory.shader import SUBSTANCE_ShaderFactory
from ..common import ADDON_ROOT, Code_Response, CLASS_SHADER_PARMS, CLASS_SHADER_OUTPUTS


class SUBSTANCE_ShaderManager():
    def __init__(self):
        pass

    def init_presets(self):
        try:
            _shaders_dir = os.path.join(ADDON_ROOT, "_presets/default").replace('\\', '/')

            _shaders_list = []
            for _filename in os.listdir(_shaders_dir):
                _path = SUBSTANCE_Utils.get_shader_file(_filename)

                _data = SUBSTANCE_Utils.get_json(_path)

                # Set shader class names
                _parms_class_name = CLASS_SHADER_PARMS.format(_filename.replace(".json", "").replace(" ", "_"))
                _outputs_class_name = CLASS_SHADER_OUTPUTS.format(_filename.replace(".json", "").replace(" ", "_"))

                _shader_preset = ShaderPreset(_filename, _data, _parms_class_name, _outputs_class_name)
                _shaders_list.append(_shader_preset)

                # Register variables class
                SUBSTANCE_ShaderFactory.register_shader_preset_classes(_shader_preset)

            return (Code_Response.success, _shaders_list)
        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Shader Preset initialization error:")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return (Code_Response.shader_preset_init_error, None)

    def remove_presets(self, shader_presets):
        try:
            for _shader_preset in shader_presets:
                SUBSTANCE_ShaderFactory.unregister_shader_preset_class(_shader_preset.parms_class_name)
                SUBSTANCE_ShaderFactory.unregister_shader_preset_class(_shader_preset.outputs_class_name)

            return Code_Response.success
        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Shader Preset removal error:")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return Code_Response.shader_preset_remove_error

    def save_presets(self, shader_preset):
        try:
            _default_shader_file = os.path.join(
                ADDON_ROOT,
                "_presets/default/" + shader_preset["filename"]).replace('\\', '/')
            _custom_shader_file = os.path.join(
                ADDON_ROOT,
                "_presets/custom/" + shader_preset["filename"]).replace('\\', '/')
            _custom_shader_path = os.path.join(
                ADDON_ROOT,
                "_presets/custom").replace('\\', '/')

            # Read Original Shader Preset
            if not os.path.exists(_default_shader_file):
                return Code_Response.shader_preset_default_not_exist_error

            _data = SUBSTANCE_Utils.get_json(_default_shader_file)

            _data["parms"] = shader_preset["parms"]
            _data["outputs"] = shader_preset["outputs"]

            # Write Custom Shader Preset
            if not os.path.exists(_custom_shader_path):
                os.mkdir(_custom_shader_path)

            SUBSTANCE_Utils.set_json(_custom_shader_file, _data)

            return Code_Response.success

        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Shader Preset saving error:")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return Code_Response.shader_preset_save_error
