from bpy import types as bpy_types

from enum import Enum


class PropertyGroupSupportedTypes(Enum):
    WINDOW_MANAGER = bpy_types.WindowManager
    TEMPORAL = WINDOW_MANAGER
    SCENE = bpy_types.Scene
    
    OBJECT = bpy_types.Object
    MESH = bpy_types.Mesh
    
    # To be extended based on needs.
