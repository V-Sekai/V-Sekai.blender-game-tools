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

# file: utils.py
# brief: General utility functions
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy
import os
import json
from time import time
import xml.etree.ElementTree as ET
import traceback

from .common import (
    Code_OutParms,
    Code_Response,
    Code_ParmType,
    Code_ParmWidget,
    Code_ParmIdentifier,
    ICONS_DICT,
    ICONS_IMAGES,
    ADDON_ROOT,
    ADDON_PACKAGE,
    IMAGE_EXPORT_FORMAT,
    CLASS_GRAPH_PARMS,
    CLASS_GRAPH_OUTPUTS,
    PARMS_DEFAULT_GROUP,
    FORMATS_DICT,
    PRESET_DEFAULT,
    PRESET_CUSTOM,
    PARM_ANGLE_CONVERSION,
    SHADER_OUTPUT_UNKNOWN_USAGE
)


class SUBSTANCE_Utils():
    # Json
    @staticmethod
    def get_json(filepath):
        _json_obj = None
        with open(filepath, encoding="utf8") as _json_file:
            _json_obj = json.load(_json_file)
        return _json_obj

    @staticmethod
    def set_json(filepath, obj):
        with open(filepath, "w", encoding="utf8") as _json_file:
            json.dump(obj, _json_file, ensure_ascii=False)

    # Time
    @staticmethod
    def get_current_time_in_ms():
        return int(round(time() * 1000))

    # Log
    @staticmethod
    def log_data(type, message, display=False):
        if display:
            bpy.ops.substance.send_message(type=type, message="Substance 3D in Blender: "+message)
        else:
            print("Substance 3D in Blender: {} - {}".format(type, message))

    @staticmethod
    def log_traceback(message):
        print("Substance 3D in Blender: ERROR - TRACEBACK:\n")
        print(message)

    @staticmethod
    def message(title="", message="", icon="INFO", context=bpy.context):
        def _draw(self, context):
            self.layout.label(text=message)
        context.window_manager.popup_menu(_draw, title=title, icon=icon)

    # Rest response
    @staticmethod
    def get_response_data(data, key):
        try:
            _result = data.json()
            if key in _result:
                return (Code_Response.success, _result[key])
            else:
                return (Code_Response.response_json_key_error, None)
        except Exception:
            return (Code_Response.response_json_error, None)

    # Icons
    @staticmethod
    def init_icons():
        _icons_dir = os.path.join(ADDON_ROOT, "_icons").replace("\\", "/")
        for _image in ICONS_IMAGES:
            if _image["id"] not in ICONS_DICT:
                ICONS_DICT.load(_image["id"], os.path.join(_icons_dir, _image["filename"]), 'IMAGE')

    # Geo
    @staticmethod
    def get_selected_geo(selected_objects):
        _filtered = []
        for _item in selected_objects:
            if hasattr(_item.data, 'materials'):
                _filtered.append(_item)
        return _filtered

    # Graph
    @staticmethod
    def get_selected_graph(context=bpy.context):
        _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
        _selected_graph_idx = int(_selected_sbsar.graphs_list)
        _selected_graph = _selected_sbsar.graphs[_selected_graph_idx]
        return _selected_graph

    # Shader
    @staticmethod
    def get_selected_shader_preset(context=bpy.context, idx=-1):
        _addon_prefs = context.preferences.addons[ADDON_PACKAGE].preferences

        _selected_preset_idx = idx
        if _selected_preset_idx < 0:
            _selected_preset_idx = int(_addon_prefs.shader_preset_list)

        _selected_shader_preset = _addon_prefs.shader_presets[_selected_preset_idx]
        return _addon_prefs,  _selected_shader_preset

    @staticmethod
    def get_shader_file(filename):
        _custom_shaders_dir = os.path.join(ADDON_ROOT, "_presets/custom").replace('\\', '/')
        _shaders_dir = os.path.join(ADDON_ROOT, "_presets/default").replace('\\', '/')

        _path = os.path.join(_custom_shaders_dir, filename)
        if not os.path.exists(_path):
            _path = os.path.join(_shaders_dir, filename)

        return _path

    # Parameters
    @staticmethod
    def parms_empty(parms):
        for _parm in parms:
            if _parm.widget != Code_ParmWidget.nowidget.value:
                return False
        return True

    @staticmethod
    def value_fix_type(identifier, widget, type, new_value):
        if widget == Code_ParmWidget.combobox.value:
            return int(new_value)
        elif widget == Code_ParmWidget.slider.value:
            if type == Code_ParmType.integer.name:
                return int(new_value)
            elif type == Code_ParmType.float.name:
                return float(new_value)
            elif (type == Code_ParmType.integer2.name or
                    type == Code_ParmType.integer3.name or
                    type == Code_ParmType.integer4.name):
                return list(new_value)
            elif (type == Code_ParmType.float2.name or
                    type == Code_ParmType.float3.name or
                    type == Code_ParmType.float4.name):
                return list(new_value)
            else:
                return 0
        elif widget == Code_ParmWidget.color.value:
            if type == Code_ParmType.float.name:
                return float(new_value)
            elif type == Code_ParmType.float3.name or type == Code_ParmType.float4.name:
                return list(new_value)
            else:
                return 0
        elif widget == Code_ParmWidget.togglebutton.value:
            return int(new_value)
        elif widget == Code_ParmWidget.angle.value:
            return float(new_value) / PARM_ANGLE_CONVERSION
        elif widget == Code_ParmWidget.position.value:
            return list(new_value)
        elif widget == Code_ParmWidget.image.value:
            if isinstance(new_value, bpy.types.Image):
                return new_value.name
            else:
                return ""
        elif widget == Code_ParmWidget.nowidget.value:
            if identifier == Code_ParmIdentifier.outputsize.value:
                return list(new_value)
            elif identifier == Code_ParmIdentifier.randomseed.value:
                return int(new_value)
            else:
                return 0
        else:
            return 0

    # Outputs
    @staticmethod
    def get_output_key(attribute_name):
        _key = attribute_name
        for _item in Code_OutParms:
            _key = _key.replace(_item.value, "")
        _parm_key = attribute_name.replace(_key+"_", "")

        return (_key, _parm_key)

    # Render
    @staticmethod
    def render_image_input(img, context):
        if not context:
            context = bpy.context

        _addon_prefs = context.preferences.addons[ADDON_PACKAGE].preferences
        _default_path = _addon_prefs.path_default

        _format_idx = int(_addon_prefs.export_format)
        _file_extension = IMAGE_EXPORT_FORMAT[_format_idx][2].replace("*", "")
        img.file_format = IMAGE_EXPORT_FORMAT[_format_idx][1]
        _image_filepath = os.path.join(_default_path, img.name + _file_extension).replace("\\", "/")
        img.save_render(_image_filepath)

        return _image_filepath

    # SBSAR
    @staticmethod
    def get_unique_name(filename, context):
        _unique_name = filename.replace(".sbsar", "")
        _temp_name = _unique_name
        _counter = 0
        while _temp_name in context.scene.loaded_sbsars:
            _counter += 1
            _temp_name = _unique_name + "_{}".format(_counter)

        if _counter:
            return _unique_name + "_{}".format(_counter)
        return _unique_name

    @staticmethod
    def sbsar_to_json(
        sbsar_id,
        unique_name,
        filename,
        filepath,
        graphs,
        parms,
        outputs,
        embedded_presets,
        default_presets,
        default_normal_format,
        default_outputsize,
        shader_outputs,
    ):
        _obj = {
            "id": sbsar_id,
            "name": unique_name,
            "filename": filename,
            "filepath": filepath,
            "graphs": []
        }
        _multi_graph = len(graphs) > 1

        for _graph_idx, _item in enumerate(graphs):
            _default_preset = default_presets[str(_graph_idx)]
            if _multi_graph:
                _mat_name = "{}-{}".format(unique_name, _item["label"]).replace(" ", "_")
                _class_name = "{}-{}".format(sbsar_id, _item["id"])
            else:
                _mat_name = "{}".format(unique_name).replace(" ", "_")
                _class_name = "{}".format(sbsar_id)

            _graph = {
                "index": _graph_idx,
                "id": _item["id"],
                "name": _item["label"],
                "mat_name": _mat_name,
                "parms_class_name": CLASS_GRAPH_PARMS.format(_class_name),
                "outputs_class_name": CLASS_GRAPH_OUTPUTS.format(_class_name),
                "parms": {},
                "parms_groups": {},
                "outputs": {},
                "presets": [],
                "$randomseed_exists": False,
                "$outputsize_exists": False
            }

            if "physicalSize" not in _item or _item["physicalSize"] == [0.0, 0.0, 0.0]:
                _graph["physicalSize"] = [1.0, 1.0, 1.0]
            else:
                _graph["physicalSize"] = [
                    _item["physicalSize"][0]/100,
                    _item["physicalSize"][1]/100,
                    _item["physicalSize"][2]/100]

            for _parm in parms:
                if _parm["graphID"] == _graph["id"]:
                    if _parm["guiWidget"] != Code_ParmWidget.nowidget.value:
                        _group = _parm["guiGroup"] if len(_parm["guiGroup"]) > 0 else PARMS_DEFAULT_GROUP
                        if _group not in _graph["parms_groups"]:
                            _graph["parms_groups"][_group] = [_parm["identifier"]]
                        else:
                            _graph["parms_groups"][_group].append(_parm["identifier"])

                    _graph["parms"][_parm["identifier"]] = {
                        "id": _parm["id"],
                        "identifier": _parm["identifier"],
                        "label": _parm["label"],
                        "graphID": _parm["graphID"],
                        "graphIDX": _graph_idx,
                        "visibleIf": _parm["visibleIf"],
                        "type": _parm["type"],
                        "guiWidget": _parm["guiWidget"],
                        "guiGroup": _parm["guiGroup"] if len(_parm["guiGroup"]) > 0 else PARMS_DEFAULT_GROUP,
                        "guiDescription": _parm["guiDescription"],
                        "userTag": _parm["userTag"],
                        "useCache": _parm["useCache"],
                        "showAsPin": _parm["showAsPin"],
                        "isHeavyDuty": _parm["isHeavyDuty"],
                        "guiVisibleIf": _parm["guiVisibleIf"],
                        "channelUse": _parm["channelUse"] if "channelUse" in _parm else None,
                        "defaultValue": _parm["defaultValue"] if "defaultValue" in _parm else "",
                        "value": _parm["value"] if "value" in _parm else "",
                        "maxValue": _parm["maxValue"] if "maxValue" in _parm else None,
                        "minValue": _parm["minValue"] if "minValue" in _parm else None,
                        "labelFalse": _parm["labelFalse"] if "labelFalse" in _parm else None,
                        "labelTrue": _parm["labelTrue"] if "labelTrue" in _parm else None,
                        "sliderClamp": _parm["sliderClamp"] if "sliderClamp" in _parm else None,
                        "sliderStep": _parm["sliderStep"] if "sliderStep" in _parm else None,
                        "enumValues": []
                    }
                    if "enumValues" in _parm:
                        for _enum_idx, _enum in enumerate(_parm["enumValues"]):
                            _graph["parms"][_parm["identifier"]]["enumValues"].append({
                                "index": _enum_idx,
                                "value": _enum["first"],
                                "label": _enum["second"],
                                "first": _enum["first"],
                                "second": _enum["second"]
                            })
                            if _enum["second"] == default_normal_format:
                                _graph["parms"][_parm["identifier"]]["value"] = _enum["first"]
                                _graph["parms"][_parm["identifier"]]["defaultValue"] = _enum["first"]

                    if _parm["identifier"] == Code_ParmIdentifier.outputsize.value:
                        _graph["$outputsize_exists"] = True
                        _graph["parms"][_parm["identifier"]]["defaultValue"] = default_outputsize
                        _graph["parms"][_parm["identifier"]]["value"] = default_outputsize
                    if _parm["identifier"] == Code_ParmIdentifier.randomseed.value:
                        _graph["$randomseed_exists"] = True

            for _output in outputs:
                if _output["graphID"] == _graph["id"]:
                    _shader_id = None
                    if _output["defaultChannelUse"] in shader_outputs.shader_preset.outputs:
                        _shader_id = shader_outputs.shader_preset.outputs[_output["defaultChannelUse"]].id

                    if _output["defaultChannelUse"] != SHADER_OUTPUT_UNKNOWN_USAGE:
                        _key = _output["defaultChannelUse"]
                    else:
                        _key = _output["identifier"]
                    _graph["outputs"][_key] = {
                        "id": _output["id"],
                        "identifier": _output["identifier"],
                        "label": _output["label"],
                        "group": _output["group"],
                        "graphID": _output["graphID"],
                        "graphIDX": _graph_idx,
                        "format": _output["format"],
                        "enabled": _output["enabled"],
                        "defaultChannelUse": _key,
                        "channelUseSpecified": _output["channelUseSpecified"],
                        "channelUse": _output["channelUse"],
                        "guiVisibleIf": _output["guiVisibleIf"],
                        "mipmaps": _output["mipmaps"],
                        "outputGuiType": _output["outputGuiType"],
                        "resultFormat": _output["resultFormat"],
                        "type": _output["type"],
                        "userTag": _output["userTag"],
                    }

                    if _shader_id is not None:
                        _graph["outputs"][_key]["shader_enabled"] = getattr(
                            shader_outputs,
                            _shader_id + Code_OutParms.enabled.value)
                        _graph["outputs"][_key]["shader_colorspace"] = getattr(
                            shader_outputs,
                            _shader_id + Code_OutParms.colorspace.value)

                        _format = getattr(shader_outputs, _shader_id + Code_OutParms.format.value)
                        _bitdepth = getattr(shader_outputs, _shader_id + Code_OutParms.bitdepth.value)
                        _graph["outputs"][_key]["shader_format"] = _format
                        _graph["outputs"][_key]["shader_bitdepth"] = SUBSTANCE_Utils.get_bitdepth(_format, _bitdepth)
                    else:
                        _addon_prefs = bpy.context.preferences.addons[ADDON_PACKAGE].preferences
                        _value_enabled = len(shader_outputs.shader_preset.outputs.keys()) == 0
                        _graph["outputs"][_key]["shader_enabled"] = _value_enabled
                        _graph["outputs"][_key]["shader_colorspace"] = _addon_prefs.output_default_colorspace
                        _format = _addon_prefs.output_default_format
                        _bitdepth = SUBSTANCE_Utils.get_bitdepth(_format, _addon_prefs.output_default_bitdepth)
                        _graph["outputs"][_key]["shader_format"] = _format
                        _graph["outputs"][_key]["shader_bitdepth"] = _bitdepth

            _graph["presets"].append({
                "label": PRESET_DEFAULT,
                "value": _default_preset,
                "embedded": True,
                "icon": "LOCKED"
            })
            _graph["presets"].append({
                "label": PRESET_CUSTOM,
                "value": _default_preset,
                "embedded": False,
                "icon": "UNLOCKED"
            })

            for _preset in embedded_presets[_graph["id"]]:
                _graph["presets"].append({
                    "label": _preset["label"],
                    "embedded": True,
                    "icon": "LOCKED",
                    "value": _preset["value"]
                })
            _obj["graphs"].append(_graph)
        return _obj

    # Presets
    @staticmethod
    def init_preset(preset, output_size, parm_output_size, values_normal_format, parms_normal_format):
        try:
            _preset_value = preset.value
            _preset_xml = ET.fromstring(_preset_value)

            if parm_output_size is not None:
                _outputsize_id = str(parm_output_size.id)
            else:
                _outputsize_id = -1

            _output_size_item = None
            _normal_format_items = []
            for _preset_input in _preset_xml:
                if parm_output_size is not None and _preset_input.attrib["uid"] == _outputsize_id:
                    _output_size_item = _preset_input
                else:
                    for _item in parms_normal_format:
                        _item_id = "{}".format(_item.id)
                        if _preset_input.attrib["uid"] == _item_id:
                            _normal_format_items.append(_preset_input)

            if _output_size_item is not None:
                _output_size_item.attrib["value"] = "{},{}".format(output_size[0], output_size[1])
            else:
                if parm_output_size is not None:
                    _el = ET.SubElement(
                        _preset_xml, "presetinput",
                        attrib={
                            "identifier": parm_output_size.identifier,
                            "uid": "{}".format(parm_output_size.id),
                            "type": "{}".format(Code_ParmType.integer2.value),
                            "value": "{},{}".format(output_size[0], output_size[1]),
                        }
                    )
                    _el.tail = "\n"

            for _idx, _item in enumerate(parms_normal_format):
                _child_found = None
                for _child in _normal_format_items:
                    if _child.attrib["uid"] == _item.id:

                        _child_found = _child
                        break
                if _child_found is not None:
                    _child.attrib["value"] = "{}".format(values_normal_format[_idx])
                else:
                    _el = ET.SubElement(
                        _preset_xml, "presetinput",
                        attrib={
                            "identifier": _item.identifier,
                            "uid": "{}".format(_item.id),
                            "type": "{}".format(Code_ParmType.integer.value),
                            "value": "{}".format(values_normal_format[_idx]),
                        }
                    )
                    _el.tail = "\n"

            _new_preset_value = ET.tostring(_preset_xml, encoding='unicode')
            return (Code_Response.success, _new_preset_value)
        except Exception:
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return (Code_Response.sbsar_init_preset_error, None)

    @staticmethod
    def update_preset_outputsize(preset_value, parm, value):
        _preset_xml = ET.fromstring(preset_value)

        _output_size_item = None
        for _preset_input in _preset_xml:
            if _preset_input.attrib["uid"] == str(parm.id):
                _output_size_item = _preset_input

        if _output_size_item is not None:
            _output_size_item.attrib["value"] = "{},{}".format(value[0], value[1])
        else:
            _el = ET.SubElement(
                _preset_xml, "presetinput",
                attrib={
                    "identifier": parm.identifier,
                    "uid": "{}".format(parm.id),
                    "type": "{}".format(Code_ParmType.integer2.value),
                    "value": "{},{}".format(value[0], value[1]),
                }
            )
            _el.tail = "\n"

        _new_preset_value = ET.tostring(_preset_xml, encoding='unicode')
        return _new_preset_value

    # Formats
    @staticmethod
    def get_formats():
        _formats = []
        for _key, _format in FORMATS_DICT.items():
            _formats.append(
                (_key, "{} ({})".format(_format["label"], _format["ext"]), _key)
            )

        return _formats

    @staticmethod
    def get_bitdepth(format, bitdepth):
        for _idx, _bitdepth in enumerate(FORMATS_DICT[format]["bitdepth"]):
            if _bitdepth == bitdepth:
                return _idx
        return 0

    # Physical Size
    @staticmethod
    def get_physical_size(physical_size, context):
        _scale = context.scene.unit_settings.scale_length

        _new_physical_size = [
            physical_size[0] * _scale,
            physical_size[1] * _scale,
            physical_size[2] * _scale
        ]
        return _new_physical_size
