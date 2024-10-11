from bl_xr import xr_session, root
from bl_xr import Node, Mesh

import numpy as np
from math import log as math_log

from ..settings_manager import settings


class Gizmo3DGrid(Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.make_grid()

    def make_grid(self):
        line_count = settings["gizmo.3d_grid.line_count"]
        line_spacing = settings["gizmo.3d_grid.line_spacing"]

        span = int(line_count / 2) * line_spacing
        intervals = np.arange(-span, span + line_spacing, line_spacing)
        intervals = [float(i) for i in intervals]

        self.mesh = Mesh()

        for x in intervals:
            for y in intervals:
                for z in intervals:
                    self.mesh.vertices.append((x - 0.002, y, z))
                    self.mesh.vertices.append((x + 0.002, y, z))

                    self.mesh.vertices.append((x, y - 0.002, z))
                    self.mesh.vertices.append((x, y + 0.002, z))

                    self.mesh.vertices.append((x, y, z - 0.002))
                    self.mesh.vertices.append((x, y, z + 0.002))

    def update(self):
        s = round(math_log(xr_session.viewer_scale, 2))
        s = pow(2, s)

        line_spacing_world = settings["gizmo.3d_grid.line_spacing"] * s

        p = xr_session.controller_main_aim_position
        for i in range(3):
            p[i] = line_spacing_world * round(p[i] / line_spacing_world)

        self.position = p
        self.scale = s


gizmo_3d_grid = Gizmo3DGrid(id="3d_grid")


def enable_gizmo():
    root.append_child(gizmo_3d_grid)


def disable_gizmo():
    root.remove_child(gizmo_3d_grid)
