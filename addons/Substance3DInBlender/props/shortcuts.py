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

# file: props/shortcuts.py
# brief: Shortcuts Property Groups
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy


def _on_shortcut_update(self, context):
    _ctrl = "Ctrl+" if self.menu_ctrl else ""
    _shift = "Shift+" if self.menu_shift else ""
    _alt = "Alt+" if self.menu_alt else ""
    self.menu_label = _ctrl + _shift + _alt + self.menu_key


class SUBSTANCE_PG_Shortcuts(bpy.types.PropertyGroup):
    # Floating Menu
    menu_name: bpy.props.StringProperty(default="Floating Menu") # noqa
    menu_ctrl: bpy.props.BoolProperty(default=True, update=_on_shortcut_update)
    menu_shift: bpy.props.BoolProperty(default=True, update=_on_shortcut_update)
    menu_alt: bpy.props.BoolProperty(default=False, update=_on_shortcut_update)
    menu_key: bpy.props.StringProperty(default='U', update=_on_shortcut_update) # noqa
    menu_label: bpy.props.StringProperty(default="Ctrl+Shift+U") # noqa

    # Load SBSAR
    load_name: bpy.props.StringProperty(default="Load SBSAR") # noqa
    load_ctrl: bpy.props.BoolProperty(default=True)
    load_shift: bpy.props.BoolProperty(default=True)
    load_alt: bpy.props.BoolProperty(default=False)
    load_key: bpy.props.StringProperty(default='L') # noqa

    # Apply Material
    apply_name: bpy.props.StringProperty(default="Apply Current Material") # noqa
    apply_ctrl: bpy.props.BoolProperty(default=True)
    apply_shift: bpy.props.BoolProperty(default=True)
    apply_alt: bpy.props.BoolProperty(default=False)
    apply_key: bpy.props.StringProperty(default='M') # noqa
