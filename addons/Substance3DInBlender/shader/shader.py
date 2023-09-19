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

# file: shader/shader.py
# brief: Shader preset class object definition
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2


class ShaderPreset_Output():
    def __init__(self, output):
        self.id = output["id"]
        self.label = output["label"]
        self.enabled = output["enabled"]
        self.optional = output["optional"]
        self.colorspace = output["colorspace"]
        self.format = output["format"]
        self.bitdepth = output["bitdepth"]
        self.normal = True if "normal" in output else False

    def to_json(self):
        _obj = {
            "id": self.id,
            "label": self.label,
            "enabled": self.enabled,
            "optional": self.optional,
            "colorspace": self.colorspace,
            "format": self.format,
            "bitdepth": self.bitdepth
        }
        if self.normal:
            _obj["normal"] = True
        return _obj


class ShaderPreset_Parm():
    def __init__(self, parm):
        self.id = parm["id"]
        self.label = parm["label"]
        self.type = parm["type"]
        self.default = parm["default"]
        self.min = parm["min"] if "min" in parm else None
        self.max = parm["max"] if "max" in parm else None

    def to_json(self):
        _obj = {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "default": self.default
        }
        if self.min is not None:
            _obj["min"] = self.min
        if self.max is not None:
            _obj["max"] = self.max
        return _obj


class ShaderPreset():
    def __init__(self, filename, data, parms_class_name, outputs_class_name):
        self.filename = filename
        self.label = data["label"]
        self.parms_class_name = parms_class_name
        self.outputs_class_name = outputs_class_name
        self.parms = {}
        self.outputs = {}

        for _key, _parm in data["parms"].items():
            _item = ShaderPreset_Parm(_parm)
            self.parms[_key] = _item

        for _key, _output in data["outputs"].items():
            _item = ShaderPreset_Output(_output)
            self.outputs[_key] = _item

    def to_json(self):
        _obj = {
            "label": self.label,
            "parms": {},
            "outputs": {},
        }

        for _key, _parm in self.parms.items():
            _obj["parms"][_key] = _parm.to_json()

        for _key, _output in self.outputs.items():
            _obj["outputs"][_key] = _output.to_json()

        return _obj
