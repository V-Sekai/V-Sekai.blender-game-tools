# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name" : "Perspective Plotter",
    "author" : "Mark Kingsnorth",
    "description" : "",
    "blender" : (2, 80, 0),
    "version" : (1, 0, 4),
    "location" : "",
    "warning" : "",
    "category" : "3D View",
    "doc_url": "https://perspective-plotter.readthedocs.io/",
}
import bpy

from . import property, ui, operators, preferences, keymaps, util
from bpy.app.handlers import persistent

@persistent
def load_handler(dummy):
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA':
            obj.perspective_plotter.running_uuid = ''

def register():
    
    preferences.register()
    property.register()
    ui.register()
    operators.register()
    keymaps.register_keymap()

    bpy.app.handlers.load_post.append(load_handler)


def unregister():

    bpy.app.handlers.load_post.remove(load_handler)

    keymaps.unregister_keymap()
    operators.unregister()
    ui.unregister()
    property.unregister()
    preferences.unregister()


