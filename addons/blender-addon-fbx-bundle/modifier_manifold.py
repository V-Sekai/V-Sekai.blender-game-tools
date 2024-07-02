import bpy, bmesh
import math
import imp

from . import modifier

imp.reload(modifier)

class Settings(modifier.Settings):
    pass

class Modifier(modifier.Modifier):
    label = "Force Manifold Mesh"
    id = "manifold"
    url = "http://renderhjs.net/fbxbundle/#modifier_manifold"

    def __init__(self):
        super().__init__()

    def draw(self, layout):
        super().draw(layout)
        
    def process_objects(self, name, objects):
        new_objects = []
        for obj in objects:
            new_objects.append(obj)

            # Select
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(state=True)
            bpy.context.view_layer.objects.active = obj

            # Switch to edit mode to apply print3d operations
            bpy.ops.object.mode_set(mode='EDIT')

            bpy.ops.mesh.print3d_check_all()
            bpy.ops.mesh.print3d_clean_non_manifold()

            # Switch back to object mode after applying print3d operations
            bpy.ops.object.mode_set(mode='OBJECT')

            new_objects.append(bpy.context.object)

        return new_objects
