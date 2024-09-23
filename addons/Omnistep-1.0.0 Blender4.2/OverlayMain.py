import bpy
import blf
import gpu
import math
import time  # for the draw callback - not frame depended - self.scene.current_timestep doesn't work here
from gpu_extras.batch import batch_for_shader
import bl_math
from mathutils import Matrix, Vector
from .Scene import SceneState

# ******************************************************************** #
class Overlay:
	def __init__(self, context, scenedata: SceneState):
		self.handle = None
		self.settings = context.scene.omnistep_settings
		self.scene = scenedata
		self.area = context.area
		self.region = context.region

		self.polyline_shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')  # better - has antialiasing
		self.play_mode = None

		self.init_recticle(context)
		self.init_message()
		self.init_radial_view_control()
		self.set_play_mode(self.settings.play_mode)
		self.enable()

	def draw_callback(self, context):
		if context.area != self.area:
			return
		self.draw_recticle()
		self.draw_message()
		self.draw_radial_view_control()

	def enable(self):
		if self.handle is None:
			self.handle = bpy.types.SpaceView3D.draw_handler_add(
				self.draw_callback, (bpy.context,), 'WINDOW', 'POST_PIXEL')

	def disable(self):
		if self.handle is not None:
			bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')
			self.handle = None

	# ================================================================ #
	def set_play_mode(self, mode):
		self.play_mode = mode   # switches ui layout

	# ================================================================ #
	def init_radial_view_control(self):
		self.radial_view_control = self.settings.radial_view_control
		self.radial_view_size = bpy.context.preferences.addons[__package__].preferences.radial_view_size * 0.01
		self.radial_view_cursor_size = bpy.context.preferences.addons[__package__].preferences.radial_view_cursor_size * 0.01
		self.radial_view_color = bpy.context.preferences.addons[__package__].preferences.radial_view_color
		self.radial_view_thickness = bpy.context.preferences.addons[__package__].preferences.radial_view_thickness
		self.radial_aim_raw = Vector((0, 0, 0))
		if self.radial_view_control:
			radius = (self.region.height * self.radial_view_cursor_size * 0.5)
			self.radial_view_cursor_batch = batch_for_shader(self.polyline_shader, 'LINE_LOOP', {"pos": self.get_circle_vertices(16, radius)})
			radius = (self.region.height * self.radial_view_size * 0.5)
			self.radial_view_circle_batch = batch_for_shader(self.polyline_shader, 'LINE_LOOP', {"pos": self.get_circle_vertices(128, radius)})

	# ---------------------------------------------------------------- #
	def draw_radial_view_control(self):
		if self.radial_view_control and self.play_mode == 'FLY':
			gpu.state.blend_set('ALPHA')
			self.polyline_shader.bind()
			self.polyline_shader.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
			self.polyline_shader.uniform_float("lineWidth", self.radial_view_thickness)
			self.polyline_shader.uniform_float("color", self.radial_view_color)

			gpu.matrix.push()
			gpu.matrix.multiply_matrix(Matrix.Translation((self.region.width * 0.5, self.region.height * 0.5, 0)))
			self.radial_view_circle_batch.draw(self.polyline_shader)
			gpu.matrix.push()
			gpu.matrix.multiply_matrix(Matrix.Translation((self.radial_aim_raw.x, self.radial_aim_raw.y, 0)))
			self.radial_view_cursor_batch.draw(self.polyline_shader)
			gpu.matrix.pop()
			gpu.matrix.pop()

	# ---------------------------------------------------------------- #
	def set_radial_view_control(self, pos: Vector):
		self.radial_aim_raw = pos.copy()

	# ================================================================ #
	def init_recticle(self, context):
		self.show_reticle = self.settings.show_reticle
		self.reticle_color = context.preferences.addons[__package__].preferences.reticle_color
		self.reticle_size = context.preferences.addons[__package__].preferences.reticle_size * 0.01
		self.reticle_thickness = context.preferences.addons[__package__].preferences.reticle_thickness

		num_segments = 64
		# Calculate the vertices of the circle
		self.vertices = []
		for j in range(self.reticle_thickness):
			self.radius = (self.region.height *
						   self.reticle_size * 0.5) + j * 1.0
			for i in range(num_segments):
				angle = i / num_segments * 2.0 * math.pi + math.pi * 0.5
				x = self.radius * math.cos(angle)
				y = self.radius * math.sin(angle)
				z = 0.0
				self.vertices.append((x, y, z))
			# Close the circle by duplicating the first vertex at the end
			self.vertices.append(self.vertices[j * (num_segments + 1)])

		self.reticle_batch = batch_for_shader(
			self.polyline_shader, 'LINE_STRIP', {"pos": self.vertices})

	# ---------------------------------------------------------------- #
	def draw_recticle(self):
		if not self.show_reticle:
			return
		gpu.state.blend_set('ALPHA')
		gpu.matrix.push()
		gpu.matrix.multiply_matrix(Matrix.Translation((self.region.width * 0.5, self.region.height * 0.5, 0)))

		self.polyline_shader.bind()
		self.polyline_shader.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
		self.polyline_shader.uniform_float("lineWidth", 1.0)
		self.polyline_shader.uniform_float("color", self.reticle_color)
		self.reticle_batch.draw(self.polyline_shader)

		gpu.matrix.pop()

	# ================================================================ #
	def init_message(self):
		self.show_message = self.settings.show_message
		self.message_visible = False
		self.message_start_time = None
		self.message_time = 0.0
		self.message_max_time = 3.0
		self.message = ' '
		self.message_width = 0.0
		self.message_color = bpy.context.preferences.addons[__package__].preferences.message_color

		self.message_dpi = bpy.context.preferences.system.dpi
		self.font_id = 0
		self.font_size = bpy.context.preferences.addons[__package__].preferences.message_size
		self.real_size = self.font_size * (self.message_dpi / 72.0)
		blf.size(self.font_id, self.real_size)
		self.line_height = blf.dimensions(self.font_id, "Tp")[1] * 1.1

	# ---------------------------------------------------------------- #
	def write(self, message):
		if not self.show_message:
			return
		self.message_visible = True
		self.message_time = 0.0
		self.message_start_time = None
		self.message = message
		blf.size(self.font_id, self.real_size)
		self.message_width = blf.dimensions(self.font_id, message)[0]

	# ---------------------------------------------------------------- #
	def draw_message(self):
		if not self.show_message or not self.message_visible:
			return

		current_time = time.time()
		if self.message_start_time is None:
			self.message_start_time = current_time

		self.message_time = current_time - self.message_start_time		

		if self.message_time >= self.message_max_time:
			self.message_visible = False
			self.message_time = 0.0
			return

		if self.message_time < self.message_max_time - 1:
			alpha = self.message_color[3]
		else:			
			alpha = bl_math.lerp(self.message_color[3], 0.0, (self.message_time - (self.message_max_time - 1)) * 10.0)
		blf.color(self.font_id, self.message_color[0], self.message_color[1], self.message_color[2], alpha)
		blf.disable(self.font_id, blf.SHADOW)
		blf.size(self.font_id, self.real_size)
		blf.position(self.font_id, self.region.width * 0.5 - self.message_width * 0.5, 50, 0)
		blf.draw(self.font_id, self.message)

	# ---------------------------------------------------------------- #
	def get_circle_vertices(self, segments, radius):
		vertices = []
		for i in range(segments):
			angle = i / segments * 2.0 * math.pi + math.pi * 0.5
			x = radius * math.cos(angle)
			y = radius * math.sin(angle)
			z = 0.0
			vertices.append((x, y, z))
		# vertices.append(vertices[0])
		return vertices

