from ..core.modifier_utils import get_faceit_armature_modifier
from . import faceit_utils as futils


def remove_unused_vertex_groups_thresh(obj, thres=0):
    v_groups_with_use = []
    vg_count = len(obj.vertex_groups)
    for v in obj.data.vertices:
        for g in v.groups:
            if g.weight > thres:
                if g not in v_groups_with_use:
                    # Safety Check
                    if g.group < vg_count:
                        v_groups_with_use.append(obj.vertex_groups[g.group])

    for grp in obj.vertex_groups:
        if grp not in v_groups_with_use:
            obj.vertex_groups.remove(grp)


def vertex_group_sanity_check(obj):
    '''Check if the vertex groups data is matching the actual objects data. This fixes a Blender indexing error and follow-up errors in faceit.'''
    vg_count = len(obj.vertex_groups)
    for v in obj.data.vertices:
        if any(g.group > vg_count for g in v.groups):
            print(f'Index Error on Object {obj.name}. Can\'t remove all zero weights. This shouldn\'t affect results')
            return False
    return True


def remove_unused_vertex_groups(obj) -> None:
    '''Remove all vertex groups that are not assigned to any vertices'''
    for vg in obj.vertex_groups:
        if not any(vg.index in [g.group for g in v.groups] for v in obj.data.vertices):
            obj.vertex_groups.remove(vg)


def remove_zero_weights_from_verts(obj, thresh=0.0) -> None:
    '''Clear weights from vertices where they are below the given threshold @thresh'''
    for v in obj.data.vertices:
        for grp_idx in (g.group for g in v.groups if g.weight <= thresh):
            try:
                obj.vertex_groups[grp_idx].remove([v.index])
            except IndexError:
                pass


def get_vertex_groups_from_objects(objects=None) -> list:
    '''Return list of vertex groups for all passed @objects'''
    vg_names = []
    if not objects:
        objects = futils.get_faceit_objects_list()

    for obj in objects:
        if obj.vertex_groups:
            vg_names.extend([vg.name for vg in obj.vertex_groups])
    return list(set(vg_names))


def get_deform_bones_from_armature(armature_obj, use_all=False):
    '''Find all deform bones and return list of their names.
    @armature_obj: obj of type armature
    '''
    deform_groups = []
    if armature_obj:
        if armature_obj.type == 'ARMATURE':
            for b in armature_obj.pose.bones:
                if b.bone.use_deform or use_all:
                    deform_groups.append(b.name)
    return deform_groups


def assign_vertex_grp(obj, vertices, grp_name, overwrite=False, mode='REPLACE'):
    '''
    assigns the vertices to a vertex group
    @obj : the object that holds the mesh
    @vertices : list of vertex indices
    @grp_name : the name of the new vertex group
    @overwrite : wether the vertices should be added to grp or replace existing grp.
    '''
    vert_group = obj.vertex_groups.get(grp_name)

    # create new group if it does not exist
    if not vert_group:
        vert_group = obj.vertex_groups.new(name=grp_name)

    if overwrite:
        # remove all verts in object from the group
        remove_verts_from_grp(obj, vert_group)

    # set active group
    obj.vertex_groups.active_index = vert_group.index
    # assign 1 to all non facial vertices
    vert_group.add(vertices, 1, mode)


def remove_verts_from_grp(obj, vertex_group, vs=None):
    '''
    remove vertices from a vertex group
    @obj : the object that holds the mesh
    @grp_name : the vertex group
    @vs : subset of vertex indices
    '''
    if vs:
        vertex_group.remove(vs)
    else:
        vertex_group.remove(range(len(obj.data.vertices)))


def remove_deform_vertex_grps(obj, armature=None, remove_all=False):
    '''
    Removes all DEF (deform) vertex groups from an object
    @armature: object of type armature
    @obj : the object
    @remove_all : Remove all Vertex Group except faceit groups
    '''
    if not obj.vertex_groups:
        return

    deform_groups = []

    if armature:
        if armature.type == 'ARMATURE':
            deform_groups = get_deform_bones_from_armature(armature_obj=armature)

    for grp in obj.vertex_groups:
        if 'faceit' not in grp.name:
            if not grp.lock_weight:
                if grp.name in deform_groups or remove_all:
                    obj.vertex_groups.remove(grp)


def remove_faceit_vertex_grps(obj):
    '''
    Remove all user defined faceit vertex groups on obj
    @obj : the object
    '''
    if len(obj.vertex_groups) <= 0:
        return
    removed = []
    for grp in obj.vertex_groups:
        if 'faceit' in grp.name:
            removed.append(grp.name)
            obj.vertex_groups.remove(grp)
    return removed


