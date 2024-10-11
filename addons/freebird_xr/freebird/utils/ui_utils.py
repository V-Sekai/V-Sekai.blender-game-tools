import bpy

from bl_xr import root
from bl_xr import Pose
from bl_xr.utils import (
    to_blender_axis_system,
    from_blender_axis_system,
    camera_position_to_matrix,
    matrix_to_camera_position,
)

from ..tools import enable_tool

from mathutils import Vector, Quaternion


def set_tool(tool_name):
    "Convenience function to enable the tool and set the default cursor size."

    tool_name = tool_name.lower()

    enable_tool(tool_name)
    set_default_cursor(tool_name)

    return True


def set_default_cursor(tool_name):
    cursor = root.q("#cursor_main")
    cursor.set_default_cursor(tool_name)

    return True


class DesktopViewport:
    @property
    def pose(self) -> Pose:
        return Pose(self.location, self.rotation)

    @pose.setter
    def pose(self, pose: Pose):
        self.rotation = pose.rotation
        self.location = pose.position

    @property
    def location(self) -> Vector:
        r3d = self.get_region_3d()
        return matrix_to_camera_position(r3d.view_matrix)

    @location.setter
    def location(self, location: Vector):
        r3d = self.get_region_3d()
        rot = r3d.view_rotation
        r3d.view_matrix = camera_position_to_matrix(location, rot)

    @property
    def rotation(self) -> Quaternion:
        r3d = self.get_region_3d()
        return to_blender_axis_system(r3d.view_rotation)

    @rotation.setter
    def rotation(self, rotation: Quaternion):
        r3d = self.get_region_3d()
        rotation = from_blender_axis_system(rotation)
        r3d.view_matrix = camera_position_to_matrix(self.location, rotation)

    def get_area(self) -> bpy.types.Area:
        return next(area for area in bpy.data.screens["Layout"].areas if area.type == "VIEW_3D")

    def get_space(self) -> bpy.types.SpaceView3D:
        area = self.get_area()
        return next(space for space in area.spaces if space.type == "VIEW_3D")

    def get_region(self) -> bpy.types.Region:
        area = self.get_area()
        return next(region for region in area.regions if region.type == "WINDOW")

    def get_region_3d(self) -> bpy.types.RegionView3D:
        space = self.get_space()
        return space.region_3d

    def temp_override(self, include_area=True):
        window = bpy.context.window_manager.windows[0]
        override = {
            "window": window,
            "screen": window.screen,
        }

        if include_area:
            override.update(
                {
                    "area": self.get_area(),
                    "space": self.get_space(),
                    "region": self.get_region(),
                }
            )
        return bpy.context.temp_override(**override)


desktop_viewport = DesktopViewport()
