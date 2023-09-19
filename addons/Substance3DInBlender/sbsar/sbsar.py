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

# file: sbsar/sbsar.py
# brief: Substance class object definition
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

from ..common import Code_ParmIdentifier


class SBS_Preset():
    def __init__(self, preset):
        self.label = preset["label"]
        self.value = preset["value"]
        self.icon = preset["icon"]
        self.embedded = preset["embedded"]

    def to_json(self):
        _obj = {
            "label": self.label,
            "value": self.value,
            "embedded": self.embedded,
            "icon": self.icon
        }
        return _obj


class SBS_Output():
    def __init__(self, output):
        self.id = output["id"]
        self.identifier = output["identifier"]
        self.label = output["label"]
        self.group = output["group"]
        self.graphID = output["graphID"]
        self.format = output["format"]
        self.enabled = output["enabled"]
        self.defaultChannelUse = output["defaultChannelUse"]
        self.channelUseSpecified = output["channelUseSpecified"]
        self.channelUse = output["channelUse"]
        self.guiVisibleIf = output["guiVisibleIf"]
        self.mipmaps = output["mipmaps"]
        self.outputGuiType = output["outputGuiType"]
        self.resultFormat = output["resultFormat"]
        self.type = output["type"]
        self.userTag = output["userTag"]
        self.shader_enabled = output["shader_enabled"]
        self.shader_colorspace = output["shader_colorspace"]
        self.shader_format = output["shader_format"]
        self.shader_bitdepth = output["shader_bitdepth"]

    def to_json(self):
        _obj = {
            "id": self.id,
            "identifier": self.identifier,
            "label": self.label,
            "group": self.group,
            "graphID": self.graphID,
            "format": self.format,
            "enabled": self.enabled,
            "defaultChannelUse": self.defaultChannelUse,
            "channelUseSpecified": self.channelUseSpecified,
            "channelUse": self.channelUse,
            "guiVisibleIf": self.guiVisibleIf,
            "mipmaps": self.mipmaps,
            "outputGuiType": self.outputGuiType,
            "resultFormat": self.resultFormat,
            "type": self.type,
            "userTag": self.userTag,
            "shader_enabled": self.shader_enabled,
            "shader_colorspace": self.shader_colorspace,
            "shader_format": self.shader_format,
            "shader_bitdepth": self.shader_bitdepth
        }

        return _obj


class SBS_EnumValue():
    def __init__(self, enum):
        self.index = enum["index"]
        self.value = enum["first"]
        self.label = enum["second"]
        self.first = enum["first"]
        self.second = enum["second"]

    def to_json(self):
        _obj = {
            "index": self.index,
            "value": self.value,
            "label": self.label,
            "first": self.first,
            "second": self.second,
        }
        return _obj


class SBS_Parm():
    def __init__(self, parm):
        self.id = parm["id"]
        self.identifier = parm["identifier"]
        self.label = parm["label"]
        self.graphID = parm["graphID"]
        self.visibleIf = parm["visibleIf"]
        self.type = parm["type"]
        self.guiWidget = parm["guiWidget"]
        self.guiGroup = parm["guiGroup"]
        self.guiDescription = parm["guiDescription"]
        self.userTag = parm["userTag"]
        self.useCache = parm["useCache"]
        self.showAsPin = parm["showAsPin"]
        self.isHeavyDuty = parm["isHeavyDuty"]
        self.guiVisibleIf = parm["guiVisibleIf"]
        self.channelUse = parm["channelUse"]
        self.defaultValue = parm["defaultValue"]
        self.value = parm["value"]
        self.maxValue = parm["maxValue"]
        self.minValue = parm["minValue"]
        self.labelFalse = parm["labelFalse"]
        self.labelTrue = parm["labelTrue"]
        self.sliderClamp = parm["sliderClamp"]
        self.sliderStep = parm["sliderStep"]
        self.enumValues = []

        for _enum in parm["enumValues"]:
            _new_enum = SBS_EnumValue(_enum)
            self.enumValues.append(_new_enum)

    def to_json(self):
        _obj = {
            "id": self.id,
            "identifier": self.identifier,
            "label": self.label,
            "graphID": self.graphID,
            "visibleIf": self.visibleIf,
            "type": self.type,
            "guiWidget": self.guiWidget,
            "guiGroup": self.guiGroup,
            "guiDescription": self.guiDescription,
            "userTag": self.userTag,
            "useCache": self.useCache,
            "showAsPin": self.showAsPin,
            "isHeavyDuty": self.isHeavyDuty,
            "guiVisibleIf": self.guiVisibleIf,
            "channelUse": self.channelUse,
            "defaultValue": self.defaultValue,
            "value": self.value,
            "maxValue": self.maxValue,
            "minValue": self.minValue,
            "labelFalse": self.labelFalse,
            "labelTrue": self.labelTrue,
            "sliderClamp": self.sliderClamp,
            "sliderStep": self.sliderStep,
            "enumValues": []
        }

        for _enum in self.enumValues:
            _obj["enumValues"].append(_enum.to_json())

        return _obj


