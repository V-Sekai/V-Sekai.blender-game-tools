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

# file: sbsar/manager.py
# brief: Substance operations manager
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2


import traceback

from .sbsar import SBSAR
from ..factory.sbsar import SUBSTANCE_SbsarFactory
from ..common import Code_Response
from ..utils import SUBSTANCE_Utils


class SUBSTANCE_SbsarManager():
    def __init__(self):
        self.sbsars = {}

    def add_sbsar_to_dict(self, sbsar):
        self.sbsars[sbsar.id] = sbsar
        return Code_Response.success

    def load_new(self, sbsar_json):
        _sbsar = SBSAR(sbsar_json)
        return _sbsar

    def get(self, sbsar_id):
        if sbsar_id not in self.sbsars:
            return None
        _sbsar = self.sbsars[sbsar_id]
        return _sbsar

    def register_sbsar(self, sbsar_id):
        if sbsar_id in self.sbsars:
            _sbsar = self.sbsars[sbsar_id]
            _result = SUBSTANCE_SbsarFactory.register_sbsar_classes(_sbsar)
            return _result
        else:
            return (Code_Response.sbsar_register_error, None)

    def remove_sbsar(self, sbsar_id):
        try:
            if sbsar_id in self.sbsars:
                _sbsar = self.sbsars[sbsar_id]
                for _graph in _sbsar.graphs:
                    SUBSTANCE_SbsarFactory.unregister_sbsar_class(_graph.parms_class_name)
                    SUBSTANCE_SbsarFactory.unregister_sbsar_class(_graph.outputs_class_name)

                return Code_Response.success
            else:
                return Code_Response.sbsar_remove_not_found_error
        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Substance removal error:")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return Code_Response.sbsar_remove_error
