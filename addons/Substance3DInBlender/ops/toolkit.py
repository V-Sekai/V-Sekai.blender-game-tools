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

# file: ops/toolkit.py
# brief:SRE Toolkit Operators
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy
from bpy_extras.io_utils import ImportHelper


from ..api import SUBSTANCE_Api
from ..common import TOOLKIT_EXT, Code_Response
from ..thread_ops import SUBSTANCE_Threads
from ..utils import SUBSTANCE_Utils


class SUBSTANCE_OT_InstallTools(bpy.types.Operator, ImportHelper):
    bl_idname = 'substance.install_tools'
    bl_label = 'Install tools'
    bl_options = {'REGISTER'}
    filter_glob: bpy.props.StringProperty(default='*{}'.format(TOOLKIT_EXT), options={'HIDDEN'}) # noqa

    def __init__(self):
        self.filepath = ''

    def execute(self, context):
        SUBSTANCE_Threads.cursor_push('WAIT')
        _result = SUBSTANCE_Api.toolkit_install(self.filepath)
        SUBSTANCE_Threads.cursor_pop()

        if _result[0] == Code_Response.success:
            SUBSTANCE_Utils.log_data("INFO", "Substance 3D Integration Tools installed correctly", display=True)
        else:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while installing the Substance 3D Integration Tools".format(_result[0]),
                display=True)
        return {'FINISHED'}


class SUBSTANCE_OT_UpdateTools(bpy.types.Operator, ImportHelper):
    bl_idname = 'substance.update_tools'
    bl_label = 'Update tools'
    bl_options = {'REGISTER'}
    filter_glob: bpy.props.StringProperty(default='*{}'.format(TOOLKIT_EXT), options={'HIDDEN'}) # noqa

    def __init__(self):
        self.filepath = ''

    def execute(self, context):
        SUBSTANCE_Threads.cursor_push('WAIT')
        _result = SUBSTANCE_Api.toolkit_update(self.filepath)
        SUBSTANCE_Threads.cursor_pop()

        if _result[0] == Code_Response.success:
            SUBSTANCE_Utils.log_data("INFO", "Substance 3D Integration Tools updated correctly", display=True)
        else:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while updating the Substance 3D Integration Tools".format(_result[0]),
                display=True)
        return {'FINISHED'}


class SUBSTANCE_OT_UninstallTools(bpy.types.Operator):
    bl_idname = 'substance.uninstall_tools'
    bl_label = 'UnInstall tools'
    bl_options = {'REGISTER'}

    def execute(self, context):
        SUBSTANCE_Threads.cursor_push('WAIT')
        _result = SUBSTANCE_Api.toolkit_uninstall()
        SUBSTANCE_Threads.cursor_pop()

        if _result[0] == Code_Response.success:
            SUBSTANCE_Utils.log_data("INFO", "Substance 3D Integration Tools fully removed", display=True)
        else:
            SUBSTANCE_Utils.log_data(
                "ERROR",
                "[{}] Error while removing the Substance 3D Integration Tools".format(_result[0]),
                display=True)
        return {'FINISHED'}
