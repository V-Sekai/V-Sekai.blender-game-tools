import bpy
import importlib
import re
from dataclasses import dataclass, field
from enum import Enum

from mathutils import Vector, Matrix #, Euler, Quaternion
from .OverlayMain import Overlay
from .Player import PlayerState, OmniStep_Player
from .Scene import SceneState, SceneBVH
from .InputManager import InputState
from .TransformNode import TransformNode

# ********************************************************* #
def extract_property_details(self, settings): # extract all data from the current script_items
	property_dict = {}
	for item in settings.script_items:
		if item.data_type == 'FLOAT':
			property_dict[item.name] = {'value': float(item.float_value), 'type': item.data_type}
		elif item.data_type == 'INT':
			property_dict[item.name] = {'value': int(item.int_value), 'type': item.data_type}
		elif item.data_type == 'STRING':
			property_dict[item.name] = {'value': str(item.string_value), 'type': item.data_type}
		elif item.data_type == 'VECTOR':
			property_dict[item.name] = {'value': Vector(item.vector_value), 'type': item.data_type}
		elif item.data_type == 'COLOR':
			property_dict[item.name] = {'value': Vector(item.color_value), 'type': item.data_type}
		if item.data_type == 'BOOLEAN':
			property_dict[item.name] = {'value': bool(item.boolean_value), 'type': item.data_type}
		elif item.data_type == 'OBJECT':
			property_dict[item.name] = {'value': item.object_reference, 'type': item.data_type}
		elif item.data_type == 'COLLECTION':
			property_dict[item.name] = {'value': item.collection_reference, 'type': item.data_type}
	return property_dict

# ********************************************************* #
class InputState(Enum):
	IDLE = 'idle'		# No input action detected
	DOWN = 'down'		# Input has just been pressed
	HOLD = 'hold'		# Input is being held down
	UP = 'up'			# Input has been released

# ********************************************************* #
@dataclass
class ScriptData:
	# ---------------------------------------------------------------- #
	@dataclass
	class Input:
		action1: 'InputState' = InputState.IDLE
		action2: 'InputState' = InputState.IDLE
		action3: 'InputState' = InputState.IDLE
		action4: 'InputState' = InputState.IDLE
		state_map = {(False, False): InputState.IDLE, (False, True): InputState.DOWN,
					  (True, False): InputState.UP, (True, True): InputState.HOLD}

		forward: bool = False	# basic inputs
		back: bool = False
		left: bool = False
		right: bool = False
		up: bool = False
		down: bool = False

		restart: bool = False
		respawn: bool = False

		pad_move: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
		pad_look: Vector = field(default_factory=lambda: Vector((0, 0, 0)))

	# ---------------------------------------------------------------- #
	@dataclass
	class Player:
		view_pos: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
		view_vec: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
		view_mat: Matrix = field(default_factory=lambda: Matrix.Identity(4))

		aim_pos: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
		aim_vec: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
		aim_mat: Matrix = field(default_factory=lambda: Matrix.Identity(4))

		root_pos: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
		root_mat: Matrix = field(default_factory=lambda: Matrix.Identity(4))

		velocity: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
		acceleration: Vector = field(default_factory=lambda: Vector((0, 0, 0)))

		is_grounded: bool = False
		is_contact: bool = False
		is_teleport: bool = False
		is_respawn: bool = False

	@dataclass
	class Scene:
		real_timestep: float = 0.0		# update loop timestep
		enable_animation: bool = False
		write_frame: bool = False
		current_frame: int = 0
		timestep: float = 0.0
		framerate: float = 0.0

	input = Input()	# NO factories, as we need this static
	player = Player()
	scene = Scene()


