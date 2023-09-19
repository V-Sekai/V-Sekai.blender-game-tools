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

# file: ops/presets.py
# brief:Presets Operators
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import os
import bpy
from bpy_extras.io_utils import ImportHelper
from ..common import PRESET_DEFAULT, PRESET_CUSTOM, PRESET_EXTENSION, Code_Response
from ..utils import SUBSTANCE_Utils
from ..api import SUBSTANCE_Api
from ..sbsar.sbsar import SBS_Preset


class SUBSTANCE_OT_AddPreset(bpy.types.Operator):
    bl_idname = 'substance.add_preset'
    bl_label = 'New Preset'
    bl_description = "Set the current parameters as a new preset"

    preset_name: bpy.props.StringProperty(name="Preset Name") # noqa

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        _layout = self.layout

        _row = _layout.row()
        _row.label(text="Preset Name: ")
        _row.prop(self, 'preset_name', text="")

    def execute(self, context):
        if len(self.preset_name) > 0:
            _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
            _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)

            _result = SUBSTANCE_Api.sbsar_preset_get(_selected_sbsar.id, _selected_graph.index)
            if _result[0] != Code_Response.success:
                SUBSTANCE_Utils.log_data(
                    "ERROR",
                    "[{}] Error while getting the newly created preset".format(Code_Response.preset_create_get_error))
                return {'FINISHED'}

            _preset_value = _result[1]

            _obj = {
                "label": self.preset_name,
                "embedded": False,
                "icon": "LOCKED",
                "value": _preset_value
            }

            _preset_obj = SBS_Preset(_obj)

            _idx = len(_selected_graph.presets)
            _preset = _selected_graph.presets.add()
            _preset.initialize(_idx, _preset_obj)

            _selected_graph.preset_callback = False
            _selected_graph.presets_list = str(_idx)
            _selected_graph.preset_callback = True

            SUBSTANCE_Utils.log_data("INFO", "Preset [{}] created".format(self.preset_name), display=True)

            self.preset_name = ""

        else:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while creating new preset [{}]".format(
                    Code_Response.preset_create_no_name_error,
                    self.preset_name),
                display=True)

        return {'FINISHED'}


class SUBSTANCE_OT_DeletePreset(bpy.types.Operator):
    bl_idname = 'substance.delete_preset'
    bl_label = 'Delete preset'
    bl_description = "Delete the current preset"

    @classmethod
    def poll(cls, context):
        _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)
        _selected_preset_idx = int(_selected_graph.presets_list)
        _selected_preset = _selected_graph.presets[_selected_preset_idx]
        return not _selected_preset.embedded and _selected_preset.icon != "UNLOCKED"

    def execute(self, context):
        _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)
        _selected_preset_idx = int(_selected_graph.presets_list)

        _selected_graph.presets_list = "0"
        _selected_graph.presets.remove(_selected_preset_idx)

        SUBSTANCE_Utils.log_data("INFO", "Preset deleted", display=True)

        return {'FINISHED'}


class SUBSTANCE_OT_ImportPreset(bpy.types.Operator, ImportHelper):
    bl_idname = 'substance.import_preset'
    bl_label = 'Import preset'
    bl_description = "Import a preset from a file"

    filter_glob: bpy.props.StringProperty(default='*' + PRESET_EXTENSION, options={'HIDDEN'}) # noqa
    files: bpy.props.CollectionProperty(name='SBSAR Presets Files', type=bpy.types.OperatorFileListElement) # noqa
    directory: bpy.props.StringProperty(subtype="DIR_PATH") # noqa

    def __init__(self):
        self.filepath = ''

    def execute(self, context):
        _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]

        for _f in self.files:
            if len(_f.name) > 0:
                _filepath = os.path.join(self.directory, _f.name)

                _result = SUBSTANCE_Api.sbsar_preset_read(_filepath)
                if _result[0] != Code_Response.success:
                    SUBSTANCE_Utils.log_data("ERROR", "[{}] Error while reading preset from file".format(_result))
                    continue
                _obj = _result[1]

                _not_found = len(_selected_sbsar.graphs)
                for _graph in _selected_sbsar.graphs:
                    if _graph.name not in _obj:
                        _not_found -= 1
                        continue

                    for _preset in _obj[_graph.name]:
                        if _preset["label"] in _graph.presets:
                            if _preset["label"] == PRESET_CUSTOM or _preset["label"] == PRESET_DEFAULT:
                                SUBSTANCE_Utils.log_data(
                                    "ERROR",
                                    "[{}] Error [{}] cannot be overwritten".format(
                                        Code_Response.preset_import_protected_error,
                                        _preset["label"]),
                                    display=True)
                                continue

                            for _existing_preset in _graph.presets:
                                if _preset["label"] != _existing_preset.name:
                                    continue
                                if _existing_preset.embedded:
                                    SUBSTANCE_Utils.log_data(
                                        "ERROR",
                                        "[{}] Error [{}] cannot be overwritten".format(
                                            Code_Response.preset_import_protected_error,
                                            _preset["label"]),
                                        display=True)
                                    continue

                                _existing_preset.value = _preset["value"]
                                SUBSTANCE_Utils.log_data(
                                    "INFO",
                                    "Preset [{}] updated.".format(_preset["label"]),
                                    display=True)
                        else:
                            _obj = {
                                "label": _preset["label"],
                                "embedded": False,
                                "icon": "LOCKED",
                                "value": _preset["value"]
                            }

                            _preset_obj = SBS_Preset(_obj)

                            _idx = len(_graph.presets)
                            _new_preset = _graph.presets.add()
                            _new_preset.initialize(_idx, _preset_obj)

                            SUBSTANCE_Utils.log_data(
                                "INFO",
                                "Preset [{}] imported.".format(_preset["label"]),
                                display=True)

                if _not_found == 0:
                    SUBSTANCE_Utils.log_data(
                        "ERROR",
                        "[{}] Error Preset [{}] cannot be imported in this substance".format(
                            Code_Response.preset_import_not_graph,
                            _f.name),
                        display=True)
                    return {'FINISHED'}

        return {'FINISHED'}


class SUBSTANCE_OT_ExportPreset(bpy.types.Operator, ImportHelper):
    bl_idname = 'substance.export_preset'
    bl_label = 'Export preset'
    bl_description = "Export current preset to a file"

    preset_name: bpy.props.StringProperty(name="Preset Name") # noqa

    def __init__(self):
        self.filepath = ''

    @classmethod
    def poll(cls, context):
        _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)
        _selected_preset_idx = int(_selected_graph.presets_list)
        _selected_preset = _selected_graph.presets[_selected_preset_idx]

        return _selected_preset.name != PRESET_DEFAULT and _selected_preset.name != PRESET_CUSTOM

    def execute(self, context):
        _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
        _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)
        _selected_preset_idx = int(_selected_graph.presets_list)
        _selected_preset = _selected_graph.presets[_selected_preset_idx]

        _result = SUBSTANCE_Api.sbsar_preset_get(_selected_sbsar.id, _selected_graph.index)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while getting the current preset".format(Code_Response.preset_export_get_error),
                display=True)
            return {'FINISHED'}
        _preset_value = _result[1]

        _result = SUBSTANCE_Api.sbsar_preset_write(
            self.filepath,
            _selected_preset.name,
            _preset_value,
            _selected_graph.name)
        if _result != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while writting the current preset".format(_result),
                display=True)
        else:
            SUBSTANCE_Utils.log_data("INFO", "Preset exported", display=True)
        return {'FINISHED'}
