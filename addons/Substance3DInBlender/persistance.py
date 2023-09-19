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

# file: persistance.py
# brief: Persistance handlers for blender
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2
import traceback
import bpy
import os
import shutil
import json
from bpy.app.handlers import persistent

from .sbsar.async_ops import _reload_sbsar_data
from .api import SUBSTANCE_Api
from .thread_ops import SUBSTANCE_Threads
from .utils import SUBSTANCE_Utils
from .material.manager import SUBSTANCE_MaterialManager
from .common import (
    Code_Response,
    ADDON_PACKAGE
)


class SUBSTANCE_Persistance():

    @staticmethod
    @persistent
    def load_pre_handler(dummy):
        pass

    @staticmethod
    @persistent
    def load_post_handler(dummy):
        try:
            # Add main thread listener
            if not bpy.app.timers.is_registered(SUBSTANCE_Threads.exec_queued_function):
                bpy.app.timers.register(SUBSTANCE_Threads.exec_queued_function)

            # Get current scene
            _scene = bpy.context.scene

            if hasattr(_scene, "loaded_sbsars") and len(_scene.loaded_sbsars) > 0:
                if not SUBSTANCE_Api.is_running:
                    # Initialize SUBSTANCE_Api
                    _result = SUBSTANCE_Api.initialize()
                    if _result[0] != Code_Response.success:
                        SUBSTANCE_Utils.log_data(
                            "ERROR",
                            "[{}] The SRE cannot initialize...".format(_result))
                        return

                for _sbsar in _scene.loaded_sbsars:
                    _sbsar.load_success = False
                    _sbsar_obj = json.loads(_sbsar.object)

                    SUBSTANCE_Threads.alt_thread_run(
                        _reload_sbsar_data,
                        (_scene, _sbsar, _sbsar_obj))

            SUBSTANCE_Utils.log_data("INFO", "Scene Substances loaded correctly")
        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Substance load failed")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())

    @staticmethod
    @persistent
    def save_pre_handler(dummy):
        try:
            SUBSTANCE_Api.temp_sbs_files.clear()
            SUBSTANCE_Api.temp_tx_files.clear()
            _addons_prefs = bpy.context.preferences.addons[ADDON_PACKAGE].preferences
            _relative_tx_path = _addons_prefs.path_relative_tx
            _scene = bpy.context.scene
            for _sbsar in _scene.loaded_sbsars:
                if not _sbsar.load_success:
                    continue

                _sbsar_obj = SUBSTANCE_Api.sbsar_get(_sbsar.id)
                _sbsar.object = json.dumps(_sbsar_obj.to_json())

                if _addons_prefs.path_relative_sbsar_enabled:
                    _original_filepath = bpy.path.abspath(_sbsar.filepath)
                    _original_filepath = os.path.abspath(_original_filepath)
                    _original_filepath = _original_filepath.replace("\\", "/")
                    _sbsar_path = _addons_prefs.path_relative_sbsar
                    _sbsar_path = _sbsar_path[2:] if _sbsar_path.startswith("//") else _sbsar_path
                    _sbsar_path = _sbsar_path[:-1] if _sbsar_path.endswith("/") else _sbsar_path
                    _sbsar.filepath = "//{}/{}".format(_sbsar_path, _sbsar.filename)
                    SUBSTANCE_Api.temp_sbs_files.append({
                        "sbsar_path": _sbsar_path,
                        "original_path": _original_filepath,
                        "filename": _sbsar.filename
                    })

                for _graph in _sbsar.graphs:
                    _parms = getattr(_scene, _graph.parms_class_name)
                    _outputs = getattr(_scene, _graph.outputs_class_name)
                    _parms = _parms.to_json()
                    _outputs = _outputs.to_json()
                    _graph.parms_data = json.dumps(_parms)
                    _graph.outputs_data = json.dumps(_outputs)

                    if SUBSTANCE_MaterialManager.get_existing_material(_graph.material.name) is None:
                        continue

                    for _output in _graph.outputs:
                        if _output.filename == "":
                            continue
                        _original_filepath = bpy.path.abspath(_output.filepath)
                        _original_filepath = os.path.abspath(_original_filepath)
                        _original_filepath = _original_filepath.replace("\\", "/")
                        _mat_path = _relative_tx_path.replace("$matname", _graph.material.name)
                        _mat_path = _mat_path[2:] if _mat_path.startswith("//") else _mat_path
                        _mat_path = _mat_path[:-1] if _mat_path.endswith("/") else _mat_path
                        _output.filepath = "//{}/{}".format(_mat_path, _output.filename)
                        SUBSTANCE_Api.temp_tx_files.append({
                            "img": "{}_{}".format(_graph.material.name, _output.name),
                            "mat_path": _mat_path,
                            "filepath": _original_filepath,
                            "filename": _output.filename,
                            "new_path": _output.filepath,
                            "mat_name": _graph.material.name
                        })
        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Susbtance pre save data error")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())

    @staticmethod
    @persistent
    def save_post_handler(dummy):
        try:
            _filepath = bpy.data.filepath.replace("\\", "/")
            _filedir = os.path.dirname(_filepath)

            for _item in SUBSTANCE_Api.temp_sbs_files:
                _sbs_dir = "{}/{}".format(_filedir, _item["sbsar_path"])
                if not os.path.exists(_sbs_dir):
                    os.makedirs(_sbs_dir)
                _src = _item["original_path"]
                _dst = "{}/{}".format(_sbs_dir, _item["filename"])
                if _src != _dst and os.path.exists(_src) and os.path.isfile(_src):
                    shutil.copyfile(_src, _dst)
                SUBSTANCE_Utils.log_data(
                    "INFO",
                    "Susbtance [{}] moved to relative path".format(_item["filename"]))

            SUBSTANCE_Utils.log_data("INFO", "Updated tx paths:")
            for _item in SUBSTANCE_Api.temp_tx_files:
                SUBSTANCE_Utils.log_data("INFO", _item)
                _tx_dir = "{}/{}".format(_filedir, _item["mat_path"])
                if not os.path.exists(_tx_dir):
                    os.makedirs(_tx_dir)
                _new_filepath = os.path.join(_tx_dir, _item["filename"]).replace("\\", "/")

                try:
                    if (_item["filepath"] != _new_filepath and
                            os.path.exists(_item["filepath"]) and
                            os.path.isfile(_item["filepath"])):
                        shutil.move(_item["filepath"], _new_filepath)
                except Exception:
                    SUBSTANCE_Utils.log_data(
                        "ERROR",
                        "Error while moving [{}] file to relative path".format(_item["filepath"]))
                    SUBSTANCE_Utils.log_traceback(traceback.format_exc())

                if _item["img"] in bpy.data.images:
                    bpy.data.images[_item["img"]].filepath = _item["new_path"]
                    bpy.data.images[_item["img"]].reload()

            SUBSTANCE_Api.temp_sbs_files.clear()
            SUBSTANCE_Api.temp_tx_files.clear()
            SUBSTANCE_Utils.log_data("INFO", "Susbtance textures saved")
        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Susbtance post save data error")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())

    @staticmethod
    @persistent
    def undo_post_handler(dummy):
        pass

    @staticmethod
    @persistent
    def depsgraph_update_post(dummy):
        _addons_prefs = bpy.context.preferences.addons[ADDON_PACKAGE].preferences
        if not _addons_prefs.auto_highlight_sbsar:
            return

        _selected_objects = bpy.context.selected_objects
        if len(_selected_objects) == 0:
            return

        if SUBSTANCE_Api.last_selection == _selected_objects:
            return

        SUBSTANCE_Api.last_selection = _selected_objects
        for _obj in _selected_objects:
            if not hasattr(_obj.data, "materials"):
                continue

            for _idx, _key in enumerate(bpy.context.scene.loaded_sbsars):
                for _graph in bpy.context.scene.loaded_sbsars[_idx].graphs:
                    if _graph.material.name in _obj.data.materials:
                        bpy.context.scene.loaded_sbsars[_idx].graphs_list = _graph.index
                        bpy.context.scene.sbsar_index = _idx
                        return
