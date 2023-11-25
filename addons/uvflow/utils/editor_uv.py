import bpy
from bpy.types import Window, Area, Context, Mesh, SpaceImageEditor
from mathutils import Vector
import bmesh
from bmesh.types import BMFace, BMLoop, BMLoopUV, BMVert, BMEdge, BMesh

from .mode import CM_ModeToggle
from uvflow.addon_utils._bcy import CyBlStruct
from uvflow.operators.op_straighten_uv_island import UVIslandData
from .view2d import get_editor_region_coord, get_editor_zoom



class CM_UseUVSync:
    def __init__(self, context: Context, state: bool = True) -> None:
        self.prev_use_sync = context.scene.tool_settings.use_uv_select_sync
        self.ts = context.scene.tool_settings
        self.use_sync = state

    def __enter__(self):
        if self.prev_use_sync == self.use_sync:
            return
        self.ts.use_uv_select_sync = self.use_sync

    def __exit__(self, exc_type, exc_value, trace) -> None:
        if self.prev_use_sync == self.use_sync:
            return
        self.ts.use_uv_select_sync = self.prev_use_sync


def get_uv_editor(wnd: Window) -> Area or None:
    for _area in wnd.screen.areas:
        if _area.type == 'IMAGE_EDITOR' and _area.ui_type == 'UV':
            return _area
    return None


def get_space_image_size(space_image: SpaceImageEditor) -> tuple[int, int]:
    if space_image.image is not None:
        return space_image.image.size
    # SIZE FALLBACK. (Is the same as Blender internal default size)
    return (256, 256)


def select_uvs_from_view3d_selection(context: Context) -> None:
    if context.mode != 'EDIT_MESH' or get_uv_editor(context.window) is None:
        return

    with CM_ModeToggle(context, 'EDIT'):
        bm: BMesh = bmesh.from_edit_mesh(context.active_object.data)
        uv_layer = bm.loops.layers.uv.active

        for face in bm.faces:
            if not face.select:
                continue
            for loop in face.loops:
                loop[uv_layer].select = True


def frame_select_uvs_from_view3d_selection(context: Context, select_uvs: bool = False) -> None:
    area = get_uv_editor(context.window)
    if area is None:
        return

    for region in area.regions:
        if region.type == 'WINDOW':
            break

    mesh: Mesh = context.active_object.data

    # This works BUT with repeated actions (spam-like actions) will crash Blender.
    # with context.temp_override(window=context.window, area=area, region=region, object=context.active_object, mesh=mesh): #, CM_UseUVSync(context, True):
    #     bpy.ops.uv.select_all(False, action='SELECT')
    #     bpy.ops.image.view_selected(False)


    with CM_ModeToggle(context, 'EDIT'):
        # Get UV Bounds.
        bm: BMesh = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.active
        bm_faces: list[BMFace] = bm.faces

        min_p = Vector((float('inf'), float('inf')))
        max_p = Vector((0, 0))

        for face in bm_faces:
            if not face.select:
                continue
            for loop in face.loops:
                looo_uv = loop[uv_layer]
                if select_uvs:
                    looo_uv.select = True
                x, y = looo_uv.uv
                min_p.x = min(min_p.x, x)
                max_p.x = max(max_p.x, x)
                min_p.y = min(min_p.y, y)
                max_p.y = max(max_p.y, y)

        bm.free()
        del bm

        # Add some margin.
        scale = 1.4

        bound_size_x = max_p.x - min_p.x
        bound_size_y = max_p.y - min_p.y

        cent_x = (min_p.x + max_p.x) / 2.0
        cent_y = (min_p.y + max_p.y) / 2.0

        size_x_half = bound_size_x * (scale * 0.5)
        size_y_half = bound_size_y * (scale * 0.5)

        min_p.x = cent_x - size_x_half
        min_p.y = cent_y - size_y_half
        max_p.x = cent_x + size_x_half
        max_p.y = cent_y + size_y_half

        # Set view to match the bounds.
        space_uv_image = area.spaces[0]
        image_size = Vector(get_space_image_size(space_uv_image))
        image_aspect_ratio = image_size[1] / image_size[0]
        image_size *= Vector((image_aspect_ratio, image_aspect_ratio))

        # Update bound size.
        bound_size_x = max_p.x - min_p.x
        bound_size_y = max_p.y - min_p.y

        # Magic.
        cy_space_image = CyBlStruct.UI_SPACE_IMAGE(space_uv_image)

        # print(cy_space_image.xof, '-->', round((cent_x - 0.5) * image_size[0], 4))
        # print(cy_space_image.yof, '-->', round((cent_y - 0.5) * image_size[1], 4))

        # Adjust the offset.
        cy_space_image.xof = round((cent_x - 0.5) * image_size[0], 4)
        cy_space_image.yof = round((cent_y - 0.5) * image_size[1], 4)

        # Then, we adjust the zoom factor.
        size_xy = (
            region.width / (bound_size_x * image_size[0]),
            region.height / (bound_size_y * image_size[1])
        )
        zoom_size = max(min(size_xy), 100)

        # print(cy_space_image.zoom, '-->', zoom_size)

        if zoom_size < 0.1 or zoom_size > 4.0:
            pass
        else:
            cy_space_image.zoom = zoom_size

        del cy_space_image

    region.tag_redraw()
