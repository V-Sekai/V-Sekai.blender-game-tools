from math import acos, pi

import bmesh
import bpy

from .vgroup_utils import get_verts_in_vgroup


def get_max_dim_in_direction(obj, direction, vertex_group_name=None):
    '''Get the furthest point of the mesh in a specified direction'''
    # world matrix
    mat = obj.matrix_world
    far_distance = 0
    far_point = direction

    if vertex_group_name:
        vs = get_verts_in_vgroup(obj, vertex_group_name)
    else:
        vs = obj.data.vertices

    for v in vs:
        point = mat @ v.co
        temp = direction.dot(point)
        # new high?
        if far_distance < temp:
            far_distance = temp
            far_point = point
    return far_point


def select_vertices_bmesh(vids, bm, deselect_others=False):
    '''select vertices using the bmesh module'''
    for v in bm.verts:
        if v.index in vids:
            v.select = True
        elif deselect_others:
            v.select = False
    bm.select_flush(True)
    bm.select_flush(False)


def select_vertices(obj, vs=None, deselect_others=False) -> None:
    '''
    select vertices using the bmesh module
    @obj: the object that holds mesh data
    @vs : vert subset to select
    @deselect_others : deselect all other vertices
    '''
    if vs:
        vids = [v.index for v in vs]
    else:
        vids = [v.index for v in obj.data.vertices]
    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
    else:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
    select_vertices_bmesh(vids, bm, deselect_others)
    if obj.mode == 'EDIT':
        bmesh.update_edit_mesh(obj.data)
    else:
        bm.to_mesh(obj.data)
        bm.free()


def get_object_center(obj):
    '''Find the center of a mesh object using the outside cage.'''
    vcos = [obj.matrix_world @ v.co for v in obj.data.vertices]

    def findCenter(vcos):
        return (max(vcos) + min(vcos)) / 2

    x, y, z = [[v[i] for v in vcos] for i in range(3)]
    center = [findCenter(axis) for axis in [x, y, z]]
    return center


def is_inside_dot(target_pt_global, mesh_obj, tolerance=0.05):
    '''
    checks if a point is inside a surface, by the dot product method
    @target_pt_global : the point to check
    @mesh_obj : the mesh as surface
    @tolerance : a threshold as inside tolerance
    '''
    # Convert the point from global space to mesh local space
    target_pt_local = mesh_obj.matrix_world.inverted() @ target_pt_global

    # Find the nearest point on the mesh and the nearest face normal
    _, pt_closest, face_normal, _ = mesh_obj.closest_point_on_mesh(target_pt_local)

    # Get the target-closest pt vector
    target_closest_pt_vec = (pt_closest - target_pt_local).normalized()

    # Compute the dot product = |a||b|*cos(angle)
    dot_prod = target_closest_pt_vec.dot(face_normal)

    # Get the angle between the normal and the target-closest-pt vector (from the dot prod)
    angle = acos(min(max(dot_prod, -1), 1)) * 180 / pi

    # Allow for some rounding error
    inside = angle < 90 - tolerance

    return inside


class GeometryIslands:
    """
    Traces the graph of edges and verts to find the islands
    @verts : bmesh vertices
    @islands : list of connected vertex islands, i.e. surfaces
    """

    verts = []
    islands = []
    # wether selected or non selected islands should be searched

    def __init__(self, bmesh_verts):
        self.verts = bmesh_verts
        self.islands = self.make_islands(self.verts)

    def make_vert_paths(self, verts):
        # Init a set for each vertex
        result = {v: set() for v in verts}
        # Loop over vertices to store connected other vertices
        for v in verts:
            for e in v.link_edges:
                other = e.other_vert(v)
                result[v].add(other)
        return result

    def make_island(self, starting_vert, paths):
        # Initialize the island
        island = [starting_vert]
        # Initialize the current vertices to explore
        current = [starting_vert]
        follow = True
        while follow:
            # Get connected vertices that are still in the paths
            eligible = set([v for v in current if v in paths])
            if len(eligible) == 0:
                follow = False  # Stops if no more
            else:
                # Get the corresponding links
                next = [paths[i] for i in eligible]
                # Remove the previous from the paths
                for key in eligible:
                    island.append(key)
                    paths.pop(key)
                # Get the new links as new inputs
                current = set([vert for sub in next for vert in sub])
        return island

    def make_islands(self, bm_verts):
        paths = self.make_vert_paths(bm_verts)
        result = []
        found = True
        while found:
            try:
                # Get one input as long there is one
                vert = next(iter(paths.keys()))
                # Deplete the paths dictionary following this starting vertex
                result.append(self.make_island(vert, paths))
            except StopIteration:
                found = False
        return result

    def get_islands(self):
        return self.islands

    def get_island_count(self):
        return len(self.islands)

    def get_island_by_vertex_index(self, index):
        for island in self.islands:
            if any(v.index == index for v in island):
                return island
        # return next((x for x in self.islands if any(index == v.index for v in x)), None)

    def get_selected_islands(self):
        for island in self.islands:
            if any(v.select for v in island):
                yield island

    def select_linked(self):
        ''' Select all linked vertices for surfaces that have a partial selection'''
        for island in self.get_selected_islands():
            for v in island:
                v.select = True


class SelectionIslands(GeometryIslands):
    '''
    Traces the graph of edges and verts to find the islands
    @verts : bmesh vertices
    @selection_islands : the islands of adjacent selected vertices
    @non_selected_islands : the islands of adjacent non selected vertices
    '''

    def __init__(self, bmesh_verts, selection_state):
        self.verts = [v for v in bmesh_verts if v.select == selection_state]
        self.islands = self.make_islands(self.verts, selection_state)

    def make_vert_paths(self, verts, selection_state):
        # Init a set for each vertex
        result = {v: set() for v in verts}
        # Loop over vertices to store connected other vertices
        for v in verts:
            for e in v.link_edges:
                other = e.other_vert(v)
                if other.select == selection_state:
                    result[v].add(other)
        return result

    def make_islands(self, bm_verts, selection_state):
        paths = self.make_vert_paths(bm_verts, selection_state)
        result = []
        found = True
        while found:
            try:
                # Get one input as long there is one
                vert = next(iter(paths.keys()))
                # Deplete the paths dictionary following this starting vertex
                result.append(self.make_island(vert, paths))
            except StopIteration:
                found = False
        return result
