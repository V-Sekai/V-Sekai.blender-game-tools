import bpy
from bpy.types import Mesh
from mathutils import Vector, kdtree
import bmesh
from bmesh.types import BMVert, BMEdge, BMLoop, BMLoopUV, BMesh, BMFace
from bpy.props import EnumProperty

from dataclasses import dataclass
from collections import defaultdict
from math import pi

from uvflow.addon_utils.types.math import BBOX_2
from uvflow.utils.math import angle_signed, direction, angle_between, distance_between
from uvflow.addon_utils import Register


def calculate_distance_uv(loop_uv_1: BMLoopUV, loop_uv_2: BMLoopUV):
    # Calculate the distance between two UV loops.
    return (loop_uv_1.uv - loop_uv_2.uv).length_squared


# Function to find the shortest path using Dijkstra's algorithm
def find_shortest_path(filter_bverts: list['BoundaryVert'], start_bvert: 'BoundaryVert', end_bvert: 'BoundaryVert') -> list['BoundaryVert']:
    filter_vert_indices = {bvert.vert_index for bvert in filter_bverts}

    # Create a dictionary to keep track of distances
    distances = {}
    for f_bvert in filter_bverts:
        distances[f_bvert] = float('inf')
    distances[start_bvert] = 0

    # Create a dictionary to keep track of previous vertices in the path
    previous_vertices = {}

    # Create a priority queue for vertices to explore
    priority_queue = [(0, start_bvert)]

    def get_bverts_by_index(_vert_index: int) -> list[BoundaryVert]:
        return [_bvert for _bvert in filter_bverts if _bvert.vert_index == _vert_index]

    while priority_queue:
        current_distance, current_bvert = priority_queue.pop(0)

        if current_distance > distances[current_bvert]:
            continue

        for neighbor_edge in current_bvert.link_edges:
            neighbor_vertex = neighbor_edge.other_vert(current_bvert.vert)

            if neighbor_vertex.index not in filter_vert_indices:
                continue

            cand_bvert_list = get_bverts_by_index(neighbor_vertex.index)

            closest_bvert = None
            min_distance = float('inf')
            for cand_bvert in cand_bvert_list:
                cand_distance = calculate_distance_uv(current_bvert, cand_bvert)
                if cand_distance < min_distance:
                    min_distance = cand_distance
                    closest_bvert = cand_bvert

            if closest_bvert is None:
                continue

            n_bvert = closest_bvert

            # weight = neighbor.calc_length()
            weight = calculate_distance_uv(current_bvert, n_bvert)
            distance = distances[current_bvert] + weight

            if distance < distances[n_bvert]:
                distances[n_bvert] = distance
                previous_vertices[n_bvert] = current_bvert
                priority_queue.append((distance, n_bvert))

    # Reconstruct the path
    path: list[BoundaryVert] = []
    current_vertex = end_bvert
    while current_vertex in previous_vertices:
        path.insert(0, current_vertex)
        current_vertex = previous_vertices[current_vertex]
    path.insert(0, end_bvert)

    if path[0].loop_index == path[-1].loop_index:
        path[0] = start_bvert
        path[-1] = end_bvert
    return path


def walk_from_vert_to_vert(bvert_A: int, bvert_B: int, select: list['BoundaryVert']) -> list['BoundaryVert']:
    return find_shortest_path(select, bvert_A, bvert_B)


@dataclass
class BoundaryVert:
    loop: BMLoop
    loop_uv: BMLoopUV

    def __hash__(self) -> int:
        return hash(self.loop) + hash(self.loop_uv)

    @property
    def vert(self) -> BMVert:
        return self.loop.vert

    @property
    def edge(self) -> BMEdge:
        return self.loop.edge

    @property
    def face(self) -> BMFace:
        return self.loop.face

    @property
    def loop_index(self) -> int:
        return self.loop.index

    @property
    def vert_index(self) -> int:
        return self.vert.index

    @property
    def link_edges(self) -> list[BMEdge]:
        return self.vert.link_edges

    @property
    def uv(self) -> Vector:
        return self.loop_uv.uv


@dataclass
class UVPrim(BoundaryVert):
    is_vert_boundary: bool = False
    is_edge_boundary: bool = False

    @property
    def is_boundary(self) -> bool:
        return self.is_vert_boundary or self.is_edge_boundary

    def __hash__(self) -> int:
        return hash(self.loop) + hash(self.loop_uv) + hash(self.is_vert_boundary) + hash(self.is_edge_boundary)

    @property
    def uv(self) -> Vector:
        return Vector(self.loop_uv.uv)

    @uv.setter
    def uv(self, uv: Vector) -> None:
        self.loop_uv.uv = uv

    @property
    def pin_uv(self) -> bool:
        return self.loop_uv.pin_uv

    @pin_uv.setter
    def pin_uv(self, pin_uv: bool) -> None:
        self.loop_uv.pin_uv = pin_uv


