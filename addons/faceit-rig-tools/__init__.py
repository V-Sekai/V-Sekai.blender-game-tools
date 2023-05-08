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
from bpy.props import *
from bpy.types import PropertyGroup, Object
from addon_utils import check

bl_info = {
    'name': 'FACEIT Rig Tools',
    'author': 'Fynn Braren',
    'description': 'Allows Animators to work with the Faceit Control Rig (No UI).',
    'blender': (2, 80, 0),
    'version': (1, 0, 1),
    'location': 'View3D',
    'warning': 'Do not install if the Faceit add-on is already installed.',
    'wiki_url': "https://faceit-doc.readthedocs.io/en/latest/",
    'tracker_url': "https://faceit-doc.readthedocs.io/en/latest/support/",
    'category': 'Animation'
}


class TargetShapes(PropertyGroup):
    name: StringProperty(
        name='Target Shape',
        description='The Target Shape',
        default='---',
    )


class ControlRigShapes(PropertyGroup):
    name: StringProperty(
        name='Expression Name',
        description='(Source Shape)',
        options=set(),
    )
    amplify: FloatProperty(
        name='Amplify Value',
        default=1.0,
        description='Use the Amplify Value to increasing or decreasing the motion of this expression.',
        soft_min=0.0,
        soft_max=10.0,
    )
    if bpy.app.version >= (2, 90, 0):
        amplify: FloatProperty(
            name='Amplify Value',
            default=1.0,
            description='Use the Amplify Value to multiply all animation values by a factor. Increase Shape Key ranges to aninate beyond the range [0,1]',
            soft_min=0.0,
            soft_max=10.0,
            override={'LIBRARY_OVERRIDABLE'},
        )
    else:
        amplify: FloatProperty(
            name='Amplify Value',
            default=1.0,
            description='Use the Amplify Value to multiply all animation values by a factor. Increase Shape Key ranges to aninate beyond the range [0,1]',
            soft_min=0.0,
            soft_max=10.0,
        )


classes = [ControlRigShapes]


def register():
    if check('faceit')[0] is True:
        return
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    Object.faceit_crig_targets = CollectionProperty(
        name='Control Rig Target Expressions',
        type=ControlRigShapes,
    )


def unregister():
    if check('faceit')[0] is True:
        return
    from bpy.utils import unregister_class

    for cls in classes:
        try:
            unregister_class(cls)
        except:
            pass
    try:
        del Object.faceit_crig_targets
    except:
        pass