# ********************************************************* #
class UserScriptInspector:
	# This is called by omnistep operator (by a command line argument),
	# to populate the Inspector UI. It saves all names and current values,
	# and reassigns the values later in 'custom_ui'
	# ---------------------------------------------------------------- #
	def __init__(self, context, command):
		self.settings = context.scene.omnistep_settings
		self.script_source = self.settings.script_source

		if command == 'create':		# Create Template
			self.create(context)

		if self.script_source is None:	# No Script Loaded
			self.settings.script_items.clear()
			return

		if command == 'refresh':	# Update Values
			self.refresh(context)

		if command == 'write':		# Writeback values to script
			self.write(context)

	# ---------------------------------------------------------------- #
	def refresh(self, context):
		global_dict = {} # = globals().copy() # Not needed it seems
		global_dict['UserScriptBase'] = UserScriptBase
		global_dict['InputState'] = InputState
		global_dict['TransformNode'] = TransformNode
		local_dict = global_dict
		UserScriptBase._settings = self.settings
		UserScriptBase._globals = global_dict
		UserScriptBase._is_running = False
		# Only Vector is needed beforehand for the ui props. equivalent to: 'from mathutils import Vector'
		mathutils_module = UserScriptBase._globals['mathutils'] = importlib.import_module('mathutils')
		UserScriptBase._globals['Vector'] = getattr(mathutils_module, 'Vector')

		UserScriptBase._property_dict = extract_property_details(self, self.settings)	# store all current names and values
		self.settings.script_items.clear()												# clear all settings items
		exec(self.script_source.as_string(), global_dict, local_dict)

		# Check if valid
		if 'CustomUserScript' not in local_dict:
			return
		self.user_script_instance = local_dict['CustomUserScript']()
		if hasattr(self.user_script_instance, 'custom_ui'):
			self.user_script_instance.custom_ui()

	# ---------------------------------------------------------------- #
	def create(self, context):
		script_content = (
		"# --- import modules in the 'imports' method below ---\n"
		"\n"
		"class CustomUserScript(UserScriptBase):\n"
		"    def custom_ui(self):\n"
		"        self.add_property('example_var', 'BOOLEAN')\n"
		"\n"
		"    def imports(self):\n"
		"        self.local_import('import bpy')\n"
		"        self.local_import('from mathutils import Vector, Quaternion, Matrix')\n"
		"\n"
		"    def start(self, context, data):\n"
		"        pass\n"
		"\n"
		"    def update(self, context, data):\n"
		"        if data.input.action1 == InputState.DOWN:\n"
		"            self.display_message(str(self.example_var))\n"
		"\n"
		"    def done(self, context, canceled, data):\n"
		"        pass\n")
		# Create a new text block or update if it already exists
		text_block = bpy.data.texts.new(name="CustomUserScript.py")
		text_block.from_string(script_content)
		text_block.cursor_set(0)
		self.settings.script_source = text_block
		self.script_source = text_block
		# Call Refresh to update Inspector
		self.refresh(context)

	# ---------------------------------------------------------------- #
	def write(self, context):
		# Get a reference to the script source as a list of lines
		lines = list(self.script_source.lines)
		script_items_dict = {item.name: item for item in self.settings.script_items}

		# Regex to extract parts of the add_property call
		property_pattern = re.compile(r"^(\s*)self\.add_property\(\s*'([^']+)',\s*'([^']+)'(?:,\s*(.*?))?\s*\)((?:\s*#.*)?)$")

		for i, line in enumerate(lines):
			line_content = line.body

			# Skip processing for commented lines
			if line_content.strip().startswith('#'):
				continue

			match = property_pattern.match(line_content)
			if match:
				indent, prop_name, data_type, remaining, comment = match.groups()

				if prop_name in script_items_dict:
					item = script_items_dict[prop_name]
					item.changed = False  # UI feedback reset
					default_value = self.extract_value(item)

					# Handle the None case for default_value
					if default_value is None:
						updated_line = f"{indent}self.add_property('{prop_name}', '{data_type.upper()}'){comment}"
					else:
						default_value_repr = repr(default_value) if not isinstance(default_value, str) else f"'{default_value}'"
						updated_line = f"{indent}self.add_property('{prop_name}', '{data_type.upper()}', {default_value_repr}){comment}"
					lines[i].body = updated_line
					continue

	# ---------------------------------------------------------------- #
	def extract_value(self, item):
		if item.data_type == 'FLOAT':
			return float(item.float_value)
		elif item.data_type == 'INT':
			return int(item.int_value)
		elif item.data_type == 'STRING':
			return str(item.string_value)
		elif item.data_type == 'VECTOR':
			return Vector(item.vector_value)
		elif item.data_type == 'COLOR':
			return Vector(item.color_value)
		elif item.data_type == 'BOOLEAN':
			return bool(item.boolean_value)
		elif item.data_type == 'MATERIAL':
			if item.material_reference is not None:
				return item.material_reference.name
			return None
		elif item.data_type == 'OBJECT':
			if item.object_reference is not None:
				return item.object_reference.name
			return None
		elif item.data_type == 'COLLECTION':
			if item.collection_reference is not None:
				return item.collection_reference.name
			return None
		elif item.data_type == 'ACTION':
			if item.action_reference is not None:
				return item.action_reference.name
			return None
		return None


