# SPDX-License-Identifier: GPL-2.0-or-later

from ..dom import Node, root
from bl_xr import xr_session
from bl_xr.consts import WHITE, BLACK

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
import traceback
from mathutils import Matrix

from .shaders import TEXTURE_RECTANGLE_SHADER, FLAT_COLOR_RECTANGLE_SHADER
from ..utils import log

draw_handle = None

texture_rect_shader = None
flat_color_rect_shader = None
flat_color_misc_shader = None

EDGE_SOFTNESS = 0.001

if not bpy.app.background:
    texture_rect_shader = gpu.types.GPUShader(TEXTURE_RECTANGLE_SHADER["vertex"], TEXTURE_RECTANGLE_SHADER["fragment"])
    flat_color_rect_shader = gpu.types.GPUShader(
        FLAT_COLOR_RECTANGLE_SHADER["vertex"], FLAT_COLOR_RECTANGLE_SHADER["fragment"]
    )
    flat_color_misc_shader = "UNIFORM_COLOR" if bpy.app.version >= (4, 0, 0) else "3D_UNIFORM_COLOR"
    flat_color_misc_shader = gpu.shader.from_builtin(flat_color_misc_shader)

even_frame = True


def draw_frame(context):
    global even_frame

    bpy.context = context

    if even_frame:
        update(root)

    if not bpy.app.background:
        draw(root)

    even_frame = not even_frame


def update(node: Node):
    if not node.get_computed_style("visible", True):
        return

    try:
        if hasattr(node, "update") and callable(node.update):
            node.update()

        for child in node.child_nodes:
            update(child)
    except:
        log.error(traceback.format_exc())


def draw(node: Node):
    if not node.get_computed_style("visible", True):
        return

    try:
        with gpu.matrix.push_pop():
            matrix_local = node.matrix_local
            if node.get_computed_style("fixed_scale", False):
                loc, rot, scale = matrix_local.decompose()
                matrix_local = Matrix.LocRotScale(loc, rot, scale * xr_session.viewer_scale)

            gpu.matrix.multiply_matrix(matrix_local)

            if node.get_computed_style("depth_test", True):
                gpu.state.depth_test_set("LESS_EQUAL")
                gpu.state.depth_mask_set(True)
            else:
                gpu.state.depth_test_set("NONE")
                gpu.state.depth_mask_set(False)

            gpu.state.blend_set("ALPHA")

            draw_node(node)

            for child in node.child_nodes:
                draw(child)
    except Exception as e:
        log.error(traceback.format_exc())


def draw_node(node: Node):
    if hasattr(node, "draw") and callable(node.draw):
        node.draw()
    elif hasattr(node, "mesh"):
        shader = flat_color_misc_shader
        shader.bind()
        shader.uniform_float(
            "color", node.get_computed_style("color", WHITE)[:3] + (node.get_computed_style("opacity", 1),)
        )

        if not hasattr(node, "_batch"):
            if len(node.mesh.faces) > 0:
                node._batch = batch_for_shader(shader, "TRIS", {"pos": node.mesh.vertices}, indices=node.mesh.faces)
            else:
                node._batch = batch_for_shader(shader, "LINES", {"pos": node.mesh.vertices})

        node._batch.draw(shader)
    else:
        background = node.get_computed_style("background")
        border = node.get_computed_style("border")
        border_radius = node.get_computed_style("border_radius")

        if not background and not border and not border_radius and not hasattr(node, "_texture"):
            return

        shader = texture_rect_shader if hasattr(node, "_texture") else flat_color_rect_shader
        shader.bind()

        if hasattr(node, "_texture"):
            shader.uniform_sampler("image", node._texture)

        if background:
            shader.uniform_float("fillColor", background[:3] + (node.get_computed_style("opacity", 1),))
        else:
            shader.uniform_float("fillColor", (0.0, 0.0, 0.0, 0.0))

        if border:
            if isinstance(border, tuple) and len(border) == 2:
                border_width, border_color = border
            elif isinstance(border, tuple):
                border_width = 0.01
                border_color = border
            else:
                border_width = border
                border_color = BLACK

            shader.uniform_float("borderWidth", border_width)
            shader.uniform_float("borderColor", border_color)
        else:
            shader.uniform_float("borderWidth", 0)
            shader.uniform_float("borderColor", (0.0, 0.0, 0.0, 0.0))

        if border_radius:
            shader.uniform_float("borderRadius", border_radius)
        else:
            shader.uniform_float("borderRadius", 0)

        bounds = node.bounds_local.size
        W, H = bounds.x, bounds.y

        shader.uniform_float("edgeSoftness", EDGE_SOFTNESS)
        shader.uniform_float("size", (W - 2 * EDGE_SOFTNESS, H - 2 * EDGE_SOFTNESS))
        shader.uniform_float("location", (W * 0.5, H * 0.5))

        if not hasattr(node, "_batch"):
            if shader == texture_rect_shader:
                # this will be a quad, with the pos
                node._batch = batch_for_shader(
                    shader,
                    "TRIS",
                    {
                        "position": [(0, 0, 0), (0, H, 0), (W, H, 0), (W, H, 0), (W, 0, 0), (0, 0, 0)],
                        "texCoord": ((0, 0), (0, 1), (1, 1), (1, 1), (1, 0), (0, 0)),
                    },
                )
            else:
                node._batch = batch_for_shader(
                    shader,
                    "TRIS",
                    {
                        "position": [(0, 0, 0), (0, H, 0), (W, H, 0), (W, H, 0), (W, 0, 0), (0, 0, 0)],
                    },
                    indices=[(0, 1, 2), (3, 4, 5)],
                )

        node._batch.draw(shader)


def on_draw_start(context):
    global draw_handle

    if draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handle, "XR")

    draw_handle = bpy.types.SpaceView3D.draw_handler_add(draw_frame, (context,), "XR", "POST_VIEW")

    # set the viewport shading, so that black strokes will show up
    area = next(area for area in bpy.context.screen.areas if area.type == "VIEW_3D")
    space = next(space for space in area.spaces if space.type == "VIEW_3D")
    space.shading.color_type = "OBJECT"
