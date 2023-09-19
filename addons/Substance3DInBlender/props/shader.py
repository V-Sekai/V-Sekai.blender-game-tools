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

# file: props/shader.py
# brief: Shader Preset Property Groups
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy

from .common import SUBSTANCE_PG_GeneralItem


class SUBSTANCE_PG_ShaderOutput(SUBSTANCE_PG_GeneralItem):
    def initialize(self, output):
        super().initialize(output)


class SUBSTANCE_PG_ShaderParm(SUBSTANCE_PG_GeneralItem):
    type: bpy.props.StringProperty(name="type")

    def initialize(self, parm):
        super().initialize(parm)
        self.type = parm.type


class SUBSTANCE_PG_ShaderPreset(bpy.types.PropertyGroup):
    filename: bpy.props.StringProperty(name="filename")
    name: bpy.props.StringProperty(name="name")
    label: bpy.props.StringProperty(name="label")

    parms_class_name: bpy.props.StringProperty(name="parms_class_name")
    parms: bpy.props.CollectionProperty(type=SUBSTANCE_PG_ShaderParm)

    outputs_class_name: bpy.props.StringProperty(name="outputs_class_name")
    outputs: bpy.props.CollectionProperty(type=SUBSTANCE_PG_ShaderOutput)

    modified: bpy.props.BoolProperty(name="modified", default=False)

    def initialize(self, shader_preset):
        self.filename = shader_preset.filename
        self.name = shader_preset.filename.replace(".json", "")
        self.label = shader_preset.label

        self.parms_class_name = shader_preset.parms_class_name
        for _key, _parm in shader_preset.parms.items():
            _parm_item = self.parms.add()
            _parm_item.initialize(_parm)

        self.outputs_class_name = shader_preset.outputs_class_name
        for _key, _output in shader_preset.outputs.items():
            _output_item = self.outputs.add()
            _output_item.initialize(_output)
