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

# file: props/sbsar.py
# brief: Substance Property Groups
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy

from ..api import SUBSTANCE_Api
from ..utils import SUBSTANCE_Utils
from .utils import get_shader_presets
from ..material.manager import SUBSTANCE_MaterialManager
from .common import SUBSTANCE_PG_GeneralItem
from ..common import (
    Code_Response,
    Code_SbsarLoadSuffix,
    Code_ParmIdentifier,
    Code_OutputSizeSuffix,
    ADDON_PACKAGE,
    SHADER_OUTPUTS_FILTER_DICT,
    RENDER_KEY
)


class SUBSTANCE_PG_SbsarOutput(SUBSTANCE_PG_GeneralItem):
    id: bpy.props.StringProperty(name="id")
    usage: bpy.props.StringProperty(name="usage")
    identifier: bpy.props.StringProperty(name="identifier")
    filepath: bpy.props.StringProperty(name="filepath", default="") # noqa
    filename: bpy.props.StringProperty(name="filename", default="") # noqa
    type: bpy.props.StringProperty(name="type", default="TX") # noqa

    def initialize(self, output):
        self.id = str(output.id)
        self.name = output.defaultChannelUse
        self.identifier = output.identifier
        self.label = output.label
        self.usage = output.defaultChannelUse


def on_linked_tiling_changed(self, context):
    if self.linked:
        self.y = self.x
        self.z = self.x
    else:
        on_tiling_changed(self, context)


def on_tiling_changed(self, context):
    if not self.callback:
        return
    _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
    if not _selected_sbsar.graphs_list.isdigit() or len(_selected_sbsar.graphs) < 1:
        return

    _selected_graph = _selected_sbsar.graphs[int(_selected_sbsar.graphs_list)]
    _addons_prefs, _selected_shader_preset = SUBSTANCE_Utils.get_selected_shader_preset(
        context,
        int(_selected_graph.shader_preset_list))
    _shader_filepath = SUBSTANCE_Utils.get_shader_file(_selected_shader_preset.filename)
    _material = SUBSTANCE_MaterialManager.get_existing_material(_selected_graph.material.name)
    _shader_graph = SUBSTANCE_Utils.get_json(_shader_filepath)

    if _material is None:
        return

    for _property in _shader_graph["properties"]:
        if _property["type"] == "tiling":
            _node_name = None
            for _node in _shader_graph["nodes"]:
                if _node["id"] == _property["id"]:
                    _node_name = _node["name"]
                    break
            if _node_name is None:
                continue
            if _node_name in _material.node_tree.nodes:
                _node = _material.node_tree.nodes[_node_name]
                _value = self.get()
                if "input" in _property:
                    setattr(_node.inputs[_property["input"]], _property["name"], _value)


class SUBSTANCE_PG_SbsarTiling(bpy.types.PropertyGroup):
    label: bpy.props.StringProperty(name="label", default="Tiling") # noqa
    x: bpy.props.FloatProperty(
        name="x",
        default=3.0,
        description="The X tiling to be used", # noqa
        update=on_linked_tiling_changed)
    y: bpy.props.FloatProperty(
        name="y",
        default=3.0,
        description="The Y tiling to be used", # noqa
        update=on_tiling_changed)
    z: bpy.props.FloatProperty(
        name="z",
        default=3.0,
        description="The Z tiling to be used", # noqa
        update=on_tiling_changed)
    linked: bpy.props.BoolProperty(
        name="linked",
        default=True,
        description='Lock/Unlock the tiling', # noqa
        update=on_linked_tiling_changed)
    callback: bpy.props.BoolProperty(default=True)

    def initialize(self, value):
        self.label = value.label
        self.x = value.x
        self.y = value.y
        self.y = value.z

    def set_from_pg(self, value):
        self.callback = False
        self.label = value.label
        self.x = value.x
        self.y = value.y
        self.y = value.z
        self.linked = value.linked
        self.callback = True

    def get(self):
        return [self.x, self.y, self.z]


