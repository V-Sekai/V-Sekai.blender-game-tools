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

# file: ops/material.py
# brief: Material operators
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2


import bpy
import os
import traceback
import json
import shutil

from ..utils import SUBSTANCE_Utils
from ..common import Code_SbsarLoadSuffix
from ..material.manager import SUBSTANCE_MaterialManager


class SUBSTANCE_OT_SetMaterial(bpy.types.Operator):
    bl_idname = 'substance.set_material'
    bl_label = 'Set material'
    bl_description = "Set the material shader network"

    data: bpy.props.StringProperty(default="") # noqa

    def execute(self, context):
        _data = json.loads(self.data)
        if len(_data["outputs"]) == 0:
            SUBSTANCE_Utils.log_data("INFO", "No render changes")
            return {'FINISHED'}

        _selected_sbsar = None
        for _item in context.scene.loaded_sbsars:
            if _item.id == _data["id"]:
                _selected_sbsar = _item

        if _selected_sbsar is None:
            SUBSTANCE_Utils.log_data("ERROR", "Substance file cannot be found", display=True)
            return {'FINISHED'}

        try:
            _selected_graph = None
            _outputs = {}
            for _graph in _selected_sbsar.graphs:
                _outputs[_graph.id] = {}
                for _output in _data["outputs"]:
                    if "graphID" not in _output:
                        continue

                    _output_graph_id = str(_output["graphID"])
                    if _output_graph_id != _graph.id:
                        continue

                    _selected_graph = _graph
                    for _sbs_output in _graph.outputs:
                        _output_id = str(_output["id"])
                        if _sbs_output.id != _output_id:
                            continue

                        if "path" not in _output:
                            continue

                        dst_dir = os.path.dirname(_output["path"])
                        filename = "{}_{}.{}".format(_graph.material.name, _sbs_output.usage, _output["imageFormat"])
                        dst_file = os.path.join(dst_dir, filename).replace("\\", "/")
                        shutil.move(_output["path"], dst_file)
                        _outputs[_graph.id][_sbs_output.usage] = {
                            "id": _sbs_output.id,
                            "path": dst_file,
                            "name": _sbs_output.name,
                            "identifier": _sbs_output.name,
                            "label": _sbs_output.label,
                            "usage": _sbs_output.usage
                        }
                        break

            if _selected_graph is None:
                SUBSTANCE_Utils.log_data("ERROR", "Substance graph cannot be found", display=True)
                return {'FINISHED'}

            _outputs = _outputs[_selected_graph.id]
            SUBSTANCE_MaterialManager.create_material(context, _selected_sbsar, _selected_graph, _outputs)

        except Exception:
            _selected_sbsar.suffix = Code_SbsarLoadSuffix.error.value[0]
            _selected_sbsar.icon = Code_SbsarLoadSuffix.error.value[1]
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Susbtance material creation error:")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())

        return {'FINISHED'}
