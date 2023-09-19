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

# file: ops/web.py
# brief: Web Operators
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy

from ..common import (
    WEB_SUBSTANCE_TOOLS,
    WEB_SUBSTANCE_SHARE,
    WEB_SUBSTANCE_SOURCE,
    WEB_SUBSTANCE_DOCS,
    WEB_SUBSTANCE_FORUMS,
    WEB_SUBSTANCE_DISCORD
    )


class SUBSTANCE_OT_GoToWebsite(bpy.types.Operator):
    bl_idname = 'substance.goto_web'
    bl_label = 'Substance 3D Open Website'
    bl_description = 'Go to Website'
    bl_options = {'REGISTER'}

    url: bpy.props.StringProperty()

    def execute(self, context):
        bpy.ops.wm.url_open(url=self.url)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


class SUBSTANCE_OT_GetTools(SUBSTANCE_OT_GoToWebsite):
    bl_idname = 'substance.goto_tools'
    bl_label = 'Substance 3D Integration Tools'
    bl_description = 'Go to Substance 3D Integration Tools'
    url: bpy.props.StringProperty(default=WEB_SUBSTANCE_TOOLS)


class SUBSTANCE_OT_GotoShare(SUBSTANCE_OT_GoToWebsite):
    bl_idname = 'substance.goto_share'
    bl_label = 'Substance 3D Community Assets'
    bl_description = 'Go to Substance 3D Community Assets'
    url: bpy.props.StringProperty(default=WEB_SUBSTANCE_SHARE)


class SUBSTANCE_OT_GotoSource(SUBSTANCE_OT_GoToWebsite):
    bl_idname = 'substance.goto_source'
    bl_label = 'Substance 3D Assets'
    bl_description = 'Go to Substance 3D Assets'
    url: bpy.props.StringProperty(default=WEB_SUBSTANCE_SOURCE)


class SUBSTANCE_OT_GotoDocs(SUBSTANCE_OT_GoToWebsite):
    bl_idname = 'substance.goto_docs'
    bl_label = 'Substance Plugin for Blender Documentation'
    bl_description = 'Go to Substance Plugin for Blender Documentation'
    url: bpy.props.StringProperty(default=WEB_SUBSTANCE_DOCS)


class SUBSTANCE_OT_GotoForums(SUBSTANCE_OT_GoToWebsite):
    bl_idname = 'substance.goto_forums'
    bl_label = 'Substance 3D Forums'
    bl_description = 'Go to Substance 3D Forums'
    url: bpy.props.StringProperty(default=WEB_SUBSTANCE_FORUMS)


class SUBSTANCE_OT_GotoDiscord(SUBSTANCE_OT_GoToWebsite):
    bl_idname = 'substance.goto_discord'
    bl_label = 'Substance 3D Discord Server'
    bl_description = 'Go to Substance 3D Discord Server'
    url: bpy.props.StringProperty(default=WEB_SUBSTANCE_DISCORD)
