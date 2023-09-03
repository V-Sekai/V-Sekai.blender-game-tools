import bpy, bmesh
from bpy.types import Context
from uvflow.prefs import UVFLOW_Preferences

def get_selected_polys(objects):
    selected = {}
    for obj in objects:
        bm = bmesh.from_edit_mesh(obj.data)
        faces = []
        for face in bm.faces:
            if face.select:
                faces.append(face.index)
        selected[obj.name] = faces
        bm.free()
    return selected

def restore_selection(objects, selection):
    bpy.ops.mesh.select_all(False, action='DESELECT')
    for obj in objects:
        if selection[obj.name]:
            bm = bmesh.from_edit_mesh(obj.data)
            for face in bm.faces:
                if face.index in selection[obj.name]:
                    face.select_set(True)
            bm.free()

def get_selected_materials(context: Context, prefs: UVFLOW_Preferences):
    materials = set()
    if prefs.pack_includes == 'MATERIAL':
        if context.mode == 'EDIT':
          objects = [x for x in bpy.data.objects if x.mode == 'EDIT']
          for obj in objects:
              bm = bmesh.from_edit_mesh(obj.data)
              for face in bm.faces:
                  if face.select:
                      materials.add(obj.material_slots[face.material_index].material)
              bm.free()
        else:
          materials.add(context.active_object.active_material)
    return materials