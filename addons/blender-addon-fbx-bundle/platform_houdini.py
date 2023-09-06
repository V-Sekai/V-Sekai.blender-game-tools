import bpy
import bmesh
import operator
import mathutils
import addon_utils

from . import platform

class Platform(platform.Platform):
	extension = 'obj'


	def __init__(self):
		super().__init__()
		

	def is_valid(self):

		return True, ""


	def file_export(self, path):
		bpy.ops.export_scene.obj(
			filepath		=path,
			use_selection=True,
			use_mesh_modifiers=True,
			use_smooth_groups=True,
			use_triangles=False,
			use_uvs=True,
			use_materials=True,
			global_scale=1,
			axis_forward = '-Z',
			axis_up = 'Y'


		)
