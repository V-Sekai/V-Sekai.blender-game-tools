import bpy
from dataclasses import dataclass, field
import math
import bl_math
from .InputManager import InputState
from .OverlayConsole import OverlayConsole
from .OverlayMain import Overlay
from .TransformNode import TransformNode
from .Scene import SceneState
from . import Utils as util

from mathutils import Matrix, Vector, Euler, Quaternion
from mathutils.bvhtree import BVHTree


# ******************************************************************** #
@dataclass
class PlayerState:
	root: TransformNode = field(default_factory=TransformNode)	# player root position
	base: TransformNode = field(default_factory=TransformNode)	# player base pitch
	head: TransformNode = field(default_factory=TransformNode)	# player head offset from base! + yaw
	cam: TransformNode = field(default_factory=TransformNode)		# eye / neck offset only

	inertia: TransformNode = field(default_factory=TransformNode)	# inertia effect
	inertia_vel: Vector = field(default_factory=lambda: Vector((0, 0, 0)))

	effect: TransformNode = field(default_factory=TransformNode)	# bank, bob etc. effect

	aim: TransformNode = field(default_factory=TransformNode) 			# root @ base @ head @ cam
	view: TransformNode = field(default_factory=TransformNode) 			# inertia @ root @ base @ head @ cam @ effects

	radial_aim: Vector = field(default_factory=lambda: Vector((0, 0, 0)))	# radial 2d aim as factor
	radial_aim_raw: Vector= field(default_factory=lambda: Vector((0, 0, 0)))	# radial 2d aim in pixels

	pitch: float = 0.0
	yaw: float = 0.0

	bank: float = 0.0
	bank_vel: float = 0.0

	velocity: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
	real_velocity: Vector = field(default_factory=lambda: Vector((0, 0, 0)))	# calculated from pos / oldpos
	real_accel: Vector = field(default_factory=lambda: Vector((0, 0, 0)))		# same, but accel

	wish_jump: bool = False
	whish_jump_time : float = 0.0

	ground_distance: float = 0.0
	ground_normal: Vector = field(default_factory=lambda: Vector((0, 0, 1)))
	ground_slope: float = 0.0
	is_grounded: bool = False
	is_contact: bool = False
	is_top_contact: bool = False
	is_stair: bool = False
	fake_ground_height: float = 0.0
	last_ground_height: float = 100_000_000 # init as high value if fly/walk switch happens in the void

	is_teleport: bool = False

