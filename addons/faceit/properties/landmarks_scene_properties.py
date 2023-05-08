from bpy.props import BoolProperty, IntProperty
from bpy.types import Scene, Object

from ..core.faceit_utils import set_lock_3d_view_rotations


def register():

    Scene.faceit_asymmetric = BoolProperty(
        name='Symmetry or no symmetry',
        description='Enable this if the Character Geometry is not symmetrical in X Axis. \
Use the manual Mirror tools instead of the Mirror modifier',
        default=False,
    )

    Scene.show_locator_empties = BoolProperty(
        name='locator empties active',
        default=False
    )


def unregister():
    del Scene.faceit_asymmetric
    del Scene.show_locator_empties
