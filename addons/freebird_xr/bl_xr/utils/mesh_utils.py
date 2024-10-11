import bpy
import bmesh

from mathutils.bvhtree import BVHTree

cached_bmesh = None
cached_bvh = None
cached_bmesh_for_ob = None


def get_bmesh(ob=None, skip_cache=False):
    global cached_bmesh, cached_bvh, cached_bmesh_for_ob

    if ob is None:
        ob = bpy.context.view_layer.objects.active

    if cached_bmesh:
        if cached_bmesh_for_ob == ob and cached_bmesh.is_valid and not skip_cache:
            # don't need to check if it's the same object, since changing the object requires an EDIT->OBJECT->EDIT transition
            # which will invalidate the bmesh anyway

            try:
                if len(cached_bmesh.verts) > 0:
                    cached_bmesh.verts[0]
            except IndexError:
                _ensure_bmesh_lookup_table()

            return cached_bmesh

        cached_bmesh.free()

    if ob.mode == "EDIT":
        bm = bmesh.from_edit_mesh(ob.data)
    else:
        bm = bmesh.new()
        bm.from_mesh(ob.data)

    cached_bmesh = bm

    _ensure_bmesh_lookup_table()

    cached_bvh = BVHTree.FromBMesh(bm)
    cached_bmesh_for_ob = ob

    return bm


def _ensure_bmesh_lookup_table():
    cached_bmesh.verts.ensure_lookup_table()
    cached_bmesh.edges.ensure_lookup_table()
    cached_bmesh.faces.ensure_lookup_table()


def get_bvh():
    return cached_bvh


def get_bmesh_elements(ob=None):
    if ob is None:
        ob = bpy.context.view_layer.objects.active
    bm = get_bmesh(ob)

    vert_mode, edge_mode, _ = bpy.context.scene.tool_settings.mesh_select_mode
    if vert_mode:
        return bm.verts
    elif edge_mode:
        return bm.edges
    else:
        return bm.faces


def reindex_bmesh():
    global cached_bvh

    bm = get_bmesh()
    _ensure_bmesh_lookup_table()

    cached_bvh = BVHTree.FromBMesh(bm)


def sync_bmesh_selection(ob):
    vert_mode, edge_mode, _ = bpy.context.scene.tool_settings.mesh_select_mode

    bm_collection = None
    mesh_collection = None

    bm = get_bmesh(ob)

    if vert_mode:
        bm_collection = bm.verts
        mesh_collection = ob.data.vertices
    elif edge_mode:
        bm_collection = bm.edges
        mesh_collection = ob.data.edges
    else:
        bm_collection = bm.faces
        mesh_collection = ob.data.polygons

    selected_indices = [el.index for el in bm_collection if el.select]

    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")

    for idx in selected_indices:
        mesh_collection[idx].select = True

    bpy.ops.object.mode_set(mode="EDIT")


def get_mesh_mode():
    vert_mode, edge_mode, face_mode = bpy.context.scene.tool_settings.mesh_select_mode
    if vert_mode:
        return "VERT"
    elif edge_mode:
        return "EDGE"
    elif face_mode:
        return "FACE"
