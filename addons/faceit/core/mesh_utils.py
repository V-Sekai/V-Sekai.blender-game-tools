import bpy
import bmesh
from math import pi, acos


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
    inside = angle < 90-tolerance

    return inside


class SelectionIslands:
    '''
    Traces the graph of edges and verts to find the islands
    @verts : bmesh vertices
    @selection_islands : the islands of adjacent selected vertices
    @non_selected_islands : the islands of adjacent non selected vertices
    '''

    verts = []
    selected_islands = []
    non_selected_islands = []
    # wether selected or non selected islands should be searched

    def __init__(self, bmesh_verts):
        self.verts = bmesh_verts
        self.sort_selection_start(self.verts)

    def make_vert_paths(self, verts, search_selected):
        # Init a set for each vertex
        result = {v: set() for v in verts}
        # Loop over vertices to store connected other vertices
        for v in verts:
            for e in v.link_edges:
                other = e.other_vert(v)
                if other.select == search_selected:
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

    def make_islands(self, bm_verts, search_selected):
        paths = self.make_vert_paths(bm_verts, search_selected)
        result = []
        found = True
        while found:
            try:
                # Get one input as long there is one
                vert = next(iter(paths.keys()))
                # Deplete the paths dictionary following this starting vertex
                result.append(self.make_island(vert, paths))
            except:
                found = False
        return result

    def sort_selection_start(self, bm_verts):
        non_selected_verts = []
        selected_verts = []
        for v in bm_verts:
            if v.select:
                selected_verts.append(v)
            else:
                non_selected_verts.append(v)
        self.selected_islands = self.make_islands(selected_verts, search_selected=True)
        self.non_selected_islands = self.make_islands(non_selected_verts, search_selected=False)

    def get_selected_islands(self):
        return self.selected_islands

    def get_non_selected_islands(self):
        return self.non_selected_islands

    def get_island_count(self):
        return len(self.non_selected_islands + self.selected_islands)


def select_vertices(obj, vs=[], flush_selection=False):
    '''
    select vertices in a mesh (OBJECT mode required)
    @obj: the object that holds mesh data
    @vs : vert subset to select
    '''
    verts = vs or obj.data.vertices
    for v in verts:
        v.select = True
    if flush_selection:
        bpy.ops.object.mode_set(mode='EDIT')
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bm.select_mode = {'VERT', 'EDGE', 'FACE'}
        bm.select_flush_mode()
        bpy.ops.object.mode_set()


def unselect_flush_vert_selection(obj, vs=[]):
    '''
    Unselect vertices in a mesh (OBJECT mode required)
    @obj: the object that holds mesh data
    @vs : vert subset to unselect
    '''
    mesh = obj.data
    verts = mesh.vertices
    faces = mesh.polygons  # not faces!
    edges = mesh.edges
    # vertices can be selected
    # to deselect vertices you need to deselect faces(polygons) and edges at first
    for f in faces:
        f.select = False
    for e in edges:
        e.select = False
    try:
        verts = vs if vs else verts
        for v in verts:
            v.select = False
    except:
        print('deselection failed')
