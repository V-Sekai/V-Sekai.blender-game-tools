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

# file: ops/sbsar.py
# brief: Sinstance Operators
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import os
import time
import bpy
from bpy_extras.io_utils import ImportHelper

from ..api import SUBSTANCE_Api
from ..material.manager import SUBSTANCE_MaterialManager
from ..utils import SUBSTANCE_Utils
from ..thread_ops import SUBSTANCE_Threads
from ..sbsar.async_ops import _initialize_sbsar_data, _duplicate_sbsar_data
from ..common import (
    Code_Response,
    Code_SbsarLoadSuffix,
    ADDON_PACKAGE,
    TOOLKIT_EXPECTED_VERSION
)


class SUBSTANCE_OT_LoadSBSAR(bpy.types.Operator, ImportHelper):
    bl_idname = 'substance.load_sbsar'
    bl_label = 'Load Substance Material'
    bl_description = 'Open file browser to select a Substance 3D material'
    bl_options = {'REGISTER'}
    filename_ext = '.sbsar'
    filter_glob: bpy.props.StringProperty(default='*.sbsar', options={'HIDDEN'}) # noqa
    files: bpy.props.CollectionProperty(name='Substance 3D material files', type=bpy.types.OperatorFileListElement) # noqa
    directory: bpy.props.StringProperty(subtype="DIR_PATH") # noqa

    def __init__(self):
        self.filepath = ''

    @classmethod
    def poll(cls, context):
        _, _toolkit_version = SUBSTANCE_Api.toolkit_version_get()
        return _toolkit_version is not None and _toolkit_version in TOOLKIT_EXPECTED_VERSION

    def invoke(self, context, event):
        if not SUBSTANCE_Api.is_running:
            # Initialize SUBSTANCE_Api
            _result = SUBSTANCE_Api.initialize()
            if _result[0] != Code_Response.success:
                SUBSTANCE_Utils.log_data("ERROR", "[{}] The SRE cannot initialize...".format(_result))
                return

        _addon_prefs = context.preferences.addons[ADDON_PACKAGE].preferences
        self.filepath = _addon_prefs.path_library
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        _addon_prefs, _selected_shader_preset = SUBSTANCE_Utils.get_selected_shader_preset(context)
        _normal_format = _addon_prefs.normal_format
        _output_size = _addon_prefs.resolution.get()

        _shader_outputs = getattr(context.scene, _selected_shader_preset.outputs_class_name)

        SUBSTANCE_Threads.cursor_push('WAIT')
        for _f in self.files:
            if len(_f.name) > 0:
                _unique_name = SUBSTANCE_Utils.get_unique_name(_f.name, context)
                _filepath = os.path.join(self.directory, _f.name)

                SUBSTANCE_Utils.log_data("INFO", "Begin loading substance from file [{}]".format(_f.name))

                # Load the sbsar to the SRE
                _result = SUBSTANCE_Api.sbsar_load(_filepath)
                if _result[0] != Code_Response.success:
                    SUBSTANCE_Utils.log_data(
                        "ERROR",
                        "Substance file [{}] located at [{}] could not be loaded".format(_f.name, _filepath),
                        display=True)
                    continue
                _sbsar_id = _result[1]

                _loaded_sbsar = context.scene.loaded_sbsars.add()
                _loaded_sbsar.initialize(_sbsar_id, _unique_name, _f.name, _filepath)
                context.scene.sbsar_index = len(context.scene.loaded_sbsars) - 1

                # Asyc call to initialize the substance information
                SUBSTANCE_Threads.alt_thread_run(
                    _initialize_sbsar_data, (
                        context,
                        _sbsar_id,
                        _unique_name,
                        _f.name,
                        _filepath,
                        _normal_format,
                        _output_size,
                        _shader_outputs))

        SUBSTANCE_Threads.cursor_pop()
        return {'FINISHED'}