# ******************************************************************** #
class OmniStep_Player:
	# ---------------------------------------------------------------- #
	def __init__(self, context, overlay: Overlay, console: OverlayConsole, scenestate: SceneState, inputstate: InputState):
		self.context = context
		self.area = context.area
		self.region = context.region

		self.console = console
		self.overlay = overlay
		self.scene = scenestate
		self.state = PlayerState()
		self.settings = context.scene.omnistep_settings
		self.input = inputstate

		# Read in Spawn Points / Views
		if self.scene.camera_view:
			self.backup_view = self.context.space_data.camera.matrix_world.inverted()
		else:
			self.backup_view = self.context.region_data.view_matrix.copy()

		self.spawns = []
		if self.settings.target_spawn == 'COLLECTION' and self.settings.spawn_collection is not None:
			self.next_spawn = 0
			for obj in self.settings.spawn_collection.objects:
				if obj.type == 'EMPTY':
					spawn = TransformNode()
					spawn.set_position(obj.matrix_world.to_translation())
					spawn.set_rotation((obj.matrix_world @ Matrix.Rotation(math.radians(90), 4, 'X')).to_euler())
					spawn.set_name(obj.name)
					self.spawns.append(spawn)

		# local copies of setting vars
		self.scale = self.settings.current_scale
		self.gravity = self.settings.current_gravity * self.scale
		self.play_mode = self.settings.play_mode
		self.child_of = self.settings.child_of
		self.parent_rotation = self.settings.parent_rotation
		self.enable_animation = self.settings.enable_animation
		self.play_animation = self.settings.play_animation
		# Camera Fov data
		if self.scene.camera_view:
			self.current_focal = self.context.space_data.camera.data.lens
		else:
			self.current_focal = self.settings.view_focal if self.settings.set_focal else context.space_data.lens
		self.adjust_focal_sens = self.settings.adjust_focal_sens

		# local teleport parameters
		self.teleport_progress = 0.0
		self.teleport_source = Vector((0, 0, 0))
		self.teleport_target = Vector((0, 0, 0))
		self.teleport_stepsize = 0.0
		self.teleport_speed = self.settings.teleport_speed * self.scale
		self.teleport_time = self.settings.teleport_time
		self.teleport_actual_speed = 0.0

		# Walk
		self.walk_mouse_damping = self.settings.walk_mouse_damping
		self.player_head_offset = self.settings.player_head_offset * self.scale
		self.player_height = self.settings.player_height * self.scale
		self.player_radius = self.settings.player_radius * self.scale

		self.walk_slope = self.settings.walk_slope
		self.stair_slope = self.settings.stair_slope

		self.always_run = self.settings.always_run
		self.walk_speed = self.settings.walk_speed * self.scale
		self.run_speed = self.settings.run_speed * self.scale
		self.jump_speed = self.settings.jump_speed * self.scale
		self.wall_jump = self.settings.wall_jump
		self.air_jump = self.settings.air_jump
		self.wishjump_timeout = self.settings.wishjump_timeout
		self.walk_banking = self.settings.walk_banking
		self.coyote_time = self.settings.coyote_time

		# Fly
		self.fly_mouse_damping = self.settings.fly_mouse_damping
		self.fly_collisions = self.settings.fly_collisions
		self.fly_radius = self.settings.fly_radius * self.scale
		self.fly_speed = self.settings.fly_speed * self.scale
		self.fly_acceleration = self.settings.fly_acceleration * self.scale
		self.fly_air_friction = self.settings.fly_air_friction * self.scale
		self.fly_banking = self.settings.fly_banking

		# Radial View
		self.radial_view = self.settings.radial_view_control
		self.trackball_rotation = self.settings.trackball_rotation
		self.trackball_balance = self.settings.trackball_balance
		self.trackball_autolevel = self.settings.trackball_autolevel
		self.radial_aim_size = bpy.context.preferences.addons[__package__].preferences.radial_view_size * 0.01
		self.radial_aim_size_raw = self.region.height * self.radial_aim_size * 0.5 # in pixels - this can change as header hides etc. but better to leave it alone
		self.radial_view_maxturn = self.settings.radial_view_maxturn

		# Motion Damping Values
		self.cam_inertia = self.settings.cam_inertia
		self.cam_inertia_spring = Vector((0, 0, 0))
		self.cam_inertia_spring.x = self.settings.cam_inertia_spring_horizontal
		self.cam_inertia_spring.y = self.settings.cam_inertia_spring_horizontal
		self.cam_inertia_spring.z = self.settings.cam_inertia_spring_vertical
		self.cam_inertia_damp = Vector((0, 0, 0))
		self.cam_inertia_damp.x = 2 * math.sqrt(self.cam_inertia_spring.x)
		self.cam_inertia_damp.y = 2 * math.sqrt(self.cam_inertia_spring.y)
		self.cam_inertia_damp.z = 2 * math.sqrt(self.cam_inertia_spring.z)

		# Banking Damping
		self.banking_spring = self.settings.banking_spring
		self.banking_damp = 2 * math.sqrt(self.banking_spring)

		self.ground_friction = self.settings.ground_friction
		self.ground_acceleration = self.settings.ground_acceleration * self.scale
		self.ground_decceleration = self.settings.ground_decceleration * self.scale
		self.air_acceleration = self.settings.air_acceleration * self.scale
		self.air_decceleration = self.settings.air_decceleration * self.scale

		# Impulse Handling
		self.impulse_waiting = False
		self.impulse_vector = Vector((0, 0, 0))
		self.impulse_clear_vel = False

	# ---------------------------------------------------------------- #
	def spawn(self, first_run):
		self.state.velocity = Vector((0,0,0))
		self.state.wish_jump = False
		name = "Inital View"

		# set damping
		if self.play_mode == 'WALK':
			self.input.damping = self.walk_mouse_damping
		else:
			self.input.damping = self.fly_mouse_damping

		if self.settings.target_spawn == 'VIEW' or not self.spawns:
			if first_run:
				self.init_from_matrix(self.context.region_data.view_matrix)
			else:
				self.init_from_matrix(self.backup_view)
			return name

		# loop over spawns:
		self.init_from_matrix(self.spawns[self.next_spawn].matrix.inverted())
		name = self.spawns[self.next_spawn].name
		self.next_spawn = (self.next_spawn + 1) % len(self.spawns)
		return name

	# ---------------------------------------------------------------- #
	def init_from_matrix(self, source_matrix):
		inverted_matrix = source_matrix.inverted()
		self.state.pitch, self.state.yaw = self.get_pitch_yaw(source_matrix)

		if self.play_mode == 'WALK':
			# Backtrace the player root
			self.state.root.set_rotation(Euler((self.state.pitch,0,self.state.yaw)))
			self.state.root.set_position(inverted_matrix.to_translation())

			self.state.root.translate(Vector((0, 0, self.player_head_offset)), space='local')
			self.state.root.set_rotation(Euler((0, 0, 0)))
			offset = (self.player_height - (0.1 * self.scale)) - self.player_radius
			self.state.root.translate(Vector((0, 0, -offset)), space='local')

			# hierarchy: root > base > head > cam
			# root is scene rot, base is yaw, head is pitch, cam is head-bob
			# root is pos, base is 0-pos and only yaw
			self.state.base.set_position(Vector((0, 0, 0)))
			self.state.base.set_rotation(Euler((0, 0, self.state.yaw)))

			self.state.head.set_position(Vector((0, 0, offset)))
			self.state.head.set_rotation(Euler((self.state.pitch, 0, 0)))

			self.state.cam.set_rotation(Euler((0, 0, 0)))
			self.state.cam.set_position(Vector((0, 0, -self.player_head_offset)))

			self.state.inertia.set_rotation(Euler((0, 0, 0)))
			self.state.inertia.set_position(Vector((0, 0, 0)))

			self.state.effect.set_rotation(Euler((0, 0, 0)))
			self.state.effect.set_position(Vector((0, 0, 0)))

			# Move out of floor:
			self.walk_init_collide()

		if self.play_mode == 'FLY':
			self.state.root.set_rotation(Euler((0, 0, 0)))
			self.state.root.set_position(inverted_matrix.to_translation())

			self.state.base.set_position(Vector((0, 0, 0)))
			self.state.base.set_rotation(Euler((0, 0, self.state.yaw)))

			self.state.head.set_position(Vector((0, 0, 0)))
			self.state.head.set_rotation(Euler((self.state.pitch, 0, 0)))

			self.state.cam.set_rotation(Euler((0, 0, 0)))
			self.state.cam.set_position(Vector((0, 0, 0)))

			self.state.inertia.set_rotation(Euler((0, 0, 0)))
			self.state.inertia.set_position(Vector((0, 0, 0)))

			self.state.effect.set_rotation(Euler((0, 0, 0)))
			self.state.effect.set_position(Vector((0, 0, 0)))
			# no init collide needed as it is a sphere - no way to get stuck

		# This is new to have values ready for the script at 'start'
		self.update_input_view()
		self.update_camera_view()

	# ---------------------------------------------------------------- #
	def update(self):
		# ========================= # Lock Movement (RETURNS!)
		if self.enable_animation and self.play_animation and self.child_of is not None:
			self.lock_move()

			if self.play_mode == 'WALK' and self.cam_inertia:
				self.camera_motion_effect()
			if self.play_mode == 'WALK':
				self.banking_effect(self.walk_banking, self.walk_speed)
			if self.play_mode == 'FLY':
				self.banking_effect(self.fly_banking, self.fly_speed)
			self.update_input_view()
			self.update_camera_view()
			return

		# ========================= # Teleport
		if self.input.teleport:
			self.input.teleport = False
			self.state.is_teleport = self.init_teleport()

		# ========================= # Teleport (RETURNS!)
		if self.state.is_teleport:
			self.teleport()
			if self.play_mode == 'WALK' and self.cam_inertia:
				self.camera_motion_effect()
			if self.play_mode == 'WALK':
				self.banking_effect(self.walk_banking, self.teleport_actual_speed)
			if self.play_mode == 'FLY':
				self.banking_effect(self.fly_banking, self.teleport_actual_speed)
			self.update_input_view()
			self.update_camera_view()
			return

		# ========================= # Respawn
		if self.input.respawn:
			self.input.respawn = False
			name = self.spawn(False)
			self.overlay.write("Respawn at: " + name)

		# ========================= # Adjust Speed
		if self.input.speed_up:
			self.input.speed_up = False
			self.adjust_speed(1.1)

		if self.input.speed_down:
			self.input.speed_down = False
			self.adjust_speed(0.9)

		if self.input.speed_reset:
			self.input.speed_reset = False
			self.reset_speed()

		# ========================= # Toggle Mode
		if self.input.toggle:
			if self.play_mode == 'WALK':
				self.play_mode = 'FLY'
				self.overlay.write("Fly Mode Active")
				self.input.damping = self.fly_mouse_damping
			else:
				self.play_mode = 'WALK'
				self.overlay.write("Walk Mode Active")
				self.input.damping = self.walk_mouse_damping

			self.init_from_matrix(self.context.region_data.view_matrix)
			self.reset_input()
			self.overlay.set_play_mode(self.play_mode)
			self.input.toggle = False


		# ========================= # Apply View from Input
		# ========================= #
		self.update_input_view()


		# ========================= #
		if self.play_mode == 'WALK':
			if self.input.jump:
				self.state.wish_jump = True
				self.state.whish_jump_time = 0.0

			if self.state.is_grounded:
				self.walk_ground_move()
			else:
				self.walk_air_move()

			# Collide
			self.walk_collide()

			# Camera Effects
			if self.cam_inertia:
				self.camera_motion_effect()

			self.banking_effect(self.walk_banking, self.run_speed)

		# ========================= #
		if self.play_mode == 'FLY':
			self.fly_move()

			if self.fly_collisions:
				self.fly_collide()
			else:
				self.fly_no_collide()

			if self.radial_view and self.trackball_rotation:
				self.banking_effect(0, self.fly_speed)
			else:
				self.banking_effect(self.fly_banking, self.fly_speed)

		# ========================= # Wishjump timeout
		if self.state.wish_jump:
			self.state.whish_jump_time += self.scene.current_timestep
			if self.state.whish_jump_time > self.wishjump_timeout:
				self.state.wish_jump = False
				self.state.whish_jump_time = 0.0

		# ========================= # Set Final View
		self.update_camera_view()

	# ---------------------------------------------------------------- #
	def update_input_view(self):
		# Update Camera Fov (if animated)
		if self.scene.camera_view:
			self.current_focal = self.context.space_data.camera.data.lens
		sensitivity = self.input.mouse_sens * ((28.0 / max(28.0, self.current_focal))**0.5) if self.adjust_focal_sens else self.input.mouse_sens
		pad_look_sens = self.input.pad_look_sens * ((28.0 / max(28.0, self.current_focal))**0.5) if self.adjust_focal_sens else self.input.pad_look_sens

		if self.play_mode == 'FLY' and self.radial_view:
			self.state.radial_aim_raw.x += self.input.mouse_move.x
			self.state.radial_aim_raw.y += self.input.mouse_move.y
			self.state.radial_aim_raw.x += self.input.pad_move.x / math.radians(pad_look_sens + 0.001)
			self.state.radial_aim_raw.y += self.input.pad_move.y / math.radians(pad_look_sens + 0.001)
			# limit vector length
			if self.state.radial_aim_raw.length > self.radial_aim_size_raw:
				self.state.radial_aim_raw = self.state.radial_aim_raw.normalized() * self.radial_aim_size_raw

			self.overlay.set_radial_view_control(self.state.radial_aim_raw)

			self.state.radial_aim = self.state.radial_aim_raw / self.radial_aim_size_raw

			yaw_delta = self.state.radial_aim.x * self.scene.current_timestep * self.radial_view_maxturn
			pitch_delta = self.state.radial_aim.y  * self.scene.current_timestep * self.radial_view_maxturn

			self.state.yaw -= yaw_delta
			self.state.pitch += pitch_delta
		else:
			self.state.yaw -= self.input.mouse_move.x * math.radians(sensitivity)
			self.state.pitch += self.input.mouse_move.y * math.radians(sensitivity) * (-1 if self.input.mouse_invert else 1)
			# Gamepad
			self.state.yaw -= self.input.pad_move.x * math.radians(pad_look_sens)
			self.state.pitch += self.input.pad_move.y * math.radians(pad_look_sens)


		if self.play_mode == 'FLY' and self.radial_view and self.trackball_rotation:
			self.state.root.set_rotation(Euler((0, 0, 0)))
			self.state.base.rotate_axis(-yaw_delta * (1.0 - self.trackball_balance), self.state.view.up(), 'global')
			self.state.base.rotate_axis(-yaw_delta * (self.trackball_balance), self.state.view.forward(), 'global')
			self.state.base.rotate_axis(pitch_delta, self.state.view.right(), 'global')

			fac = bl_math.clamp(bl_math.lerp((self.scene.current_timestep * self.trackball_autolevel), 0.0, self.state.real_velocity.length / self.fly_speed))
			alignment_factor = 1.0 - abs(self.state.base.forward().dot(Vector((0, 0, 1)))) # less leveling on poles
			self.state.base.look_at(self.state.base.forward(), factor=fac * alignment_factor)

			self.state.effect.set_rotation(Euler((0, 0, self.state.bank)))
		else:
			self.state.pitch = max(min(self.state.pitch, math.pi - 0.0001), 0.0001)

			self.state.base.set_rotation(Euler((0, 0, self.state.yaw)))
			self.state.head.set_rotation(Euler((self.state.pitch, 0, 0)))
			self.state.effect.set_rotation(Euler((0, 0, self.state.bank)))

		# Set aim for better data used by the fly mode and others, recalc at end again
		# Aim only cares about the real state, without effects
		self.state.aim.set_matrix(self.state.root.matrix @ self.state.base.matrix @ self.state.head.matrix @ self.state.cam.matrix)

	# ---------------------------------------------------------------- #
	def reset_input(self):
		self.state.radial_aim_raw.x = 0
		self.state.radial_aim_raw.y = 0

	# ---------------------------------------------------------------- #
	def update_camera_view(self):
		# aim does not take into account banking and inertia
		# view does
		if self.play_mode == 'WALK':
			if self.cam_inertia:
				# motion effect first, as this is world space, not camera space
				mat = (self.state.inertia.matrix @ self.state.root.matrix @ self.state.base.matrix @ self.state.head.matrix @ self.state.cam.matrix @ self.state.effect.matrix)
				if self.scene.camera_view:
					self.context.space_data.camera.matrix_world = mat
					#self.context.space_data.camera.keyframe_insert(data_path="location")
					#self.context.space_data.camera.keyframe_insert(data_path="rotation_euler")
				else:
					self.context.region_data.view_matrix = mat.inverted()
				self.state.view.set_matrix(mat)
			else:
				mat = (self.state.root.matrix @ self.state.base.matrix @ self.state.head.matrix @ self.state.cam.matrix @ self.state.effect.matrix)
				if self.scene.camera_view:
					self.context.space_data.camera.matrix_world = mat
				else:
					self.context.region_data.view_matrix = mat.inverted()
				self.state.view.set_matrix(mat)

		if self.play_mode == 'FLY':
			mat = (self.state.root.matrix @ self.state.base.matrix @ self.state.head.matrix @ self.state.cam.matrix @ self.state.effect.matrix)
			if self.scene.camera_view:
					self.context.space_data.camera.matrix_world = mat
			else:
				self.context.region_data.view_matrix = mat.inverted()
			self.state.view.set_matrix(mat)

		# Aim 2nd calc round
		self.state.aim.set_matrix(self.state.root.matrix @ self.state.base.matrix @ self.state.head.matrix @ self.state.cam.matrix)

	# ---------------------------------------------------------------- #
	def walk_ground_move(self):
		if not self.state.wish_jump:
			self.walk_apply_friction(1.0)

		wishdir = self.state.base.forward() * self.input.direction.y + self.state.base.right() * self.input.direction.x
		wishdir = wishdir.normalized()

		wishdir = util.intersect_line_plane_vertical(wishdir, Vector((0,0,0)), self.state.ground_normal)
		wishdir = wishdir.normalized()

		self.state.velocity = util.project_point_on_plane(self.state.velocity, Vector((0,0,0)), self.state.ground_normal)

		# This makes problems at low speeds, off for now..
		# if self.state.is_stair and self.state.real_velocity.length > 0: # normalize vel if on stair, to avoid too high speed
		#	self.state.velocity *= self.state.velocity.length / self.state.real_velocity.length

		if self.always_run ^ self.input.speed:
			wishspeed = self.run_speed
		else:
			wishspeed = self.walk_speed

		# * self.input.direction.length for gamepad support
		self.accelerate(wishdir, wishspeed * self.input.direction.length, self.ground_acceleration + self.ground_friction)
		

		self.state.velocity.z += -self.gravity * self.scene.current_timestep
		
		if self.state.wish_jump:
			self.state.velocity.z = self.jump_speed
			self.state.wish_jump = False
			self.state.whish_jump_time = 0.0

	# ---------------------------------------------------------------- #
	def walk_air_move(self):
		wishdir = self.state.base.forward() * self.input.direction.y + self.state.base.right() * self.input.direction.x
		wishdir = wishdir.normalized()

		if self.always_run ^ self.input.speed:
			wishspeed = self.run_speed
		else:
			wishspeed = self.walk_speed

		if self.state.velocity.dot(wishdir) < 0:
			accel = self.air_decceleration
		else:
			accel = self.air_acceleration

		# Removed 07.2024, dont think its useful anymore
		# if math.fabs(self.input.direction.y) < 0.001 and math.fabs(self.input.direction.x) > 0.001:
		# 	if wishspeed > self.side_strafe_speed:
		# 		wishspeed = self.side_strafe_speed
		# 	accel = self.side_strafe_acceleration

		# * self.input.direction.length for gamepad support
		self.accelerate(wishdir, wishspeed * self.input.direction.length, accel)

		# Gravity
		self.state.velocity.z -= self.gravity * self.scene.current_timestep

		if self.wall_jump and self.state.is_contact and self.state.wish_jump:
			self.state.velocity.z = self.jump_speed
			self.state.wish_jump = False

		if self.state.wish_jump and self.air_jump:
			self.state.velocity.z = self.jump_speed
			self.state.wish_jump = False

	# ---------------------------------------------------------------- #
	def walk_apply_friction(self, t):
		speed = self.state.real_velocity.length # instead .velocity, 09.2024

		if self.always_run ^ self.input.speed:
			target_speed = self.run_speed
		else:
			target_speed = self.walk_speed

		# Minimum control for grip
		if speed < self.ground_decceleration:
			control = self.ground_decceleration
		
			# fix low speeds 02.09.2024
			if self.input.direction.length > 0.001:
				control *= target_speed / self.ground_decceleration
		else:
			control = speed

		drop = control * self.ground_friction * self.scene.current_timestep * t
		newspeed = speed - drop
		if newspeed < 0:
			newspeed = 0
		if speed > 0:
			newspeed /= speed

		self.state.velocity.x *= newspeed
		self.state.velocity.y *= newspeed
		self.state.velocity.z *= newspeed

	# ---------------------------------------------------------------- #
	def accelerate(self, wishdir, wishspeed, accel):
		tempvel = self.state.velocity.copy()
		tempvel /= self.scale
		
		currentspeed = tempvel.dot(wishdir)
		addspeed = (wishspeed / self.scale) - currentspeed

		if addspeed <= 0:
			return
		
		accelspeed = (accel / self.scale) * self.scene.current_timestep * (wishspeed / self.scale)

		if accelspeed > addspeed:
			accelspeed = addspeed

		self.state.velocity.x += accelspeed * wishdir.x * self.scale 
		self.state.velocity.y += accelspeed * wishdir.y * self.scale
		self.state.velocity.z += accelspeed * wishdir.z * self.scale

		# here because accelerate is called from ground and air move, for flying its only once after accel.
		if self.impulse_waiting:
			self.impulse_waiting = False
			if self.impulse_clear_vel:
				self.state.velocity = self.impulse_vector
			else:
				self.state.velocity += self.impulse_vector

	# ---------------------------------------------------------------- #
	def walk_collide(self):
		self.state.is_grounded = False
		self.state.is_stair = False
		self.state.is_contact = False

		old_realvel = self.state.real_velocity.copy()
		old_pos = self.state.root.position.copy()

		for i in range(self.scene.collision_samples):
			self.state.root.translate(self.state.velocity * self.scene.current_timestep * (1.0 / self.scene.collision_samples))
			self.walk_sub_collide()

		self.state.real_velocity = (self.state.root.position - old_pos) * (1 / self.scene.current_timestep)
		self.state.real_accel = (self.state.real_velocity - old_realvel) * (1 / self.scene.current_timestep)

	# ---------------------------------------------------------------- #
	def walk_sub_collide(self):
		mindist = self.player_radius
		body_mindist = mindist * 0.99		# make middle / top collider a bit smaller to avoid stair velocity problems
		walk_slope = self.walk_slope
		stair_slope = self.stair_slope
		hit_pos = None
		hit_normal = None
		hit_id = None
		hit_distance = None
		epsilon = 0.0001 * self.scale
		expand = 2.0	# double it, so that steep stairs get accepted as stair

		base_position = self.state.root.get_position()

		# ************ Fake Ground **************
		hit_pos, hit_normal, hit_id, hit_distance = self.scene.bvhtree.ray_cast(base_position, Vector((0,0,-1)))
		if hit_pos is None:
			if self.state.last_ground_height > base_position.z - (mindist * 0.5):
				self.state.last_ground_height = base_position.z - mindist

			if self.state.last_ground_height > base_position.z - mindist:
				base_position.z =  self.state.last_ground_height + mindist
				self.state.is_grounded = True
				self.state.is_contact = True
			self.state.ground_normal = Vector((0,0,1))

			# Fake Ground - handle sides
			hit_pos, hit_normal, hit_id, hit_distance = self.scene.bvhtree.find_nearest(base_position, mindist)
			if hit_pos is not None and hit_distance <= mindist + epsilon:
				self.state.is_contact = True
				vec = (base_position - hit_pos).normalized()
				base_position += vec * (mindist - hit_distance)
				self.state.velocity = util.reflect_velocity(self.state.velocity, vec)
			# Fake Ground - Body Collider
			topcenter = Vector((0, 0, mindist * 2))
			hit_pos, hit_normal, hit_id, hit_distance = self.scene.bvhtree.find_nearest(base_position + topcenter, mindist)
			if hit_pos is not None and hit_distance <= mindist + epsilon:
				self.state.is_contact = True
				vec = (base_position + topcenter - hit_pos).normalized()
				base_position += vec * (mindist - hit_distance)
				self.state.velocity = util.reflect_velocity(self.state.velocity, vec)

			self.state.root.set_position(base_position)
			return

		# ************ Feet Collider ************
		# ****** classic ground flat fallback (optimally this is never used) ******
		hit_pos, hit_normal, hit_id, hit_distance = self.scene.bvhtree.ray_cast(base_position, Vector((0,0,-1)))
		if hit_pos is not None:
			hit_normal = -hit_normal if hit_normal.z < 0 else hit_normal # fix flipped normals
			backup_dist = hit_distance
			backup_normal = hit_normal.normalized()
			if hit_distance <= mindist + epsilon:
				self.state.is_grounded = True
				self.state.is_contact = True
				self.state.ground_distance = hit_distance
				self.state.ground_normal = hit_normal.normalized()
				self.state.ground_slope = math.degrees(math.acos(hit_normal.z))
				self.state.last_ground_height = hit_pos.z

		# ****** advanced ground handling ******
		hit_pos, hit_normal, hit_id, hit_distance = self.scene.bvhtree.find_nearest(base_position, mindist)
		if hit_normal is not None:
			hit_normal = -hit_normal if hit_normal.z < 0 else hit_normal # fix flipped normals

		if hit_pos is not None and hit_distance <= mindist + epsilon:
			self.state.is_contact = True
			self.state.ground_slope = math.degrees(math.acos(hit_normal.z))
			vec = (base_position - hit_pos).normalized()
			contact_slope = math.degrees(math.acos(vec.z))

			check_vec = -vec.copy()
			check_vec.z += 0.01  # * self.scale # vec is normalized! some small amount is enough at all scales to find the next flat stair
			_, check_n, *_ = self.scene.bvhtree.ray_cast(base_position, check_vec, mindist * 2)
			if check_n is not None:
				check_n = -check_n if check_n.z < 0 else check_n # fix flipped normals
			if check_n is not None and self.state.ground_distance < mindist * expand and math.degrees(math.acos(check_n.z)) < walk_slope:
				hit_normal = check_n

			if contact_slope <= walk_slope and not self.state.is_top_contact:
				self.state.is_grounded = True
				self.state.last_ground_height = hit_pos.z
				self.state.ground_distance = hit_distance
				self.state.ground_normal = hit_normal.normalized()
				self.state.ground_slope = math.degrees(math.acos(hit_normal.z))
				# prefer the better normal
				if backup_normal.z > hit_normal.z:
					self.state.ground_distance = backup_dist
					self.state.ground_normal = backup_normal
					self.state.ground_slope = math.degrees(math.acos(backup_normal.z))
				base_position += Vector((0,0,1)) * (mindist - hit_distance)
			elif contact_slope > walk_slope and contact_slope < stair_slope and backup_dist < mindist * expand and math.degrees(math.acos(hit_normal.z)) < walk_slope: # and not self.state.is_top_contact:
				self.state.is_stair = True
				self.state.is_grounded = True
				self.state.ground_distance = hit_distance
				self.state.ground_normal = hit_normal.normalized()
				self.state.ground_slope = math.degrees(math.acos(hit_normal.z))
				base_position += Vector((0,0,1)) * (mindist - hit_distance)
			else:
				base_position += vec * (mindist - hit_distance)
				self.state.velocity = util.reflect_velocity(self.state.velocity, vec)

		# ************ Body Collider ************
		# a second sphere balanced on top of the base sphere.
		# combined height is mindist * 4
		topcenter = Vector((0, 0, self.player_height - self.player_radius * 2.0))
		hit_pos, hit_normal, hit_id, hit_distance = self.scene.bvhtree.find_nearest(base_position + topcenter, body_mindist)
		if hit_pos is not None and hit_distance <= body_mindist + epsilon:
			self.state.is_contact = True
			self.state.is_top_contact = True
			vec = (base_position + topcenter - hit_pos).normalized()
			base_position += vec * (body_mindist - hit_distance)
			if not self.state.is_stair:
				self.state.velocity = util.reflect_velocity(self.state.velocity, vec)
		else:
			self.state.is_top_contact = False # reset here to get last state above

		# ************ Middle Collider ************
		# a third sphere in the middle.
		topcenter *= 0.5 #Vector((0, 0, (self.player_height - self.player_radius * 2.0) * 0.5))
		hit_pos, hit_normal, hit_id, hit_distance = self.scene.bvhtree.find_nearest(base_position + topcenter, body_mindist)
		if hit_pos is not None and hit_distance <= body_mindist + epsilon:
			self.state.is_contact = True
			vec = (base_position + topcenter - hit_pos).normalized()
			base_position += vec * (body_mindist - hit_distance)
			if not self.state.is_stair:
				self.state.velocity = util.reflect_velocity(self.state.velocity, vec)

		# Update the root
		self.state.root.set_position(base_position)

	# ---------------------------------------------------------------- #
	def walk_init_collide(self):
		# make sure we are not stuck in the floor on startup, and if player height change
		base_position = self.state.root.get_position()
		head_position = (self.state.root.matrix @ self.state.base.matrix @ self.state.head.matrix).to_translation()

		hit_pos, hit_normal, hit_id, hit_distance = self.scene.bvhtree.ray_cast(head_position, Vector((0,0,-1)))
		if hit_pos is not None and hit_distance < self.player_height - (0.1 * self.scale):
			base_position.z += self.player_height - (0.1 * self.scale) - hit_distance

		self.state.root.set_position(base_position)

	# ---------------------------------------------------------------- #
	def fly_accelerate(self, wishdir, wishspeed, accel):
		old_magnitude = self.state.velocity.length
		self.state.velocity += accel * wishdir * self.scene.current_timestep
		if self.state.velocity.length > wishspeed:
			# Original Code
			#self.state.velocity = self.state.velocity.normalized() * wishspeed
			# This is better for handling impulses
			self.state.velocity = self.state.velocity.normalized() * old_magnitude * 0.99

	# ---------------------------------------------------------------- #
	def fly_apply_friction(self):
		speed =  self.state.real_velocity.length
		drop = self.fly_air_friction * self.scene.current_timestep
		newspeed = speed - drop
		if newspeed < 0:
			newspeed = 0
		if speed > 0:
			newspeed /= speed

		self.state.velocity *= newspeed

	# ---------------------------------------------------------------- #
	def fly_move(self):
		self.fly_apply_friction()

		wishdir = (self.state.aim.up() * -self.input.direction.y
				+ self.state.aim.right() * self.input.direction.x
				+ self.state.aim.forward() * self.input.direction.z)
		wishdir = wishdir.normalized()

		wishdir *= self.input.direction.length # Gamepad support

		# * self.input.direction.length on next line is also gamepad support
		self.fly_accelerate(wishdir, self.fly_speed * self.input.direction.length, self.fly_acceleration + self.fly_air_friction)

		if self.impulse_waiting:
			self.impulse_waiting = False
			if self.impulse_clear_vel:
				self.state.velocity = self.impulse_vector
			else:
				self.state.velocity += self.impulse_vector

	# ---------------------------------------------------------------- #
	def fly_collide(self):
		self.state.is_grounded = False	# if left over from walk
		self.state.is_stair = False
		self.state.is_contact = False

		old_realvel = self.state.real_velocity.copy()
		old_pos = self.state.root.position.copy()

		for i in range(self.scene.collision_samples):
			self.state.root.translate(self.state.velocity * self.scene.current_timestep * (1.0 / self.scene.collision_samples))
			self.fly_sub_collide()

		self.state.real_velocity = (self.state.root.position - old_pos) * (1 / self.scene.current_timestep)
		self.state.real_accel = (self.state.real_velocity - old_realvel) * (1 / self.scene.current_timestep)

	# ---------------------------------------------------------------- #
	def fly_no_collide(self):
		self.state.is_grounded = False	# if left over from walk
		self.state.is_stair = False
		self.state.is_contact = False

		old_realvel = self.state.real_velocity.copy()
		old_pos = self.state.root.position.copy()

		self.state.root.translate(self.state.velocity * self.scene.current_timestep)

		self.state.real_velocity = (self.state.root.position - old_pos) * (1 / self.scene.current_timestep)
		self.state.real_accel = (self.state.real_velocity - old_realvel) * (1 / self.scene.current_timestep)

	# ---------------------------------------------------------------- #
	def fly_sub_collide(self):
		mindist = self.fly_radius
		hit_pos = None
		hit_normal = None
		hit_id = None
		hit_distance = None
		base_position = self.state.root.get_position()

		hit_pos, hit_normal, hit_id, hit_distance = self.scene.bvhtree.find_nearest(base_position, mindist)
		if hit_pos is not None and hit_distance <= mindist:
			self.state.is_contact = True
			vec = (base_position - hit_pos).normalized()
			base_position += vec * (mindist - hit_distance)
			self.state.velocity = util.reflect_velocity(self.state.velocity, vec)
		# Update the root
		self.state.root.set_position(base_position)

	# ---------------------------------------------------------------- #
	def adjust_speed(self, factor):
		self.walk_speed *= factor
		self.run_speed *= factor
		#self.jump_speed *=factor

		self.fly_speed *= factor
		self.fly_acceleration *= factor
		self.fly_air_friction *= factor

		self.teleport_speed *= factor
		if self.play_mode == 'WALK':
			if self.always_run:
				self.overlay.write(f"Speed Adjust, Run Speed: {self.run_speed:.2f} [m/s]")
			else:
				self.overlay.write(f"Speed Adjust, Walk Speed: {self.walk_speed:.2f} [m/s]")

		if self.play_mode == 'FLY':
			self.overlay.write(f"Speed Adjust, Fly Speed {self.fly_speed:.2f} [m/s]")

	# ---------------------------------------------------------------- #
	def reset_speed(self):
		self.walk_speed = self.settings.walk_speed * self.scale
		self.run_speed = self.settings.run_speed * self.scale
		#self.jump_speed = self.settings.jump_speed * self.scale

		self.fly_speed = self.settings.fly_speed * self.scale
		self.fly_acceleration = self.settings.fly_acceleration * self.scale
		self.fly_air_friction = self.settings.fly_air_friction * self.scale

		self.teleport_speed = self.settings.teleport_speed * self.scale

		self.overlay.write("Speed Reset")

	# ---------------------------------------------------------------- #
	def init_teleport(self):
		hit_pos = None
		hit_normal = None
		hit_id = None
		hit_distance = None
		self.teleport_source = self.state.root.get_position()
		radius = 1.0
		if self.play_mode == 'WALK':
			radius = self.player_radius
		if self.play_mode == 'FLY':
			radius = self.fly_radius

		hit_pos, hit_normal, hit_id, hit_distance = self.scene.bvhtree.ray_cast(self.state.aim.get_position(), -self.state.aim.up())
		if hit_pos is not None:
			flip = -self.state.aim.up().dot(hit_normal)	# make sure the wall looks in our direction
			if flip > 0.0:
				hit_normal *= -1
			vec = (-self.state.aim.up() * (hit_distance)) + hit_normal * self.player_radius # - self.state.head.get_position()
			self.teleport_target = self.teleport_source + vec
			self.teleport_progress = 0.0

			time_based_stepsize = 1.0 / self.teleport_time
			speed_based_stepsize = self.teleport_speed / vec.length
			self.teleport_stepsize = max(time_based_stepsize, speed_based_stepsize)
			self.teleport_actual_speed = self.teleport_stepsize * vec.length

			self.overlay.write("Teleport")
			return True
		return False

	# ---------------------------------------------------------------- #
	def teleport(self):
		self.teleport_progress += self.teleport_stepsize * self.scene.current_timestep
		self.teleport_progress = bl_math.clamp(self.teleport_progress, 0.0, 1.0)

		old_realvel = self.state.real_velocity.copy()
		old_pos = self.state.root.position.copy()

		self.state.root.set_position(self.teleport_source.lerp(self.teleport_target, util.ease_out_quad(self.teleport_progress)))
		if self.play_mode == 'WALK':
			self.walk_init_collide()

		self.state.real_velocity = (self.state.root.position - old_pos) * (1 / self.scene.current_timestep)
		self.state.real_accel = (self.state.real_velocity - old_realvel) * (1 / self.scene.current_timestep)

		if self.teleport_progress >= 1.0:
			self.state.velocity = Vector((0,0,0))
			self.state.is_teleport = False

	# ---------------------------------------------------------------- #
	def lock_move(self):
		old_realvel = self.state.real_velocity.copy()
		old_pos = self.state.root.position.copy()

		offset = Vector((0, 0, 0))
		if self.play_mode == 'WALK':
			offset = Vector((0, 0, (self.player_height - (0.1 * self.scale)) - self.player_radius))

		vec = self.child_of.matrix_world.to_translation()

		if self.parent_rotation == 'FULL':
			offset = self.child_of.matrix_world.to_3x3() @ offset
			self.state.root.set_position((vec - offset))
		else:
			self.state.root.set_position(vec - offset)

		if self.parent_rotation == 'NONE':
			pass
		elif self.parent_rotation == 'ZAXIS':
			if self.child_of.rotation_mode == 'QUATERNION':
				z_rotation = self.child_of.matrix_world.to_quaternion().to_euler().z
			else:
				z_rotation = self.child_of.matrix_world.to_euler().z

			self.state.root.set_rotation(Euler((0, 0, z_rotation)))
		elif self.parent_rotation == 'FULL':
			self.state.root.set_rotation(self.child_of.matrix_world.to_euler())

		self.state.real_velocity = (self.state.root.position - old_pos) * (1 / self.scene.current_timestep)
		self.state.real_accel = (self.state.real_velocity - old_realvel) * (1 / self.scene.current_timestep)

	# ---------------------------------------------------------------- #
	def banking_effect(self, target_bank, target_speed):
		# if impulse etc., limit max bank
		target_speed = max(target_speed, self.state.velocity.length)

		# Run Banking Physics at scene.physics_timestep (120 fps)
		num_fixed_steps = min(128, max(1, round(self.scene.current_timestep / self.scene.physics_timestep)))
		fixed_timestep = self.scene.current_timestep / num_fixed_steps

		for _ in range(num_fixed_steps):
			tempvel = self.state.real_velocity.copy() / self.scale
			bank_target = tempvel.dot(self.state.aim.right()) / (target_speed / self.scale)
			# Factor 1.0 == 45 deg
			bank_target *= target_bank * 0.5
			# Calculate the difference between the target bank and the current bank
			bank_difference = bank_target - self.state.bank
			# Apply spring force based on the difference
			spring_force = self.banking_spring * bank_difference
			# Apply damping force based on the current banking velocity
			damping_force = (-self.banking_damp * self.state.bank_vel)
			# Calculate the total force
			total_force = spring_force + damping_force
			# Update the banking velocity
			self.state.bank_vel += total_force * fixed_timestep
			# Update the bank state
			self.state.bank += self.state.bank_vel * fixed_timestep

	# ---------------------------------------------------------------- #
	def camera_motion_effect(self):
		num_fixed_steps = min(128, max(1, round(self.scene.current_timestep / self.scene.physics_timestep)))
		fixed_timestep = self.scene.current_timestep / num_fixed_steps

		for _ in range(num_fixed_steps):
			# Update velocity using acceleration and damping
			accel = -self.state.real_accel * fixed_timestep
			self.state.inertia_vel += accel

			# this avoids overshoot with big K and big Timesteps!
			# a different limiting strategy than with banking, as target pos is zero
			self.state.inertia_vel *= (Vector((1,1,1)) - util.vector_clamp(self.cam_inertia_damp * fixed_timestep, -1.0, 1.0))

			# Apply spring force to velocity
			spring_force = -self.cam_inertia_spring * self.state.inertia.get_position()
			self.state.inertia_vel += spring_force * fixed_timestep

			# Update position using the updated velocity
			final_change = self.state.inertia_vel * fixed_timestep
			self.state.inertia.translate(final_change)
			# Clamp
			maxdisplace = self.player_radius * 0.9
			clamped_pos = util.vector_clamp(self.state.inertia.get_position(), -maxdisplace, maxdisplace)
			# Clamp Z+ to avoid head ceiling clipping
			clamped_pos.z = bl_math.clamp(clamped_pos.z, -maxdisplace, 0.08)
			# Apply the value
			self.state.inertia.set_position(clamped_pos)

			# Avoid jitter
			if self.state.inertia.get_position().length < self.player_radius * 0.005:
				self.state.inertia.set_position(Vector((0, 0, 0)))
				self.state.inertia_vel = Vector((0, 0, 0))

	# ---------------------------------------------------------------- #
	def get_pitch_yaw(self, source_matrix):
		# the to_euler does not work, no matter what - this is the way
		view_matrix_inv = source_matrix.inverted()
		# Compute the forward direction vector from the inverted view matrix
		forward_vector = view_matrix_inv.to_3x3() @ Vector((0.0, 0.0, -1.0))
		forward_vector.normalize()
		# Yaw is the angle between the projection of the forward vector on the XY plane and the Y axis
		yaw = -math.atan2(forward_vector.x, forward_vector.y)
		# Pitch is the angle between the forward vector and its projection on the XY plane
		pitch = math.asin(forward_vector.z) + (math.pi * 0.5)
		return pitch, yaw

	# User Methods =================================================== #
	def user_set_position(self, pos, clear_velocity=False):
		if not self.state.is_teleport:
			self.state.root.set_position(pos)
			if clear_velocity:
				self.state.velocity = Vector((0,0,0))

	# ---------------------------------------------------------------- #
	def user_apply_impulse(self, vec, clear_velocity=False):
		if not self.state.is_teleport:
			# Needs to be post-poned to the velocity update loops in walk accel etc.
			self.impulse_waiting = True
			self.impulse_clear_vel = clear_velocity
			self.impulse_vector = vec

	# ---------------------------------------------------------------- #
	def user_respawn(self, obj=None):
		if not self.state.is_teleport:
			self.state.velocity = Vector((0,0,0))
			self.state.wish_jump = False

			if obj is None:
				name = self.spawn(False)
				self.overlay.write("UserScript: Respawn at: " + name)
			else:
				spawn = TransformNode()
				spawn.set_position(obj.matrix_world.to_translation())
				spawn.set_rotation((obj.matrix_world @ Matrix.Rotation(math.radians(90), 4, 'X')).to_euler())
				self.init_from_matrix(spawn.matrix.inverted())
				spawn = None

	# ---------------------------------------------------------------- #
	def user_ray_cast_player(self, pos, vec):
		if self.play_mode == 'FLY':
			return util.ray_sphere_intersection(pos, vec, self.state.root.get_position(), self.fly_radius)
		if self.play_mode == 'WALK':
			hitpos, hitnorm, dist = util.ray_sphere_intersection(pos, vec, self.state.root.get_position(), self.player_radius)
			if hitpos is not None:
				return hitpos, hitnorm, dist
			topcenter = Vector((0, 0, self.player_height - self.player_radius * 2.0))
			hitpos, hitnorm = util.ray_sphere_intersection(pos, vec, self.state.root.get_position() + topcenter, self.player_radius)
			if hitpos is not None:
				return hitpos, hitnorm, dist
			topcenter *= 0.5
			hitpos, hitnorm = util.ray_sphere_intersection(pos, vec, self.state.root.get_position() + topcenter, self.player_radius)
			if hitpos is not None:
				return hitpos, hitnorm, dist
			return False, Vector((0, 0, 0)), Vector((0, 0, 0)), 0.0