class SUBSTANCE_PG_SbsarPhysicalSize(bpy.types.PropertyGroup):
    label: bpy.props.StringProperty(name="label", default="Physical Size") # noqa
    x: bpy.props.FloatProperty(
        name="x",
        default=1.0,
        description="The X physical size to be used") # noqa
    y: bpy.props.FloatProperty(
        name="y",
        default=1.0,
        description="The Y physical size to be used") # noqa
    z: bpy.props.FloatProperty(
        name="z",
        default=1.0,
        description="The Z physical size to be used") # noqa

    def initialize(self, value):
        self.x = value.x
        self.y = value.y
        self.y = value.z

    def set_from_pg(self, value):
        self.x = value.x
        self.y = value.y
        self.y = value.z

    def get(self):
        return [self.x, self.y, self.z]


class SUBSTANCE_PG_SbsarParm(SUBSTANCE_PG_GeneralItem):
    type: bpy.props.StringProperty(name="type")
    widget: bpy.props.StringProperty(name="widget")
    group: bpy.props.StringProperty(name="group")
    visible: bpy.props.BoolProperty(name="visible", default=True)

    def initialize(self, parm):
        self.name = parm.identifier
        self.label = parm.label
        self.type = parm.type
        self.widget = parm.guiWidget
        self.group = parm.guiGroup
        self.visible = parm.visibleIf

    def set_from_pg(self, value):
        self.visible = value.visible


class SUBSTANCE_PG_SbsarPreset(bpy.types.PropertyGroup):
    index: bpy.props.StringProperty(name="index", description="The index of the preset in the Substance 3D graph") # noqa
    name: bpy.props.StringProperty(name="name", description="The preset name of the Substance 3D graph") # noqa
    value: bpy.props.StringProperty(name="value", description="The preset value of the Substance 3D graph") # noqa
    icon: bpy.props.StringProperty(name="icon", description="The preset icon that shows if a preset is editable") # noqa
    embedded: bpy.props.BoolProperty(name="embedded", description="The preset origin") # noqa

    def initialize(self, index, preset):
        self.index = str(index)
        self.name = preset.label
        self.value = preset.value
        self.icon = preset.icon
        self.embedded = preset.embedded

    def set_from_pg(self, value):
        self.index = value.index
        self.name = value.name
        self.value = value.value
        self.icon = value.icon
        self.embedded = value.embedded


class SUBSTANCE_PG_SbsarParmGroup(bpy.types.PropertyGroup):
    index: bpy.props.IntProperty(name="index")
    name: bpy.props.StringProperty(name="name")
    collapsed: bpy.props.BoolProperty(default=False)

    def initialize(self, index, group):
        self.index = index
        self.name = group


class SUBSTANCE_PG_SbsarMaterial(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="name", description="The ID of the Substance 3D shader material") # noqa
    shader: bpy.props.StringProperty(name="shader", default="") # noqa


def on_parm_preset_updated(self, context):
    if not self.preset_callback:
        return
    _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
    _selected_preset_idx = int(self.presets_list)
    _selected_preset = self.presets[_selected_preset_idx]
    _render_id = RENDER_KEY.format(_selected_sbsar.id, self.index)
    _result = SUBSTANCE_Api.sbsar_preset_changed(
        _render_id,
        _selected_sbsar.id,
        int(self.index),
        self.id,
        _selected_preset.value)

    if _result[0] != Code_Response.success:
        return

    _data = {
        "sbsar_id": _selected_sbsar.id,
        "parms": {}
    }

    for _item in _result[1]:
        if str(_item["graphID"]) != self.id:
            continue

        if "value" not in _item:
            continue
        _data["parms"][_item["identifier"]] = _item["value"]

    if Code_ParmIdentifier.outputsize.value in _data["parms"]:
        _output_size = _data["parms"][Code_ParmIdentifier.outputsize.value]
        if _output_size[0] == _output_size[1]:
            _data["parms"][Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.linked.value] = True
        else:
            _data["parms"][Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.linked.value] = False

    _parms_class = getattr(context.scene, self.parms_class_name)
    _parms_class.callback["enabled"] = False
    _parms_class.from_json(_data)
    _parms_class.callback["enabled"] = True


