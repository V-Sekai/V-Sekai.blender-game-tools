

import bpy
from bpy.types import Scene
from bpy.props import BoolProperty

# --------------- CLASSES --------------------
# | - Property Groups (Collection-/PointerProperty)
# ----------------------------------------------


# --------------- FUNCTIONS --------------------
# | - Update/Getter/Setter
# ----------------------------------------------


# --------------- REGISTER/UNREGISTER --------------------
# |
# --------------------------------------------------------


def register():

    Scene.faceit_shapes_generated = BoolProperty(
        name='Generated Shape Keys',
        default=False,
    )


def unregister():
    del Scene.faceit_shapes_generated
