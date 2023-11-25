'''
Copyright (C) 2021-2023 Orange Turbine
https://orangeturbine.com
orangeturbine@cgcookie.com

This file is part of UV Flow.

The code for UV Flow is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <https://www.gnu.org/licenses>.
'''

bl_info = {
  "name": "UV Flow",
  "author": "Orange Turbine, Juan Fran Matheu, Jonathan Lampel",
  "version": (0, 9, 8),
  "blender": (3, 6, 5),
  "location": "3D View > Mesh Edit Mode > Toolbar",
  "description": "Tools for unwrapping meshes at warp speed",
  "warning": "Beta",
  "wiki_url": "https://cgcookie.github.io/uvflow",
  "category": "3D View",
}

import bpy

if bpy.app.background:
  # Fix #25. Skip registering if Blender is in background.
  def register():
    pass
  def unregister():
    pass
else:
  from uvflow.addon_utils import init_modules 
  init_modules()

  def register():
      from uvflow.addon_utils import register_modules
      register_modules()

  def unregister():
      from uvflow.addon_utils import unregister_modules
      unregister_modules()
