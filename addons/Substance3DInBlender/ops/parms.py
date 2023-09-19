"""
Copyright (C) 2022 Adobe.
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# file: ops/parms.py
# brief: Parameter Operators
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy
from random import randint

from ..utils import SUBSTANCE_Utils
from ..common import PARMS_MAX_RANDOM_SEED, Code_ParmIdentifier


class SUBSTANCE_OT_RandomizeSeed(bpy.types.Operator):
    bl_idname = 'substance.randomize_seed'
    bl_label = 'Randomize'
    bl_description = 'Generate a new random value for the current SBSAR randomseed parameter'

    def execute(self, context):

        _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)
        _parms = getattr(context.scene, _selected_graph.parms_class_name)
        _value = randint(0, PARMS_MAX_RANDOM_SEED)
        setattr(_parms, Code_ParmIdentifier.randomseed.value, _value)

        return {'FINISHED'}
