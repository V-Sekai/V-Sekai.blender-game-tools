# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****

import bpy
from . import auto_load
from bpy.props import IntProperty

bl_info = {
    'name': 'FACEIT',
    'author': 'Fynn Braren',
    'description': 'Semi-automatically generate IPhoneX Shape Keys - Performance Capture for ANY Character! ',
    'blender': (2, 80, 0),
    'version': (2, 0, 17),
    'location': 'View3D',
    'warning': '',
    'wiki_url': "https://faceit-doc.readthedocs.io/en/latest/",
    'tracker_url': "https://faceit-doc.readthedocs.io/en/latest/support/",
    'category': 'Animation'
}


auto_load.init()


class FaceitPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    web_links: bpy.props.BoolProperty(
        name='Show Web Links',
        description='Display Links to the Documentation in the Faceit UI',
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'web_links', icon='INFO')


def register():
    bpy.utils.register_class(FaceitPreferences)
    auto_load.register()

    def get_version(self):
        return bl_info['version'][0]

    bpy.types.Scene.faceit_version = IntProperty(
        name='Faceit Version',
        default=1,
        options=set(),
        get=get_version,
    )


def unregister():
    bpy.utils.unregister_class(FaceitPreferences)
    auto_load.unregister()
    bpy.types.Scene.faceit_version
