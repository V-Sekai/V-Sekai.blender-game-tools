# ##### BEGIN GPL LICENSE BLOCK #####

#Copyright (C) 2021 Alberto Gonzalez & Vjaceslav Tissen
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# ##### END GPL LICENSE BLOCK #####
# 
import bmesh
import bpy
import os
import subprocess
import sys

from bpy.types import Operator

import bgl
import blf

import bmesh

import gpu
from gpu_extras.batch import batch_for_shader

import mathutils
import math

from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_line_plane

from bpy_extras.view3d_utils import (
    region_2d_to_vector_3d,
    region_2d_to_origin_3d
)

from bpy_extras.view3d_utils import region_2d_to_location_3d

from bgl import (GL_ALWAYS, GL_BLEND, glDepthFunc, glDisable, glEnable, 
                glPointSize)

from gpu.types import GPUShader
from gpu_extras.batch import batch_for_shader

import time
from struct import pack

from mathutils import geometry
from bpy_extras.io_utils import unpack_list
import fnmatch

from mathutils import Vector
from bpy_extras import view3d_utils

from math import sqrt

from mathutils.kdtree import KDTree

import numpy as np
import random

from bpy.props import IntProperty, FloatProperty


def setup_swmesh(self,context):
    bpy.ops.object.editmode_toggle()
    bpy.ops.transform.resize(value=(1,1,1), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=6.11591, use_proportional_connected=False, use_proportional_projected=False)
    bpy.ops.object.editmode_toggle()

    bpy.ops.mesh.primitive_plane_add(enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(0.05, 0.05, 0.05))

    bpy.ops.transform.resize(value=(1,1,1), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=6.11591, use_proportional_connected=False, use_proportional_projected=False)
    bpy.ops.object.shade_smooth()

    bpy.context.active_object.show_in_front = True
    bpy.ops.transform.rotate(value=1.5708, orient_axis='X', orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', constraint_axis=(True, False, False), mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=6.11591, use_proportional_connected=False, use_proportional_projected=False)

    plane = bpy.context.active_object
    plane.name = "SimplyWrapMesh"
    
    strip = bpy.data.objects['SimplyWrapMesh']
    curve = bpy.data.objects['simply_curve']
    if bpy.context.scene.shrink_curve == True:
        curvewrap = curve.modifiers.new(name="CurveWrap", type='SHRINKWRAP')
        curvewrap.target = self.obj
        curvewrap.wrap_mode = 'ABOVE_SURFACE'
        curvewrap.use_apply_on_spline = True
    bpy.ops.object.shade_smooth()

    curveSub = curve.modifiers.new(name="CurveSubdivision", type='SUBSURF')

    stripsize = strip.modifiers.new(name="StripSize", type='SMOOTH')
    
    stripsize.factor = 3
    
    simplyarray = strip.modifiers.new(name="SimplyArray", type='ARRAY')
    simplyarray.curve = bpy.data.objects["simply_curve"]
    simplyarray.fit_type = 'FIT_CURVE'
    simplyarray.use_merge_vertices = True
    simplyarray.show_on_cage = True
    
    simplycurve = strip.modifiers.new(name="SimplyCurve", type='CURVE')
    simplycurve.object = bpy.data.objects["simply_curve"]
    simplycurve.show_on_cage = True
    
    simplywrapcloth = strip.modifiers.new(name="SimplyWrapCloth", type='CLOTH')
    simplywrapcloth.show_viewport = False
    simplywrapcloth.collision_settings.distance_min = 0.001

    simplywrapcloth.collision_settings.use_self_collision = True
    simplywrapcloth.collision_settings.self_distance_min = 0.001

    simplywrapcloth.settings.time_scale = 0.1
    simplywrapcloth.settings.quality = 20
    
    simplywrapcloth.collision_settings.collision_quality = 20
    simplywrapcloth.collision_settings.use_self_collision = True
    simplywrapcloth.collision_settings.self_friction = 50.0

    simplywrapcloth.settings.shrink_min = -0.2
    bpy.context.object.modifiers["SimplyWrapCloth"].settings.keyframe_insert(data_path='shrink_min', frame=0)

    simplywrapcloth.settings.shrink_min = 0.1
    bpy.context.object.modifiers["SimplyWrapCloth"].settings.keyframe_insert(data_path='shrink_min', frame=10)

    simplywrapcloth.settings.shrink_min = 0.1
    bpy.context.object.modifiers["SimplyWrapCloth"].settings.keyframe_insert(data_path='shrink_min', frame=20)

    simplywrapcloth.settings.shrink_min = 0.4
    bpy.context.object.modifiers["SimplyWrapCloth"].settings.keyframe_insert(data_path='shrink_min', frame=30)

    #SURFACE OFFSET
    simplywrapcloth.collision_settings.distance_min = 0.015
    
    #SELF COLLISION MINUMUM
    simplywrapcloth.collision_settings.self_distance_min = 0.001

    simplywrapcloth.settings.vertex_group_mass = "PinWrap"


    bpy.ops.object.modifier_add(type='SOLIDIFY')
    bpy.context.active_object.modifiers["Solidify"].name = "SimplyWrapSolidify"
    bpy.context.active_object.modifiers["SimplyWrapSolidify"].offset = 0
    bpy.context.object.modifiers["SimplyWrapSolidify"].show_in_editmode = False

    bpy.ops.object.modifier_add(type='SMOOTH')
    bpy.context.active_object.modifiers["Smooth"].name = "SimplyWrapSmooth"


    bpy.ops.object.modifier_add(type='SUBSURF')
    bpy.context.active_object.modifiers["Subdivision"].name = "SimplyWrapSubdivision"
    bpy.context.active_object.modifiers["SimplyWrapSubdivision"].show_in_editmode = False
    bpy.context.active_object.modifiers["SimplyWrapSubdivision"].show_viewport = False