def on_shader_preset_updated(self, context):
    if not self.shader_preset_callback:
        return

    _addons_prefs, _selected_shader_preset = SUBSTANCE_Utils.get_selected_shader_preset(
        context,
        int(self.shader_preset_list))
    _shader_class = getattr(context.scene, _selected_shader_preset.outputs_class_name)
    _output_class = getattr(context.scene, self.outputs_class_name)
    _shader_obj = _shader_class.get()

    _obj = {
        "sbsar_id": self.id,
        "outputs": {}
    }

    for _item in self.outputs:
        _obj["outputs"][_item.name] = {}
        if _item.usage in _shader_obj:
            _obj["outputs"][_item.name]["shader_enabled"] = _shader_obj[_item.usage]["enabled"]
            _obj["outputs"][_item.name]["shader_colorspace"] = _shader_obj[_item.usage]["colorspace"]
            _obj["outputs"][_item.name]["shader_format"] = _shader_obj[_item.usage]["format"]
            _obj["outputs"][_item.name]["shader_bitdepth"] = _shader_obj[_item.usage]["bitdepth"]
        else:
            _obj["outputs"][_item.name]["shader_enabled"] = False
            _obj["outputs"][_item.name]["shader_colorspace"] = _addons_prefs.output_default_colorspace
            _obj["outputs"][_item.name]["shader_format"] = _addons_prefs.output_default_format
            _obj["outputs"][_item.name]["shader_bitdepth"] = _addons_prefs.output_default_bitdepth

    _output_class.mat_callback["enabled"] = False
    _output_class.from_json(_obj)
    _output_class.mat_callback["enabled"] = True

    _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
    SUBSTANCE_MaterialManager.create_material(context, _selected_sbsar, self, {})


def get_preset_items(self, context):
    _presets = []
    for _idx, _preset in enumerate(self.presets):
        _item = (str(_idx), _preset.name, "{}:{}".format(_idx, _preset.name), _preset.icon, _idx)
        _presets.append(_item)
    return _presets


class SUBSTANCE_PG_SbsarGraph(bpy.types.PropertyGroup):
    index: bpy.props.StringProperty(
        name="index",
        description="The index of the graph in the Substance 3D material") # noqa
    id: bpy.props.StringProperty(
        name="id",
        description="The ID of the Substance 3D graph") # noqa
    name: bpy.props.StringProperty(
        name="name",
        description="The name of the Substance 3D graph") # noqa
    material: bpy.props.PointerProperty(type=SUBSTANCE_PG_SbsarMaterial)
    tiling: bpy.props.PointerProperty(
        name="tiling",
        description="The default tiling to be used in the shader network", # noqa
        type=SUBSTANCE_PG_SbsarTiling)
    physical_size: bpy.props.PointerProperty(
        name="physical_size",
        description="The physical size of the material", # noqa
        type=SUBSTANCE_PG_SbsarPhysicalSize)

    presets: bpy.props.CollectionProperty(type=SUBSTANCE_PG_SbsarPreset)
    presets_list: bpy.props.EnumProperty(
        name="presets",
        description="The available presets on ths SBSAR file", # noqa
        items=get_preset_items,
        update=on_parm_preset_updated)
    preset_callback: bpy.props.BoolProperty(name="preset_callback", default=True)

    shader_preset_list: bpy.props.EnumProperty(
        name="shader_preset_list",
        description="The available shader network presets", # noqa
        items=get_shader_presets,
        update=on_shader_preset_updated)
    shader_preset_callback: bpy.props.BoolProperty(name="shader_preset_callback", default=True)

    outputs_filter: bpy.props.EnumProperty(
        name="outputs_filter",
        description="Filter the outputs displayed", # noqa
        items=SHADER_OUTPUTS_FILTER_DICT)
    parm_groups: bpy.props.CollectionProperty(type=SUBSTANCE_PG_SbsarParmGroup)

    parms_class_name: bpy.props.StringProperty(name="parms_class_name")
    parms: bpy.props.CollectionProperty(type=SUBSTANCE_PG_SbsarParm)
    parms_data: bpy.props.StringProperty(name="parms_data")

    outputs_class_name: bpy.props.StringProperty(name="outputs_class_name")
    outputs: bpy.props.CollectionProperty(type=SUBSTANCE_PG_SbsarOutput)
    outputs_data: bpy.props.StringProperty(name="outputs_data")

    outputsize_exists: bpy.props.BoolProperty(name="embedded", description="The preset origin") # noqa
    randomseed_exists: bpy.props.BoolProperty(name="embedded", description="The preset origin") # noqa

    def initialize(self, index, graph):
        _addon_prefs = bpy.context.preferences.addons[ADDON_PACKAGE].preferences

        self.index = str(index)
        self.id = str(graph.id)
        self.name = graph.name
        self.material.name = graph.material.name
        self.parms_class_name = graph.parms_class_name
        self.outputs_class_name = graph.outputs_class_name
        self.shader_preset_callback = False
        self.shader_preset_list = _addon_prefs.shader_preset_list
        self.shader_preset_callback = True
        self.tiling.x = _addon_prefs.tiling.x
        self.tiling.y = _addon_prefs.tiling.y
        self.tiling.z = _addon_prefs.tiling.z
        self.tiling.linked = _addon_prefs.tiling.linked
        self.physical_size.x = graph.physicalSize[0]
        self.physical_size.y = graph.physicalSize[1]
        self.physical_size.z = graph.physicalSize[2]
        self.outputsize_exists = graph.outputsize_exists
        self.randomseed_exists = graph.randomseed_exists

        for _idx, _group in enumerate(graph.parms_groups):
            new_group = self.parm_groups.add()
            new_group.initialize(_idx, _group)

        for _idx, _preset in enumerate(graph.presets):
            _item = self.presets.add()
            _item.initialize(_idx, _preset)

        for _key, _parm in graph.parms.items():
            _item = self.parms.add()
            _item.initialize(_parm)

        for _key, _output in graph.outputs.items():
            _item = self.outputs.add()
            _item.initialize(_output)


