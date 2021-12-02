from bpy.types import Scene
from bpy.props import BoolProperty, FloatProperty

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

    Scene.faceit_vertex_size = FloatProperty(
        name='vertex size',
        default=3
    )


def unregister():
    del Scene.faceit_asymmetric
    del Scene.show_locator_empties
    del Scene.faceit_vertex_size
