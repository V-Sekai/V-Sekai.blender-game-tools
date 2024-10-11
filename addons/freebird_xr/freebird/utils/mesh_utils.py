import bpy
import bmesh
import numpy as np

from bl_xr.utils import get_mesh_mode, get_bmesh_elements

from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree

bmesh_copy = None
bvh_copy = None


def reset_scale(ob):
    bpy.context.view_layer.objects.active = ob

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.object.mode_set(mode="OBJECT")

    # so that bevel does not get scaled along the axes
    mesh = ob.data

    # read the current verts
    verts = np.empty(3 * len(mesh.vertices), "f")
    mesh.vertices.foreach_get("co", verts)

    verts = np.reshape(verts, (-1, 3))

    # transform the verts
    coords4d = np.ones((len(mesh.vertices), 4), "f")
    coords4d[:, :-1] = verts

    bbox = np.array([ob.matrix_world @ Vector(v) for v in ob.bound_box], "f")

    coords = np.einsum("ij,aj->ai", ob.matrix_world, coords4d)[:, :-1]
    mid_pt = np.average(bbox, axis=0)
    coords -= mid_pt
    coords = np.reshape(coords, -1)

    # apply the transformed verts
    mesh.vertices.foreach_set("co", coords)

    # reset the object transform
    ob.location = Vector(mid_pt)
    ob.scale = Vector((1, 1, 1))

    # flush the changes
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.object.mode_set(mode="OBJECT")


def make_bmesh_copy():
    global bmesh_copy, bvh_copy

    select_mode = get_mesh_mode()

    elements = get_bmesh_elements()
    indices = [e.index for e in elements if e.select]

    # clear the current selection in the mesh (not bmesh)
    bpy.ops.mesh.select_mode(type="VERT")
    bpy.ops.mesh.select_all(action="DESELECT")

    bpy.ops.mesh.select_mode(type=select_mode)
    bpy.ops.object.mode_set(mode="OBJECT")

    # re-select the previous selection in the mesh
    mesh = bpy.context.view_layer.objects.active.data
    if select_mode == "VERT":
        for idx in indices:
            mesh.vertices[idx].select = True
    elif select_mode == "EDGE":
        for idx in indices:
            mesh.edges[idx].select = True
    elif select_mode == "FACE":
        for idx in indices:
            mesh.polygons[idx].select = True

    # keep a copy of the previous mesh, to reset after each interactive operation frame
    bmesh_copy = bmesh.new()
    bmesh_copy.from_mesh(mesh)

    bmesh_copy.verts.ensure_lookup_table()
    bmesh_copy.edges.ensure_lookup_table()
    bmesh_copy.faces.ensure_lookup_table()

    bvh_copy = BVHTree.FromBMesh(bmesh_copy)

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type=select_mode)


def get_bmesh_copy():
    return bmesh_copy


def get_bvh_copy():
    return bvh_copy


def revert_to_bmesh_copy():
    select_mode = get_mesh_mode()
    ob = bpy.context.view_layer.objects.active

    if ob.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    bmesh_copy.to_mesh(ob.data)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type=select_mode)


def free_bmesh_copy():
    global bmesh_copy

    if bmesh_copy is not None:
        bmesh_copy.free()
        bmesh_copy = None
