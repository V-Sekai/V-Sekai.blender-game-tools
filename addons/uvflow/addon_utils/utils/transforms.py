import bmesh
from mathutils import Matrix, Vector, Quaternion
from bpy.types import Object
from typing import List

def apply_scale(objects: List[Object]):
    prev_scale = {}
    for obj in objects:
        prev_scale[obj.name] = obj.scale.copy()
        mat = Matrix.LocRotScale(Vector((0, 0, 0)), Quaternion((0, 0, 0, 0)), obj.scale)
        bm = bmesh.from_edit_mesh(obj.data)
        bm.transform(mat)
        bm.free()
    return prev_scale

def restore_scale(objects: List[Object], prev_scales):
    for obj in objects:
        for i in range(3):
            scale = prev_scales[obj.name]
            if [i] != 0:
                scale[i] = 1 / scale[i]
        mat = Matrix.LocRotScale(Vector((0, 0, 0)), Quaternion((0, 0, 0, 0)), scale)
        bm = bmesh.from_edit_mesh(obj.data)
        bm.transform(mat)
        bm.free()