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

# file: presets/manager.py
# brief: Manager for preset related operations
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import xml.etree.ElementTree as ET

import traceback

from ..utils import SUBSTANCE_Utils
from ..common import Code_Response, PRESET_EXTENSION


class SUBSTANCE_PresetManager():
    def __init__(self):
        pass

    def preset_write_file(self, filepath, preset_name, preset, graph_name):
        try:
            _dir_path = filepath + preset_name + PRESET_EXTENSION
            _root = ET.Element('sbspresets')
            _root.set('formatversion', '1.1')
            _root.set('count', '1')

            _pkg = ET.SubElement(_root, 'sbspreset')
            _pkg.set('pkgurl', "pkg:///" + graph_name)
            _pkg.set('label', preset_name)

            _preset_xml = ET.fromstring(preset)

            for _preset_input in _preset_xml:
                _el = ET.SubElement(_pkg, 'presetinput')
                _el.set('identifier', _preset_input.attrib['identifier'])
                _el.set('uid', _preset_input.attrib['uid'])
                _el.set('type', _preset_input.attrib['type'])
                _el.set('value', _preset_input.attrib['value'])

            _tree = ET.ElementTree(_root)
            ET.indent(_tree, space=" ", level=0)
            _tree.write(_dir_path)
            return Code_Response.success

        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Writing preset error:")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())

            return Code_Response.preset_export_error

    def preset_read_file(self, filepath):
        try:
            with open(filepath) as _f:
                _preset_file = _f.read()
            _root = ET.fromstring(_preset_file)

            _obj = {}

            for _child in _root.findall('sbspreset'):
                _preset_value = ET.tostring(_child, encoding='unicode')

                _graph = _child.attrib['pkgurl'].split('?')[0]
                _graph = _graph.replace("pkg:///", "")
                _graph = _graph.replace("pkg://", "")

                if _graph not in _obj:
                    _obj[_graph] = []

                _obj[_graph].append({
                    "label": _child.attrib['label'],
                    "value": _preset_value
                })

            return (Code_Response.success, _obj)

        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Reading preset error:")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())

            return (Code_Response.preset_import_error, None)
