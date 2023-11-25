import bpy, bmesh
from bpy.types import Context, Mesh, Object

from collections import defaultdict

from uvflow.utils.decorators import time_it

@time_it
def get_selected_faces(objects: list[Object]):
    selected: dict[str, list[int]] = defaultdict(list)
    for obj in objects:
        bm = bmesh.from_edit_mesh(obj.data)
        add_face_index = selected[obj.name].append
        {add_face_index(face.index) for face in bm.faces if face.select}
        bm.free()
    return selected


@time_it
def restore_face_selection(objects: list[Object], selection: dict[str, list[int]]):
    bpy.ops.mesh.select_all(False, action='DESELECT')
    for obj in objects:
        face_sel = selection[obj.name]
        if len(face_sel) == 0:
            continue
        bm = bmesh.from_edit_mesh(obj.data)
        bm_faces = bm.faces
        bm_faces.ensure_lookup_table()
        sel_face = lambda face_index: bm_faces[face_index].select_set(True)
        {sel_face(face_index) for face_index in face_sel}
        bm.free()