class UVIslandData:

    def __enter__(self) -> 'UVIslandData':
        mesh = self.mesh
        self.bm = bmesh.from_edit_mesh(mesh)
        self.active_uv_layer = self.bm.loops.layers.uv.active

        self.bm_loops: list[BMLoop] = [l for f in self.bm.faces for l in f.loops]
        self.calc_boundaries(pin_boundaries=False)

        return self

    def __exit__(self, exc_type, exc_value, trace) -> None:
        if hasattr(self, 'uv_prim'):
            for uvp in self.uv_prim.values():
                uvp.loop_uv.select = True
            del self.uv_prim
            del self.uvp_per_uv_coord
        self.bm.free()
        del self.bm
        if hasattr(self, 'boundary_verts'):
            del self.boundary_verts
        if hasattr(self, 'bbox'):
            del self.bbox
        if hasattr(self, 'bm_loops'):
            del self.bm_loops

    def __init__(self, mesh: Mesh) -> None:
        ''' UVIsland should be selected in UV Editor. '''
        self.mesh = mesh


    def pin_boundaries(self, enable: bool = True):
        if not hasattr(self, 'boundary_verts'):
            self.calc_boundaries(pin_boundaries=enable)
        else:
            for bvert in self.boundary_verts:
                bvert.loop_uv.pin_uv = enable


    def calc_boundaries(self, pin_boundaries: bool = False) -> None:
        bm = self.bm

        # Accessor for BMLoopUV data.
        loop_uv_accessor = bm.loops.layers.uv.active

        # Sequences.
        bm_faces: list[BMFace] = bm.faces
        bm_loops: list[BMLoop] = (l for f in bm_faces for l in f.loops)

        uv_prim: dict[int, UVPrim] = {}
        boundary_verts: list[BoundaryVert] = []

        def _uvloop_select_pin(loop_uv: BMLoopUV, state: bool, use_pin: bool = False) -> None:
            loop_uv.select = state
            if use_pin:
                loop_uv.pin_uv = state

        for loop in bm_loops:
            loop_uv: BMLoopUV = loop[loop_uv_accessor]
            if not loop_uv.select: # not loop.face.select: # any([edge.select for edge in loop.face.edges]):
                # Exclude if no selected.
                continue

            _uvloop_select_pin(loop_uv, state=False, use_pin=pin_boundaries)

            uv_prim[loop.index] = UVPrim(
                loop,
                loop_uv,
            )

        uvp_per_uv_coord: dict[tuple, list[UVPrim]] = defaultdict(list)
        for uvp in uv_prim.values():
            uvp_per_uv_coord[uvp.uv.to_tuple()].append(uvp)

        for uv_co, uvp_list in uvp_per_uv_coord.items():
            if len(uvp_list) == 1:
                uvp = uvp_list[0]
                boundary_verts.append(BoundaryVert(uvp.loop, uvp.loop_uv))
                uvp.is_vert_boundary = True
                uvp.is_edge_boundary = True
            if len(uvp_list) == 2:
                # Only one of the loops is really a boundary, the other is a cross edge.
                # But we set both as boundary, one as edge-vert boundary and the other (cross) as vert boundary.
                for uvp in uvp_list:
                    if len(uvp.edge.link_faces) == 1:
                        boundary_verts.append(BoundaryVert(uvp.loop, uvp.loop_uv))
                        uvp.is_vert_boundary = True
                        uvp.is_edge_boundary = True
                    else:
                        uvp.is_vert_boundary = True

        self.uv_prim = uv_prim
        self.boundary_verts = boundary_verts
        self.uvp_per_uv_coord = uvp_per_uv_coord

        # print("BOUNDARY VERTICES:")
        # for bound_vert in boundary_verts:
        #     print("\t- ", bound_vert.__dict__)

        self.calc_bbox()


    def calc_bbox(self):
        boundary_verts: list[BoundaryVert] = self.boundary_verts

        if boundary_verts == []:
            return

        ''' Bounding Box. '''
        # Get min and max to determine the bounds of the cage.
        min_u_bvert = min(boundary_verts, key=lambda x: x.uv[0])
        min_v_bvert = min(boundary_verts, key=lambda x: x.uv[1])
        max_u_bvert = max(boundary_verts, key=lambda x: x.uv[0])
        max_v_bvert = max(boundary_verts, key=lambda x: x.uv[1])

        min_u = min_u_bvert.uv[0]
        min_v = min_v_bvert.uv[1]
        max_u = max_u_bvert.uv[0]
        max_v = max_v_bvert.uv[1]

        self.bbox = BBOX_2(min_u, max_u, min_v, max_v)

        # print("BBOX:\n", self.bbox.__dict__)


    def is_grid(self, limit_corners: bool = False) -> bool:
        ''' GRID-LIKE UV ISLAND SUPPORT:
            If we detect that exactly 4 UV coords have a single loop liked,
            then we can ensure that it is a grid-like mesh. '''

        # All faces must be quads.
        for uvp in self.uv_prim.values():
            face = uvp.face
            if len(face.verts) != 4:
                return False

        # Must have 4 well-defined corners.
        uvp_per_uv_coord = self.uvp_per_uv_coord
        corners = [uvps[0] for uvps in uvp_per_uv_coord.values() if len(uvps) == 1]

        if limit_corners:
            if len(corners) != 4:
                return False
        elif len(corners) < 4:
            return False

        self.grid_corners = corners
        return True


    def straighten_grid__follow_active_quad(self) -> None:
        if len(self.grid_corners) == 0:
            return

        # If the UV Island is a large one rotated at 45º it will be problematic.
        for uvp in self.uv_prim.values():
            uvp.loop_uv.select = True
            uvp.loop_uv.select_edge = True
        bpy.ops.uv.align_rotation(False)

        uv_layer = self.active_uv_layer
        any_corner = self.grid_corners[0]
        selected_face = any_corner.face

        # Calculate the dimensions of the quad face in the UV space.
        x_min, y_min, x_max, y_max = (float('inf'), float('inf'), float('-inf'), float('-inf'))
        for loop in selected_face.loops:
            uv = loop[uv_layer].uv
            x_min = min(x_min, uv.x)
            y_min = min(y_min, uv.y)
            x_max = max(x_max, uv.x)
            y_max = max(y_max, uv.y)

        # See which face corner is the lowest and leftist one.
        loops = list(selected_face.loops)
        loops.sort(key=lambda loop: loop[uv_layer].uv.x + loop[uv_layer].uv.y)
        ## print("SORTED LOOPS:", loops)
        ## bot_left_loop: BMLoop = loops[0]

        # Calculate the size of the quad face in the UV space.
        width = x_max - x_min
        height = y_max - y_min

        # Calculate the center of the quad face in the UV space.
        center_x = (x_min + x_max) / 2.0
        center_y = (y_min + y_max) / 2.0

        # Determine the side length of the square in the UV space.
        ## side_length = max(width, height)

        # Calculate the new UV coordinates to make the quad a square.

        for loop in selected_face.loops:
            uv = loop[uv_layer].uv
            ## new_u = (uv.x - center_x) * (side_length / 2) + center_x
            ## new_v = (uv.y - center_y) * (side_length / 2) + center_y
            ## loop[uv_layer].uv = (new_u, new_v)
            new_u = x_max if uv.x > center_x else x_min
            new_v = y_max if uv.y > center_y else y_min
            loop[uv_layer].uv = (new_u, new_v)

        ## bot_left_loop[uv_layer].uv = (x_min, y_min)
        ## bot_left_loop.link_loop_prev[uv_layer].uv = (x_min, y_max)
        ## bot_left_loop.link_loop_next[uv_layer].uv = (x_max, y_min)
        ## bot_left_loop.link_loop_next.link_loop_next[uv_layer].uv = (x_max, y_max)

        # Deselect add and ensure we are in face selection mode.
        bpy.ops.uv.select_all(False, action='DESELECT')
        bpy.ops.uv.select_mode(False, type='FACE')

        # Make our straightened quad the active one.
        self.bm.faces.active = any_corner.face

        for loop in any_corner.face.loops:
            loop[uv_layer].select = True

        # Follow active quads! This will straigthen connected quads based on the active one.
        bpy.ops.uv.follow_active_quads(False)


    def straighten_grid__find_pattern(self, size_method: str = 'PRESERVE') -> None:
        bbox = self.bbox
        uvp_per_uv_coord = self.uvp_per_uv_coord
        grid_corners = self.grid_corners
        uv_prim = self.uv_prim

        ## print("CORNERS:", grid_corners)

        # Manual-Search and Clasify the corners.
        uvp__bottom_left = None
        uvp__bottom_right = None
        uvp__top_left = None
        uvp__top_right = None

        # First search for the bottom-left corner... kind of...

        def _edge_angle_uv(_uvp: UVPrim) -> tuple[Vector, float]:
            uv_1 = _uvp.uv
            uv_2 = uv_prim[_uvp.loop.link_loop_next.index].uv
            v1 = direction(uv_2, uv_1)
            v2 = Vector((1, 0))
            return v1, angle_signed(v1, v2, as_degrees=True)

        corner_loops_info = [(*_edge_angle_uv(c), c.loop_index) for c in grid_corners]

        ## print(corner_loops_info)

        candidate_by_direction: UVPrim = None
        wanted_direction = Vector((1, 0))
        min_dir_factor = float('inf')
        candidate_by_angle: UVPrim = None
        wanted_angle_next = 0
        min_ang_next_factor = float('inf')

        for (loop_dir, loop_ang_next, loop_index) in corner_loops_info:
            diff = wanted_direction - loop_dir
            dir_factor = abs(diff.x) + abs(diff.y)
            if dir_factor < min_dir_factor:
                min_dir_factor = dir_factor
                candidate_by_direction = uv_prim[loop_index]

            if abs(loop_ang_next) < min_ang_next_factor:
                min_ang_next_factor = abs(loop_ang_next)
                candidate_by_angle = uv_prim[loop_index]

        ## print(candidate_by_direction, min_dir_factor)
        ## print(candidate_by_angle, min_ang_next_factor)

        uvp__bottom_left = candidate_by_direction

        # Then, we need to find the rest of the corners by walking from out start loop (bottom left).
        def walk_search_corner(src_uvp: UVPrim,
                               prev_uvp: UVPrim,
                               curr_uvp: UVPrim,
                               dst_uvps: list[UVPrim],
                               get_next_loop: callable,
                               get_final_loop: callable,
                               walked: set[UVPrim]) -> UVPrim:
            if curr_uvp is None:
                return None
            ## if prev_uvp is None:
            ##     print(f"From {curr_uvp.loop_index} to {[uvp.loop_index for uvp in dst_uvps]}")
            ## print(f"\t> L:{curr_uvp.loop_index}, V:{curr_uvp.vert_index}, F:{curr_uvp.face.index}\t[{get_final_loop is None}]")
            if curr_uvp in walked:
                return None
            walked.add(curr_uvp)
            if curr_uvp in dst_uvps:
                return curr_uvp
            if get_final_loop is None:
                # last chance lost! :-(
                return None
            curr_face = curr_uvp.face
            next_loop: BMLoop = get_next_loop(curr_uvp.loop)
            next_uvp = uv_prim.get(next_loop.index, None)
            next_face = next_loop.face
            if (next_uvp is None or next_uvp == src_uvp or curr_face == next_face) and get_final_loop is not None:
                next_loop: BMLoop = get_final_loop(curr_uvp.loop)
                next_uvp = uv_prim.get(next_loop.index, None)
                get_final_loop = None
            return walk_search_corner(src_uvp, curr_uvp, next_uvp, dst_uvps, get_next_loop, get_final_loop, walked)

        corners = grid_corners.copy()
        corners.remove(uvp__bottom_left)
        ## print('BL:', uvp__bottom_left)
        uvp__top_left     : UVPrim = walk_search_corner(
            src_uvp=uvp__bottom_left,
            prev_uvp=None,
            curr_uvp=uvp__bottom_left,
            dst_uvps=corners,
            get_next_loop=lambda loop: loop.link_loop_prev.link_loop_prev.link_loop_radial_next,
            get_final_loop=lambda loop: loop.link_loop_prev,
            walked=set())
        if uvp__top_left is None:
            return
        else:
            ## print('TL:', uvp__top_left)
            corners.remove(uvp__top_left)
        uvp__top_right    : UVPrim = walk_search_corner(
            src_uvp=uvp__top_left,
            prev_uvp=None,
            curr_uvp=uvp__top_left,
            dst_uvps=corners,
            get_next_loop=lambda loop: loop.link_loop_prev.link_loop_prev.link_loop_radial_next,
            get_final_loop=lambda loop: loop.link_loop_prev,
            walked=set())
        if uvp__top_right is None:
            return
        else:
            ## print('TR:', uvp__top_right)
            corners.remove(uvp__top_right)
        uvp__bottom_right : UVPrim = walk_search_corner(
            src_uvp=uvp__bottom_left,
            prev_uvp=None,
            curr_uvp=uvp__bottom_left,
            dst_uvps=corners,
            get_next_loop=lambda loop: loop.link_loop_next.link_loop_radial_next.link_loop_next,
            get_final_loop=lambda loop: loop.link_loop_next,
            walked=set())
        if uvp__bottom_right is None:
            return
        else:
            ## print('BR:', uvp__bottom_right)
            corners.remove(uvp__bottom_right)


        ## print("Bottom-Left corner:", uvp__bottom_left.loop_index, uvp__bottom_left.uv)
        ## print("Top-Left corner:", uvp__top_left.loop_index, uvp__top_left.uv)
        ## print("Bottom-Right corner:", uvp__bottom_right.loop_index, uvp__bottom_right.uv)
        ## print("Top-Right corner:", uvp__top_right.loop_index, uvp__top_right.uv)

        del self.grid_corners

        # Create dictionaries to store rows and columns
        grid: dict[tuple[int, int], UVPrim] = {}

        walked_uvp: set[int] = set()

        # Iterate through the selected vertices and group them into rows and columns based on angle
        def walk_vert(uvp: UVPrim, col_index: int = 0, row_index: int = 0, do_break: bool = False) -> None:
            ## print(uvp.loop_index, col_index, row_index)
            if uvp is None:
                print("WARN! None uvp, stopping...")
                return
            # if uvp.loop_index not in uv_prim:
            #     return
            if uvp.loop_index in walked_uvp:
                # print("WARN! We already walked over this uvp:", uvp.loop_index, uvp.vert_index)
                return
            if (col_index, row_index) in grid:
                # print("WARN! Grid Slot already set! ->", col_index, row_index, "\t- Trying to insert:", uvp)
                return

            grid[(col_index, row_index)] = uvp
            walked_uvp.add(uvp.loop_index)

            if do_break:
                return

            curr_face = uvp.face

            right_loop = uvp.loop.link_loop_next.link_loop_radial_next.link_loop_next
            if curr_face == right_loop.face:
                right_loop = uvp.loop.link_loop_next
                return
            right_uvp = uv_prim.get(right_loop.index, None)
            walk_vert(right_uvp, col_index + 1, row_index, do_break=do_break)

            top_loop = uvp.loop.link_loop_prev.link_loop_prev.link_loop_radial_next
            if curr_face == top_loop.face:
                top_loop = uvp.loop.link_loop_prev
                return
            top_uvp = uv_prim.get(top_loop.index, None)
            walk_vert(top_uvp, col_index, row_index + 1, do_break=do_break)

        # Get all cols and rows.
        walk_vert(uvp__bottom_left, 0, 0)

        # Get number of cols and rows.
        slots = list(grid.keys())
        cols_n = max(slots, key=lambda slot: slot[0])[0] + 1
        rows_n = max(slots, key=lambda slot: slot[1])[1] + 1

        print(cols_n, rows_n)


        # We do these exptra walks to fix the top and right borders.
        def walk_right_border_up(uvp: UVPrim, break_uvp: UVPrim, col_index: int = 0, row_index: int = 0) -> None:
            if uvp is break_uvp: return
            if uvp is None: return
            if uvp.loop_index in walked_uvp: return

            grid[(col_index, row_index)] = uvp
            walked_uvp.add(uvp.loop_index)

            top_loop = uvp.loop.link_loop_next.link_loop_radial_next.link_loop_next
            top_uvp = uv_prim.get(top_loop.index, None)
            walk_right_border_up(top_uvp, break_uvp, col_index, row_index + 1)

        walk_right_border_up(uvp__bottom_right, uvp__top_right, col_index=cols_n, row_index=0)

        def walk_top_border_right(uvp: UVPrim, break_uvp: UVPrim, col_index: int = 0, row_index: int = 0) -> None:
            if uvp is break_uvp: return
            if uvp is None: return
            if uvp.loop_index in walked_uvp: return

            grid[(col_index, row_index)] = uvp
            walked_uvp.add(uvp.loop_index)

            right_loop = uvp.loop.link_loop_prev.link_loop_prev.link_loop_radial_next
            right_uvp = uv_prim.get(right_loop.index, None)
            walk_top_border_right(right_uvp, break_uvp, col_index + 1, row_index)

        walk_top_border_right(uvp__top_left, uvp__top_right, col_index=0, row_index=rows_n)


        # Calculate the even spaces in X/U (rows) and Y/V (cols).
        if size_method == 'BBOX':
            grid_width = bbox.width
            grid_height = bbox.height

        else:
            row_heights = [0] * rows_n
            col_widths = [0] * cols_n

            for row_index in range(rows_n):
                prev_col_uvp = None
                for col_index in range(cols_n):
                    uvp = grid.get((col_index, row_index), None)
                    if uvp is None:
                        continue
                    if prev_col_uvp is None:
                        prev_col_uvp = uvp
                        continue
                    d = (prev_col_uvp.uv - uvp.uv).length_squared # calculate_distance_uv(uvp, prev_col_uvp)
                    col_widths[col_index-1] = d
                    prev_col_uvp = uvp

            for col_index in range(cols_n):
                prev_row_uvp = None
                for row_index in range(rows_n):
                    uvp = grid.get((col_index, row_index), None)
                    if uvp is None:
                        continue
                    if prev_row_uvp is None:
                        prev_row_uvp = uvp
                        continue
                    d = (prev_row_uvp.uv - uvp.uv).length_squared
                    row_heights[row_index-1] = d
                    prev_row_uvp = uvp

            # To solve special cases where the number of rows or cols is 1...
            if rows_n == 1:
                slot_0_0 = uvp__bottom_left
                slot_0_1 = uvp__top_left
                row_heights[0] = calculate_distance_uv(
                    slot_0_0,
                    slot_0_1
                )

            if cols_n == 1:
                slot_0_0 = uvp__bottom_left
                slot_1_0 = uvp__bottom_right
                col_widths[0] = calculate_distance_uv(
                    slot_0_0,
                    slot_1_0
                )

            # We need to scale it up a bit... Atm just fit the greatest dimension to the BBOX.
            grid_width = sum(col_widths)
            grid_height = sum(row_heights)

            if grid_width > grid_height:
                grid_height = bbox.width / grid_width * grid_height
                grid_width = bbox.width
            else:
                grid_width = bbox.height / grid_height * grid_width
                grid_height = bbox.height

            # Fake bounding box.
            bbox.max_x = bbox.min_x + grid_width
            bbox.max_y = bbox.min_y + grid_height

            print("col_widths", col_widths)
            print("row_heights", row_heights)

        print("Grid Size:", grid_width, grid_height)

        quad_width = grid_width / cols_n
        quad_height = grid_height / rows_n

        # Place borders in the bbox bounds.
        uvp__bottom_left.uv = bbox.bottom_left.to_tuple()
        uvp__bottom_right.uv = bbox.bottom_right.to_tuple()
        uvp__top_left.uv = bbox.top_left.to_tuple()
        uvp__top_right.uv = bbox.top_right.to_tuple()

        # Here we create the grid out of the rows/cols info we got.
        min_u = bbox.min_x
        min_v = bbox.min_y

        for (col_index, row_index), uvp in grid.items():
            new_uv_coord = (
                min_u + (col_index * quad_width),
                min_v + (row_index * quad_height)
            )
            for _uvp in uvp_per_uv_coord[uvp.uv.to_tuple()]:
                _uvp.loop_uv.uv = new_uv_coord

        # bpy.ops.uv.select_all(False, action='DESELECT')


    def is_radial(self) -> bool:
        ''' We need to find 2 circles. An inner one and an outer one. '''
        boundary_verts = self.boundary_verts
        uv_prim = self.uv_prim

        if len(boundary_verts) % 2 != 0:
            # Must have pair of loops in the boundaries.
            print("SKIP StraightenRadial: Must have pair of loops in the boundaries")
            return False

        # 1. Calculate the center of the circle.
        center_point: Vector = Vector((0, 0))
        for bvert in boundary_verts:
            center_point += bvert.uv
        center_point /= len(boundary_verts)

        # Loops per UV.
        uvp_per_uv_coord: dict[tuple, list[UVPrim]] = defaultdict(list)
        for uvp in self.uv_prim.values():
            uvp_per_uv_coord[uvp.uv.to_tuple()].append(uvp)

        # 2. Clasify the boundary vertices as outer or inner.
        # Get a loop in which the next loop is a boundary vert too (since same vertex/UV coords can be shared by 2 different boundary loops).
        # If it is, we can check the angle difference between these loops to determine if we are walking CW or CCW direction.
        # - CW direction means we are walking on the inner circle.
        # - CCW direction means we are walking on the outer circle.
        inner_circle_bverts: list[BoundaryVert] = []
        outer_circle_bverts: list[BoundaryVert] = []
        alt_inner_circle_bverts: list[UVPrim] = []
        alt_outer_circle_bverts: list[UVPrim] = []

        # boundary_verts_dict = {bvert.loop_index: bvert for bvert in boundary_verts}
        # get_bvert_from_loop = lambda loop: boundary_verts_dict.get(loop.index, None)

        uv_layer = self.active_uv_layer

        for bvert in boundary_verts:
            next_loop = bvert.loop.link_loop_next

            v1 = direction(center_point, bvert.uv)
            v2 = direction(center_point, next_loop[uv_layer].uv)
            angle = angle_signed(v1, v2, as_degrees=True)

            ## print(bvert.loop_index, next_loop.index, v1.to_tuple(), v2.to_tuple(), angle)

            if angle < 0:
                # CW. aka inner
                inner_circle_bverts.append(bvert)
                # Ignore since we already add the same UV even if not the same loop. (to avoid issues with relationships with unwanted loop directions)
                alt_inner_circle_bverts.append(uv_prim.get(next_loop.index))
            else:
                # CC2. aka outer
                outer_circle_bverts.append(bvert)
                # Ignore since we already add the same UV even if not the same loop. (to avoid issues with relationships with unwanted loop directions)
                alt_outer_circle_bverts.append(uv_prim.get(next_loop.index))

        ## print(len(inner_circle_bverts), len(outer_circle_bverts))

        # BREAK IF...
        if len(inner_circle_bverts) == 0 or len(outer_circle_bverts) == 0:
            print("SKIP StraightenRadial: no inner or outer circle boundary vertices were found")
            return False
        if len(inner_circle_bverts) != len(outer_circle_bverts):
            print("SKIP StraightenRadial: inner and outer circle boundary vertices does not match")
            return False

        self.center_point = center_point
        self.inner_circle_bverts = inner_circle_bverts
        self.outer_circle_bverts = outer_circle_bverts
        self.alt_inner_circle_bverts = alt_inner_circle_bverts
        self.alt_outer_circle_bverts = alt_outer_circle_bverts

        ## print("INNERS:", [uvp.loop_index for uvp in inner_circle_bverts])
        ## print("OUTERS:", [uvp.loop_index for uvp in outer_circle_bverts])
        ## print("ALT-INNERS:", [uvp.loop_index for uvp in alt_inner_circle_bverts])
        ## print("ALT-OUTERS:", [uvp.loop_index for uvp in alt_outer_circle_bverts])


        ## bpy.ops.uv.select_all(False, action='DESELECT')
        ## for bvert in boundary_verts:
        ##     bvert.loop_uv.select = True
        ##     bvert.loop_uv.select_edge = True

        ## print("BOUNDARY VERTS:", [bvert.loop_index for bvert in boundary_verts])

        return True


    def straighten_radial(self) -> None:
        uv_prim = self.uv_prim
        uv_layer = self.active_uv_layer
        boundary_vert_indices = {bvert.loop_index for bvert in self.boundary_verts}

        outer_circle_bverts = self.outer_circle_bverts
        inner_circle_bverts = self.inner_circle_bverts
        alt_inner_circle_bverts = self.alt_inner_circle_bverts

        outer_circle_loop_indices = {bvert.loop_index for bvert in outer_circle_bverts}

        # Get the relationship between inner loop and outer loop.
        walked_loop_indices: set[int] = set()
        inner_outer_paths: dict[BoundaryVert, list[UVPrim]] = defaultdict(list)

        def _walk_to_outer(src_inner_bvert: BoundaryVert, curr_uvp: UVPrim, final_step: bool = False) -> None:
            if curr_uvp is None:
                ## print("\t- NONE")
                return
            if curr_uvp.loop_index in walked_loop_indices:
                ## print("\t- MATCH OUTER!")
                return

            inner_outer_paths[src_inner_bvert].append(curr_uvp)
            walked_loop_indices.add(curr_uvp.loop_index)
            ## print("\t-", curr_uvp.loop_index)

            if final_step or curr_uvp.loop_index in outer_circle_loop_indices:
                # `curr_uvp.loop_index in outer_circle_loop_indices` may never match since the outer walking is in the opposite direction...
                # which means, will gather another loop with the same UV coords but different index.
                # Since we won't use the outer that much in the next process, we can simply ignore this by now
                # and work based on the inner-outer paths we walk here which should be enough.
                ## print("\t- FINAL!")
                return

            curr_face = curr_uvp.face

            outer_loop = curr_uvp.loop.link_loop_next.link_loop_radial_next.link_loop_next
            outer_uvp = uv_prim.get(outer_loop.index, None)
            outer_face = outer_loop.face
            if outer_uvp is None or curr_face == outer_face:
                outer_loop = curr_uvp.loop.link_loop_next
                outer_uvp = uv_prim.get(outer_loop.index, None)
                final_step = True
            _walk_to_outer(src_inner_bvert, outer_uvp, final_step=final_step)

        for alt_inner_bvert in alt_inner_circle_bverts:
            ## print("Walk from inner to outer...", alt_inner_bvert.loop_index)
            # Get all radial cross loops in outer-inner direction.
            _walk_to_outer(alt_inner_bvert, alt_inner_bvert)


        # Rip at some point.
        ripped_loops_head: list[UVPrim] = []
        ripped_loops_tail: list[UVPrim] = []

        # for inner_bvert, path in inner_outer_paths.items():
        #     print(inner_bvert)
        #     for loop in path:
        #         print(f"\t- {loop.loop_index}")

        any_alt_inner_bvert = alt_inner_circle_bverts[0]
        inner_outer_path = inner_outer_paths[any_alt_inner_bvert]
        bpy.ops.uv.select_all(False, action='DESELECT')
        for uvp in inner_outer_path:
            if uvp.loop_index not in boundary_vert_indices:
                uvp.loop_uv.select = True
                uvp.loop_uv.select_edge = True
                uvp.pin_uv = True
                ripped_loops_head.append(uvp)
                if next_uvp := uv_prim.get(uvp.loop.link_loop_next.index, None):
                    if next_uvp.loop_index not in boundary_vert_indices:
                        next_uvp.loop_uv.select = True
                        # next_uvp.loop_uv.select_edge = True
                        next_uvp.pin_uv = True
                        ripped_loops_head.append(next_uvp)

                        # if radial_next_uvp := uv_prim.get(uvp.loop.link_loop_radial_next.link_loop_prev.index, None):
                        #     if radial_next_uvp.loop_index not in boundary_vert_indices:
                        #         radial_next_uvp.loop_uv.select = True
                        #         ripped_loops_tail.append(radial_next_uvp)

                # if radial_uvp := uv_prim.get(uvp.loop.link_loop_radial_next.index, None):
                #     if radial_uvp.loop_index not in boundary_vert_indices:
                #         ripped_loops_tail.append(radial_uvp)
                #         radial_uvp.loop_uv.select = True
                #         radial_uvp.loop_uv.select_edge = True

        # We just need a loop from the other side... which at the rip time it will be a boundary loop at the tail.
        tail_start = uv_prim.get(ripped_loops_head[-1].loop.link_loop_radial_next.index)
        ## tail_start.loop_uv.select = True
        ## tail_start.loop_uv.select_edge = True

        ## print("RIPPED HEAD:", [uvp.loop_index for uvp in ripped_loops_head])
        ## print("RIPPED TAIL:", [uvp.loop_index for uvp in ripped_loops_tail])

        # Separate head and tail loops. (aka rip)
        start_end_line: Vector = direction(ripped_loops_head[0].uv, ripped_loops_head[-1].uv)
        perp_line: Vector = Vector((1, -start_end_line.x / max(start_end_line.y, 1)))
        off = perp_line * 0.01
        for head_uvp in ripped_loops_head:
            head_uvp.uv += off
        head_uvp.loop.link_loop_next[uv_layer].uv += off
        # for tail_uvp in ripped_loops_tail:
        #     tail_uvp.uv -= off

        # Get width and height.
        ## width = 0
        ## for index in range(1, len(ripped_loops_head), 2):
        ##     uvp1 = ripped_loops_head[index - 1]
        ##     uvp2 = ripped_loops_head[index]
        ##     width += calculate_distance_uv(uvp2, uvp1)
        ## height = 0
        ## for uvp in outer_circle_bverts:
        ##     height += calculate_distance_uv(uvp, uvp.loop.link_loop_next[uv_layer])
        ## for uvp in inner_circle_bverts:
        ##     height += calculate_distance_uv(uvp, uvp.loop.link_loop_next[uv_layer])
        ## height /= 2

        outer_radius = sum([
            distance_between(self.center_point, bvert.uv) for bvert in outer_circle_bverts
        ]) / len(outer_circle_bverts)
        inner_radius = sum([
            distance_between(self.center_point, bvert.uv) for bvert in inner_circle_bverts
        ]) / len(inner_circle_bverts)
        # thickness = sum([
        #     distance_between(bverts[0].uv, bverts[-1].uv) for bverts in inner_outer_paths.values()
        # ]) / len(inner_circle_bverts)
        # mid_radius = (outer_radius + inner_radius) / 2
        width = outer_radius - inner_radius
        height = 2 * pi * outer_radius

        min_u = self.bbox.min_x
        min_v = self.bbox.min_y

        iwidth = width / len(ripped_loops_head)
        iheight = height / len(inner_circle_bverts)

        ## print("Size:", width, height)

        # Sort inner boundary vertices by angle (relative to one of the head bvert).
        head_bvert_ref = ripped_loops_head[0]
        v1 = direction(head_bvert_ref.uv, self.center_point)
        def _get_angle_between_head_and_uvp(_uvp: UVPrim) -> float:
            ang = angle_signed(direction(_uvp.uv, self.center_point), v1, as_degrees=True)
            if ang < 0:
                ang = 360 + ang
            ## print(_uvp.loop_index, ang)
            return ang
        alt_inner_circle_bverts.sort(key=lambda _uvp: _get_angle_between_head_and_uvp(_uvp))

        # Move head to the last path.
        alt_inner_circle_bverts.append(alt_inner_circle_bverts.pop(0))

        # Fake add tail from rip.
        _walk_to_outer(tail_start, tail_start)
        # inner_outer_paths[inner_tail_bvert] = ripped_loops_tail
        alt_inner_circle_bverts.insert(0, tail_start)
        inner_outer_paths[tail_start] = list(reversed(inner_outer_paths[tail_start]))

        # Loops per UV.
        uvp_per_uv_coord = self.uvp_per_uv_coord

        ## print("Order of rows:", [uvp.loop_index for uvp in alt_inner_circle_bverts])

        # Apply new UV coordinates.
        for row_index, alt_inner_bvert in enumerate(alt_inner_circle_bverts):
            # New Row.
            path = inner_outer_paths[alt_inner_bvert]
            for col_index, path_uvp in enumerate(path):
                # New col.
                uv = (
                    min_u + iwidth * col_index,
                    min_v + iheight * row_index
                )
                for uvp in uvp_per_uv_coord[path_uvp.uv.to_tuple()]:
                    uvp.uv = uv


        # Cleanup.
        del self.alt_inner_circle_bverts
        del self.alt_outer_circle_bverts
        del self.inner_circle_bverts
        del self.outer_circle_bverts
        del outer_circle_loop_indices
        del walked_loop_indices
        del inner_outer_paths
        del ripped_loops_head
        del ripped_loops_tail


    def straighten_borders(self, method: str = 'MIN_MAX') -> None:
        boundary_verts = self.boundary_verts

        if boundary_verts == []:
            return

        bbox = self.bbox

        # We create a BVHTree for the bbox points.
        # Then we use it to get nearest boundary UV coord to each corners.
        # So we translate that UV coord to the corner coordinate.
        tree = kdtree.KDTree(len(boundary_verts))
        for i, bvert in enumerate(boundary_verts):
            tree.insert((*bvert.uv, 0.0), i)
        tree.balance()

        top_left_index      : int = tree.find((bbox.min_x, bbox.max_y, 0.0))[1]
        bottom_left_index   : int = tree.find((bbox.min_x, bbox.min_y, 0.0))[1]
        bottom_right_index  : int = tree.find((bbox.max_x, bbox.min_y, 0.0))[1]
        top_right_index     : int = tree.find((bbox.max_x, bbox.max_y, 0.0))[1]

        del tree

        bvert__top_left     : BoundaryVert = boundary_verts[top_left_index]
        bvert__bottom_left  : BoundaryVert = boundary_verts[bottom_left_index]
        bvert__bottom_right : BoundaryVert = boundary_verts[bottom_right_index]
        bvert__top_right    : BoundaryVert = boundary_verts[top_right_index]

        # Get border vertices by sides.
        borders = (
            # self.top_border
            (walk_from_vert_to_vert(bvert__top_right, bvert__top_left, boundary_verts), 'T', 'Y'),
            # self.bottom_border
            (walk_from_vert_to_vert(bvert__bottom_left, bvert__bottom_right, boundary_verts), 'B', 'Y'),
            # self.left_border
            (walk_from_vert_to_vert(bvert__top_left, bvert__bottom_left, boundary_verts), 'L', 'X'),
            # self.right_border
            (walk_from_vert_to_vert(bvert__bottom_right, bvert__top_right, boundary_verts), 'R', 'X'),
        )

        ## print("BORDERS:")
        ## for (bverts, border_id, align_axis) in borders:
        ##     print(f"\t[{border_id}:{align_axis}] BVert Count: {len(bverts)}")
        ##     for bvert in bverts:
        ##         print(f"\t  > Vert: {bvert.vert.index},\tLoop: {bvert.loop.index},\tUV: {bvert.uv}")
        ## print("\t- Top-Left:", bvert__top_left.vert_index, bvert__top_left.loop_index, bvert__top_left.uv)
        ## print("\t- Bottom-Left:", bvert__bottom_left.vert_index, bvert__bottom_left.loop_index, bvert__bottom_left.uv)
        ## print("\t- Bottom-Right:", bvert__bottom_right.vert_index, bvert__bottom_right.loop_index, bvert__bottom_right.uv)
        ## print("\t- Top-Right:", bvert__top_right.vert_index, bvert__top_right.loop_index, bvert__top_right.uv)

        if method == 'AVERAGE':
            for (bverts, border_id, align_axis) in borders:
                average_h = 0.0
                for bvert in bverts:
                    if align_axis == 'X':
                        average_h += bvert.uv.x
                    else:
                        average_h += bvert.uv.y

                average_h /= len(bverts)
                for bvert in bverts:
                    if align_axis == 'X':
                        bvert.loop_uv.uv.x = average_h
                    else:
                        bvert.loop_uv.uv.y = average_h

        elif method == 'MIN_MAX':
            for (bverts, border_id, align_axis) in borders:
                if border_id in {'L', 'B'}:
                    min_max_func = min
                    min_max_h = 1.0
                else:
                    min_max_func = max
                    min_max_h = 0.0

                for bvert in bverts:
                    if align_axis == 'X':
                        min_max_h = min_max_func(bvert.uv.x, min_max_h)
                    else:
                        min_max_h = min_max_func(bvert.uv.y, min_max_h)

                for bvert in bverts:
                    if align_axis == 'X':
                        bvert.loop_uv.uv.x = min_max_h
                    else:
                        bvert.loop_uv.uv.y = min_max_h


        ''' OVERLAP SOLVER...
            Since the detected border points are projected to the calculated bounding/border surface.
            Sometimes the UV coordinates of those points are not quite optimal since they can provoke overlaps with its adjacent geometry.
            So we need to go through each UV point for each border, in the correct order corner->corner,
            and then flip the UV coordinates in the X/Y coordinates of the current point is underneath the next point.
        '''
        def flip_x(bvert_a, bvert_b): bvert_a.loop_uv.uv.x, bvert_b.loop_uv.uv.x = bvert_b.uv.x, bvert_a.uv.x
        def flip_y(bvert_a, bvert_b): bvert_a.loop_uv.uv.y, bvert_b.loop_uv.uv.y = bvert_b.uv.y, bvert_a.uv.y

        check_pot_overlap_func_by_border_id = {
            'L': lambda bvert_a, bvert_b: bvert_a.uv.y < bvert_b.uv.y, # From top to bottom.
            'R': lambda bvert_a, bvert_b: bvert_a.uv.y > bvert_b.uv.y, # From bottom to top.
            'B': lambda bvert_a, bvert_b: bvert_a.uv.x > bvert_b.uv.x, # From right to left.
            'T': lambda bvert_a, bvert_b: bvert_a.uv.x < bvert_b.uv.x  # From left to right.
        }

        # 2 passes is enough...
        for i in range(2):
            for (bverts, border_id, align_axis) in borders:
                flip_func = flip_y if align_axis == 'X' else flip_x
                check_pot_overlap_func = check_pot_overlap_func_by_border_id[border_id]
                prev_bvert = None
                bverts_count = len(bverts)
                for i, curr_bvert in enumerate(bverts):
                    if prev_bvert is None:
                        # Start. (corner)
                        prev_bvert = curr_bvert
                        continue
                    if (i + 1) >= bverts_count:
                        # End. (corner)
                        break
                    next_bvert = bverts[i + 1]

                    if check_pot_overlap_func(curr_bvert, next_bvert):
                        # Potential overlap detected! FLIP IT!
                        flip_func(curr_bvert, next_bvert)
                        curr_bvert, next_bvert = next_bvert, curr_bvert

                    prev_bvert = curr_bvert

        del borders


    def unwrap(self, pin_boundaries: bool = False) -> None:
        if not hasattr(self, 'uv_prim'):
            self.calc_boundaries(pin_boundaries=pin_boundaries)

        bpy.ops.uv.select_all(False, action='DESELECT')
        for uvp in self.uv_prim.values():
            uvp.loop_uv.select = True

        bpy.ops.uv.unwrap(False)
        bpy.ops.uv.minimize_stretch(fill_holes=False, blend=0, iterations=100)