# ********************************************************* #
class UserScript:
	# ---------------------------------------------------------------- #
	def __init__(self, context, overlay: Overlay, playerstate: PlayerState, scenestate: SceneState, inputstate: InputState, omnistep_player: OmniStep_Player):
		self.context = context
		self.settings = context.scene.omnistep_settings
		self.script_source = self.settings.script_source
		if self.script_source is None:
			return

		self.enabled = self.settings.enable_scripting and self.script_source is not None
		if not self.enabled:
			return

		self.valid = True 		# does the Script have the correct class
		self.canceled = False	# Exit state info for the user script. Return or Esc

		# Global References
		self.overlay = overlay
		self.player = playerstate
		self.scenestate = scenestate
		self.input = inputstate
		self.script_data = ScriptData()

		# Assign static values (which are not available in state classes)
		self.script_data.scene.enable_animation = self.settings.enable_animation
		self.script_data.scene.timestep = 1.0 / self.scenestate.scene_framerate
		self.script_data.scene.framerate = self.scenestate.scene_framerate

		# Helpers
		self.old_action1 = False
		self.old_action2 = False
		self.old_action3 = False
		self.old_action4 = False

		# Prepare Script
		global_dict = {}
		global_dict['UserScriptBase'] = UserScriptBase
		global_dict['InputState'] = InputState
		global_dict['TransformNode'] = TransformNode
		local_dict = global_dict # allows classes etc. in the userscript, better than '{}'

		# Private Global
		UserScriptBase._context = self.context
		UserScriptBase._overlay = self.overlay	# These are available for all instaces, also at init
		UserScriptBase._settings = self.settings # To add custom variables
		UserScriptBase._globals = global_dict
		UserScriptBase._omnistep_player = omnistep_player
		UserScriptBase._scenestate = self.scenestate
		UserScriptBase._collection_set = set(self.context.scene.collection.children_recursive)

		# Public Global
		UserScriptBase.player = UserScriptBase.Player(UserScriptBase)
		UserScriptBase.scene = UserScriptBase.Scene(UserScriptBase)
		UserScriptBase.util = UserScriptBase.Util(UserScriptBase)

		# Only Vector is needed beforehand for the ui props. equivalent to: 'from mathutils import Vector'
		mathutils_module = UserScriptBase._globals['mathutils'] = importlib.import_module('mathutils')
		UserScriptBase._globals['Vector'] = getattr(mathutils_module, 'Vector')
		UserScriptBase._is_running = True

		UserScriptBase._property_dict = extract_property_details(self, self.settings)	# store all current names and values
		self.settings.script_items.clear()												# clear all settings items

		exec(self.script_source.as_string(), global_dict, local_dict)

		if 'CustomUserScript' in local_dict:
			self.user_script_instance = local_dict['CustomUserScript']()
			if hasattr(self.user_script_instance, 'custom_ui'):
				self.user_script_instance.custom_ui() # run again, in case of first run
		else:
			self.valid = False
			return

		if hasattr(self.user_script_instance, 'imports'):
			self.user_script_instance.imports()
		self.user_script_instance.start(self.context, self.script_data) # Run Start Method

	# ---------------------------------------------------------------- #
	def update(self):
		if self.script_source is None or not self.enabled or not self.valid:
			return

		# Update Player (TransformNode are already linked by reference)
		self.script_data.player.view_pos = self.player.view.get_position()
		self.script_data.player.view_vec = -self.player.view.up()	# Reverse, as view-mat is -Z
		self.script_data.player.view_mat = self.player.view.matrix.copy()

		self.script_data.player.aim_pos = self.player.aim.get_position()
		self.script_data.player.aim_vec = -self.player.aim.up()
		self.script_data.player.aim_mat = self.player.aim.matrix.copy()

		self.script_data.player.root_pos = self.player.root.get_position()
		self.script_data.player.root_mat = self.player.root.matrix.copy()

		self.script_data.player.velocity = self.player.velocity
		self.script_data.player.acceleration = self.player.real_accel

		self.script_data.player.is_grounded = self.player.is_grounded
		self.script_data.player.is_contact= self.player.is_contact
		self.script_data.player.is_teleport = self.player.is_teleport
		self.script_data.player.is_respawn = self.input.respawn

		# Update Inputs
		self.script_data.input.action1 = ScriptData.input.state_map[(self.old_action1, self.input.action1)]
		self.script_data.input.action2 = ScriptData.input.state_map[(self.old_action2, self.input.action2)]
		self.script_data.input.action3 = ScriptData.input.state_map[(self.old_action3, self.input.action3)]
		self.script_data.input.action4 = ScriptData.input.state_map[(self.old_action4, self.input.action4)]
		self.old_action1 = self.input.action1
		self.old_action2 = self.input.action2
		self.old_action3 = self.input.action3
		self.old_action4 = self.input.action4

		self.script_data.input.forward = self.input.forward
		self.script_data.input.back = self.input.back
		self.script_data.input.left = self.input.left
		self.script_data.input.right = self.input.right
		self.script_data.input.up = self.input.up
		self.script_data.input.down = self.input.down

		self.script_data.input.restart = self.input.restart
		self.script_data.input.respawn = self.input.respawn

		self.script_data.input.pad_move = self.input.pad_raw_move
		self.script_data.input.pad_look = self.input.pad_raw_look

		# Update Scene
		self.script_data.scene.real_timestep = self.scenestate.current_timestep
		self.script_data.scene.write_frame = self.scenestate.write_frame
		self.script_data.scene.current_frame = self.scenestate.scene_frame

		# Update Script
		self.user_script_instance.update(self.context, self.script_data)

	# ---------------------------------------------------------------- #
	def late_update(self):
		if self.script_source is None or not self.enabled or not self.valid:
			return
		self.user_script_instance.late_update(self.context, self.script_data)

	# ---------------------------------------------------------------- #
	def cancel(self):
		if self.script_source is None or not self.enabled or not self.valid:
			return
		self.canceled = True

	# ---------------------------------------------------------------- #
	def disable(self):
		if self.script_source is None or not self.enabled or not self.valid:
			return
		self.user_script_instance.done(self.context, self.canceled, self.script_data)


