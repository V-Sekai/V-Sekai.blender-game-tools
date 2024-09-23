import bpy
import blf
import gpu
import math
from collections import deque
from gpu_extras.batch import batch_for_shader

class OverlayConsole:
	def __init__(self, context, max_lines, font_size, draw_box):
		# Globals
		self.handle = None
		self.max_lines = max_lines
		self.data = deque(maxlen=max_lines)
		self.area = context.area
		self.draw_box = draw_box
		self.dpi = context.preferences.system.dpi

		# Font
		self.font_id = 0
		self.font_size = font_size
		self.real_size = self.font_size * (self.dpi / 72.0)
		blf.size(self.font_id, self.real_size)
		self.line_height = blf.dimensions(self.font_id, "Tp")[1] * 1.1

		# Console Background Box
		if self.draw_box:
			height = 15 + self.max_lines * self.line_height + 15
			if bpy.app.version < (4, 0, 0):
				self.shader = gpu.shader.from_builtin("2D_UNIFORM_COLOR")
			else:
				self.shader = gpu.shader.from_builtin("UNIFORM_COLOR")
			vertices = [(0, 0), (0, height), (context.area.width, height), (context.area.width, 0)]
			indices = [(0, 1, 2), (0, 2, 3)]
			self.batch = batch_for_shader(self.shader, 'TRIS', {"pos": vertices}, indices=indices)

		self.enable()


	def write(self, text):
		self.data.appendleft(text)


	def draw_callback(self, context):
		if context.area != self.area:
			return

		if self.draw_box:
			# Draw Background Box
			gpu.state.blend_set('ALPHA')
			self.shader.bind()
			self.shader.uniform_float("color", (0.0, 0.0, 0.0, 0.6))  # RGBA color
			self.batch.draw(self.shader)
		else:
			blf.enable(self.font_id, blf.SHADOW)
			blf.shadow(self.font_id, 3, 0, 0, 0, 1)  # 5px offset, black color, alpha 1
			blf.shadow_offset(self.font_id, 2, -2)  # 3px offset to bottom-right

		blf.size(self.font_id, self.real_size)
		blf.color(self.font_id, 0.980, 0.751, 0.00, 1.00)

		y = 15
		for line in self.data:
			blf.position(self.font_id, 15, y, 0)
			blf.draw(self.font_id, line)
			y += self.line_height

	def enable(self):
		if self.handle is None:
			self.handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback, (bpy.context,), 'WINDOW', 'POST_PIXEL')

	def disable(self):
		if self.handle is not None:
			bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')
			self.handle = None