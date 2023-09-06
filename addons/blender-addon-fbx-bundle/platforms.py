import bpy
import bmesh
import operator
import mathutils
import sys

from mathutils import Vector

from . import platform_unity
from . import platform_gltf
from . import platform_unreal
from . import platform_blender
from . import platform_obj
from . import platform_houdini


import imp
imp.reload(platform_unity)
imp.reload(platform_gltf)
imp.reload(platform_unreal)
imp.reload(platform_blender)
imp.reload(platform_obj)
imp.reload(platform_houdini)


platforms = {
	'UNITY' : platform_unity.Platform(),
	'GLTF' : platform_gltf.Platform(),
	'UNREAL' : platform_unreal.Platform(),
	'BLENDER' : platform_blender.Platform(),
	'OBJ' : platform_obj.Platform(),
	'HOUDINI' : platform_houdini.Platform()
}
