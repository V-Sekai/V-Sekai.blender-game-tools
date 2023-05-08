

from bpy.props import BoolProperty
from bpy.types import Scene


def register():

    Scene.faceit_shapes_generated = BoolProperty(
        name='Generated Shape Keys',
        default=False,
    )


def unregister():
    del Scene.faceit_shapes_generated
