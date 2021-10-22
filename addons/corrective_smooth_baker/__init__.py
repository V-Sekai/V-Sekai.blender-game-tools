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

bl_info = {
    "name": "Corrective Smooth Baker",
    "author": "mesh online / Modified (https://github.com/fire)",
    "version": (3, 3, 0),
    "blender": (2, 80, 0),
    "location": "View3D > UI > Skeleton Corrective Smooth Baker",
    "description": "Skeleton Corrective Smooth Baker",
    "warning": "",
    "wiki_url": "",
    "category": "Object",
    }


if "bpy" in locals():
    import importlib
    importlib.reload(corrective_smooth_baker)


def register():
    from .corrective_smooth_baker import register_corrective_smooth_baker
    register_corrective_smooth_baker()


def unregister():
    from .corrective_smooth_baker import unregister_corrective_smooth_baker
    unregister_corrective_smooth_baker()
