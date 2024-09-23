import sys

if sys.platform == 'win32':
    import ctypes
    from ctypes import Structure, c_uint, c_short, c_byte, c_ushort, c_ubyte, windll

import bpy
import math
import bl_math
from dataclasses import dataclass, field
from enum import Enum

from .OverlayConsole import OverlayConsole
from .Scene import SceneState
from . import Utils as util
from mathutils import Vector

# ********************************************************* #
@dataclass
class InputState:
	mouse_pos_raw: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
	mouse_pos_raw_old: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
	mouse_move: Vector = field(default_factory=lambda: Vector((0, 0, 0)))

	mouse_pos_old: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
	mouse_pos: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
	mouse_pos_vel: Vector = field(default_factory=lambda: Vector((0, 0, 0)))

	mouse_sens: float = 0.0			# needed for focal adjustment in player
	mouse_invert: bool = False		# needed for logic in player

	# Mouse Damping Part
	mouse_spring: float = field(default=1500, init=False)
	mouse_damping: float = field(default=0, init=False)

	def __post_init__(self):
		self.damping = 0.1

	@property
	def damping(self):
		return self.mouse_spring

	@damping.setter
	def damping(self, value: float):
		value = value ** 0.35
		k = util.remap(value, (1.0, 0.0), (10, 3000))
		self.mouse_spring = k
		self.mouse_damping = 2 * math.sqrt(self.mouse_spring)

	@damping.getter
	def damping(self):
		return self.mouse_spring

	# Gamepad (raw, pos and oldpos are not the stick states, but translated to a 2d space pos, like mousepos)
	pad_pos_raw: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
	pad_pos_raw_old: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
	pad_move: Vector = field(default_factory=lambda: Vector((0, 0, 0)))

	pad_pos_old: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
	pad_pos: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
	pad_pos_vel: Vector = field(default_factory=lambda: Vector((0, 0, 0)))

	pad_look_sens: float = 0.0	# needed for focal adjustment in player

	# actual stick values (-1 to 1)
	pad_raw_move: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
	pad_raw_look: Vector = field(default_factory=lambda: Vector((0, 0, 0)))

	forward: bool = False
	back: bool = False
	left: bool = False
	right: bool = False
	up: bool = False
	down: bool = False

	jump: bool = False
	toggle: bool = False
	speed: bool = False	# run / walk

	speed_up: bool = False
	speed_down: bool = False
	speed_reset: bool = False

	respawn: bool = False
	teleport: bool = False
	restart: bool = False

	action1: bool = False
	action2: bool = False
	action3: bool = False
	action4: bool = False

	direction: Vector = field(default_factory=lambda: Vector((0, 0, 0)))

