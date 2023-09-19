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

# file: props/common.py
# brief: Common Property Groups
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy

from ..common import RESOLUTIONS_DICT


class SUBSTANCE_PG_GeneralItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="name")
    label: bpy.props.StringProperty(name="label")

    def initialize(self, item):
        self.name = item.id
        self.label = item.label


def on_linked_tiling_changed(self, context):
    if self.linked:
        self.y = self.x
        self.z = self.x
    else:
        on_tiling_changed(self, context)


def on_tiling_changed(self, context):
    pass


class SUBSTANCE_PG_Tiling(bpy.types.PropertyGroup):
    label: bpy.props.StringProperty(name="label", default="Tiling") # noqa
    x: bpy.props.FloatProperty(
        name="x",
        default=3.0,
        description="The X tiling to be used", # noqa
        update=on_linked_tiling_changed)
    y: bpy.props.FloatProperty(
        name="y",
        default=3.0,
        description="The Y tiling to be used", # noqa
        update=on_tiling_changed)
    z: bpy.props.FloatProperty(
        name="z",
        default=3.0,
        description="The Z tiling to be used", # noqa
        update=on_tiling_changed)
    linked: bpy.props.BoolProperty(
        name="linked",
        default=True,
        description='Lock/Unlock the tiling', # noqa
        update=on_linked_tiling_changed)

    def initialize(self, value):
        self.label = value.label
        self.x = value.x
        self.y = value.y
        self.y = value.z

    def get(self):
        return [self.x, self.y, self.z]


def on_update_resolution(self, context):
    if self.linked:
        self.height = self.width


class SUBSTANCE_PG_Resolution(bpy.types.PropertyGroup):
    label: bpy.props.StringProperty(name="label", default="Resolution") # noqa
    width: bpy.props.EnumProperty(
        name="width",
        default="10",
        description="The width of the exported map", # noqa
        items=RESOLUTIONS_DICT,
        update=on_update_resolution)
    height: bpy.props.EnumProperty(
        name="height",
        default="10",
        description="The height of the exported map", # noqa
        items=RESOLUTIONS_DICT)
    linked: bpy.props.BoolProperty(
        name="linked",
        default=True,
        description='Lock/Unlock the resolution', # noqa
        update=on_update_resolution)

    def initialize(self, value):
        self.label = value.label
        self.width = value.width
        self.height = value.height

    def get(self):
        return [int(self.width), int(self.height)]
