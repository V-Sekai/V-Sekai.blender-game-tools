from bpy.props import BoolProperty, IntProperty
from bpy.types import Scene, Object

def register():

    Scene.faceit_asymmetric = BoolProperty(
        name='Symmetry or no symmetry',
        description='Enable this if the Character Geometry is not symmetrical in X Axis. \
Use the manual Mirror tools instead of the Mirror modifier',
        default=False,
    )


def unregister():
    del Scene.faceit_asymmetric