class SUBSTANCE_OT_ApplySBSAR(bpy.types.Operator):
    bl_idname = 'substance.apply_sbsar'
    bl_label = 'Apply the Substance 3D material'

    @classmethod
    def description(cls, context, properties):
        _selected_geo = SUBSTANCE_Utils.get_selected_geo(context.selected_objects)
        if len(context.scene.loaded_sbsars) > 0 and len(_selected_geo) > 0:
            _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
            if _selected_sbsar.load_success:
                return "Applies the selected Substance 3D material to the selected object(s)"
            else:
                return "This Substance 3D material loaded incorrectly"
        else:
            return "Please load at least one Substance file and select an object in the scene"

    @classmethod
    def poll(cls, context):
        _selected_geo = SUBSTANCE_Utils.get_selected_geo(context.selected_objects)
        if len(context.scene.loaded_sbsars) > 0 and len(_selected_geo) > 0:
            _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
            return _selected_sbsar.load_success
        return False

    def execute(self, context):
        _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)
        _material = SUBSTANCE_MaterialManager.get_existing_material(_selected_graph.material.name)

        if _material is None:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "Substance Material needs to finish rendering before applying",
                display=True)
            return {'FINISHED'}

        _selected_objects = bpy.context.selected_objects
        if len(_selected_objects) == 0:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "Material [{}] cannot be added, there are no selected objects".format(_material.name),
                display=True)
            return {'FINISHED'}

        for _obj in _selected_objects:
            if not hasattr(_obj.data, "materials"):
                continue
            _obj.data.materials.append(_material)

        SUBSTANCE_Utils.log_data(
            "INFO",
            "Material slot with substance [{}] added to the object".format(_material.name),
            display=True)
        return {'FINISHED'}


class SUBSTANCE_OT_DuplicateSBSAR(bpy.types.Operator):
    bl_idname = 'substance.duplicate_sbsar'
    bl_label = 'Duplicate the Substance 3D material'

    @classmethod
    def description(cls, context, properties):
        if len(context.scene.loaded_sbsars) > 0:
            _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
            if _selected_sbsar.load_success:
                return "Duplicate the selected Substance 3D material"
            else:
                return "This Substance 3D material loaded incorrectly"
        else:
            return "Please load at least one Substance file"

    @classmethod
    def poll(cls, context):
        if len(context.scene.loaded_sbsars) > 0:
            _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
            return _selected_sbsar.load_success
        return False

    def execute(self, context):
        SUBSTANCE_Threads.cursor_push('WAIT')
        _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
        _unique_name = SUBSTANCE_Utils.get_unique_name(_selected_sbsar.name, context)

        # Duplicate the selected substance in the SRE
        _result = SUBSTANCE_Api.sbsar_duplicate(_selected_sbsar.id)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "Substance  [{}] could not be duplicated".format(_selected_sbsar.name),
                display=True)
            SUBSTANCE_Threads.cursor_pop()
            return {'FINISHED'}
        _sbsar_id = _result[1]

        _loaded_sbsar = context.scene.loaded_sbsars.add()
        _loaded_sbsar.initialize(_sbsar_id, _unique_name, _selected_sbsar.filename, _selected_sbsar.filepath)
        context.scene.sbsar_index = len(context.scene.loaded_sbsars) - 1

        # Asyc call to duplicate the substance information
        SUBSTANCE_Threads.alt_thread_run(
            _duplicate_sbsar_data, (
                context,
                _sbsar_id,
                _selected_sbsar,
                _loaded_sbsar))

        SUBSTANCE_Utils.log_data(
            "INFO",
            "Substance [{}] duplicated succesfully".format(_selected_sbsar.name),
            display=True)
        SUBSTANCE_Threads.cursor_pop()
        return {'FINISHED'}