# ********************************************************* #
class UserScriptBase:
	# Private Global Variables
	_context = None
	_overlay = None
	_globals = None
	_settings = None
	_property_dict = None
	_omnistep_player = None	# Used for Impulse methods etc.
	_scenestate = None		# for (dynamic) bvh methods etc.
	_collection_set = None	# used for utils - copy and move object to collection. avoids problems with rigidbodyworld
	_is_running = False 	# is this instance for ui updates or a script execution? Needed for parameter handling

	# Public Global (for namespace logic - e.g. self.player.dosomething() )
	player = None
	scene = None
	util = None

	# Player Class =================================================== #
	class Player:
		def __init__(self, outer_instance):	# init is done manually in the prep for the class (above)
			self._outer = outer_instance

		def set_position(self, pos, clear_velocity=False):
			self._outer._omnistep_player.user_set_position(pos, clear_velocity)

		def apply_impulse(self, vec, clear_velocity=False):
			self._outer._omnistep_player.user_apply_impulse(vec, clear_velocity)

		def respawn(self, obj=None):
			if not obj:
				self._outer._omnistep_player.user_respawn()
			else:
				self._outer._omnistep_player.user_respawn(obj=obj)

		def ray_cast(self, pos, vec):
			return self._outer._omnistep_player.user_ray_cast_player(pos, vec)

	# Scene Class ==================================================== #
	class Scene:
		def __init__(self, outer_instance):	# init is done manually in the prep for the class (above)
			self._outer = outer_instance

		def set_dynamic_collider(self, obj, full_evaluation=False):
			self._outer._scenestate.bvhtree.dynamic_bvh_set_obj(obj, full_evaluation)

		def remove_dynamic_collider(self, obj):
			self._outer._scenestate.bvhtree.dynamic_bvh_remove_obj(obj)

		def clear_dynamic_colliders(self):
			self._outer._scenestate.bvhtree.dynamic_bvh_clear_all()

		def ray_cast(self, pos, vec, distance=1.84467e+19):
			return self._outer._scenestate.bvhtree.ray_cast(pos, vec, distance)

		def bvh_find_nearest(self, pos, distance=1.84467e+19):
			return self._outer._scenestate.bvhtree.find_nearest(pos, distance)

	# Scene Util ===================================================== #
	class Util:
		def __init__(self, outer_instance):
			self._outer = outer_instance

		def duplicate_obj(self, obj, target_collection=None, deep_copy=False):
			if obj is None or not isinstance(obj, bpy.types.Object):
				raise ValueError("util.duplicate_object: Invalid object provided")

			new_obj = obj.copy()
			if deep_copy:
				new_obj.data = obj.data.copy()
			if target_collection is not None:
				target_collection.objects.link(new_obj)
			else:
				original_collection = None
				for col in obj.users_collection:
					if col in self._outer._collection_set:
						original_collection = col
						break

				if original_collection:
					original_collection.objects.link(new_obj)
				else:	# If no suitable collection found, link to the scene collection
					bpy.context.scene.collection.objects.link(new_obj)

			return new_obj

		def delete_obj(self, obj):
			if obj is None or not isinstance(obj, bpy.types.Object):
				raise ValueError("util.duplicate_object: Invalid object provided")

			for col in obj.users_collection:
				col.objects.unlink(obj)
			bpy.data.objects.remove(obj, do_unlink=True)

		def align_to_obj(self, source_obj, target_obj, mode='lrs'):
			if not isinstance(source_obj, bpy.types.Object) or not isinstance(target_obj, bpy.types.Object):
				raise ValueError("util.align_object: Source and target must be Blender objects")

			mode = mode.lower()

			if 'l' in mode:
				source_obj.location = target_obj.matrix_world.to_translation()

			if 'r' in mode:
				if source_obj.rotation_mode != target_obj.rotation_mode:
					if target_obj.rotation_mode == 'QUATERNION':
						source_obj.rotation_quaternion = target_obj.rotation_quaternion.copy()
					else:
						source_obj.rotation_euler = target_obj.rotation_euler.copy()
				else:
					if target_obj.rotation_mode == 'QUATERNION':
						source_obj.rotation_quaternion = target_obj.rotation_quaternion.copy()
					else:
						source_obj.rotation_euler = target_obj.rotation_euler.copy()

			if 's' in mode:
				source_obj.scale = target_obj.scale.copy()

		def align_to_ray(self, obj, pos, direction, forward='Y', up='Z'):
			vec = direction.normalized()
			rot_mat = vec.to_track_quat(forward, up).to_matrix().to_4x4()
			obj.matrix_world = Matrix.Translation(pos) @ rot_mat

		def translate_obj(self, obj, vec, space='local'):
			if space == 'global':
				obj.location += vec
			elif space == 'local':
				obj.location += obj.matrix_world.to_3x3() * vec

		def ray_cast_obj(self, obj, pos, direction):
			if obj.type != 'MESH':
				return False, None, None, -1

			local_dir = obj.matrix_world.inverted().to_3x3() @ direction.normalized()
			local_start = obj.matrix_world.inverted() @ pos

			hit, location, normal, index = obj.ray_cast(local_start, local_dir)

			if hit:
				location = obj.matrix_world @ location
				normal = obj.matrix_world.to_3x3() @ normal.normalized()

			return hit, location, normal, index

		def insert_transform_keys(self, obj, scene_frame=None, interpolation='LINEAR'):
			if scene_frame is None:
				scene_frame = self._outer._scenestate.scene_frame

			if obj is None:
				return
			# Insert keyframes for location and scale
			obj.keyframe_insert(data_path="location", frame=scene_frame)
			obj.keyframe_insert(data_path="scale", frame=scene_frame)

			rotation_data_path = "rotation_quaternion" if obj.rotation_mode == 'QUATERNION' else "rotation_euler"
			obj.keyframe_insert(data_path=rotation_data_path, frame=scene_frame)

			# Adjust interpolation right after creating the keyframes
			if obj.animation_data and obj.animation_data.action:
				for fcurve in obj.animation_data.action.fcurves:
					if fcurve.data_path in ["location", "scale", rotation_data_path]:
						for keyframe_point in fcurve.keyframe_points:
							if keyframe_point.co[0] == scene_frame:
								keyframe_point.interpolation = interpolation

		def insert_vis_keys(self, obj, state, scene_frame=None):
			if scene_frame is None:
				scene_frame = self._outer._scenestate.scene_frame

			if obj is None:
				return

			obj.hide_viewport = not state
			obj.hide_render = not state
			obj.keyframe_insert('hide_viewport', frame=scene_frame)
			obj.keyframe_insert('hide_render', frame=scene_frame)

		def clear_collection(self, collection):
			objects_to_delete = [obj for obj in collection.objects]
			# First pass: unlink and schedule removals without deleting anything yet
			for obj in objects_to_delete:
				for col in obj.users_collection:
					col.objects.unlink(obj)
			# Second pass: remove objects
			for obj in objects_to_delete:
				bpy.data.objects.remove(obj, do_unlink=True)

		def get_collection_objs(self, collection, filter=None):
			# supported filters:
			# 'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'ARMATURE', 'LATTICE', 'EMPTY', 'GPENCIL',
        	# 'CAMERA', 'LIGHT', 'SPEAKER', 'LIGHT_PROBE'
			if not collection:
				return None

			filtered_objs = []
			for obj in collection.objects:
				if filter is None or obj.type == filter:
					filtered_objs.append(obj)

			return filtered_objs



	# Main Methods =================================================== #
	def __init__(self):
		# super().__init__() # Run this in the user space init to call this base class
		# not needed in the current setup
		pass

	# ---------------------------------------------------------------- #
	def start(self, context, data):
		pass

	# ---------------------------------------------------------------- #
	def update(self, context, data):
		pass

	# ---------------------------------------------------------------- #
	def late_update(self, context, data):
		pass

	# ---------------------------------------------------------------- #
	def done(self, context, state, data):
		pass


	# User Exposed Methods =========================================== #
	def display_message(self, message):
		self._overlay.write(str(message))

	# ---------------------------------------------------------------- #
	def local_import(self, import_string): #, alias=None):
		# old implementation:
		# If an alias is provided, use it; otherwise, use the module_name as the key
		#key = alias if alias else module_name
		#self._globals[key] = importlib.import_module(module_name)

		# Split the string to analyze it
		parts = import_string.split()

		if "import" in parts and "from" in parts:
			# Example: "from mathutils import Vector, Quaternion"
			module_name = parts[1]
			imports = parts[-1].split(',')
			module = importlib.import_module(module_name)
			for item in imports:
				item = item.strip()
				self._globals[item] = getattr(module, item)

		elif "import" in parts and "as" in parts:
			# Example: "import mathutils as mu"
			module_name = parts[1]
			alias = parts[-1]
			self._globals[alias] = importlib.import_module(module_name)

		elif "import" in parts:
			# Example: "import mathutils"
			module_name = parts[-1]
			self._globals[module_name] = importlib.import_module(module_name)

		else:
			print("Invalid import format")

	# ---------------------------------------------------------------- #
	def add_property(self, name, data_type, default=None): # This creates ui entries
		# Add new property item
		new_item = self._settings.script_items.add()
		new_item.data_type = data_type
		new_item.name = name

		actual_value = None		# Initialize a variable to hold the actual value

		# TWO CODE PATHS: Either 'Read Parameters' or actual Run.
		if self._is_running:
			# Priorities: Property Values > Script Values > Defaults
			actual_value = self._set_from_property(new_item)
			if actual_value is None:
				actual_value = self._set_from_script(new_item, data_type, default)
			# Defaults
			if actual_value is None:
				actual_value = self._set_from_defaults(new_item)
		else:
			# Priorities: Script Values (if exist) > Property Values > Defaults
			actual_value = self._set_from_script(new_item, data_type, default)
			# Property Values
			if actual_value is None:
				actual_value = self._set_from_property(new_item)
			# Defaults
			if actual_value is None:
				actual_value = self._set_from_defaults(new_item)

		# Set or update the instance variable with the actual value
		if actual_value is not None:
			setattr(self, name, actual_value)
		new_item.changed = False

	# Private Methods ================================================ #
	def _is_default_type_valid(self, data_type, default):
		if data_type == 'FLOAT' and isinstance(default, float):
			return True
		elif data_type == 'INT' and isinstance(default, int):
			return True
		elif data_type == 'STRING' and isinstance(default, str):
			return True
		elif data_type == 'VECTOR' and isinstance(default, (tuple, list)) and len(default) == 3:
			return True
		elif data_type == 'COLOR' and isinstance(default, (tuple, list)) and len(default) == 4:
			return True
		elif data_type == 'BOOLEAN' and isinstance(default, bool):
			return True
		elif data_type == 'MATERIAL' and isinstance(default, str):
			return True
		elif data_type == 'OBJECT' and isinstance(default, str):
			return True
		elif data_type == 'COLLECTION' and isinstance(default, str):
			return True
		elif data_type == 'ACTION' and isinstance(default, str):
			return True
		return False

	# ---------------------------------------------------------------- #
	def _set_from_property(self, item):	# Set UI from Property Values
		actual_value = None
		if item.name in self._property_dict:
			previous_entry = self._property_dict[item.name]
			if previous_entry['type'] == item.data_type:
				if item.data_type == 'FLOAT':
					actual_value = previous_entry['value']
					item.float_value = actual_value
				elif item.data_type == 'INT':
					actual_value = previous_entry['value']
					item.int_value = actual_value
				elif item.data_type == 'STRING':
					actual_value = previous_entry['value']
					item.string_value = actual_value
				elif item.data_type == 'VECTOR':
					actual_value = Vector(previous_entry['value'])  # Ensure it's a copy
					item.vector_value = actual_value[:]
				elif item.data_type == 'COLOR':
					actual_value = Vector(previous_entry['value'])  # Use Vector to handle RGBA
					item.color_value = actual_value[:]
				if item.data_type == 'BOOLEAN':
					actual_value = previous_entry['value']
					item.boolean_value = actual_value
				elif item.data_type == 'OBJECT':
					actual_value = previous_entry['value']
					item.object_reference = actual_value
				elif item.data_type == 'COLLECTION':
					actual_value = previous_entry['value']
					item.collection_reference = actual_value
				elif item.data_type == 'ACTION':
					actual_value = previous_entry['value']
					item.action_reference = actual_value
		return actual_value

	# ---------------------------------------------------------------- #
	def _set_from_defaults(self, item): # Set UI from Defaults
		actual_value = None
		if item.data_type == 'FLOAT':
			actual_value = float(item.float_value)
		elif item.data_type == 'INT':
			actual_value = int(item.int_value)
		elif item.data_type == 'STRING':
			actual_value = str(item.string_value)
		elif item.data_type == 'VECTOR':
			actual_value = Vector(item.vector_value)
		elif item.data_type == 'COLOR':
			actual_value = Vector(item.color_value)
		elif item.data_type == 'BOOLEAN':
			actual_value = bool(item.boolean_value)
		elif item.data_type == 'MATERIAL':
			actual_value = None # item.material_reference
		elif item.data_type == 'OBJECT':
			actual_value = None # item.object_reference
		elif item.data_type == 'COLLECTION':
			actual_value = None # item.collection_reference
		elif item.data_type == 'ACTION':
			actual_value = None # item.action_reference
		return actual_value

	# ---------------------------------------------------------------- #
	def _set_from_script(self, item, data_type, value):
		actual_value = None
		# check if script is valid
		valid = False
		if data_type == 'FLOAT' and isinstance(value, float):
			valid = True
		elif data_type == 'INT' and isinstance(value, int):
			valid = True
		elif data_type == 'STRING' and isinstance(value, str):
			valid = True
		elif data_type == 'VECTOR' and isinstance(value, Vector) and len(value) == 3:
			valid = True
		elif data_type == 'COLOR' and isinstance(value, Vector) and len(value) == 4:
			valid = True
		elif data_type == 'BOOLEAN' and isinstance(value, bool):
			valid = True
		elif data_type == 'MATERIAL' and isinstance(value, str):
			valid = True
		elif data_type == 'OBJECT' and isinstance(value, str):
			valid = True
		elif data_type == 'COLLECTION' and isinstance(value, str):
			valid = True
		elif data_type == 'ACTION' and isinstance(value, str):
			valid = True
		# use script value
		if valid:
			if data_type == 'FLOAT':
				actual_value = value
				item.float_value = actual_value
			elif data_type == 'INT':
				actual_value = value
				item.int_value = actual_value
			elif data_type == 'STRING':
				actual_value = value
				item.string_value = actual_value
			elif data_type == 'VECTOR':
				actual_value = Vector(value)  # Ensure it's a copy
				item.vector_value = actual_value[:]
			elif data_type == 'COLOR':
				actual_value = Vector(value)  # Use Vector to handle RGBA
				item.color_value = actual_value[:]
			if data_type == 'BOOLEAN':
				actual_value = value
				item.boolean_value = actual_value
			elif data_type == 'OBJECT':
				if value in bpy.data.objects:
					actual_value = bpy.data.objects[value]  # Retrieve the object reference from its name
				item.object_reference = actual_value
			elif data_type == 'COLLECTION':
				if value in bpy.data.collections:
					actual_value = bpy.data.collections[value]  # Retrieve the collection reference from its name
				item.collection_reference = actual_value
			elif data_type == 'ACTION':
				if value in bpy.data.actions:
					actual_value = bpy.data.actions[value]  # Retrieve the action reference from its name
				item.action_reference = actual_value

		return actual_value


