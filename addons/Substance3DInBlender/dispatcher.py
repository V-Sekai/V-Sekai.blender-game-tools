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

# file: dispatcher.py
# brief: Async comms handler
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2
import bpy
import os
import shutil

from .network.callback import SRE_CallbackInterface
from .api import SUBSTANCE_Api
from .common import ADDON_PACKAGE


class Server_GET_Dispatcher(SRE_CallbackInterface):
    def execute(self, data):
        _addon_prefs = bpy.context.preferences.addons[ADDON_PACKAGE].preferences
        if not os.path.exists(_addon_prefs.path_default):
            os.makedirs(_addon_prefs.path_default)

        for _output in data["outputs"]:
            if "path" in _output:
                _cache_path = _output["path"].replace("\\", "/")
                _filename = os.path.basename(_cache_path)
                _new_path = os.path.join(_addon_prefs.path_default, _filename).replace("\\", "/")
                shutil.move(_cache_path, _new_path)
                _output["path"] = _new_path

        SUBSTANCE_Api.sbsar_render_callback(data)