class SBS_Material():
    def __init__(self, name):
        self.name = name


class SBS_Graph():
    def __init__(self, index, graph):
        self.index = index
        self.id = graph["id"]
        self.name = graph["name"]
        self.material = SBS_Material(graph["mat_name"])
        self.parms_class_name = graph["parms_class_name"]
        self.outputs_class_name = graph["outputs_class_name"]
        self.physicalSize = graph["physicalSize"]
        self.randomseed_exists = graph["$randomseed_exists"]
        self.outputsize_exists = graph["$outputsize_exists"]
        self.parms = {}
        self.parms_groups = {}
        self.outputs = {}
        self.presets = []

        for _key, _parm in graph["parms"].items():
            _new_parm = SBS_Parm(_parm)
            self.parms[_key] = _new_parm

        for _key, _parm_group in graph["parms_groups"].items():
            self.parms_groups[_key] = _parm_group

        for _key, _output in graph["outputs"].items():
            _new_output = SBS_Output(_output)
            self.outputs[_key] = _new_output

        for _preset in graph["presets"]:
            _new_preset = SBS_Preset(_preset)
            self.presets.append(_new_preset)

    def get_normal_formats(self, normal_format):
        _parms = []
        _value = []
        for _key, _parm in self.parms.items():
            for _item in _parm.enumValues:
                if _item.label == normal_format:
                    _parms.append(_parm)
                    _value.append(_item.value)
                    break
        return (_parms, _value)

    def get_outputsize(self):
        for _key, _parm in self.parms.items():
            if _parm.identifier == Code_ParmIdentifier.outputsize.value:
                return _parm
        return None

    def to_json(self):
        _obj = {
            "id": self.id,
            "name": self.name,
            "mat_name": self.material.name,
            "parms_groups": self.parms_groups,
            "physicalSize": self.physicalSize,
            "$randomseed_exists": self.randomseed_exists,
            "$outputsize_exists": self.outputsize_exists,
            "parms": {},
            "outputs": {},
            "presets": [],
            "parms_class_name": self.parms_class_name,
            "outputs_class_name": self.outputs_class_name
        }
        for _key, _parm in self.parms.items():
            _obj["parms"][_key] = _parm.to_json()

        for _key, _output in self.outputs.items():
            _obj["outputs"][_key] = _output.to_json()

        for _preset in self.presets:
            _obj["presets"].append(_preset.to_json())

        return _obj


class SBSAR():
    def __init__(self, json_obj):
        self.id = json_obj["id"]
        self.name = json_obj["name"]
        self.filename = json_obj["filename"]
        self.filepath = json_obj["filepath"]
        self.graphs = []

        for _idx, _graph in enumerate(json_obj["graphs"]):
            _new_graph = SBS_Graph(_idx, _graph)
            self.graphs.append(_new_graph)

    def to_json(self):
        _obj = {
            "id": self.id,
            "name": self.name,
            "filename": self.filename,
            "filepath": self.filepath,
            "graphs": []
        }

        for _graph in self.graphs:
            _obj["graphs"].append(_graph.to_json())
        return _obj
