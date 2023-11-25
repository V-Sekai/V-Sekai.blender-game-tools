import bmesh
from mathutils import Matrix, Vector, Quaternion
from bpy.types import Object
from typing import List

from uvflow.utils.decorators import time_it


@time_it
def apply_scale(objects: List[Object]):
    prev_scale = {}
    for obj in objects:
        prev_scale[obj.name] = obj.scale.copy()
        if obj.scale != (1, 1, 1):
            mat = Matrix.LocRotScale(Vector((0, 0, 0)), Quaternion((0, 0, 0, 0)), obj.scale)
            bm = bmesh.from_edit_mesh(obj.data)
            bm.transform(mat)
            bm.free()
    return prev_scale


@time_it
def restore_scale(objects: List[Object], prev_scales):
    for obj in objects:
        if obj.scale != (1, 1, 1):
            for i in range(3):
                scale = prev_scales[obj.name]
                if [i] != 0:
                    scale[i] = 1 / scale[i]
            mat = Matrix.LocRotScale(Vector((0, 0, 0)), Quaternion((0, 0, 0, 0)), scale)
            bm = bmesh.from_edit_mesh(obj.data)
            bm.transform(mat)
            bm.free()