@Register.OPS.GENERIC
class SmartStraightenUVIsland:
    label = "Smart Straighten UV Island"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH' and context.active_object.mode == 'EDIT'

    def execute(self, context):
        ''' Requires a user selection. '''

        # Check if UV Editor is active
        if context.area.type != 'IMAGE_EDITOR':
            self.report({'ERROR'}, "UV Editor is not active")
            return {'CANCELLED'}

        # Get the selected UV island
        # bpy.ops.uv.select_linked_pick(deselect=False)

        mesh: Mesh = context.active_object.data
        with UVIslandData(mesh) as uv_island:
            if uv_island.is_grid(limit_corners=False):
                uv_island.straighten_grid__follow_active_quad()
                uv_island.mesh.update()
            elif uv_island.is_radial():
                uv_island.straighten_radial()
                uv_island.mesh.update()
            else:
                uv_island.straighten_borders(method='MIN_MAX')
                uv_island.pin_boundaries(enable=True)
                uv_island.unwrap()
                uv_island.pin_boundaries(enable=False)

        return {'FINISHED'}


@Register.OPS.GENERIC
class StraightenUVIslandBorders:
    label = "Straighten UV Island Borders"
    bl_options = {'REGISTER', 'UNDO'}

    method: EnumProperty(
        name="Select",
        items=(
            ('MIN_MAX', "Min Max", ""),
            ('AVERAGE', "Average", "")
        ),
        default='MIN_MAX'
    )

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH' and context.active_object.mode == 'EDIT'

    def execute(self, context):
        ''' Requires a user selection. '''

        # Check if UV Editor is active
        if context.area.type != 'IMAGE_EDITOR':
            self.report({'ERROR'}, "UV Editor is not active")
            return {'CANCELLED'}

        # Get the selected UV island
        # bpy.ops.uv.select_linked_pick(deselect=False)


        mesh: Mesh = context.active_object.data
        with UVIslandData(mesh) as uv_island:
            uv_island.straighten_borders(method=self.method)
            uv_island.pin_boundaries(enable=True)
            uv_island.unwrap()
            uv_island.pin_boundaries(enable=False)

        return {'FINISHED'}


