"""
Copyright (C) 2021 Adobe.
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


# Substance in Blender launch the substance website
# 5/27/2020
import bpy
from bpy.types import Operator


class SUBSTANCE_OT_GetTools(Operator):
    """Open the Substance 3D Integration Tools website"""
    bl_idname = 'substance.goto_tools'
    bl_label = 'Substance 3D Integration Tools'
    bl_description = 'Go to Substance 3D Integration Tools'
    bl_options = {'REGISTER'}

    def execute(self, context):
        bpy.ops.wm.url_open(url="https://www.adobeprerelease.com/beta/68A24EE2-2EA8-416F-D95B-23B8E64E5DE8")
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


class SUBSTANCE_OT_GotoShare(Operator):
    """Open the Substance 3D Share website"""
    bl_idname = 'substance.goto_share'
    bl_label = 'Substance 3D Community Assets'
    bl_description = 'Go to Substance 3D Community Assets'
    bl_options = {'REGISTER'}

    def execute(self, context):
        bpy.ops.wm.url_open(url="https://share-beta.substance3d.com/")
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


class SUBSTANCE_OT_GotoSource(Operator):
    """Open the Substance 3D Source website"""
    bl_idname = 'substance.goto_source'
    bl_label = 'Substance 3D Assets'
    bl_description = 'Go to Substance 3D Assets'
    bl_options = {'REGISTER'}

    def execute(self, context):
        bpy.ops.wm.url_open(url="https://source.substance3d.com/")
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)
