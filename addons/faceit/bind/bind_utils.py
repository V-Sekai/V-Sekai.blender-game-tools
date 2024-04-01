import bpy
import bmesh

from ..core.modifier_utils import get_modifiers_of_type
from ..core import mesh_utils
from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils


def select_vertices_outside_face_hull(obj, face_hull):
    '''Removes all weights outside of the facial area on the main face object.
    Parameters:
        @face_obj: the object
        @face_hull: the convex hull that encompasses the face
    '''
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    # deselect all verts:
    for f in bm.faces:
        f.select = False
    bm.select_flush(False)
    # select all verts that are inside the facial hull
    # false positives included due to rounding errors
    for v in bm.verts:
        pt = obj.matrix_world @ v.co
        if mesh_utils.is_inside_dot(pt, face_hull):
            v.select = True
    if any([v.select for v in bm.verts]):
        # SelectionIslands finds and stores selected and non-selected islands
        selection_islands = mesh_utils.SelectionIslands(bm.verts, selection_state=True)
        _selected_islands = selection_islands.get_islands()

        def _keep_only_biggest_island(islands, select_value):
            '''keep only the biggest island, all smaller should be added to/ removed from selection/non-selection
            @islands (list) : list of list of vertices
            @select_value (Bool) : add to selection or remove from selection
            '''
            if len(islands) > 1:
                biggest = max(islands, key=lambda x: len(x))
                for i in islands:
                    if len(i) < len(biggest):
                        for v in i:
                            v.select_set(select_value)
        # keep only the biggest island, the rest should be removed from selection
        _keep_only_biggest_island(_selected_islands, select_value=False)
        bm.select_flush(True)
        bm.select_flush(False)
        bm.to_mesh(obj.data)
        bm.free()
        # sometimes single verts get ignore by the selectionislands class, remove by shrink grow selection once
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_less()
        bpy.ops.mesh.select_more()
        bpy.ops.object.mode_set(mode='OBJECT')
        # assign all vertices outside of the hull to the DEF-face vertex group
        v_face_inv = [v.index for v in obj.data.vertices if not v.select]
    else:
        v_face_inv = [v.index for v in obj.data.vertices]
    vg_utils.assign_vertex_grp(obj, v_face_inv, 'DEF-face', overwrite=True)
    mesh_utils.select_vertices(obj)


def scale_bind_objects(factor, objects, reverse=False,):
    # set transform pivot to 3d cursor in case scaling has to be altered

    scale_factor = (factor,) * 3 if not reverse else (1 / factor,) * 3
    futils.clear_object_selection()
    # select all facial objects
    for obj in objects:
        futils.set_active_object(obj.name)
    bpy.ops.transform.resize(value=scale_factor, orient_type='GLOBAL')


def data_transfer_vertex_groups(obj_from, obj_to, apply=True, method=''):
    futils.clear_object_selection()
    futils.set_active_object(obj_to.name)

    # create, setup data transfer modifier
    data_mod = obj_to.modifiers.new(name='DataTransfer', type='DATA_TRANSFER')
    data_mod.object = obj_from
    data_mod.use_vert_data = True
    data_mod.data_types_verts = {'VGROUP_WEIGHTS'}

    if method:
        data_mod.vert_mapping = method
    else:
        if get_modifiers_of_type(obj_to, 'MIRROR'):
            data_mod.vert_mapping = 'NEAREST'
        else:
            data_mod.vert_mapping = 'TOPOLOGY'

    safe_count = 100
    while obj_to.modifiers.find(data_mod.name) != 0:
        bpy.ops.object.modifier_move_up(modifier=data_mod.name)
        if safe_count <= 0:
            break
        safe_count -= 1

    bpy.ops.object.datalayout_transfer(modifier=data_mod.name)

    if apply:

        if bpy.app.version >= (2, 90, 0):
            bpy.ops.object.modifier_apply(modifier=data_mod.name)
        else:
            bpy.ops.object.modifier_apply(apply_as='DATA', modifier=data_mod.name)

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.object.vertex_group_clean(group_select_mode='ALL')
        bpy.ops.object.mode_set(mode='OBJECT')


def split_by_faceit_groups(obj):
    '''Split the object into parts by assigned faceit vertex groups'''
    futils.clear_object_selection()
    futils.set_active_object(obj.name)
    for grp in obj.vertex_groups:
        if 'faceit_' in grp.name:
            vs = vg_utils.get_verts_in_vgroup(obj, grp.name)
            if grp.name == 'faceit_main':
                # get the vertices that are only in the main group
                vs = [v for v in vs if len(v.groups) == 1]
            if not vs:
                obj.vertex_groups.remove(grp)
                continue
            if len(vs) == len(obj.data.vertices):
                # No need to split, the object is already separated
                break
            bpy.ops.object.mode_set(mode='EDIT')
            mesh_utils.select_vertices(obj, [v.index for v in vs], deselect_others=True)
            bpy.ops.mesh.separate(type='SELECTED')
            bpy.ops.object.mode_set()

    split_objects = [split_obj for split_obj in bpy.context.selected_objects if split_obj.type == 'MESH']
    for s_obj in split_objects:
        if vg_utils.vertex_group_sanity_check(obj):
            vg_utils.remove_zero_weights_from_verts(s_obj)
            vg_utils.remove_unused_vertex_groups(s_obj)
    return split_objects


def split_object(obj):

    futils.clear_object_selection()
    futils.set_active_object(obj.name)

    bpy.ops.object.mode_set(mode='EDIT')

    bpy.ops.mesh.separate(type='LOOSE')

    bpy.ops.object.mode_set()

    split_objects = [split_obj for split_obj in bpy.context.selected_objects if split_obj.type == 'MESH']
    for s_obj in split_objects:
        if vg_utils.vertex_group_sanity_check(obj):
            vg_utils.remove_zero_weights_from_verts(s_obj)
            vg_utils.remove_unused_vertex_groups(s_obj)

    return split_objects


def create_facial_hull(context, lm_obj):
    '''Duplicates Landmarks mesh and creates a convex hull object from it. Encompasses the face.'''

    # duplicate facial setup - create facial hull as weight envelope
    futils.clear_object_selection()
    futils.set_active_object(lm_obj.name)
    bpy.ops.object.duplicate_move()
    face_hull = context.object
    # apply the mirror mod on hull
    for mod in face_hull.modifiers:
        if mod.name == 'Mirror':
            bpy.ops.object.modifier_apply(modifier=mod.name)
    # make convex hull from the mesh
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.convex_hull()
    # scale up slightly to include whole deform area
    context.scene.tool_settings.transform_pivot_point = 'MEDIAN_POINT'
    bpy.ops.transform.resize(value=(2, 1.1, 1.2))

    bpy.ops.object.mode_set(mode='OBJECT')

    return face_hull
