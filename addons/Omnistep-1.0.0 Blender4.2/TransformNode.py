from mathutils import Matrix, Vector, Euler, Quaternion

# Forward into view is -z, because thats the way the view matrix works in blender.
# can be a bit confusing for userscripts.., but needs to be, so it works with generic objects
# This only affects view related nodes of the player

# ********************************************************* #
class TransformNode:
	def __init__(self, position=Vector((0,0,0)), rotation=Euler((0,0,0)), scale=Vector((1,1,1)), obj=None):
		self.position = position.copy()
		self.rotation = rotation.copy()
		self.scale = scale.copy()
		self.obj = obj
		self.name = 'default'		
		if self.obj:	# If object reference is supplied, use its matrix as start			
			self.set_matrix(self.obj.matrix_world)
		else:
			self._update_matrix()		

	def _update_matrix(self):
		loc_matrix = Matrix.Translation(self.position)
		rot_matrix = self.rotation.to_matrix().to_4x4()
		scale_matrix = Matrix.Diagonal(self.scale).to_4x4()
		self.matrix = loc_matrix @ rot_matrix @ scale_matrix
		if self.obj:
			self.obj.matrix_world = self.matrix

	def set_matrix(self, matrix: Matrix):
		self.matrix = matrix.copy()
		self.position = matrix.to_translation()
		self.rotation = matrix.to_euler()
		self.scale = matrix.to_scale()
		if self.obj:
			self.obj.matrix_world = self.matrix

	# Movement
	# ---------------------------------------------------------------- #
	def translate(self, vector, space='global'):
		if space == 'global':
			self.position += vector
		elif space == 'local':
			self.position += self.matrix.to_3x3() @ vector
		self._update_matrix()

	def set_position(self, position: Vector):
		self.position = position.copy()
		self._update_matrix()

	def get_position(self) -> Vector:
		return self.matrix.to_translation()

	# Rotation
	# ---------------------------------------------------------------- #
	def set_rotation(self, rotation: Euler):
		self.rotation = rotation.copy()
		self._update_matrix()

	def get_rotation(self) -> Euler:
		return self.rotation

	def get_rotation_quaternion(self) -> Quaternion:
		return self.rotation.to_quaternion()

	def rotate(self, euler_angles):
		self.rotation.rotate(euler_angles)
		self._update_matrix()

	def rotate_axis(self, angle: float, axis: Vector, space='global'):
		rot_mat = Matrix.Rotation(angle, 4, axis)
		if space == 'global':
			self.matrix = rot_mat @ self.matrix
		elif space == 'local':
			self.matrix = self.matrix @ rot_mat
		self.rotation = self.matrix.to_euler()
		self._update_matrix()

	def look_at(self, target, up='Z', factor=1.0):
		direction = (target - self.position).normalized()
		target_rot_quat = direction.to_track_quat('Y', up)

		# Get the current orientation quaternion
		current_rot_quat = self.rotation.to_quaternion()

		# Slerp between the current orientation and the target orientation
		slerped_quat = current_rot_quat.slerp(target_rot_quat, factor)

		self.rotation = slerped_quat.to_euler()
		self._update_matrix()

	# Scale
	# ---------------------------------------------------------------- #
	def set_scale(self, scale: Vector):
		self.scale = scale.copy()
		self._update_matrix()

	def get_scale(self) -> Vector:
		return self.matrix.to_scale()

	# Local
	# ---------------------------------------------------------------- #
	def forward(self) -> Vector:
		return self.matrix.to_3x3() @ Vector((0,1,0))

	def right(self) -> Vector:
		return self.matrix.to_3x3() @ Vector((1,0,0))

	def up(self) -> Vector:
		return self.matrix.to_3x3() @ Vector((0,0,1))

	# Global
	# ---------------------------------------------------------------- #
	def align_to(self, other: 'TransformNode'):
		self.set_matrix(other.matrix)

	# Meta
	# ---------------------------------------------------------------- #
	def set_name(self, name):
		self.name = name

