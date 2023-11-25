from bpy.types import Context, Region
from mathutils import Vector


def get_editor_zoom(region: Region) -> float:
    view2d = region.view2d
    region_height = region.height
    view_height = view2d.region_to_view(0, region_height)[1] - view2d.region_to_view(0, 0)[1]
    if view_height == 0:
        return 1
    return region_height / view_height


def get_editor_region_coord(region: Region, view_co: Vector, clip: bool = False) -> Vector:
    return Vector(region.view2d.view_to_region(*view_co, clip=clip))


def get_editor_view_coord(region: Region, region_point: Vector) -> Vector:
    return Vector(region.view2d.region_to_view(*region_point))
