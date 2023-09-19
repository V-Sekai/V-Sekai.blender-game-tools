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

# file: api.py
# brief: Central API that connects the Remote engine operations with blender
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import os
import time
import traceback

from .toolkit.manager import SRE_ToolkitManager
from .presets.manager import SUBSTANCE_PresetManager
from .sbsar.manager import SUBSTANCE_SbsarManager
from .shader.manager import SUBSTANCE_ShaderManager
from .network.manager import SUBSTANCE_ServerManager
from .render.manager import SUBSTANCE_RenderManager
from .utils import SUBSTANCE_Utils
from .thread_ops import SUBSTANCE_Threads
from .sbsar.async_ops import _set_parm_visibility
from .common import (
    Code_Response,
    Code_OutParms,
    Code_ParmWidget,
    Code_RequestType,
    Code_RequestVerb,
    Code_ParmIdentifier,
    SRE_URI,
    SERVER_HOST,
    PRESET_DEFAULT,
    ADDON_PACKAGE,
    RENDER_KEY
)


class SUBSTANCE_Api():
    is_running = False
    toolkit_manager = SRE_ToolkitManager()
    server_manager = SUBSTANCE_ServerManager()
    sbsar_manager = SUBSTANCE_SbsarManager()
    shader_manager = SUBSTANCE_ShaderManager()
    presets_manager = SUBSTANCE_PresetManager()
    render_manager = SUBSTANCE_RenderManager()
    listeners = {
        "head": [],
        "get": [],
        "post": [],
        "patch": []
    }
    temp_tx_files = []
    temp_sbs_files = []
    last_selection = None

    # MAIN
    @classmethod
    def initialize(cls):
        # Time
        _time_start = time.time()
        SUBSTANCE_Utils.log_data("INFO", "Plugin initialization...")

        _result = cls.toolkit_start()
        if _result != Code_Response.success and _result != Code_Response.toolkit_already_started:
            SUBSTANCE_Utils.log_data("ERROR", "[{}] Toolkit failed to initialize...".format(_result), display=True)
            return (_result, None)
        elif _result == Code_Response.toolkit_already_started:
            SUBSTANCE_Utils.log_data("INFO", "[{}] Toolkit is already in use by another client...".format(_result))
        else:
            SUBSTANCE_Utils.log_data("INFO", "Toolkit Initialized...")

        _result = cls.toolkit_version_get()
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data("ERROR", "[{}] Failed to get Toolkit version...".format(_result), display=True)
            return (_result[0], None)
        SUBSTANCE_Utils.log_data("INFO", "Toolkit version [{}]...".format(_result[1]))

        _result = cls.server_manager.server_start()
        if _result != Code_Response.success and _result != Code_Response.server_already_running_error:
            SUBSTANCE_Utils.log_data("ERROR", "[{}] Server failed to initialize...".format(_result), display=True)
            return (_result, None)
        elif _result != Code_Response.server_already_running_error:
            SUBSTANCE_Utils.log_data("INFO", "[{}] Server already running...".format(_result))
        else:
            SUBSTANCE_Utils.log_data("INFO", "Server Initialized...")

        _result = cls.server_manager.server_port()
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data("ERROR", "[{}] Port Undefined".format(_result[0]), display=True)
            return _result
        SUBSTANCE_Utils.log_data("INFO", "Server Port [{}]".format(_result[1]))

        _result = cls.msg_system_start()
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data("ERROR", "[{}] System start failed".format(_result[0]), display=True)
            return _result
        cls.is_running = True

        '''
        _result_formats = cls.msg_system_formats()
        if _result_formats[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Message system formats failed, loading local formats instead".format(_result_formats[0]))
        SUBSTANCE_Utils.log_data("INFO","SRE formats loaded...")
        print(_result_formats)
        '''

        # Time
        _time_end = time.time()
        _load_time = round(_time_end - _time_start, 3)
        SUBSTANCE_Utils.log_data("INFO", "SRE Initialized sucessfully in [{}] seconds".format(_load_time), display=True)

        return _result

    @classmethod
    def shutdown(cls):
        if not cls.is_running:
            return Code_Response.success

        cls.is_running = False
        _result = cls.msg_system_end(request_type=Code_RequestType.r_async)
        if _result != Code_Response.success:
            SUBSTANCE_Utils.log_data("ERROR", "[{}] Message system end failed...".format(_result))
        else:
            SUBSTANCE_Utils.log_data("INFO", "Message system end success")
        _result = cls.server_manager.server_stop()
        if _result != Code_Response.success:
            SUBSTANCE_Utils.log_data("ERROR", "[{}] Server failed to shutdown...".format(_result))
        else:
            SUBSTANCE_Utils.log_data("INFO", "Server Terminated...")
        _result = cls.toolkit_stop()
        if (_result != Code_Response.success and
                _result != Code_Response.toolkit_in_use and
                _result != Code_Response.toolkit_not_running_error):
            SUBSTANCE_Utils.log_data("ERROR", "[{}] Toolkit failed to shutdown...".format(_result))
        elif _result == Code_Response.toolkit_in_use:
            SUBSTANCE_Utils.log_data("INFO", "[{}] Toolkit is still in use by another client...".format(_result))
        elif _result == Code_Response.toolkit_not_running_error:
            SUBSTANCE_Utils.log_data("INFO", "[{}] Toolkit no longer running...".format(_result))
        else:
            SUBSTANCE_Utils.log_data("INFO", "Toolkit Terminated...")
        return _result

    # LISTENERS
    @classmethod
    def listeners_add(cls, type, listener):
        cls.listeners[type].append(listener)
        return Code_Response.success

    @classmethod
    def listeners_remove(cls, type, listener):
        try:
            cls.listeners[type].remove(listener)
            return Code_Response.success
        except Exception:
            return Code_Response.api_listener_remove_error

    @classmethod
    def listeners_call(cls, type, data):
        for _listener in cls.listeners[type]:
            _listener.execute(data)

    # TOOLKIT
    @classmethod
    def toolkit_version_get(cls):
        if cls.toolkit_manager.is_installed():
            _result = cls.toolkit_manager.version_get()
            return _result
        else:
            return (Code_Response.toolkit_not_installed_error, None)

    @classmethod
    def toolkit_start(cls):
        if cls.toolkit_manager.is_installed():
            return cls.toolkit_manager.start()
        else:
            return Code_Response.toolkit_not_installed_error

    @classmethod
    def toolkit_stop(cls):
        if cls.toolkit_manager.is_installed():
            _result = cls.msg_system_active()
            if _result[0] != Code_Response.success:
                return _result
            if _result[1] > 1:
                return (Code_Response.toolkit_in_use, _result[1])
            return cls.toolkit_manager.stop()
        else:
            return Code_Response.toolkit_not_installed_error

    @classmethod
    def toolkit_install(cls, filepath):
        if cls.toolkit_manager.is_running():
            _result = cls.msg_system_active()
            if _result[0] != Code_Response.success:
                return _result
            if _result[1] > 1:
                return (Code_Response.toolkit_in_use, _result[1])

        _result = cls.toolkit_manager.install(filepath)
        if _result != Code_Response.success:
            return (_result, None)
        _result = cls.initialize()
        return _result

    @classmethod
    def toolkit_update(cls, filepath):
        if cls.toolkit_manager.is_running():
            _result = cls.msg_system_active()
            if _result[0] != Code_Response.success:
                return _result
            if _result[1] > 1:
                return (Code_Response.toolkit_in_use, _result[1])
            _result = cls.shutdown()
        _result = cls.toolkit_manager.update(filepath)
        if _result != Code_Response.success:
            return (_result, None)
        _result = cls.initialize()
        return _result

    @classmethod
    def toolkit_uninstall(cls):
        if cls.toolkit_manager.is_running():
            _result = cls.msg_system_active()
            if _result[0] != Code_Response.success:
                return _result
            if _result[1] > 1:
                return (Code_Response.toolkit_in_use, _result[1])
            _result = cls.shutdown()

        return (cls.toolkit_manager.uninstall(), None)

    # SBSAR
    @classmethod
    def sbsar_load(cls, filepath):
        _result = cls.msg_sbsar_add(filepath)
        _sbsar_id = _result[1]
        if _result[0] != Code_Response.success:
            return (_result[0], None)
        return (Code_Response.success, _sbsar_id)

    @classmethod
    def sbsar_duplicate(cls, id):
        _result = cls.msg_sbsar_duplicate(id)
        _sbsar_id = _result[1]
        if _result[0] != Code_Response.success:
            return (_result[0], None)
        return (Code_Response.success, _sbsar_id)

    @classmethod
    def sbsar_get_parms(cls, sbsar_id):
        _result = cls.msg_sbsar_get_parms(sbsar_id)
        _sbsar_parms = _result[1]
        if _result[0] != Code_Response.success:
            return (_result[0], None)
        return (Code_Response.success, _sbsar_parms)

    @classmethod
    def sbsar_get_outputs(cls, sbsar_id):
        _result = cls.msg_sbsar_get_outputs(sbsar_id)
        _sbsar_outputs = _result[1]
        if _result[0] != Code_Response.success:
            return (_result[0], None)
        return (Code_Response.success, _sbsar_outputs)

    @classmethod
    def sbsar_get_graphs_info(cls, sbsar_id):
        _result = cls.msg_sbsar_get_graphs_info(sbsar_id)
        _sbsar_graphs_info = _result[1]
        if _result[0] != Code_Response.success:
            return (_result[0], None)
        return (Code_Response.success, _sbsar_graphs_info)

    @classmethod
    def sbsar_get_embedded_presets(cls, sbsar_id, sbsar_graphs_info):
        _sbsar_embedded_presets = {}
        for _idx, _graph in enumerate(sbsar_graphs_info):
            _result = cls.msg_sbsar_get_embedded_presets(sbsar_id, _idx)
            if _result[0] != Code_Response.success:
                return (_result[0], None)
            _sbsar_embedded_presets[_graph["id"]] = _result[1]
        return (Code_Response.success, _sbsar_embedded_presets)

    @classmethod
    def sbsar_get_presets(cls, sbsar_id):
        _result = cls.msg_sbsar_get_presets(sbsar_id)
        _sbsar_preset = _result[1]
        if _result[0] != Code_Response.success:
            return (_result[0], None)
        return (Code_Response.success, _sbsar_preset)

    @classmethod
    def sbsar_create(cls, sbsar_json):
        try:
            _sbsar = cls.sbsar_manager.load_new(sbsar_json)
            return (Code_Response.success, _sbsar)
        except Exception:
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return (Code_Response.sbsar_create_error, None)

    @classmethod
    def sbsar_get(cls, sbsar_id):
        return cls.sbsar_manager.get(sbsar_id)

    @classmethod
    def sbsar_initialize_presets(cls, sbsar, default_normal_format, default_outputsize):
        try:
            for _graph in sbsar.graphs:
                _parm_output_size = _graph.get_outputsize()
                _parms_normal_format, _values_normal_format = _graph.get_normal_formats(default_normal_format)

                for _preset in _graph.presets:
                    # Sets the default resolution and normal format as defined in the addon preferences
                    _result = SUBSTANCE_Utils.init_preset(
                        _preset,
                        default_outputsize,
                        _parm_output_size,
                        _values_normal_format,
                        _parms_normal_format)
                    if _result[0] != Code_Response.success:
                        SUBSTANCE_Utils.log_data(
                            "ERROR",
                            "[{}] Error while updating in the sbsar [{}] the preset[{}] ".format(
                                _result,
                                sbsar.name,
                                _preset.label))
                        return (Code_Response.sbsar_update_presets_error, None)

                    _new_preset_value = _result[1]
                    _preset.value = _new_preset_value

                    # Loads the new default preset to the SRE
                    if _preset.label == PRESET_DEFAULT:
                        _result = cls.msg_sbsar_load_preset(
                            sbsar.id,
                            _graph.index,
                            _preset.value,
                            Code_RequestType.r_sync)
                        if _result[0] != Code_Response.success:
                            SUBSTANCE_Utils.log_data(
                                "ERROR",
                                "[{}] Error while initializing the substance [{}] with preset[{}] ".format(
                                    _result,
                                    sbsar.name,
                                    _preset.label))
                            return (Code_Response.sbsar_set_default_presets_error, None)

            return (Code_Response.success, sbsar)
        except Exception:
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return (Code_Response.sbsar_initialize_presets_error, None)

    @classmethod
    def sbsar_initialize_outputs(cls, context, sbsar, shader_outputs):
        try:
            for _graph in sbsar.graphs:
                for _key, _output in _graph.outputs.items():
                    if _output.defaultChannelUse in shader_outputs.shader_preset.outputs:
                        _format = getattr(shader_outputs, _output.defaultChannelUse + Code_OutParms.format.value)
                    else:
                        _addon_prefs = context.preferences.addons[ADDON_PACKAGE].preferences
                        _format = _addon_prefs.output_default_format

                    _result = cls.msg_sbsar_set_output(sbsar.id, _output.id, _format, Code_RequestType.r_sync)
                    if _result[0] != Code_Response.success:
                        SUBSTANCE_Utils.log_data(
                            "ERROR",
                            "[{}] Error while setting up the format for the output [{}] in the sbsar [{}]".format(
                                _result,
                                _output.label,
                                sbsar.name))
                        return (Code_Response.sbsar_update_output_error, None)

            return (Code_Response.success, None)
        except Exception:
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return (Code_Response.sbsar_initialize_outputs_error, None)

    @classmethod
    def sbsar_register(cls, sbsar_id):
        _result = cls.sbsar_manager.register_sbsar(sbsar_id)
        return _result

    @classmethod
    def sbsar_unregister(cls, sbsar_id):
        _result = cls.msg_sbsar_remove(sbsar_id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while removing the sbsar with ID [{}] from the SRE".format(_result,  sbsar_id))
        else:
            SUBSTANCE_Utils.log_data(
                "INFO",
                "[{}] Sbsar with ID [{}] was fully removed from the SRE".format(_result[0],  sbsar_id))

        _result = cls.sbsar_manager.remove_sbsar(sbsar_id)
        if _result != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while unregistering the sbsar with ID [{}]".format(_result,  sbsar_id))
        return _result

    @classmethod
    def sbsar_add_key(cls, sbsar):
        return cls.sbsar_manager.add_sbsar_to_dict(sbsar)

    # Rendering
    @classmethod
    def sbsar_is_rendering(cls, sbsar_id):
        if sbsar_id in cls.render_manager.render_current:
            return 2
        else:
            for _key in cls.render_manager.render_queue:
                if sbsar_id in _key:
                    return 1
        return 0

    @classmethod
    def sbsar_set_output(cls, sbsar_id, graph_idx, graph_id, output_id, value, request_type=Code_RequestType.r_async):
        _result = cls.msg_sbsar_set_output(sbsar_id, output_id, value, request_type=request_type)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while updating the output with the value [{}]".format(_result,  value))
            return Code_Response.success

    @classmethod
    def sbsar_parm_update(cls, context, sbsar_id, graph_idx, graph_id, parm, value, output_size, callback):
        _sync = False
        if (
            parm.guiWidget == Code_ParmWidget.combobox.value or
            parm.guiWidget == Code_ParmWidget.togglebutton.value or
            parm.guiWidget == Code_ParmWidget.image.value or
            parm.identifier == Code_ParmIdentifier.outputsize.value
        ):
            _sync = True

        _render_id = RENDER_KEY.format(sbsar_id, graph_idx)
        if _sync:
            return callback(context, _render_id, sbsar_id, graph_idx, graph_id, parm, value, output_size)
        else:
            cls.render_manager.parm_queue_add(
                context,
                _render_id,
                sbsar_id,
                graph_idx,
                graph_id,
                parm,
                value,
                output_size,
                callback
            )
            return Code_Response.parm_update_async

    @classmethod
    def sbsar_set_parm(
            cls,
            render_id,
            sbsar_id,
            graph_idx,
            graph_id,
            parm_id,
            value,
            output_size,
            request_type=Code_RequestType.r_sync):
        _result = cls.msg_sbsar_update_parm(sbsar_id, parm_id, value, request_type=request_type)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while updating the parameter with the value [{}]".format(_result,  value))
            return (_result[0], None)

        _result = cls.sbsar_get_presets(sbsar_id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while updating the custom preset".format(_result[0]))
            return (_result[0], None)
        _preset_value = _result[1][graph_idx]

        _result = cls.sbsar_get_parms(sbsar_id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while getting the *.sbsar file parameters".format(_result[0]))
            return (Code_Response.success, _preset_value)
        _sbsar_parms = _result[1]

        SUBSTANCE_Threads.alt_thread_run(
            _set_parm_visibility, (
                sbsar_id,
                graph_idx,
                graph_id,
                _sbsar_parms))

        cls.sbsar_render(render_id, sbsar_id, graph_idx, request_type)
        return (Code_Response.success, _preset_value)

    @classmethod
    def sbsar_render(cls, render_id, sbsar_id, graph_idx, request_type=Code_RequestType.r_sync):
        cls.render_manager.graph_render(
            render_id,
            sbsar_id,
            graph_idx,
            request_type,
            cls.msg_sbsar_render
        )

    @classmethod
    def sbsar_render_callback(cls, data):
        cls.render_manager.render_finish(data)

    # Presets
    @classmethod
    def sbsar_preset_changed(cls, render_id, sbsar_id, graph_idx, graph_id, preset_value, render=True):
        _result = cls.msg_sbsar_load_preset(sbsar_id, graph_idx, preset_value)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while initializing the substance with preset ".format(_result))
            return _result

        _result = cls.sbsar_get_parms(sbsar_id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while getting the *.sbsar file parameters".format(_result[0]))
            return _result
        _sbsar_parms = _result[1]

        SUBSTANCE_Threads.alt_thread_run(
            _set_parm_visibility, (
                sbsar_id,
                graph_idx,
                graph_id,
                _sbsar_parms))

        if render:
            cls.sbsar_render(render_id, sbsar_id, graph_idx)

        return _result

    @classmethod
    def sbsar_preset_get(cls, sbsar_id, graph_idx):
        _result = cls.sbsar_get_presets(sbsar_id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data("ERROR", "[{}] Error while getting the current preset".format(_result[0]))
            return (_result[0], None)
        _preset_value = _result[1][graph_idx]
        return (Code_Response.success, _preset_value)

    @classmethod
    def sbsar_preset_write(cls, filepath, preset_name, preset, graph_name):
        _result = cls.presets_manager.preset_write_file(filepath, preset_name, preset, graph_name)
        return _result

    @classmethod
    def sbsar_preset_read(cls, filepath):
        _result = cls.presets_manager.preset_read_file(filepath)
        return _result

    # MSG SYSTEM
    @classmethod
    def msg_system_active(cls, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.get,
                "{}/system/active".format(SRE_URI)
            )
            if _result[0] != Code_Response.success:
                return (_result[0], None)
            _result = SUBSTANCE_Utils.get_response_data(_result[1], "active")
            if _result[0] != Code_Response.success:
                return _result
            return (Code_Response.success, int(_result[1]))
        else:
            return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_system_formats(cls, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.get,
                "{}/system/imageformats".format(SRE_URI)
            )
            if _result[0] != Code_Response.success:
                return (_result[0], None)

            _result = SUBSTANCE_Utils.get_response_data(_result[1], "supportedformats")
            return _result
        else:
            return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_system_render(cls, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.get,
                "{}/system/processingunit".format(SRE_URI)
            )
            if _result[0] != Code_Response.success:
                return (_result[0], None)
            _result = SUBSTANCE_Utils.get_response_data(_result[1], "processingunit")
            return _result
        else:
            return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_system_start(cls, request_type=Code_RequestType.r_sync):
        if cls.toolkit_manager.is_running():
            _data = {"pid": os.getpid()}
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.patch,
                "{}/system/start".format(SRE_URI),
                data=_data
            )
            return _result
        else:
            return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_system_end(cls, request_type=Code_RequestType.r_sync):
        if cls.toolkit_manager.is_running():
            _data = {"pid": os.getpid()}
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.patch,
                "{}/system/end".format(SRE_URI),
                data=_data,
                ignore_connection_error=True
            )

            return _result
        else:
            return Code_Response.toolkit_not_running_error

    # MSG SBSAR
    @classmethod
    def msg_sbsar_add(cls, filepath, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _result = cls.server_manager.server_port()
            if _result[0] != Code_Response.success:
                return (_result[0], None)
            _server_uri = "http://{}:{}".format(SERVER_HOST, _result[1])
            _data = {
                "path": filepath,
                "renderCallback": _server_uri,
                "format": "tga"
            }
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.post,
                "{}/sbsar".format(SRE_URI),
                data=_data
            )
            if _result[0] != Code_Response.success:
                return (_result[0], None)
            _result = SUBSTANCE_Utils.get_response_data(_result[1], "id")
            return _result
        else:
            if cls.toolkit_manager.is_installed():
                return (Code_Response.toolkit_not_installed_error, None)
            else:
                return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_sbsar_remove(cls, id, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.delete,
                "{}/sbsar/{}".format(SRE_URI, id),
            )
            return _result
        else:
            if cls.toolkit_manager.is_installed():
                return (Code_Response.toolkit_not_installed_error, None)
            else:
                return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_sbsar_duplicate(cls, id, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.post,
                "{}/sbsar/{}/duplicate".format(SRE_URI, id)
            )
            if _result[0] != Code_Response.success:
                return (_result[0], None)
            _result = SUBSTANCE_Utils.get_response_data(_result[1], "id")
            return _result
        else:
            if cls.toolkit_manager.is_installed():
                return (Code_Response.toolkit_not_installed_error, None)
            else:
                return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_sbsar_get_parms(cls, id, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.get,
                "{}/sbsar/{}/parameters".format(SRE_URI, id)
            )
            if _result[0] != Code_Response.success:
                return (_result[0], None)
            _result = SUBSTANCE_Utils.get_response_data(_result[1], "parameters")
            return _result
        else:
            if cls.toolkit_manager.is_installed():
                return (Code_Response.toolkit_not_installed_error, None)
            else:
                return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_sbsar_update_parm(cls, id, parm_id, value, request_type=Code_RequestType.r_async):
        if cls.is_running:
            _data = {"value": value}

            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.patch,
                "{}/sbsar/{}/parameter/{}".format(SRE_URI, id, parm_id),
                data=_data
            )
            return _result
        else:
            if cls.toolkit_manager.is_installed():
                return (Code_Response.toolkit_not_installed_error, None)
            else:
                return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_sbsar_get_outputs(cls, id, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.get,
                "{}/sbsar/{}/outputs".format(SRE_URI, id)
            )
            if _result[0] != Code_Response.success:
                return (_result[0], None)
            _result = SUBSTANCE_Utils.get_response_data(_result[1], "outputs")
            return _result
        else:
            if cls.toolkit_manager.is_installed():
                return (Code_Response.toolkit_not_installed_error, None)
            else:
                return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_sbsar_set_output(cls, id, output_id, value, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _data = {"resultFormat": value}
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.patch,
                "{}/sbsar/{}/output/{}".format(SRE_URI, id, output_id),
                data=_data
            )
            return _result
        else:
            if cls.toolkit_manager.is_installed():
                return (Code_Response.toolkit_not_installed_error, None)
            else:
                return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_sbsar_get_graphs_info(cls, id, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.get,
                "{}/sbsar/{}/graphsinfo".format(SRE_URI, id)
            )
            if _result[0] != Code_Response.success:
                return (_result[0], None)
            _result = SUBSTANCE_Utils.get_response_data(_result[1], "graphsinfo")
            return _result
        else:
            if cls.toolkit_manager.is_installed():
                return (Code_Response.toolkit_not_installed_error, None)
            else:
                return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_sbsar_get_presets(cls, sbsar_id, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.get,
                "{}/sbsar/{}/presets".format(SRE_URI, sbsar_id)
            )
            if _result[0] != Code_Response.success:
                return (_result[0], None)
            _result = SUBSTANCE_Utils.get_response_data(_result[1], "presets")
            return _result
        else:
            if cls.toolkit_manager.is_installed():
                return (Code_Response.toolkit_not_installed_error, None)
            else:
                return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_sbsar_load_preset(cls, sbsar_id, graph_idx, preset, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _data = {
                "preset": preset
            }
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.patch,
                "{}/sbsar/{}/preset/{}".format(SRE_URI, sbsar_id, graph_idx),
                data=_data
            )
            return _result
        else:
            if cls.toolkit_manager.is_installed():
                return (Code_Response.toolkit_not_installed_error, None)
            else:
                return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_sbsar_get_embedded_presets(cls, sbsar_id, graph_idx, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.get,
                "{}/sbsar/{}/embeddedpresets/{}".format(SRE_URI, sbsar_id, graph_idx)
            )
            if _result[0] != Code_Response.success:
                return (_result[0], None)
            _result = SUBSTANCE_Utils.get_response_data(_result[1], "embeddedpresets")
            return _result
        else:
            if cls.toolkit_manager.is_installed():
                return (Code_Response.toolkit_not_installed_error, None)
            else:
                return (Code_Response.toolkit_not_running_error, None)

    @classmethod
    def msg_sbsar_render(cls, id, index, request_type=Code_RequestType.r_sync):
        if cls.is_running:
            _result = cls.server_manager.server_send_message(
                request_type,
                Code_RequestVerb.patch,
                "{}/sbsar/{}/render/{}".format(SRE_URI, id, index),
            )
            return _result
        else:
            if cls.toolkit_manager.is_installed():
                return (Code_Response.toolkit_not_installed_error, None)
            else:
                return (Code_Response.toolkit_not_running_error, None)

    # Shader Presets
    @classmethod
    def shader_presets_initialize(cls):
        _result = cls.shader_manager.init_presets()
        return _result

    @classmethod
    def shader_presets_remove(cls, shader_presets):
        _result = cls.shader_manager.remove_presets(shader_presets)
        return _result

    @classmethod
    def shader_presets_save(cls, shader_preset):
        _result = cls.shader_manager.save_presets(shader_preset)
        return _result