class SUBSTANCE_OT_ReloadSBSAR(bpy.types.Operator):
    bl_idname = 'substance.reload_sbsar'
    bl_label = 'Refresh the Substance 3D material'

    @classmethod
    def description(cls, context, properties):
        if len(context.scene.loaded_sbsars) > 0:
            return "Reloads the selected Substance 3D material"
        else:
            return "Please load at least one Substance file"

    @classmethod
    def poll(cls, context):
        if len(context.scene.loaded_sbsars) > 0:
            _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
            return (_selected_sbsar.suffix == Code_SbsarLoadSuffix.error.value[0] or
                    _selected_sbsar.suffix == Code_SbsarLoadSuffix.success.value[0])
        return False

    def execute(self, context):
        _addon_prefs, _selected_shader_preset = SUBSTANCE_Utils.get_selected_shader_preset(context)
        _normal_format = _addon_prefs.normal_format
        _output_size = _addon_prefs.resolution.get()

        _shader_outputs = getattr(context.scene, _selected_shader_preset.outputs_class_name)

        SUBSTANCE_Threads.cursor_push('WAIT')
        # Time
        _time_start = time.time()

        # Get intial values
        _original_index = context.scene.sbsar_index
        _selected_sbsar = context.scene.loaded_sbsars[_original_index]
        _unique_name = _selected_sbsar.name
        _filename = _selected_sbsar.filename
        _filepath = _selected_sbsar.filepath
        _old_sbsar_id = _selected_sbsar.id

        # Turn off the substance
        _selected_sbsar.load_success = False

        # Remove the substance from the list
        context.scene.loaded_sbsars.remove(context.scene.sbsar_index)
        if context.scene.sbsar_index != 0 and context.scene.sbsar_index >= len(context.scene.loaded_sbsars):
            context.scene.sbsar_index = len(context.scene.loaded_sbsars) - 1

        # Unregister the dynamic classes
        _result = SUBSTANCE_Api.sbsar_unregister(_old_sbsar_id)

        # Load the sbsar to the SRE
        _result = SUBSTANCE_Api.sbsar_load(_filepath)
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "Substance file [{}] located at [{}] could not be reloaded".format(_filename, _filepath),
                display=True)
            SUBSTANCE_Threads.cursor_pop()
            return {'FINISHED'}
        _sbsar_id = _result[1]

        # Re-add the substance to the list
        _loaded_sbsar = context.scene.loaded_sbsars.add()
        _loaded_sbsar.initialize(_sbsar_id, _unique_name, _filename, _filepath)

        # Reposition the substance in the place it was originally in the list
        context.scene.loaded_sbsars.move(len(context.scene.loaded_sbsars) - 1, _original_index)
        context.scene.sbsar_index = _original_index

        # Asyc call to initialize the substance information
        SUBSTANCE_Threads.alt_thread_run(
            _initialize_sbsar_data,
            (
                context,
                _sbsar_id,
                _unique_name,
                _filename,
                _filepath,
                _normal_format,
                _output_size,
                _shader_outputs))

        # Time
        _time_end = time.time()
        _load_time = round(_time_end - _time_start, 3)
        SUBSTANCE_Utils.log_data(
            "INFO",
            "Substance [{}] located at [{}] was loaded correctly\n -ID: {}\n -Loading time: {} seconds\n".format(
                _unique_name,
                _filepath,
                _sbsar_id,
                _load_time),
            display=True)
        SUBSTANCE_Threads.cursor_pop()
        return {'FINISHED'}


class SUBSTANCE_OT_RemoveSBSAR(bpy.types.Operator):
    bl_idname = 'substance.remove_sbsar'
    bl_label = 'Remove the Substance 3D material'

    @classmethod
    def description(cls, context, properties):
        if len(context.scene.loaded_sbsars) > 0:
            return "Remove the selected Substance 3D material"
        else:
            return "Please load at least one Substance file"

    @classmethod
    def poll(cls, context):
        if len(context.scene.loaded_sbsars) > 0:
            _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
            return (_selected_sbsar.suffix == Code_SbsarLoadSuffix.error.value[0] or
                    _selected_sbsar.suffix == Code_SbsarLoadSuffix.success.value[0])
        return False

    def execute(self, context):
        _idx = context.scene.sbsar_index
        _selected_sbsar = context.scene.loaded_sbsars[_idx]
        _sbsar_id = _selected_sbsar.id
        _load_success = _selected_sbsar.load_success
        _sbsar_name = _selected_sbsar.name

        _mats = []
        for _graph in _selected_sbsar.graphs:
            _mats.append(_graph.material.name)

        context.scene.loaded_sbsars.remove(_idx)
        if context.scene.sbsar_index != 0 and context.scene.sbsar_index >= len(context.scene.loaded_sbsars):
            context.scene.sbsar_index = len(context.scene.loaded_sbsars) - 1

        if _load_success:
            SUBSTANCE_Api.sbsar_unregister(_sbsar_id)
            context.area.tag_redraw()

        for _mat in _mats:
            _m = SUBSTANCE_MaterialManager.get_existing_material(_mat)
            if _m is None:
                continue
            _m.use_fake_user = False

        SUBSTANCE_Utils.log_data("INFO", "Substance [{}] was removed correctly".format(_sbsar_name), display=True)
        return {'FINISHED'}
