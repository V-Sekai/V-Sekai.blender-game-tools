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


class SUBSTANCE_OT_Message(bpy.types.Operator):
    bl_idname = 'substance.send_message'
    bl_label = 'Message'
    bl_description = "Send the user a message"

    type: bpy.props.StringProperty(default="INFO") # noqa
    message: bpy.props.StringProperty(default="") # noqa
    _timer = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            self.cancel(context)
            self.report({self.type}, self.message)
            return {'FINISHED'}
        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(time_step=1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
