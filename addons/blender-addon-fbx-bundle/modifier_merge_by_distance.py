import bpy, bmesh
import math
import imp

from . import modifier

imp.reload(modifier)

class Settings(modifier.Settings):
    pass

class Modifier(modifier.Modifier):
    label = "Merge by distance"
    id = "merge_doubles"
    url = "http://renderhjs.net/fbxbundle/#merge_by_distance"

    def __init__(self):
        super().__init__()

    def draw(self, layout):
        super().draw(layout)
        
    def process_objects(self, name, objects):
        new_objects = []
        for obj in objects:
            # Check if the object is in the current view layer
            if obj.name in bpy.context.view_layer.objects:
                new_objects.append(obj)

                # Select
                bpy.ops.object.select_all(action="DESELECT")
                try:
                    obj.select_set(state=True)
                    bpy.context.view_layer.objects.active = obj

                    # Ensure the object is a mesh
                    if obj.type == 'MESH':
                        # Switch to edit mode to apply operations
                        bpy.ops.object.mode_set(mode='EDIT')

                        # Merge by distance
                        bpy.ops.mesh.select_all(action='SELECT')
                        bpy.ops.mesh.remove_doubles(threshold=0.0001)  # Adjust the threshold as needed

                        # Switch back to object mode after applying operations
                        bpy.ops.object.mode_set(mode='OBJECT')

                    new_objects.append(bpy.context.object)
                except RuntimeError as e:
                    print(f"RuntimeError: {e}")
            else:
                print(f"Object '{obj.name}' is not in the current view layer and cannot be selected.")
        return new_objects

