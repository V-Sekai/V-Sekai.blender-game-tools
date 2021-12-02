

from bpy.types import Scene
from bpy.props import FloatProperty

# --------------- CLASSES --------------------
# | - Property Groups (Collection-/PointerProperty)
# ----------------------------------------------


# --------------- FUNCTIONS --------------------
# | - Update/Getter/Setter
# ----------------------------------------------

def update_shape_key_slider_min(self, context):
    '''Set the minimum range always below max range'''
    min = self.faceit_shape_key_slider_min
    max = self.faceit_shape_key_slider_max
    if min >= max:
        self.faceit_shape_key_slider_min = max-.001


def update_shape_key_slider_max(self, context):
    '''Set the maximum range always above minimum range'''
    min = self.faceit_shape_key_slider_min
    max = self.faceit_shape_key_slider_max
    if max <= min:
        self.faceit_shape_key_slider_max = min+.001

# --------------- REGISTER/UNREGISTER --------------------
# |
# --------------------------------------------------------


def register():

    Scene.faceit_shape_key_slider_min = FloatProperty(
        name='Range Min',
        description='Slider miminum value for all shape keys.',
        default=0,
        min=-10,
        max=10,
        precision=3,
        update=update_shape_key_slider_min,
    )

    Scene.faceit_shape_key_slider_max = FloatProperty(
        name='Max',
        description='Slider maximum value for all shape keys.',
        default=1,
        min=-10,
        max=10,
        precision=3,
        update=update_shape_key_slider_max,
    )


def unregister():
    del Scene.faceit_shape_key_slider_min
    del Scene.faceit_shape_key_slider_max
