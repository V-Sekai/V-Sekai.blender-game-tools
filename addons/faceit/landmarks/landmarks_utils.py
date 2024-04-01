import bpy
from mathutils import Quaternion

from ..core.mesh_utils import get_object_center


def is_landmarks_active(lm_obj):
    if lm_obj is None:
        return False
    return not (lm_obj.hide_viewport or lm_obj.hide_get())


def check_is_quad_view(area):
    if area.spaces.active.region_quadviews is not None:
        return len(area.spaces.active.region_quadviews) != 0


def check_if_area_is_active(area, x, y):
    if (x >= area.x and y >= area.y and x < area.width + area.x and y < area.height + area.y):
        return True


def set_front_view(region_3d, lock_rotation=True, view_selected=True):

    # for window in context.window_manager.windows:
    #     screen = window.screen
    #     for area in screen.areas:
    #         if area.type == 'VIEW_3D':
    #             r3d = area.spaces[0].region_3d
    # if region_3d.view_rotation != Quaternion((0.7071067690849304, 0.7071067690849304, -0.0, -0.0)):

    if view_selected:
        view_center = get_object_center(bpy.context.object)
        region_3d.view_location = view_center

    region_3d.view_rotation = Quaternion((0.7071067690849304, 0.7071067690849304, -0.0, -0.0))
    region_3d.view_perspective = 'ORTHO'
    region_3d.lock_rotation = lock_rotation


def unlock_3d_view():
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.lock_rotation = False
