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

# file: render/manager.py
# brief: Render operations manager
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import json
import threading

from .. thread_ops import SUBSTANCE_Threads
from ..common import PARAM_UPDATE_DELAY_S, Code_SbsarLoadSuffix


class SUBSTANCE_RenderManager():
    def __init__(self):
        self.parm_lock = threading.Lock()
        self.render_lock = threading.Lock()
        self.render_current = ""
        self.parm_change_queue = {}
        self.render_queue = {}

    # Parameter render call
    def parm_queue_add(self, context, render_id, sbsar_id, graph_idx, graph_id, parm, value, output_size, callback):
        with self.parm_lock:
            if render_id in self.parm_change_queue:
                self.parm_change_queue[render_id].cancel()
                self.parm_change_queue.pop(render_id)

            self.parm_change_queue[render_id] = SUBSTANCE_Threads.timer_thread_run(
                PARAM_UPDATE_DELAY_S,
                self._parm_render_update,
                (context, render_id, sbsar_id, graph_idx, graph_id, parm, value, output_size, callback)
            )

    def _parm_render_update(
            self,
            context,
            render_id,
            sbsar_id,
            graph_idx,
            graph_id,
            parm,
            value,
            output_size,
            callback):
        with self.parm_lock:
            self.parm_change_queue.pop(render_id)
            callback(context, render_id, sbsar_id, graph_idx, graph_id, parm, value, output_size)

    # Render call
    def graph_render(self, render_id, sbsar_id, graph_idx, request_type, callback):
        def _set_render_tag():
            import bpy
            for _item in bpy.context.scene.loaded_sbsars:
                if _item.id == sbsar_id:
                    _item.suffix = Code_SbsarLoadSuffix.render.value[0]
                    _item.icon = Code_SbsarLoadSuffix.render.value[1]
                    break

        with self.render_lock:
            if self.render_current == "":
                self.render_current = render_id
                callback(sbsar_id, graph_idx, request_type)
            else:
                if render_id not in self.render_queue:
                    self.render_queue[render_id] = {
                        "render_id": render_id,
                        "sbsar_id": sbsar_id,
                        "graph_idx": graph_idx,
                        "request_type": request_type,
                        "callback": callback
                    }
        SUBSTANCE_Threads.main_thread_run(_set_render_tag)

    def render_finish(self, data):
        _current_sbsar_id = None
        _next_render = None
        with self.render_lock:
            if self.render_current != "":
                _current_sbsar_id = self.render_current.split("_")[0]
                self.render_current = ""
            if len(self.render_queue.keys()) > 0:
                _keys = self.render_queue.keys()
                _key = list(_keys)[0]
                _next_render = self.render_queue.pop(_key, None)
        if _next_render is not None:
            self.graph_render(
                _next_render["render_id"],
                _next_render["sbsar_id"],
                _next_render["graph_idx"],
                _next_render["request_type"],
                _next_render["callback"]
            )

        def _set_material_info():
            import bpy
            str_data = json.dumps(data)
            bpy.ops.substance.set_material(data=str_data)
            for _item in bpy.context.scene.loaded_sbsars:
                if _current_sbsar_id is not None and _item.id == _current_sbsar_id:
                    _item.suffix = Code_SbsarLoadSuffix.success.value[0]
                    _item.icon = Code_SbsarLoadSuffix.success.value[1]

        SUBSTANCE_Threads.main_thread_run(_set_material_info)
