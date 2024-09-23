import bpy
import blf
import gpu
import math
from collections import deque
from gpu_extras.batch import batch_for_shader
import bl_math
from mathutils import Matrix, Vector, Euler, Quaternion

class OverlayGraph:
	def __init__(self, context, max_data, draw_size, target_range_center):
		self.handle = None
		self.max_data = max_data
		self.data = deque(maxlen=max_data)
		self.area = context.area

		self.draw_size = Vector((draw_size, draw_size * 0.4, 0))
		if bpy.app.version < (4, 0, 0):
				self.shader = gpu.shader.from_builtin("2D_UNIFORM_COLOR")
		else:
			self.shader = gpu.shader.from_builtin("UNIFORM_COLOR")
		
		self.vertices = [(0, 0)] * max_data
		self.batch = batch_for_shader(self.shader, 'LINE_STRIP', {"pos": self.vertices})		
		self.min_value = target_range_center * 0.5
		self.max_value = target_range_center * 2
		self.aspect = 4.0
		self.enable()


	def write(self, datapoint):
		self.data.append(datapoint)
	
		self.vertices = []
		for i, y in enumerate(self.data):
			# Scale y based on the min and max values
			y = bl_math.clamp(y, self.min_value, self.max_value)
			y = self.draw_size.y * ((y - self.min_value) / (self.max_value - self.min_value))			
			self.vertices.append((self.area.width - self.max_data - 32 + i, y + 32))
			
		self.batch = batch_for_shader(self.shader, 'LINE_STRIP', {"pos": self.vertices})
		

	def draw_callback(self, context):
		if context.area != self.area:
			return
		gpu.state.blend_set('ALPHA')
		self.shader.bind()
		self.shader.uniform_float("color", (0.980, 0.751, 0.00, 0.80))
		self.batch.draw(self.shader)
		
	def enable(self):
		if self.handle is None:
			self.handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback, (bpy.context,), 'WINDOW', 'POST_PIXEL')

	def disable(self):
		if self.handle is not None:
			bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')
			self.handle = None