@Register.OPS.GENERIC
class StraightenGridUVIsland_FindPattern:
    label = "Straighten Grid UV Island (even cols and rows)"
    bl_description = "By finding a 4-cornered grid-like pattern. It won't work in more complex cases (use the other grid straigthen method instead)"
    bl_options = {'REGISTER', 'UNDO'}

    size_method: EnumProperty(
        name="Select",
        items=(
            ('BBOX', "Bounding Box", "Fit the grid to the original bounding box"),
            ('PRESERVE', "Preserve Size", "Preserve the grid width and height")
        ),
        default='BBOX'
    )

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH' and context.active_object.mode == 'EDIT'

    def execute(self, context):
        ''' Requires a user selection. '''

        # Check if UV Editor is active
        if context.area.type != 'IMAGE_EDITOR':
            self.report({'ERROR'}, "UV Editor is not active")
            return {'CANCELLED'}

        # Get the selected UV island
        # bpy.ops.uv.select_linked_pick(deselect=False)

        mesh: Mesh = context.active_object.data
        with UVIslandData(mesh) as uv_island:
            if not uv_island.is_grid(limit_corners=True):
                self.report({'ERROR'}, "UV Island is not Grid-Like!")
                return {'CANCELLED'}
            uv_island.straighten_grid__find_pattern(size_method=self.size_method)
            uv_island.mesh.update()

        return {'FINISHED'}


