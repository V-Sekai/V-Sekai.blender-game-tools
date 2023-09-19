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

# file: material/manager.py
# brief: Material operations manager
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import traceback
from copy import deepcopy
import time
import os
import bpy
from ..thread_ops import SUBSTANCE_Threads
from ..utils import SUBSTANCE_Utils
from ..common import RENDER_IMG_UPDATE_DELAY_S


class SUBSTANCE_MaterialManager():

    @staticmethod
    def get_image(name, filepath):
        if name in bpy.data.images:
            _image = bpy.data.images[name]
            _image_filepath = bpy.path.abspath(_image.filepath)
            _image_filepath = os.path.abspath(_image_filepath)
            _image_filepath = _image_filepath.replace("\\", "/")
            _new_filepath = filepath.replace("\\", "/")

            if _image_filepath != _new_filepath:
                _image.filepath = _new_filepath
            _image.reload()
            return _image
        _image = bpy.data.images.load(filepath=filepath.replace("\\", "/"))
        _image.name = name
        return _image

    @staticmethod
    def get_existing_material(material_name):
        if material_name in bpy.data.materials:
            return bpy.data.materials[material_name]
        return None

    @staticmethod
    def _reset_image(node, image):
        def _set_image():
            node.image = image
        SUBSTANCE_Threads.main_thread_run(_set_image)

    @staticmethod
    def create_material(context, selected_sbsar, selected_graph, outputs):
        try:
            SUBSTANCE_Threads.cursor_push('WAIT')

            _addons_prefs, _selected_shader_preset = SUBSTANCE_Utils.get_selected_shader_preset(
                context,
                int(selected_graph.shader_preset_list))
            _shader_parms_class = getattr(context.scene, _selected_shader_preset.parms_class_name)

            _shader_filepath = SUBSTANCE_Utils.get_shader_file(_selected_shader_preset.filename)

            _material = SUBSTANCE_MaterialManager.get_existing_material(selected_graph.material.name)

            _shader_graph = SUBSTANCE_Utils.get_json(_shader_filepath)
            _shader_outputs_class = getattr(context.scene, selected_graph.outputs_class_name)

            _shader_outputs = _shader_outputs_class.to_json()["outputs"]

            _ordered_outputs = {}
            for _idx, _output in enumerate(_shader_outputs):
                _ordered_outputs[_output] = _idx

            if _material is None or _selected_shader_preset.name != selected_graph.material.shader:
                # Time
                _time_start = time.time()

                if _material is None:
                    _material = bpy.data.materials.new(name=selected_graph.material.name)

                    if _addons_prefs.auto_attach_material:
                        _active_obj = bpy.context.active_object
                        _active_obj.data.materials.append(_material)

                _material.use_nodes = True
                try:
                    _material.cycles.displacement_method = 'BOTH'
                except Exception:
                    pass

                # Cleanup graph
                _mat_nodes = _material.node_tree.nodes
                for _node in _mat_nodes:
                    _mat_nodes.remove(_node)

                if selected_graph.material.name in bpy.data.node_groups:
                    _subgroup = bpy.data.node_groups[selected_graph.material.name]
                    for _node in _subgroup.nodes:
                        _subgroup.nodes.remove(_node)
                    for _output in _subgroup.inputs:
                        _subgroup.inputs.remove(_output)
                    for _output in _subgroup.outputs:
                        _subgroup.outputs.remove(_output)

                # Add static shader nodes
                _items = {}
                for _node in _shader_graph["nodes"]:
                    _name = _node["name"].replace("$matname", selected_graph.material.name)
                    if _node["path"] == "root":
                        _nodes = _mat_nodes
                    else:
                        _nodes = _items[_node["path"].replace("root/", "")].node_tree.nodes

                    if _name in _nodes:
                        _items[_node["id"]] = _nodes[_name]
                    else:
                        _items[_node["id"]] = _nodes.new(_node["type"])
                        _items[_node["id"]].name = _name
                        if _node["type"] == "NodeFrame":
                            _items[_node["id"]].label = _node["label"]
                            continue

                        _items[_node["id"]].location = (_node["location"][0], _node["location"][1])
                        if _node["type"] == "ShaderNodeGroup":
                            if selected_graph.material.name in bpy.data.node_groups:
                                _node_tree = bpy.data.node_groups[selected_graph.material.name]
                            else:
                                _node_tree = bpy.data.node_groups.new(
                                    type='ShaderNodeTree',
                                    name=selected_graph.material.name)
                            _items[_node["id"]].node_tree = _node_tree

                # Get the substance Node Group
                _sbs_group = _material.node_tree.nodes["{}_sbsar".format(selected_graph.material.name)]

                # Initialize Enabled outputs
                _location = [-600, 0]
                for _output in _ordered_outputs:
                    if _output not in _shader_outputs:
                        continue

                    _filepath = selected_graph.outputs[_output].filepath
                    _filename = selected_graph.outputs[_output].filename
                    if _output in outputs:
                        _filepath = outputs[_output]["path"]
                        _filename = bpy.path.basename(outputs[_output]["path"])
                        selected_graph.outputs[_output].filepath = _filepath
                        selected_graph.outputs[_output].filename = _filename

                    if _filepath != "" and _shader_outputs[_output]["shader_enabled"]:
                        _name = "Tx {}".format(_output)
                        if _name in _sbs_group.node_tree.nodes:
                            _items["tx_{}".format(_output)] = _sbs_group.node_tree.nodes[_name]
                            _items["tx_{}".format(_output)].location = (_location[0], _location[1])
                        else:
                            _items["tx_{}".format(_output)] = _sbs_group.node_tree.nodes.new("ShaderNodeTexImage")
                            _items["tx_{}".format(_output)].name = "Tx {}".format(_output)
                            _items["tx_{}".format(_output)].location = (_location[0], _location[1])

                            _img_name = "{}_{}".format(selected_graph.material.name, _output)
                            _img = SUBSTANCE_MaterialManager.get_image(_img_name, _filepath)
                            _img.colorspace_settings.name = _shader_outputs[_output]["shader_colorspace"]
                            _items["tx_{}".format(_output)].image = _img

                            if _output in _shader_graph["outputs"] and "normal" in _shader_graph["outputs"][_output]:
                                _items["normal_{}".format(_output)] = _sbs_group.node_tree.nodes.new(
                                    "ShaderNodeNormalMap")
                                _items["normal_{}".format(_output)].name = "Normal {}".format(_output)
                                _items["normal_{}".format(_output)].location = (_location[0] + 300, _location[1])

                        _location[1] -= 300

                # Initialize shader sockets
                for _socket in _shader_graph["sockets"]:
                    if "dependency" in _socket:
                        if _socket["dependency"] not in _items:
                            continue
                    if _socket["source"] == "input" and _socket["name"] not in _items[_socket["id"]].inputs:
                        _items[_socket["id"]].node_tree.inputs.new(_socket["type"], _socket["name"])
                    elif _socket["source"] == "output" and _socket["name"] not in _items[_socket["id"]].outputs:
                        _items[_socket["id"]].node_tree.outputs.new(_socket["type"], _socket["name"])

                # Create output sockets for enabled outputs that are not part of the shader
                for _output in _ordered_outputs:
                    if _output not in _shader_outputs:
                        continue
                    if _output not in _sbs_group.outputs and _shader_outputs[_output]["shader_enabled"]:
                        _sbs_group.node_tree.outputs.new("NodeSocketColor", _output)

                # Remove unused Nodes
                for _node in _shader_graph["nodes"]:
                    if "dependency" in _node:
                        for _value in _node["dependency"]:
                            if _value not in _items:
                                if _node["path"] == "root":
                                    _mat_nodes.remove(_items[_node["id"]])
                                else:
                                    _node_path = _node["path"].replace("root/", "")
                                    _items[_node_path].node_tree.nodes.remove(_items[_node["id"]])
                                del _items[_node["id"]]
                                break
                    if _node["type"] == "NodeFrame":
                        for _key in _node["children"]:
                            if _key in _items:
                                _items[_key].parent = _items[_node["id"]]
                        _items[_node["id"]].update()

                # Initialize shader properties
                for _property in _shader_graph["properties"]:
                    if _property["id"] not in _items:
                        continue
                    if "dependency" in _property:
                        for _value in _property["dependency"]:
                            if _value not in _items:
                                continue

                    if _property["type"] == "string":
                        setattr(_items[_property["id"]], _property["name"], _property["value"])
                    elif _property["type"] == "float":
                        setattr(_items[_property["id"]], _property["name"], _property["value"])
                    elif _property["type"] == "tiling":
                        if "input" in _property:
                            _value = selected_graph.tiling.get()
                            setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "physical_size":
                        if "input" in _property:
                            _value = selected_graph.physical_size.get()
                            _value = SUBSTANCE_Utils.get_physical_size(_value, context)
                            _value = [1/_value[0], 1/_value[1], 1/_value[0]]
                            setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "emissive_intensity":
                        _value = getattr(_shader_parms_class, _property["type"])
                        setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "ao_mix":
                        if "input" in _property:
                            _value = getattr(_shader_parms_class, _property["type"])
                            setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "disp_midlevel":
                        if "input" in _property:
                            _value = getattr(_shader_parms_class, _property["type"])
                            setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "disp_scale":
                        if "input" in _property:
                            _value = getattr(_shader_parms_class, _property["type"])
                            setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "disp_physical_scale":
                        if "input" in _property:
                            _value = selected_graph.physical_size.get()[2]
                            setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "projection_blend":
                        _value = getattr(_shader_parms_class, _property["type"])
                        setattr(_items[_property["id"]], _property["name"], _value)
                    else:
                        setattr(_items[_property["id"]], _property["name"], _property["value"])

                # Initialize links
                for _link in _shader_graph["links"]:
                    if (_link["from"] in _items and
                            _link["to"] in _items and
                            _link["output"] in _items[_link["from"]].outputs and
                            _link["input"] in _items[_link["to"]].inputs):
                        if _link["path"] == "root":
                            _material.node_tree.links.new(
                                _items[_link["from"]].outputs[_link["output"]],
                                _items[_link["to"]].inputs[_link["input"]])
                        else:
                            _items[_link["path"].replace("root/", "")].node_tree.links.new(
                                _items[_link["from"]].outputs[_link["output"]],
                                _items[_link["to"]].inputs[_link["input"]])

                selected_graph.material.shader = _selected_shader_preset.name
                _material.use_fake_user = True

                # Time
                _time_end = time.time()
                _load_time = round(_time_end - _time_start, 3)
                SUBSTANCE_Utils.log_data(
                    "INFO",
                    "Material [{}] Created [{}]".format(selected_graph.material.name, _load_time),
                    display=True)
            else:
                # Time
                _time_start = time.time()

                for _key in outputs:
                    _filepath = outputs[_key]["path"]
                    _img_name = "{}_{}".format(selected_graph.material.name, _output)
                    SUBSTANCE_MaterialManager.get_image(_img_name, _filepath)

                _sbs_group = _material.node_tree.nodes["{}_sbsar".format(selected_graph.material.name)]
                _sbs_group_nodes = _sbs_group.node_tree.nodes
                _mat_nodes = _material.node_tree.nodes

                # Remove disabled outputs image
                for _output in _sbs_group.node_tree.outputs:
                    if not _shader_outputs[_output.name]["shader_enabled"]:
                        _sbs_group.node_tree.outputs.remove(_output)

                # Remove image nodes not used
                for _node in _sbs_group_nodes:
                    if type(_node) != bpy.types.ShaderNodeTexImage and type(_node) != bpy.types.ShaderNodeNormalMap:
                        continue

                    _output = _node.name.replace("Tx ", "").replace("Normal ", "")
                    if not _shader_outputs[_output]["shader_enabled"]:
                        _sbs_group_nodes.remove(_node)

                # Get all graph items
                _new_nodes = []
                _items = {}
                for _node in _shader_graph["nodes"]:
                    _name = _node["name"].replace("$matname", selected_graph.material.name)
                    if _node["path"] == "root":
                        _nodes = _mat_nodes
                    else:
                        _nodes = _items[_node["path"].replace("root/", "")].node_tree.nodes

                    if _name in _nodes:
                        _items[_node["id"]] = _nodes[_name]
                    else:
                        _new_nodes.append(_node["id"])
                        _items[_node["id"]] = _nodes.new(_node["type"])
                        _items[_node["id"]].name = _name
                        if _node["type"] == "NodeFrame":
                            _items[_node["id"]].label = _node["label"]
                            continue

                        _items[_node["id"]].location = (_node["location"][0], _node["location"][1])
                        if _node["type"] == "ShaderNodeGroup":
                            _node_tree = bpy.data.node_groups.new(
                                type='ShaderNodeTree',
                                name=selected_graph.material.name)
                            _items[_node["id"]].node_tree = _node_tree

                # Initialize Enabled outputs
                _location = [-600, 0]
                for _output in _ordered_outputs:
                    if _output not in _shader_outputs:
                        continue

                    _filepath = selected_graph.outputs[_output].filepath
                    _filename = selected_graph.outputs[_output].filename
                    if _output in outputs:
                        _filepath = outputs[_output]["path"]
                        _filename = bpy.path.basename(outputs[_output]["path"])
                        selected_graph.outputs[_output].filepath = _filepath
                        selected_graph.outputs[_output].filename = _filename

                    if _filepath != "" and _shader_outputs[_output]["shader_enabled"]:
                        _name = "Tx {}".format(_output)
                        if _name in _sbs_group.node_tree.nodes:
                            _items["tx_{}".format(_output)] = _sbs_group.node_tree.nodes[_name]
                        else:
                            _new_nodes.append("tx_{}".format(_output))
                            _items["tx_{}".format(_output)] = _sbs_group.node_tree.nodes.new("ShaderNodeTexImage")
                            _items["tx_{}".format(_output)].name = "Tx {}".format(_output)

                            if _output in _shader_graph["outputs"] and "normal" in _shader_graph["outputs"][_output]:
                                _items["normal_{}".format(_output)] = _sbs_group.node_tree.nodes.new(
                                    "ShaderNodeNormalMap")
                                _items["normal_{}".format(_output)].name = "Normal {}".format(_output)
                                _items["normal_{}".format(_output)].location = (_location[0] + 300, _location[1])

                            # Add common properties to outputs that are not part of the shader
                            if _output not in _shader_graph["outputs"]:
                                for _property in _shader_graph["properties"]:
                                    if _property["id"] == "tx_":
                                        _new_propery = deepcopy(_property)
                                        _new_propery["id"] = "tx_{}".format(_output)
                                        _shader_graph["properties"].append(_new_propery)

                        _items["tx_{}".format(_output)].location = (_location[0], _location[1])

                        _img_name = "{}_{}".format(selected_graph.material.name, _output)
                        _img = SUBSTANCE_MaterialManager.get_image(_img_name, _filepath)
                        _img.colorspace_settings.name = _shader_outputs[_output]["shader_colorspace"]
                        _items["tx_{}".format(_output)].image = _img

                        _location[1] -= 300

                # Remove unused Nodes
                for _node in _shader_graph["nodes"]:
                    if "dependency" in _node:
                        for _value in _node["dependency"]:
                            if _value not in _items:
                                if _node["path"] == "root":
                                    _mat_nodes.remove(_items[_node["id"]])
                                else:
                                    _items[_node["path"].replace("root/", "")].node_tree.nodes.remove(
                                        _items[_node["id"]])
                                del _items[_node["id"]]
                                break
                    if _node["type"] == "NodeFrame":
                        for _key in _node["children"]:
                            if _key in _items:
                                _items[_key].parent = _items[_node["id"]]
                        _items[_node["id"]].update()

                # Initialize shader properties
                for _property in _shader_graph["properties"]:
                    if _property["id"] not in _items:
                        continue
                    if _property["id"] not in _new_nodes:
                        continue
                    if "dependency" in _node:
                        for _value in _node["dependency"]:
                            if _value not in _items:
                                continue

                    if _property["type"] == "string":
                        setattr(_items[_property["id"]], _property["name"], _property["value"])
                    elif _property["type"] == "float":
                        setattr(_items[_property["id"]], _property["name"], _property["value"])
                    elif _property["type"] == "tiling":
                        if "input" in _property:
                            _value = selected_graph.tiling.get()
                            setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "physical_size":
                        if "input" in _property:
                            _value = selected_graph.physical_size.get()
                            _value = SUBSTANCE_Utils.get_physical_size(_value, context)
                            _value = [1/_value[0], 1/_value[1], 1/_value[0]]
                            setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "emissive_intensity":
                        if "input" in _property:
                            _value = getattr(_shader_parms_class, _property["type"])
                            setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "ao_mix":
                        if "input" in _property:
                            _value = getattr(_shader_parms_class, _property["type"])
                            setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "disp_midlevel":
                        if "input" in _property:
                            _value = getattr(_shader_parms_class, _property["type"])
                            setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "disp_scale":
                        if "input" in _property:
                            _value = getattr(_shader_parms_class, _property["type"])
                            setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "disp_physical_scale":
                        if "input" in _property:
                            _value = selected_graph.physical_size.get()[2]
                            setattr(_items[_property["id"]].inputs[_property["input"]], _property["name"], _value)
                    elif _property["type"] == "projection_blend":
                        _value = getattr(_shader_parms_class, _property["type"])
                        setattr(_items[_property["id"]], _property["name"], _value)
                    else:
                        setattr(_items[_property["id"]], _property["name"], _property["value"])

                # Initialize shader sockets
                for _socket in _shader_graph["sockets"]:
                    if "dependency" in _socket:
                        if _socket["dependency"] not in _items:
                            continue
                    if _socket["source"] == "input" and _socket["name"] not in _items[_socket["id"]].inputs:
                        _items[_socket["id"]].node_tree.inputs.new(_socket["type"], _socket["name"])
                    elif _socket["source"] == "output" and _socket["name"] not in _items[_socket["id"]].outputs:
                        _items[_socket["id"]].node_tree.outputs.new(_socket["type"], _socket["name"])

                # Create output sockets for enabled outputs that are not part of the shader
                _dyna_links = []
                for _output in _ordered_outputs:
                    if _output not in _shader_outputs:
                        continue
                    if _output not in _sbs_group.outputs and _shader_outputs[_output]["shader_enabled"]:
                        _sbs_group.node_tree.outputs.new("NodeSocketColor", _output)
                        _dyna_links.append({
                            "from": "NODE_GROUP_IN",
                            "to": "tx_{}".format(_output),
                            "output": "UV",
                            "input": "Vector",
                            "path": "root/SBSAR"
                        })
                        _dyna_links.append({
                            "from": "tx_{}".format(_output),
                            "to": "NODE_GROUP_OUT",
                            "output": "Color",
                            "input": _output,
                            "path": "root/SBSAR"
                        })

                # Sort sockets
                _n = len(_sbs_group.node_tree.outputs)
                for _idx in range(_n):
                    _sorted = True
                    for _jdx in range(_n - _idx - 1):
                        _a_key = _sbs_group.node_tree.outputs[_jdx].name
                        _b_key = _sbs_group.node_tree.outputs[_jdx + 1].name
                        _a_weight = _ordered_outputs[_a_key]
                        _b_weight = _ordered_outputs[_b_key]
                        if _a_weight > _b_weight:
                            _sbs_group.node_tree.outputs.move(_jdx, _jdx + 1)
                            _sorted = False
                    if _sorted:
                        break

                # Initialize links
                for _link in _shader_graph["links"]:
                    if (_link["from"] in _items and
                            _link["to"] in _items and
                            _link["output"] in _items[_link["from"]].outputs and
                            _link["input"] in _items[_link["to"]].inputs):
                        if _link["path"] == "root":
                            if not _items[_link["to"]].inputs[_link["input"]].is_linked or "force" in _link:
                                _material.node_tree.links.new(
                                    _items[_link["from"]].outputs[_link["output"]],
                                    _items[_link["to"]].inputs[_link["input"]])
                        else:
                            if not _items[_link["to"]].inputs[_link["input"]].is_linked or "force" in _link:
                                _items[_link["path"].replace("root/", "")].node_tree.links.new(
                                    _items[_link["from"]].outputs[_link["output"]],
                                    _items[_link["to"]].inputs[_link["input"]])

                for _link in _dyna_links:
                    if (_link["from"] in _items and
                            _link["to"] in _items and
                            _link["output"] in _items[_link["from"]].outputs and
                            _link["input"] in _items[_link["to"]].inputs):
                        if _link["path"] == "root":
                            if not _items[_link["to"]].inputs[_link["input"]].is_linked or "force" in _link:
                                _material.node_tree.links.new(
                                    _items[_link["from"]].outputs[_link["output"]],
                                    _items[_link["to"]].inputs[_link["input"]])
                        else:
                            if not _items[_link["to"]].inputs[_link["input"]].is_linked or "force" in _link:
                                _items[_link["path"].replace("root/", "")].node_tree.links.new(
                                    _items[_link["from"]].outputs[_link["output"]],
                                    _items[_link["to"]].inputs[_link["input"]])

                # Hack to autoupdate images in cycles
                if _addons_prefs.cycles_autoupdate_enabled:
                    for _key in _items:
                        if not hasattr(_items[_key], "image"):
                            continue

                        _img = _items[_key].image
                        _items[_key].image = None
                        SUBSTANCE_Threads.timer_thread_run(
                            RENDER_IMG_UPDATE_DELAY_S,
                            SUBSTANCE_MaterialManager._reset_image,
                            (_items[_key], _img)
                        )

                # Time
                _time_end = time.time()
                _load_time = round(_time_end - _time_start, 3)
                SUBSTANCE_Utils.log_data(
                    "INFO",
                    "Material [{}] Updated [{}]".format(selected_graph.material.name, _load_time),
                    display=True)
            SUBSTANCE_Threads.cursor_pop()
        except Exception:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "An error ocurred while setting the material [{}]".format(selected_graph.material.name),
                display=True)
            SUBSTANCE_Threads.cursor_pop()
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Susbtance material creation error")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())

    @staticmethod
    def refresh_material(material):
        pass
