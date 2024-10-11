# SPDX-License-Identifier: GPL-2.0-or-later

from mathutils import Vector, Quaternion

# directions
VEC_RIGHT = Vector((1, 0, 0)).freeze()
VEC_FORWARD = Vector((0, 1, 0)).freeze()
VEC_UP = Vector((0, 0, 1)).freeze()
VEC_ZERO = Vector().freeze()
VEC_ONE = Vector((1, 1, 1)).freeze()
QUAT_IDENTITY = Quaternion().freeze()

# colors (rgba)
BLACK = (0, 0, 0, 1)
WHITE = (1, 1, 1, 1)
RED = (1, 0, 0, 1)
GREEN = (0, 1, 0, 1)
GREEN_MILD = (50.0 / 255, 168.0 / 255, 82.0 / 255, 1)
BLUE = (0, 0, 1, 1)
YELLOW = (1, 1, 0, 1)
ORANGE = (1, 0.5, 0, 1)
BLUE_MS = (47.0 / 255, 132.0 / 255, 228.0 / 255, 1)
RED_MILD = (237.0 / 255, 78.0 / 255, 81.0 / 255, 1)

# numbers
EPSILON = 0.00001