def remove_all_weight(obj, vs=None, armature_obj=None):
    '''
    remove all weights from DEF groups for passed vertices
    @obj : object to that holds groups and mesh
    @vs : the vertices that should be unweighted
    '''
    deform_groups = []

    if not armature_obj:
        arm_mod = get_faceit_armature_modifier(obj)
        if arm_mod:
            armature_obj = arm_mod.object

    if armature_obj:
        if armature_obj.type == 'ARMATURE':
            deform_groups = get_deform_bones_from_armature(armature_obj)

    if not obj.vertex_groups:
        return
    # either vertex subset to unweight or all
    verts = vs if vs else obj.data.vertices
    for grp in obj.vertex_groups:
        if grp.name in deform_groups:
            grp.remove([v.index for v in verts])


def remove_vgroups_from_verts(obj, vs=None, filter_keep=None):
    # either vertex subset to unweight or all
    verts = vs if vs else obj.data.vertices
    for v in verts:
        for i, v_grp_elem in enumerate(v.groups):
            try:
                if obj.vertex_groups[v_grp_elem.group].name not in filter_keep:
                    v.groups[i].weight = 0
            except IndexError:
                print(f'Index Error on obj {obj.name}. Is it a linked duplicate?')
                break


def get_faceit_vertex_grps(obj, groups_filter=None):
    '''
    check for user defined faceit groups on obj
    returns : list of all faceit groups on obj
    @obj : the object
    @groups_filter : list of vertex groups to check for, keywords alloud
    '''
    if len(obj.vertex_groups) <= 0:
        return []
    faceit_groups = []
    for grp in obj.vertex_groups:
        if groups_filter:
            if any((i == grp.name) for i in groups_filter):
                faceit_groups.append(grp.name)
        else:
            if 'faceit' in grp.name:
                faceit_groups.append(grp.name)
    return faceit_groups


def get_objects_with_vertex_group(vgroup_name, objects=None, get_all=False):
    '''Find objects in the list with the specified vertex group'''
    objects = objects or futils.get_faceit_objects_list()
    if not objects:
        return
    # return only the first occurence of vgroup in objects
    if not get_all:
        try:
            obj = next(iter([obj for obj in objects if vgroup_name in obj.vertex_groups]))
            return obj
        except StopIteration:
            return
    # return all occurences of vgroup in objects
    else:
        found_objects = []
        for obj in objects:
            if vgroup_name in obj.vertex_groups:
                # if obj.vertex_groups.get(vgroup_name):
                found_objects.append(obj)
        return found_objects


def get_verts_in_vgroup(obj, grp_name):
    '''
    get all vertices in a vertex group
    Returns : list of vertices in group, else None
    @obj : object holds group and verts
    @grp_name : the name of the vertex group to get verts from
    '''
    vg_idx = obj.vertex_groups.find(grp_name)
    if vg_idx == -1:
        return
    # get all vertices in faceit group
    return [v for v in obj.data.vertices if vg_idx in [vg.group for vg in v.groups]]


def has_verts_without_grps(obj):
    return any(not v.groups for v in obj.data.vertices)


def invert_vertex_group_weights(obj, vgrp):
    '''Return new vertex group with invertex weights from the given @vgrp'''
    vgroup = obj.vertex_groups.new(name=vgrp.name + '_invert')
    vg_index = vgrp.index

    for i, vert in enumerate(obj.data.vertices):
        available_groups = [v_group_elem.group for v_group_elem in vert.groups]

        inv_weight = 1
        if vg_index in available_groups:
            inv_weight = 1 - vgrp.weight(i)

        vgroup.add([i], inv_weight, 'REPLACE')

    return vgroup


# def join_vertex_groups(ob, vertex_groups=None, new_group_name='GROUP_JOIN'):

#     vgroup = ob.vertex_groups.new(name=new_group_name)
#     vg_indices = [vg.index for vg in ob.vertex_groups if vg.name in vertex_groups]

#     for i, vert in enumerate(ob.data.vertices):
#         # vgroup indices
#         available_groups = [v_group_elem.group for v_group_elem in vert.groups if v_group_elem.group in vg_indices]

#         sum_all_vg = sum([vg.weight(i) for vg in ob.vertex_groups if vg.index in available_groups])

#         if sum_all_vg > 0:
#             vgroup.add([i], sum_all_vg, 'REPLACE')

#     return vgroup