# ********************************************************* #
class OmniStep_InputManager:
	# ---------------------------------------------------------------- #
	def __init__(self, context, console: OverlayConsole, scenestate: SceneState):
		self.state = InputState()
		self.settings = context.scene.omnistep_settings
		self.console = console
		self.scene = scenestate
		self.context = context

		prefs = bpy.context.preferences.addons[__package__].preferences

		if self.settings.override_addon_settings:
			self.mouse_sensitivity = self.settings.mouse_sensitivity
			self.mouse_invert_y =self.settings.mouse_invert_y
		else:
			self.mouse_sensitivity = prefs.mouse_sensitivity
			self.mouse_invert_y = prefs.mouse_invert_y

		self.key_forward = prefs.key_forward
		self.key_back = prefs.key_back
		self.key_left = prefs.key_left
		self.key_right = prefs.key_right
		self.key_up = prefs.key_up
		self.key_down = prefs.key_down
		self.key_jump = prefs.key_jump
		self.key_toggle = prefs.key_toggle
		self.key_speed = prefs.key_speed

		self.key_speed_up = prefs.key_speed_up
		self.key_speed_down = prefs.key_speed_down
		self.key_speed_reset = prefs.key_speed_reset

		self.key_respawn = prefs.key_respawn
		self.key_teleport = prefs.key_teleport
		self.key_restart = prefs.key_restart

		self.key_action1 = prefs.key_action1
		self.key_action2 = prefs.key_action2
		self.key_action3 = prefs.key_action3
		self.key_action4 = prefs.key_action4

		self.state.mouse_sens = self.mouse_sensitivity * 0.01
		self.state.mouse_invert = self.mouse_invert_y

		# Gamepad
		self.pad_available = True if sys.platform == 'win32' else False
		self.pad_enabled = prefs.pad_enabled

		if self.pad_enabled and sys.platform == 'win32':
			self.pad_move_dead_zone = prefs.pad_move_dead_zone * 0.01
			self.pad_look_dead_zone = prefs.pad_look_dead_zone * 0.01

			self.state.pad_look_sens = prefs.pad_look_sens
			self.pad_look_exponent = prefs.pad_look_exponent
			self.pad_look_invert_y = -1 if prefs.pad_look_invert_y else 1


			self.pad_jump = int(prefs.pad_jump)
			self.pad_jump_oldstate = False
			self.pad_toggle = int(prefs.pad_toggle)
			self.pad_toggle_oldstate = False
			self.pad_teleport = int(prefs.pad_teleport)
			self.pad_teleport_oldstate = False
			self.pad_respawn = int(prefs.pad_respawn)
			self.pad_respawn_oldstate = False
			self.pad_action1 = int(prefs.pad_action1)
			self.pad_action1_oldstate = False
			self.pad_action2 = int(prefs.pad_action2)
			self.pad_action2_oldstate = False
			self.pad_action3 = int(prefs.pad_action3)
			self.pad_action3_oldstate = False
			self.pad_action4 = int(prefs.pad_action4)
			self.pad_action4_oldstate = False

			self.XINPUT_DLL = ctypes.windll.xinput1_4

			# XInput Structures
			class XINPUT_GAMEPAD(Structure):
				_fields_ = [
					("wButtons", c_ushort),
					("bLeftTrigger", c_ubyte),
					("bRightTrigger", c_ubyte),
					("sThumbLX", c_short),
					("sThumbLY", c_short),
					("sThumbRX", c_short),
					("sThumbRY", c_short),
				]

			class XINPUT_STATE(Structure):
				_fields_ = [
					("dwPacketNumber", c_uint),
					("Gamepad", XINPUT_GAMEPAD),
				]

			def get_gamepad_state(gamepad_id=0):
				state = XINPUT_STATE()				
				result = self.XINPUT_DLL.XInputGetState(gamepad_id, ctypes.byref(state))
				if result == 0:  # ERROR_SUCCESS
					return state.Gamepad
				else:
					return None

			self.get_gamepad_state = get_gamepad_state # expose it

	# ---------------------------------------------------------------- #
	def process_event(self, event):
		if event.type == self.key_forward:
			if event.value == 'PRESS':
				self.state.forward = True
			if event.value == 'RELEASE':
				self.state.forward = False

		if event.type == self.key_back:
			if event.value == 'PRESS':
				self.state.back = True
			if event.value == 'RELEASE':
				self.state.back = False

		if event.type == self.key_left:
			if event.value == 'PRESS':
				self.state.left = True
			if event.value == 'RELEASE':
				self.state.left = False

		if event.type == self.key_right:
			if event.value == 'PRESS':
				self.state.right = True
			if event.value == 'RELEASE':
				self.state.right = False

		if event.type == self.key_up:
			if event.value == 'PRESS':
				self.state.up = True
			if event.value == 'RELEASE':
				self.state.up = False

		if event.type == self.key_down:
			if event.value == 'PRESS':
				self.state.down = True
			if event.value == 'RELEASE':
				self.state.down = False

		if event.type == self.key_jump:
			if event.value == 'PRESS':
				self.state.jump = True
			if event.value == 'RELEASE':
				self.state.jump = False

		if event.type == self.key_toggle:
			if event.value == 'PRESS':
				self.state.toggle = True
			if event.value == 'RELEASE':
				self.state.toggle = False

		if event.type == self.key_speed:
			if event.value == 'PRESS':
				self.state.speed = True
			if event.value == 'RELEASE':
				self.state.speed = False

		if event.type == self.key_teleport:
			if event.value == 'PRESS':
				self.state.teleport = True
			if event.value == 'RELEASE':
				self.state.teleport = False

		if event.type == self.key_respawn:
			if event.value == 'PRESS':
				self.state.respawn = True
			if event.value == 'RELEASE':
				self.state.respawn = False

		if event.type == self.key_restart:
			if event.value == 'PRESS':
				self.state.restart = True
			if event.value == 'RELEASE':
				self.state.restart = False

		if event.type == self.key_speed_up:
			if event.value == 'PRESS':
				self.state.speed_up = True
			if event.value == 'RELEASE':
				self.state.speed_up = False

		if event.type == self.key_speed_down:
			if event.value == 'PRESS':
				self.state.speed_down = True
			if event.value == 'RELEASE':
				self.state.speed_down = False

		if event.type == self.key_speed_reset:
			if event.value == 'PRESS':
				self.state.speed_reset = True
			if event.value == 'RELEASE':
				self.state.speed_reset = False

		if event.type == self.key_action1:
			if event.value == 'PRESS':
				self.state.action1 = True
			if event.value == 'RELEASE':
				self.state.action1 = False

		if event.type == self.key_action2:
			if event.value == 'PRESS':
				self.state.action2 = True
			if event.value == 'RELEASE':
				self.state.action2 = False

		if event.type == self.key_action3:
			if event.value == 'PRESS':
				self.state.action3 = True
			if event.value == 'RELEASE':
				self.state.action3 = False

		if event.type == self.key_action4:
			if event.value == 'PRESS':
				self.state.action4 = True
			if event.value == 'RELEASE':
				self.state.action4 = False

	# ---------------------------------------------------------------- #
	def update_direction(self):
		self.state.direction = Vector((0, 0, 0))

		if self.state.right:
			self.state.direction.x = 1.0
		if self.state.left:
			self.state.direction.x = -1.0

		if self.state.forward:
			self.state.direction.y = 1.0
		if self.state.back:
			self.state.direction.y = -1.0

		if self.state.up:
			self.state.direction.z = 1.0
		if self.state.down:
			self.state.direction.z = -1.0

		if not self.state.right and not self.state.left:
			self.state.direction.x = 0
		if not self.state.forward and not self.state.back:
			self.state.direction.y = 0
		if not self.state.up and not self.state.down:
			self.state.direction.z = 0

		if self.state.right and self.state.left:
			self.state.direction.x = 0
		if self.state.forward and self.state.back:
			self.state.direction.y = 0
		if self.state.up and self.state.down:
			self.state.direction.z = 0

		self.state.direction = self.state.direction.normalized()	# added for gamepad support and changes in wishdir math
		# direction gets scaled later in the gampad section (if present)

	# ---------------------------------------------------------------- #
	def process_mousemove(self, event, first_run):
		if first_run:
			self.state.mouse_pos_raw.x = event.mouse_x
			self.state.mouse_pos_raw.y = event.mouse_y
			self.state.mouse_pos_raw_old.x = self.state.mouse_pos_raw.x
			self.state.mouse_pos_raw_old.y = self.state.mouse_pos_raw.y

			self.state.mouse_pos.x = event.mouse_x
			self.state.mouse_pos.y = event.mouse_y
			self.state.mouse_pos_old.x = self.state.mouse_pos.x
			self.state.mouse_pos_old.y = self.state.mouse_pos.y

			self.state.mouse_move = self.state.mouse_pos - self.state.mouse_pos_old
			return


		self.state.mouse_pos_raw_old.x = self.state.mouse_pos_raw.x
		self.state.mouse_pos_raw_old.y = self.state.mouse_pos_raw.y
		self.state.mouse_pos_raw.x = event.mouse_x
		self.state.mouse_pos_raw.y = event.mouse_y
		#self.state.mouse_move_raw = self.state.mouse_pos_raw - self.state.mouse_pos_raw_old


		self.state.mouse_pos_old = self.state.mouse_pos.copy()
		# Run Phyiscs at scene.physics_timestep (120 fps)
		num_fixed_steps = min(128, max(1, round(self.scene.current_timestep / self.scene.physics_timestep)))
		fixed_timestep = self.scene.current_timestep / num_fixed_steps

		for _ in range(num_fixed_steps):
			bank_difference = self.state.mouse_pos_raw - self.state.mouse_pos
			spring_force = self.state.mouse_spring * bank_difference
			damping_force = -self.state.mouse_damping * self.state.mouse_pos_vel
			total_force = spring_force + damping_force

			self.state.mouse_pos_vel += total_force * fixed_timestep
			self.state.mouse_pos += self.state.mouse_pos_vel * fixed_timestep

		self.state.mouse_move = self.state.mouse_pos - self.state.mouse_pos_old

	# ---------------------------------------------------------------- #
	def clear_triggers(self):
		self.state.jump = False
		self.state.respawn = False
		self.state.restart = False

	# ---------------------------------------------------------------- #
	def update_gamepad(self):
		if not self.pad_enabled or not self.pad_available:
			return
		# get data
		gamepad_data = self.get_gamepad_state()
		if gamepad_data == None:
			return

		#print(gamepad_data.wButtons)
		input_value = self.get_gamepad_input("sThumbLX", self.pad_move_dead_zone, gamepad_data, 32767.5)
		self.state.pad_raw_move.x = input_value
		self.state.direction.x += input_value
		input_value = self.get_gamepad_input("sThumbLY", self.pad_move_dead_zone, gamepad_data, 32767.5)
		self.state.pad_raw_move.y = input_value
		self.state.direction.y += input_value

		self.state.pad_raw_move.z = 0
		input_value = self.get_gamepad_input("bLeftTrigger", self.pad_move_dead_zone, gamepad_data, 255)
		self.state.direction.z -= input_value
		self.state.pad_raw_move.z -= input_value
		input_value = self.get_gamepad_input("bRightTrigger", self.pad_move_dead_zone, gamepad_data, 255)
		self.state.direction.z += input_value
		self.state.pad_raw_move.z += input_value

		if self.state.direction.length > 1.0:
			self.state.direction = self.state.direction.normalized()

		
		# Look
		self.state.pad_pos_raw_old.x = self.state.pad_pos_raw.x
		self.state.pad_pos_raw_old.y = self.state.pad_pos_raw.y

		input_value = self.get_gamepad_input("sThumbRX", self.pad_look_dead_zone, gamepad_data, 32767.5)
		self.state.pad_raw_look.x = input_value
		self.state.pad_pos_raw.x += self.response_curve(input_value, self.pad_look_exponent)

		input_value = self.get_gamepad_input("sThumbRY", self.pad_look_dead_zone, gamepad_data, 32767.5) * self.pad_look_invert_y
		self.state.pad_pos_raw.y += self.response_curve(input_value, self.pad_look_exponent)
		self.state.pad_raw_look.y = input_value

		self.state.pad_pos_old = self.state.pad_pos.copy()
		# Run Phyiscs at scene.physics_timestep (120 fps)
		num_fixed_steps = min(128, max(1, round(self.scene.current_timestep / self.scene.physics_timestep)))
		fixed_timestep = self.scene.current_timestep / num_fixed_steps

		for _ in range(num_fixed_steps):
			bank_difference = self.state.pad_pos_raw - self.state.pad_pos
			spring_force = self.state.mouse_spring * bank_difference
			damping_force = -self.state.mouse_damping * self.state.pad_pos_vel
			total_force = spring_force + damping_force

			self.state.pad_pos_vel += total_force * fixed_timestep
			self.state.pad_pos += self.state.pad_pos_vel * fixed_timestep

		self.state.pad_move = self.state.pad_pos - self.state.pad_pos_old

		# # Buttons
		current_jump_state = bool(gamepad_data.wButtons & self.pad_jump)	# Update jump state
		if current_jump_state != self.pad_jump_oldstate:
		 	self.pad_jump_oldstate = current_jump_state
		 	self.state.jump = current_jump_state

		current_toggle_state = bool(gamepad_data.wButtons & self.pad_toggle)	# Update toggle state
		if current_toggle_state != self.pad_toggle_oldstate:
			self.pad_toggle_oldstate = current_toggle_state
			self.state.toggle = current_toggle_state

		current_teleport_state = bool(gamepad_data.wButtons & self.pad_teleport)	# Update teleport state
		if current_teleport_state != self.pad_teleport_oldstate:
			self.pad_teleport_oldstate = current_teleport_state
			self.state.teleport = current_teleport_state

		current_respawn_state = bool(gamepad_data.wButtons & self.pad_respawn)	# Update respawn state
		if current_respawn_state != self.pad_respawn_oldstate:
			self.pad_respawn_oldstate = current_respawn_state
			self.state.respawn = current_respawn_state

		current_action1_state = bool(gamepad_data.wButtons & self.pad_action1)	# Update action1 state
		if current_action1_state != self.pad_action1_oldstate:
			self.pad_action1_oldstate = current_action1_state
			self.state.action1 = current_action1_state

		current_action2_state = bool(gamepad_data.wButtons & self.pad_action2)	# Update action2 state
		if current_action2_state != self.pad_action2_oldstate:
			self.pad_action2_oldstate = current_action2_state
			self.state.action2 = current_action2_state

		current_action3_state = bool(gamepad_data.wButtons & self.pad_action3)	# Update action2 state
		if current_action3_state != self.pad_action3_oldstate:
			self.pad_action3_oldstate = current_action3_state
			self.state.action3 = current_action3_state

		current_action4_state = bool(gamepad_data.wButtons & self.pad_action4)	# Update action2 state
		if current_action4_state != self.pad_action4_oldstate:
			self.pad_action4_oldstate = current_action4_state
			self.state.action4 = current_action4_state

	# ---------------------------------------------------------------- #
	def get_gamepad_input(self, attr, deadzone, data, scale):
		result = (getattr(data, attr, 0) / scale)
		# Apply dead zone
		if abs(result) < deadzone:
			return 0
		return result

	# ---------------------------------------------------------------- #
	def response_curve(self, input_value, exponent):
		return (abs(input_value) ** exponent) * (input_value / abs(input_value) if input_value != 0 else 0)

