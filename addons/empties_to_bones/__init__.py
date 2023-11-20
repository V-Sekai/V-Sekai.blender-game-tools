bl_info = {
	"name": "Empties to Bones",
	"author": "Artell",
	"version": (1, 0, 1),
	"blender": (3, 0, 1),
	"location": "3D View > Tool> Empties to Bone",
	"description": "Convert a hierarchy made of empties to an armature with bones",
	"category": "Animation"}

import bpy
from . empties_to_bones import *

classes = (EB_create_armature, EB_PT_menu)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
        
def unregister():
    from bpy.utils import unregister_class    
    for cls in reversed(classes):
        unregister_class(cls)           
