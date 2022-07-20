"""OpenGL drawing code for the texture browser.

Requires Blender 2.80 or newer.
"""

import typing

import bgl
import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader

if bpy.app.background:
    shader = None
    texture_shader = None
else:
    shader = gpu.shader.from_builtin("2D_UNIFORM_COLOR")
    texture_shader = gpu.shader.from_builtin("2D_IMAGE")

Float2 = typing.Tuple[float, float]
Float3 = typing.Tuple[float, float, float]
Float4 = typing.Tuple[float, float, float, float]


def text(
    pos2d: Float2,
    display_text: typing.Union[str, typing.List[str]],
    rgba: Float4 = (1.0, 1.0, 1.0, 1.0),
    fsize=12,
    align="L",
):
    """Draw text with the top-left corner at 'pos2d'."""

    dpi = bpy.context.preferences.system.dpi
    gap = 12
    x_pos, y_pos = pos2d
    font_id = 0
    blf.size(font_id, fsize, dpi)

    # Compute the height of one line.
    mwidth, mheight = blf.dimensions(font_id, "Tp")  # Use high and low letters.
    mheight *= 1.5

    # Split text into lines.
    if isinstance(display_text, str):
        mylines = display_text.split("\n")
    else:
        mylines = display_text
    maxwidth = 0
    maxheight = len(mylines) * mheight

    for idx, line in enumerate(mylines):
        text_width, text_height = blf.dimensions(font_id, line)
        if align == "C":
            newx = x_pos - text_width / 2
        elif align == "R":
            newx = x_pos - text_width - gap
        else:
            newx = x_pos

        # Draw
        blf.position(font_id, newx, y_pos - mheight * idx, 0)
        blf.color(font_id, rgba[0], rgba[1], rgba[2], rgba[3])
        blf.draw(font_id, " " + line)

        # saves max width
        if maxwidth < text_width:
            maxwidth = text_width

    return maxwidth, maxheight


def aabox(v1: Float2, v2: Float2, rgba: Float4):
    """Draw an axis-aligned box."""
    coords = [
        (v1[0], v1[1]),
        (v1[0], v2[1]),
        (v2[0], v2[1]),
        (v2[0], v1[1]),
    ]
    shader.bind()
    shader.uniform_float("color", rgba)

    batch = batch_for_shader(shader, "TRI_FAN", {"pos": coords})
    batch.draw(shader)


def aabox_with_texture(v1: Float2, v2: Float2):
    """Draw an axis-aligned box with a texture."""
    coords = [
        (v1[0], v1[1]),
        (v1[0], v2[1]),
        (v2[0], v2[1]),
        (v2[0], v1[1]),
    ]
    texture_shader.bind()
    texture_shader.uniform_int("image", 0)

    batch = batch_for_shader(
        texture_shader,
        "TRI_FAN",
        {
            "pos": coords,
            "texCoord": ((0, 0), (0, 1), (1, 1), (1, 0)),
        },
    )
    batch.draw(texture_shader)


def bind_texture(texture: bpy.types.Image):
    """Bind a Blender image to a GL texture slot."""
    bgl.glActiveTexture(bgl.GL_TEXTURE0)
    bgl.glBindTexture(bgl.GL_TEXTURE_2D, texture.bindcode)


def load_texture(texture: bpy.types.Image) -> int:
    """Load the texture, return OpenGL error code."""
    return texture.gl_load()