def on_graph_changed(self, context):
    _graph_index = int(self.graphs_list)
    _selected_graph = self.graphs[_graph_index]

    if SUBSTANCE_MaterialManager.get_existing_material(_selected_graph.material.name) is None:
        _render_id = RENDER_KEY.format(self.id, _selected_graph.index)
        SUBSTANCE_Api.sbsar_render(_render_id, self.id, _graph_index)


def get_graph_items(self, context):
    _graphs = []
    for _idx, _graph in enumerate(self.graphs):
        _item = (_graph.index, _graph.name, "{}:{}:{}".format(_graph.index, _graph.name, _graph.id))
        _graphs.append(_item)
    if len(_graphs) == 0:
        return [("0", "NONE", "NONE:NONE:NONE")]
    return _graphs


def on_suffix_update(self, context):
    if self.suffix == Code_SbsarLoadSuffix.success.value[0]:
        self.loading = Code_SbsarLoadSuffix.success.value[1]
        self.load_success = True
    elif self.suffix == Code_SbsarLoadSuffix.error.value[0]:
        self.loading = Code_SbsarLoadSuffix.error.value[1]
        self.load_success = False


class SUBSTANCE_PG_Sbsar(bpy.types.PropertyGroup):
    id: bpy.props.StringProperty(name="id", description="The ID of the Substance 3D *.sbsar file") # noqa
    name: bpy.props.StringProperty(name="name", description="The name of the Substance *.sbsar file") # noqa
    filename: bpy.props.StringProperty(name='filename', description='The name of the *.sbsar file') # noqa
    filepath: bpy.props.StringProperty(name='filepath', description='The path to the *.sbsar file') # noqa
    object: bpy.props.StringProperty(name='object')

    graphs: bpy.props.CollectionProperty(type=SUBSTANCE_PG_SbsarGraph)
    graphs_list: bpy.props.EnumProperty(
        name="graphs",
        description="The available graphs of the Substance 3D material", # noqa
        items=get_graph_items,
        update=on_graph_changed)

    suffix: bpy.props.StringProperty(
        name="suffix",
        default=Code_SbsarLoadSuffix.loading.value[0],
        update=on_suffix_update)
    icon: bpy.props.StringProperty(
        name="icon",
        default=Code_SbsarLoadSuffix.loading.value[1],
        update=on_suffix_update)

    loading: bpy.props.StringProperty(name="loading", default="TEMP") # noqa
    load_success: bpy.props.BoolProperty(default=False)

    def initialize(self, _sbsar_id, name, filename, filepath):
        self.id = _sbsar_id
        self.name = name
        self.filename = filename
        self.filepath = filepath

    def set_sbsar(self, sbsar):
        for _idx, _graph in enumerate(sbsar.graphs):
            _new_graph = self.graphs.add()
            _new_graph.initialize(_idx, _graph)

    def reset_sbsar(self):
        self.graphs.clear()
