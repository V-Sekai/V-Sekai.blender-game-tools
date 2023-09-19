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

# file: factory/shader.py
# brief: Dynamic class creation for shader objects
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy
from ..props.utils import get_bitdepths
from ..utils import SUBSTANCE_Utils
from ..shader.callbacks import SUBSTANCE_ShaderCallbacks
from ..common import (
    Code_ShaderParmType,
    Code_OutParms,
    COLORSPACES_DICT
)


class SUBSTANCE_ShaderFactory():
    # Shader preset parameters
    @staticmethod
    def create_parm_item(parm):
        if parm.type == Code_ShaderParmType.float_slider.value or parm.type == Code_ShaderParmType.float_maxmin.value:
            return bpy.props.FloatProperty(
                name=parm.id,
                default=parm.default,
                soft_max=parm.max,
                soft_min=parm.min,
                update=SUBSTANCE_ShaderCallbacks.on_parm_changed)
        else:
            return None

    @staticmethod
    def register_parms_class(shader_preset):
        _attributes = {}
        for _key, _parm in shader_preset.parms.items():
            _attribute = SUBSTANCE_ShaderFactory.create_parm_item(_parm)
            if _attribute:
                _attributes[_key] = _attribute

        def _on_reset(self):
            for _attr_name in self.__annotations__:
                _parm = None
                for _key, _p in self.shader_preset.parms.items():
                    if _p.id == _attr_name:
                        _parm = _p
                        break
                if _parm is not None:
                    setattr(self, _attr_name, _parm.default)

        def _get(self):
            _obj = self.shader_preset.to_json()
            for _key, _item in _obj["parms"].items():
                _item["default"] = getattr(self, _item["id"])
            return _obj["parms"]

        _parms_class = type(
            shader_preset.parms_class_name,
            (bpy.types.PropertyGroup,),
            {
                "__annotations__": _attributes,
                "shader_preset": shader_preset,
                "reset": _on_reset,
                "get": _get
            })

        bpy.utils.register_class(_parms_class)
        setattr(
            bpy.types.Scene,
            shader_preset.parms_class_name,
            bpy.props.PointerProperty(name=shader_preset.parms_class_name, type=_parms_class))

    # Shader preset outputs
    @staticmethod
    def create_output_item(output):
        _attributes = [
            bpy.props.BoolProperty(
                name=output.id + Code_OutParms.enabled.value,
                default=output.enabled,
                description="The default value to enable/disable the baking of the {} map".format(output.label),
                update=SUBSTANCE_ShaderCallbacks.on_output_changed),
            bpy.props.EnumProperty(
                name=output.id + Code_OutParms.colorspace.value,
                default=output.colorspace,
                description="The default colorspace to be used when creating the shader network",
                items=COLORSPACES_DICT,
                update=SUBSTANCE_ShaderCallbacks.on_output_changed),
            bpy.props.EnumProperty(
                name=output.id + Code_OutParms.format.value,
                default=output.format,
                description="The default file format to be used by the Output",
                items=SUBSTANCE_Utils.get_formats(),
                update=SUBSTANCE_ShaderCallbacks.on_output_changed),
            bpy.props.EnumProperty(
                name=output.id + Code_OutParms.bitdepth.value,
                default=SUBSTANCE_Utils.get_bitdepth(output.format, output.bitdepth),
                description="The default bitdepth of the Output",
                items=lambda self, context: get_bitdepths(self, context,  output.id + Code_OutParms.format.value),
                update=SUBSTANCE_ShaderCallbacks.on_output_changed)
        ]
        return _attributes

    @staticmethod
    def register_output_class(shader_preset):
        _attributes = {}
        for _key, _output in shader_preset.outputs.items():
            _attribute = SUBSTANCE_ShaderFactory.create_output_item(_output)
            _attributes[_key + Code_OutParms.enabled.value] = _attribute[0]
            _attributes[_key + Code_OutParms.colorspace.value] = _attribute[1]
            _attributes[_key + Code_OutParms.format.value] = _attribute[2]
            _attributes[_key + Code_OutParms.bitdepth.value] = _attribute[3]

        def _on_reset(self):
            for _attr_name in self.__annotations__:
                _key = _attr_name
                for _item in Code_OutParms:
                    _key = _key.replace(_item.value, "")
                _parm_key = _attr_name.replace(_key+"_", "")

                _output = None
                for _k, _o in self.shader_preset.outputs.items():
                    if _o.id == _key:
                        _output = _o
                        break

                if _output is not None:
                    _output_json = _output.to_json()
                    _value = _output_json[_parm_key]
                    setattr(self, _attr_name, _value)

        def _get(self):
            _obj = self.shader_preset.to_json()
            for _key, _item in _obj["outputs"].items():
                _item["enabled"] = getattr(self, _item["id"] + Code_OutParms.enabled.value)
                _item["colorspace"] = getattr(self, _item["id"] + Code_OutParms.colorspace.value)
                _item["format"] = getattr(self, _item["id"] + Code_OutParms.format.value)
                _item["bitdepth"] = getattr(self, _item["id"] + Code_OutParms.bitdepth.value)

                if self.shader_preset.outputs[_key].normal:
                    _item["normal"] = True
            return _obj["outputs"]

        _output_class = type(
            shader_preset.outputs_class_name,
            (bpy.types.PropertyGroup,),
            {
                "__annotations__": _attributes,
                "shader_preset": shader_preset,
                "reset": _on_reset,
                "get": _get
            })
        bpy.utils.register_class(_output_class)
        setattr(
            bpy.types.Scene,
            shader_preset.outputs_class_name,
            bpy.props.PointerProperty(name=shader_preset.outputs_class_name, type=_output_class))

    # General
    @staticmethod
    def register_shader_preset_classes(shader_preset):
        SUBSTANCE_ShaderFactory.register_parms_class(shader_preset)
        SUBSTANCE_ShaderFactory.register_output_class(shader_preset)

    @staticmethod
    def unregister_shader_preset_class(class_name):
        if hasattr(bpy.context.scene, class_name):
            _object = getattr(bpy.context.scene, class_name)
            _class_type = type(_object)
            delattr(bpy.types.Scene, class_name)
            bpy.utils.unregister_class(_class_type)
