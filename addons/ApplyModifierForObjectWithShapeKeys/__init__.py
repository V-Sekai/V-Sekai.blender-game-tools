# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****

# Date: 01 February 2015
# Blender script
# Description: Apply modifier and remove from the stack for object with shape keys
# (Pushing 'Apply' button in 'Object modifiers' tab result in an error 'Modifier cannot be applied to a mesh with shape keys').

bl_info = {
    "name":         "Apply modifier for object with shape keys",
    "author":       "Przemysław Bągard, additonal contributions by Iszotic, updated to 2.93 by Fro Zen",
    "blender":      (2,93,0),
    "version":      (0,1,3),
    "location":     "Context menu",
    "description":  "Apply modifier and remove from the stack for object with shape keys (Quality of life fix)",
    "category":     "Object Tools > Multi Shape Keys"
}

import bpy

def register():
    from .apply_modifier_shape_keys import register as reg
    reg()

def unregister():
    from .apply_modifier_shape_keys import unregister as unreg
    unreg()
