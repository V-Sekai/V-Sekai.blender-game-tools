from bpy.props import (BoolProperty)
from bpy.types import Scene


def register():

    Scene.faceit_weights_restorable = BoolProperty(
        default=False,
    )
    Scene.faceit_expressions_restorable = BoolProperty(
        default=False,
    )
    Scene.faceit_corrective_sk_restorable = BoolProperty(
        default=False,
    )


def unregister():
    del Scene.faceit_weights_restorable
    del Scene.faceit_expressions_restorable
    del Scene.faceit_corrective_sk_restorable
