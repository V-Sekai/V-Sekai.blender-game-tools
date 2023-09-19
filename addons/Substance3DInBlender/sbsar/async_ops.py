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

# file: sbsar/async_ops.py
# brief: Asynchronous substance operations
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy
import os
import traceback
import time
import json


from ..utils import SUBSTANCE_Utils
from ..thread_ops import SUBSTANCE_Threads
from ..common import (
    Code_Response,
    Code_ParmIdentifier,
    Code_OutputSizeSuffix,
    Code_SbsarLoadSuffix,
    RENDER_KEY,
    CLASS_GRAPH_PARMS,
    CLASS_GRAPH_OUTPUTS
)


# Async function to get sbsar information
def _initialize_sbsar_data(
        context,
        sbsar_id,
        unique_name,
        filename,
        filepath,
        default_normal_format,
        default_outputsize,
        shader_outputs):
    # Callbacks
    def _callback_get_parms():
        for _item in context.scene.loaded_sbsars:
            if _item.id == sbsar_id:
                _item.suffix = Code_SbsarLoadSuffix.get_parms.value[0]
                _item.icon = Code_SbsarLoadSuffix.get_parms.value[1]
                break

    def _callback_get_outputs():
        for _item in context.scene.loaded_sbsars:
            if _item.id == sbsar_id:
                _item.suffix = Code_SbsarLoadSuffix.get_outputs.value[0]
                _item.icon = Code_SbsarLoadSuffix.get_outputs.value[1]
                break

    def _callback_get_graphs():
        for _item in context.scene.loaded_sbsars:
            if _item.id == sbsar_id:
                _item.suffix = Code_SbsarLoadSuffix.get_graphs.value[0]
                _item.icon = Code_SbsarLoadSuffix.get_graphs.value[1]
                break

    def _callback_get_embedded_presets():
        for _item in context.scene.loaded_sbsars:
            if _item.id == sbsar_id:
                _item.suffix = Code_SbsarLoadSuffix.get_embedded_presets.value[0]
                _item.icon = Code_SbsarLoadSuffix.get_embedded_presets.value[1]
                break

    def _callback_get_presets():
        for _item in context.scene.loaded_sbsars:
            if _item.id == sbsar_id:
                _item.suffix = Code_SbsarLoadSuffix.get_default_presets.value[0]
                _item.icon = Code_SbsarLoadSuffix.get_default_presets.value[1]
                break

    def _callback_sbsar_create():
        for _item in context.scene.loaded_sbsars:
            if _item.id == sbsar_id:
                _item.suffix = Code_SbsarLoadSuffix.create_sbsar.value[0]
                _item.icon = Code_SbsarLoadSuffix.create_sbsar.value[1]
                break

    def _callback_sbsar_init_presets():
        for _item in context.scene.loaded_sbsars:
            if _item.id == sbsar_id:
                _item.suffix = Code_SbsarLoadSuffix.init_preset.value[0]
                _item.icon = Code_SbsarLoadSuffix.init_preset.value[1]
                break

    def _callback_sbsar_init_outputs():
        for _item in context.scene.loaded_sbsars:
            if _item.id == sbsar_id:
                _item.suffix = Code_SbsarLoadSuffix.init_outputs.value[0]
                _item.icon = Code_SbsarLoadSuffix.init_outputs.value[1]
                break

    def _callback_sbsar_parm_create():
        for _item in context.scene.loaded_sbsars:
            if _item.id == sbsar_id:
                _item.suffix = Code_SbsarLoadSuffix.crate_parms.value[0]
                _item.icon = Code_SbsarLoadSuffix.crate_parms.value[1]
                break

    def _callback_error():
        for _item in context.scene.loaded_sbsars:
            if _item.id == sbsar_id:
                _item.suffix = Code_SbsarLoadSuffix.error.value[0]
                _item.icon = Code_SbsarLoadSuffix.error.value[1]
                SUBSTANCE_Utils.log_data(
                    "ERROR",
                    "An error ocurred while loading the Substance [{}]".format(_item.name),
                    display=True)
                break

    def _callback_success():
        try:
            _result = SUBSTANCE_Api.sbsar_register(sbsar_id)
            if _result[0] != Code_Response.success:
                SUBSTANCE_Utils.log_data(
                    "ERROR",
                    "[{}] Error while registering the Substance with ID [{}]".format(_result[0], sbsar_id))
                _callback_error()
                return
            _sbsar = _result[1]
            for _item in context.scene.loaded_sbsars:
                if _item.id == sbsar_id:
                    _item.set_sbsar(_sbsar)
                    _item.suffix = Code_SbsarLoadSuffix.success.value[0]
                    _item.icon = Code_SbsarLoadSuffix.success.value[1]
                    SUBSTANCE_Utils.log_data(
                        "INFO",
                        "Substance [{}] was loaded correctly".format(_item.name),
                        display=True)
                    break
        except Exception:
            _callback_error()
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Susbtance register error:")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())

    try:
        from ..api import SUBSTANCE_Api
        # Time
        _time_start = time.time()

        # Substance Info calls
        SUBSTANCE_Threads.main_thread_run(_callback_get_parms)
        _result = SUBSTANCE_Api.sbsar_get_parms(sbsar_id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while getting the *.sbsar file parameters".format(_result[0]))
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            return
        _sbsar_parms = _result[1]

        SUBSTANCE_Threads.main_thread_run(_callback_get_outputs)
        _result = SUBSTANCE_Api.sbsar_get_outputs(sbsar_id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while getting the *.sbsar outputs".format(_result[0]))
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            return
        _sbsar_outputs = _result[1]

        SUBSTANCE_Threads.main_thread_run(_callback_get_graphs)
        _result = SUBSTANCE_Api.sbsar_get_graphs_info(sbsar_id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while getting the *.sbsar graphs".format(_result[0]))
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            return
        _sbsar_graphs_info = _result[1]

        SUBSTANCE_Threads.main_thread_run(_callback_get_embedded_presets)
        _result = SUBSTANCE_Api.sbsar_get_embedded_presets(sbsar_id, _sbsar_graphs_info)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while getting the *.sbsar embedded presets".format(_result[0]))
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            return
        _sbsar_embedded_presets = _result[1]

        SUBSTANCE_Threads.main_thread_run(_callback_get_presets)
        _result = SUBSTANCE_Api.sbsar_get_presets(sbsar_id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while getting the *.sbsar default preset".format(_result[0]))
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            return
        _sbsar_default_presets = _result[1]

        SUBSTANCE_Threads.main_thread_run(_callback_sbsar_create)
        _sbsar_json = SUBSTANCE_Utils.sbsar_to_json(
            sbsar_id,
            unique_name,
            filename,
            filepath,
            _sbsar_graphs_info,
            _sbsar_parms,
            _sbsar_outputs,
            _sbsar_embedded_presets,
            _sbsar_default_presets,
            default_normal_format,
            default_outputsize,
            shader_outputs
        )

        _result = SUBSTANCE_Api.sbsar_create(_sbsar_json)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while creating the substance".format(_result[0]))
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            return
        _sbsar = _result[1]

        SUBSTANCE_Threads.main_thread_run(_callback_sbsar_init_presets)
        _result = SUBSTANCE_Api.sbsar_initialize_presets(_sbsar, default_normal_format, default_outputsize)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while initializing the substance presets".format(_result[0]))
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            return
        _sbsar = _result[1]

        SUBSTANCE_Threads.main_thread_run(_callback_sbsar_init_outputs)
        _result = SUBSTANCE_Api.sbsar_initialize_outputs(context, _sbsar, shader_outputs)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while initializing the substance outputs".format(_result[0]))
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            return

        SUBSTANCE_Threads.main_thread_run(_callback_sbsar_parm_create)

        SUBSTANCE_Api.sbsar_add_key(_sbsar)

        _render_id = RENDER_KEY.format(_sbsar.id, _sbsar.graphs[0].index)
        SUBSTANCE_Api.sbsar_render(_render_id, _sbsar.id, 0)

        # Time
        _time_end = time.time()
        _load_time = round(_time_end - _time_start, 3)
        SUBSTANCE_Utils.log_data(
            "INFO",
            "Substance [{}] was loaded correctly\n -ID: {}\n -FILE: {}\n -Loading time: {} seconds\n".format(
                _sbsar.name,
                _sbsar.id,
                _sbsar.filepath,
                _load_time))
        SUBSTANCE_Threads.main_thread_run(_callback_success)
    except Exception:
        SUBSTANCE_Utils.log_data("ERROR", "Unknown Error while getting the *.sbsar outputs")
        SUBSTANCE_Utils.log_traceback(traceback.format_exc())
        SUBSTANCE_Threads.main_thread_run(_callback_error)


def _set_parm_visibility(sbsar_id, graph_idx, graph_id, sbsar_parms):
    try:
        _new_parms = {}
        for _item in sbsar_parms:
            if str(_item["graphID"]) == str(graph_id):
                _new_parms[_item["identifier"]] = _item["visibleIf"]

        def _callback_visibility():
            _selected_sbsar = None
            for _item in bpy.context.scene.loaded_sbsars:
                if _item.id == sbsar_id:
                    _selected_sbsar = _item
                    break

            if _selected_sbsar is None:
                return

            _graph = _selected_sbsar.graphs[int(graph_idx)]
            for _key, _parm in _graph.parms.items():
                if _parm.name in _new_parms:
                    _parm.visible = _new_parms[_parm.name]

        SUBSTANCE_Threads.main_thread_run(_callback_visibility)

    except Exception:
        SUBSTANCE_Utils.log_data("ERROR", "Exception - Unknown Error while setting parameter visibility:")
        SUBSTANCE_Utils.log_traceback(traceback.format_exc())


def _reload_sbsar_data(scene, sbsar, sbsar_obj):
    def _callback_reload():
        sbsar.suffix = Code_SbsarLoadSuffix.get_parms.value[0]
        sbsar.icon = Code_SbsarLoadSuffix.get_parms.value[1]

    def _callback_error():
        sbsar.suffix = Code_SbsarLoadSuffix.error.value[0]
        sbsar.icon = Code_SbsarLoadSuffix.error.value[1]
        SUBSTANCE_Utils.log_data(
            "ERROR",
            "An error ocurred while reloading the substance [{}]".format(sbsar.name),
            display=True)

    def _callback_success():
        sbsar.suffix = Code_SbsarLoadSuffix.success.value[0]
        sbsar.icon = Code_SbsarLoadSuffix.success.value[1]
        SUBSTANCE_Utils.log_data(
            "INFO",
            "Substance [{}] was reloaded correctly".format(sbsar.name),
            display=True)

    try:
        from ..api import SUBSTANCE_Api
        SUBSTANCE_Threads.main_thread_run(_callback_reload)

        # Check if sbsar file exists
        _original_filepath = bpy.path.abspath(sbsar.filepath)
        _original_filepath = os.path.abspath(_original_filepath)
        _original_filepath = _original_filepath.replace("\\", "/")
        if not os.path.exists(_original_filepath):
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "Substance file [{}] doesn't exist".format(sbsar.filepath))
            return

        # Load the sbsar to the SRE
        _result = SUBSTANCE_Api.sbsar_load(_original_filepath)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "Substance file [{}] located at [{}] could not be loaded".format(sbsar.filename, sbsar.filepath))
            return
        _sbsar_id = _result[1]

        _result = SUBSTANCE_Api.sbsar_get_graphs_info(_sbsar_id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while getting the *.sbsar graphs".format(_result[0]))
            return
        _sbsar_graphs_info = _result[1]

        # Set the new sbsar ID
        _old_sbsar_id = sbsar.id
        sbsar.id = _sbsar_id
        sbsar_obj["id"] = _sbsar_id
        _multi_graph = len(sbsar_obj["graphs"]) > 1
        for _idx, _graph in enumerate(sbsar_obj["graphs"]):
            _graph["id"] = _sbsar_graphs_info[_idx]["id"]
            if _multi_graph:
                _class_name = "{}-{}".format(_sbsar_id, _graph["id"])
            else:
                _class_name = "{}".format(_sbsar_id)
            _graph["parms_class_name"] = CLASS_GRAPH_PARMS.format(_class_name)
            _graph["outputs_class_name"] = CLASS_GRAPH_OUTPUTS.format(_class_name)
            for _key, _output in _graph["parms"].items():
                _output["graphID"] = _sbsar_graphs_info[_idx]["id"]

            for _key, _parm in _graph["outputs"].items():
                _parm["graphID"] = _sbsar_graphs_info[_idx]["id"]

        for _key, _graph in sbsar.graphs.items():
            _graph.id = str(_sbsar_graphs_info[int(_graph.index)]["id"])
            _graph.parms_class_name = _graph.parms_class_name.replace(_old_sbsar_id, _sbsar_id)
            _graph.outputs_class_name = _graph.outputs_class_name.replace(_old_sbsar_id, _sbsar_id)

        # Load the sbsar to the Substance API sbsar manager
        _result = SUBSTANCE_Api.sbsar_create(sbsar_obj)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            SUBSTANCE_Utils.log_data("ERROR", "Error while loading the sbsar object")
            return
        _sbsar_obj = _result[1]

        SUBSTANCE_Api.sbsar_add_key(_sbsar_obj)
        _result = SUBSTANCE_Api.sbsar_register(_sbsar_id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            SUBSTANCE_Utils.log_data("ERROR", "Error while registering the sbsar classes")
            return
        _sbsar_obj = _result[1]

        for _graph in sbsar.graphs:
            _selected_preset = _graph.presets[int(_graph.presets_list)]

            _data = json.loads(_graph.outputs_data)
            _outputs_class = getattr(scene, _graph.outputs_class_name)
            _outputs_class.mat_callback["enabled"] = False
            _outputs_class.from_json(_data)
            _outputs_class.mat_callback["enabled"] = True

            _render_id = RENDER_KEY.format(sbsar.id, _graph.index)
            _result = SUBSTANCE_Api.sbsar_preset_changed(
                _render_id,
                sbsar.id,
                int(_graph.index),
                _graph.id,
                _selected_preset.value,
                render=False
            )
            if _result[0] != Code_Response.success:
                SUBSTANCE_Threads.main_thread_run(_callback_error)
                SUBSTANCE_Utils.log_data("ERROR", "Error while setting  the preset")
                continue

            _data = {
                "sbsar_id": sbsar.id,
                "parms": {}
            }
            for _item in _result[1]:
                if str(_item["graphID"]) != _graph.id:
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

            _parms_class = getattr(scene, _graph.parms_class_name)
            _parms_class.callback["enabled"] = False
            _parms_class.from_json(_data)
            _parms_class.callback["enabled"] = True

        # Reset images
        for _graph in sbsar.graphs:
            for _output in _graph.outputs:
                _img_name = "{}_{}".format(_graph.material.name, _output.name)
                if _img_name in bpy.data.images:
                    bpy.data.images[_img_name].filepath = _output.filepath
                    bpy.data.images[_img_name].reload()

        SUBSTANCE_Threads.main_thread_run(_callback_success)
        sbsar.load_success = True
    except Exception:
        SUBSTANCE_Threads.main_thread_run(_callback_error)
        SUBSTANCE_Utils.log_data("ERROR", "Exception - Unknown Error while setting parameter visibility")
        SUBSTANCE_Utils.log_traceback(traceback.format_exc())


def _duplicate_sbsar_data(context, sbsar_id, selected_sbsar, sbsar):

    def _callback_get_graphs():
        sbsar.suffix = Code_SbsarLoadSuffix.get_graphs.value[0]
        sbsar.icon = Code_SbsarLoadSuffix.get_graphs.value[1]

    def _callback_error():
        sbsar.suffix = Code_SbsarLoadSuffix.error.value[0]
        sbsar.icon = Code_SbsarLoadSuffix.error.value[1]
        SUBSTANCE_Utils.log_data(
            "ERROR",
            "Error ocurred while duplicating substance [{}]".format(sbsar.name),
            display=True)

    def _callback_success():
        sbsar.suffix = Code_SbsarLoadSuffix.success.value[0]
        sbsar.icon = Code_SbsarLoadSuffix.success.value[1]
        SUBSTANCE_Utils.log_data(
            "INFO",
            "Substance [{}] was duplicated correctly".format(sbsar.name),
            display=True)

    try:
        from ..api import SUBSTANCE_Api
        # Time
        _time_start = time.time()

        SUBSTANCE_Threads.main_thread_run(_callback_get_graphs)
        _result = SUBSTANCE_Api.sbsar_get_graphs_info(sbsar_id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while getting the *.sbsar graphs".format(_result[0]))
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            return
        _sbsar_graphs_info = _result[1]
        _sbsar_obj = SUBSTANCE_Api.sbsar_get(selected_sbsar.id)
        _sbsar_json = _sbsar_obj.to_json()

        _sbsar_json["id"] = sbsar_id
        _sbsar_json["name"] = sbsar.name
        _multi_graph = len(_sbsar_json["graphs"]) > 1
        for _idx, _graph in enumerate(_sbsar_json["graphs"]):
            _graph["id"] = _sbsar_graphs_info[_idx]["id"]
            if _multi_graph:
                _mat_name = "{}-{}".format(sbsar.name, _graph["name"]).replace(" ", "_")
                _class_name = "{}-{}".format(sbsar_id, _graph["id"])
            else:
                _mat_name = "{}".format(sbsar.name).replace(" ", "_")
                _class_name = "{}".format(sbsar_id)
            _graph["mat_name"] = _mat_name
            _graph["parms_class_name"] = CLASS_GRAPH_PARMS.format(_class_name)
            _graph["outputs_class_name"] = CLASS_GRAPH_OUTPUTS.format(_class_name)
            for _key, _output in _graph["parms"].items():
                _output["graphID"] = _sbsar_graphs_info[_idx]["id"]

            for _key, _parm in _graph["outputs"].items():
                _parm["graphID"] = _sbsar_graphs_info[_idx]["id"]

        _result = SUBSTANCE_Api.sbsar_create(_sbsar_json)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while creating the substance".format(_result[0]))
            return
        _sbsar = _result[1]

        SUBSTANCE_Api.sbsar_add_key(_sbsar)
        _result = SUBSTANCE_Api.sbsar_register(sbsar_id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Threads.main_thread_run(_callback_error)
            SUBSTANCE_Utils.log_data("ERROR", "Error while registering the sbsar classes")
            return
        _sbsar_obj = _result[1]

        # Set presets
        sbsar.set_sbsar(_sbsar_obj)
        for _idx, _graph in enumerate(sbsar.graphs):
            _original_graph = selected_sbsar.graphs[_idx]
            _graph.presets.clear()
            _graph.tiling.set_from_pg(_original_graph.tiling)
            _graph.shader_preset_callback = False
            _graph.shader_preset_list = _original_graph.shader_preset_list
            _graph.shader_preset_callback = True
            # Initialize outputs
            _orignal_outputs_class = getattr(context.scene, _original_graph.outputs_class_name)
            _outputs_class = getattr(context.scene, _graph.outputs_class_name)
            _orignal_data = _orignal_outputs_class.to_json()
            _outputs_class.mat_callback["enabled"] = False
            _outputs_class.from_json(_orignal_data)
            _outputs_class.mat_callback["enabled"] = True
            for _preset in _original_graph.presets:
                _new_preset = _graph.presets.add()
                _new_preset.set_from_pg(_preset)

            _graph.presets_list = _original_graph.presets_list

        # Time
        _time_end = time.time()
        _load_time = round(_time_end - _time_start, 3)
        SUBSTANCE_Utils.log_data(
            "INFO",
            "Substance [{}] was duplicated correctly\n -ID: {}\n -Loading time: {} seconds\n".format(
                sbsar.name,
                sbsar_id,
                _load_time))
        SUBSTANCE_Threads.main_thread_run(_callback_success)
    except Exception:
        SUBSTANCE_Threads.main_thread_run(_callback_error)
        SUBSTANCE_Utils.log_data("ERROR", "Exception - Unknown Error while setting parameter visibility")
        SUBSTANCE_Utils.log_traceback(traceback.format_exc())
