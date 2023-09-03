''' Immediate Drawing functions. '''

import bpy
from typing import Tuple
from mathutils import Vector
import gpu
from gpu.types import GPUBatch, GPUShader
from gpu_extras.batch import batch_for_shader

from .shaders import SHADERS


# Useful types.
RGBA = Tuple[float, float, float, float]

SHADER_POLYLINE_UNIFORM_COLOR = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')


bat_cache = {}


def line_3d(coords: Tuple[Vector], line_thickness: float = 1.0, u_color: RGBA = (1, 0, 0, 1), cache_idname: str = None, cache_tag_redraw: bool = False):
    ''' coords points MUST be mathutils.Vector type. '''
    lines = []
    for a, b in zip(coords[:-1], coords[1:]):
        lines.append(a)
        lines.append(b)

    shader: GPUShader = SHADER_POLYLINE_UNIFORM_COLOR
    if cache_idname and not cache_tag_redraw and cache_idname in bat_cache:
        batch = bat_cache[cache_idname]
    else:
        batch: GPUBatch = batch_for_shader(
            shader, 'LINES', {"pos": lines}
        )

    region = bpy.context.region

    shader.bind()
    shader.uniform_float('lineWidth', line_thickness)
    shader.uniform_float('viewportSize', (region.width, region.height))
    shader.uniform_float('color', u_color)

    batch.draw(shader)


def line_dashed_3d(coords: Tuple[Vector], line_thickness: float = 1.0, u_color: RGBA = (1, 0, 0, 1), u_scale: float = 1.0, u_spacing: float = 0.2):
    ''' coords points MUST be mathutils.Vector type. '''
    line_lengths = [0]
    for a, b in zip(coords[:-1], coords[1:]):
        line_lengths.append(line_lengths[-1] + (a - b).length)

    shader: GPUShader = SHADERS.LINE_DASHED_3D()
    batch: GPUBatch = batch_for_shader(
        shader, 'LINES', {"position": coords, "lineLength": line_lengths}
    )

    shader.bind()
    matrix = bpy.context.region_data.perspective_matrix
    shader.uniform_float("u_ViewProjectionMatrix", matrix)
    shader.uniform_float("u_Color", u_color)
    shader.uniform_float("u_DashSize", u_scale)
    shader.uniform_float("u_Spacing", u_spacing)

    if line_thickness != 1.0:
        _line = gpu.state.line_width_get()
        gpu.state.line_width_set(line_thickness)
    batch.draw(shader)
    if line_thickness != 1.0:
        gpu.state.line_width_set(_line)


def line_dashed_2d(coords: Tuple[Vector], u_color: RGBA = (1, 0, 0, 1), u_scale: float = 1.0, u_spacing: float = 0.2):
    ''' coords points MUST be mathutils.Vector type. '''
    line_lengths = [0]
    for a, b in zip(coords[:-1], coords[1:]):
        line_lengths.append(line_lengths[-1] + (a - b).length)

    shader: GPUShader = SHADERS.LINE_DASHED_2D()
    batch: GPUBatch = batch_for_shader(
        shader, 'LINES', {"position": coords, "lineLength": line_lengths}
    )

    shader.bind()
    shader.uniform_float("u_Color", u_color)
    shader.uniform_float("u_DashSize", u_scale)
    shader.uniform_float("u_Spacing", u_spacing)
    
    batch.draw(shader)


def point_3d(coords: Tuple[Vector], point_size: float = 1.0, u_color: RGBA = (1, 0, 0, 1), u_color_outline: RGBA = None, u_outline_width: float = 1.0, cache_idname: str = None, cache_tag_redraw: bool = False):
    ''' Set u_color_outline (RGBA) or not depending if want to draw an outline or not. '''
    if len(coords) == 0:
        return

    if u_color_outline is not None:
        shader: GPUShader = SHADERS.POINT_OUTLINE_3D()
    else:
        shader: GPUShader = SHADERS.POINT_3D()

    if cache_idname and not cache_tag_redraw and cache_idname in bat_cache:
        batch = bat_cache[cache_idname]
    else:
        batch: GPUBatch = batch_for_shader(
            shader, 'POINTS', {"pos": coords}
        )

    shader.bind()
    shader.uniform_float("size", point_size)
    shader.uniform_float("color", u_color)
    if u_color_outline is not None:
        shader.uniform_float("outlineWidth", u_outline_width)
        shader.uniform_float("outlineColor", u_color)

    if point_size != 1.0:
        #gpu.state.program_point_size_set(True)
        gpu.state.point_size_set(point_size)
    batch.draw(shader)
    if point_size != 1.0:
        gpu.state.point_size_set(1.0)
        #gpu.state.program_point_size_set(False)