@Register.OPS.GENERIC
class StraightenGridUVIsland_FollowActiveQuad:
    label = "Straighten Grid UV Island"
    bl_description = "By using follow active quad"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH' and context.active_object.mode == 'EDIT'

    def execute(self, context):
        ''' Requires a user selection. '''

        # Check if UV Editor is active
        if context.area.type != 'IMAGE_EDITOR':
            self.report({'ERROR'}, "UV Editor is not active")
            return {'CANCELLED'}

        # Get the selected UV island
        # bpy.ops.uv.select_linked_pick(deselect=False)

        mesh: Mesh = context.active_object.data
        with UVIslandData(mesh) as uv_island:
            if not uv_island.is_grid(limit_corners=False):
                self.report({'ERROR'}, "UV Island is not Grid-Like!")
                return {'CANCELLED'}
            uv_island.straighten_grid__follow_active_quad()
            uv_island.mesh.update()

        return {'FINISHED'}


@Register.OPS.GENERIC
class StraightenRadialUVIsland:
    label = "Straighten Radial UV Island"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH' and context.active_object.mode == 'EDIT'

    def execute(self, context):
        ''' Requires a user selection. '''

        # Check if UV Editor is active
        if context.area.type != 'IMAGE_EDITOR':
            self.report({'ERROR'}, "UV Editor is not active")
            return {'CANCELLED'}

        # Get the selected UV island
        # bpy.ops.uv.select_linked_pick(deselect=False)

        mesh: Mesh = context.active_object.data
        with UVIslandData(mesh) as uv_island:
            if not uv_island.is_radial():
                self.report({'ERROR'}, "UV Island is not Radial-Like!")
                return {'CANCELLED'}
            uv_island.straighten_radial()
            uv_island.mesh.update()

        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(SmartStraightenUVIsland.bl_idname)
    self.layout.operator(StraightenUVIslandBorders.bl_idname)
    self.layout.operator(StraightenGridUVIsland_FindPattern.bl_idname)
    self.layout.operator(StraightenGridUVIsland_FollowActiveQuad.bl_idname)
    self.layout.operator(StraightenRadialUVIsland.bl_idname)

def register():
    bpy.types.IMAGE_MT_uvs.append(menu_func)

def unregister():
    bpy.types.IMAGE_MT_uvs.remove(menu_func)
