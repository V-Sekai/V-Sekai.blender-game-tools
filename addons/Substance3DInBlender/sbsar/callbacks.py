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

# file: shader/callbacks.py
# brief: Callbacks for susbtance outputs and properties
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy


from ..utils import SUBSTANCE_Utils
from ..material.manager import SUBSTANCE_MaterialManager
from ..common import (
    Code_OutParms,
    Code_Response,
    Code_ParmWidget,
    Code_ParmIdentifier,
    Code_OutputSizeSuffix,
    PRESET_CUSTOM
)


class SUBSTANCE_SbsarCallbacks():
    # Outputs
    @staticmethod
    def on_output_changed(self, context, output_parm_identifier):
        if not self.callback["enabled"]:
            return

        _value = getattr(self, output_parm_identifier)
        _key, _parm_key = SUBSTANCE_Utils.get_output_key(output_parm_identifier)

        _output = self.default.outputs[_key]

        if _parm_key == Code_OutParms.format.value.replace("_", ""):
            from ..api import SUBSTANCE_Api
            SUBSTANCE_Api.sbsar_set_output(
                self.sbsar_id,
                self.default.index,
                self.default.id,
                _output.id,
                _value
            )
        elif _parm_key == Code_OutParms.enabled.value.replace("_", ""):
            _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
            _selected_graph_idx = int(_selected_sbsar.graphs_list)
            _selected_graph = _selected_sbsar.graphs[_selected_graph_idx]

            if self.mat_callback["enabled"]:
                SUBSTANCE_MaterialManager.create_material(context, _selected_sbsar, _selected_graph, {})

    # Output Size
    @staticmethod
    def on_linked_changed(self, context, parm_identifier):
        if not hasattr(self, Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.linked.value):
            return

        _linked = getattr(self, Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.linked.value)
        _new_width_width = getattr(self, Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.width.value)
        if _linked:
            setattr(self, Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.height.value, _new_width_width)
        else:
            SUBSTANCE_SbsarCallbacks.on_outputsize_changed(self, context, parm_identifier)

    @staticmethod
    def on_outputsize_changed(self, context, parm_identifier):
        if not self.callback["enabled"]:
            return

        _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)
        _selected_preset = int(_selected_graph.presets_list)

        if not _selected_graph.outputsize_exists:
            return

        _parm = self.default.parms[Code_ParmIdentifier.outputsize.value]
        _output_size_x = getattr(self,  Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.width.value)
        _output_size_y = getattr(self,  Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.height.value)
        _value = [int(_output_size_x), int(_output_size_y)]

        from ..api import SUBSTANCE_Api
        _result = SUBSTANCE_Api.sbsar_parm_update(
            None,
            self.sbsar_id,
            str(self.default.index),
            self.default.id,
            _parm,
            _value,
            _value,
            SUBSTANCE_SbsarCallbacks.on_parm_update
        )
        if _result[0] == Code_Response.success:
            _new_preset_value = SUBSTANCE_Utils.update_preset_outputsize(
                _selected_graph.presets[_selected_preset].value,
                self.default.parms[Code_ParmIdentifier.outputsize.value],
                _value
            )
            _selected_graph.presets[_selected_preset].value = _new_preset_value

    # Parameters
    @staticmethod
    def on_parm_update(context, render_id, sbsar_id, graph_idx, graph_id, parm, value, output_size):
        _value = SUBSTANCE_Utils.value_fix_type(parm.identifier, parm.guiWidget, parm.type, value)
        if parm.guiWidget == Code_ParmWidget.image.value:
            if _value == "":
                return Code_Response.parm_image_empty

            _filepath = bpy.data.images[_value].filepath
            if _filepath == "":
                _filepath = SUBSTANCE_Utils.render_image_input(bpy.data.images[_value], bpy.context)
            _value = _filepath

        from ..api import SUBSTANCE_Api
        _result = SUBSTANCE_Api.sbsar_set_parm(
            render_id,
            sbsar_id,
            graph_idx,
            graph_id,
            parm.id,
            _value,
            output_size
        )

        if context is not None and _result[0] == Code_Response.success:
            _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)
            _selected_graph.presets[PRESET_CUSTOM].value = _result[1]

        return _result

    @staticmethod
    def on_parm_changed(self, context, parm_identifier):
        if not self.callback["enabled"]:
            return

        _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)
        _selected_preset = int(_selected_graph.presets_list)

        if _selected_graph.presets[_selected_preset].name != PRESET_CUSTOM:
            _selected_graph.preset_callback = False
            _selected_graph.presets_list = _selected_graph.presets[PRESET_CUSTOM].index
            _selected_graph.preset_callback = True

        _parm = self.default.parms[parm_identifier]
        _new_value = getattr(self, parm_identifier)

        _output_size = None
        if _selected_graph.outputsize_exists:
            _output_size_x = getattr(self,  Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.width.value)
            _output_size_y = getattr(self,  Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.height.value)
            _output_size = [_output_size_x, _output_size_y]

        from ..api import SUBSTANCE_Api
        SUBSTANCE_Api.sbsar_parm_update(
            context,
            self.sbsar_id,
            str(self.default.index),
            self.default.id,
            _parm,
            _new_value,
            _output_size,
            SUBSTANCE_SbsarCallbacks.on_parm_update
        )
