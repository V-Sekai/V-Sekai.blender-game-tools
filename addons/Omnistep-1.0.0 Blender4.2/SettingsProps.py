import bpy
import math
from . import Utils as util
from .SettingsPanel import OMNISTEP_CollectionItem
from .SettingsPanel import OMNISTEP_DynamicItem

# ********************************************************* #
class OmniStep_Settings(bpy.types.PropertyGroup):
	
	# region SYSTEM
	override_addon_settings: bpy.props.BoolProperty(name="Override Addon Settings",
						description="Override some Global Addon Setting per blend-file. Keymaps are set in the addon-preferences only",
						default=False)
	mouse_sensitivity: bpy.props.FloatProperty(name="Mouse Sensitivity", soft_min=0.0, soft_max=100.0, default=5)
	mouse_invert_y: bpy.props.BoolProperty(name="Invert Mouse Y", default=False)
	# endregion

	# region SCENE
	# System
	operator_running: bpy.props.BoolProperty(name="Operator Runnning", default=False)
	operator_error: bpy.props.BoolProperty(name="internal Operator Error", default=False)
	operator_errorstate:  bpy.props.StringProperty(name="internal Operator Error State",
						description="", default="")

	# View
	set_view: bpy.props.EnumProperty(name="View",
		description="Set View",
		items=[
			('CURRENT', "Current", "Starts from the current View. Either Camera or Perspective"),
			('CAMERA', "Active Camera", "Starts from the active Camera"),
		], default='CURRENT')

	set_focal: bpy.props.BoolProperty(name="Set Focal Length",
						description="Override the current viewport Focal Length (NOT for Cameras)",
						default=True)
	view_focal: bpy.props.FloatProperty(name="Focal Length", unit='CAMERA', options=set(), default=28, min=1, max=250)

	original_focal: bpy.props.FloatProperty(name="internal Original Focal Length", default=28, min=1, max=250)
	original_autokey: bpy.props.BoolProperty(name="internal Original AutoKey", default=False)


	target_spawn: bpy.props.EnumProperty(name="Spawn at",
		items=[
			('VIEW', "View", "Starts and respawns at the current view / camera"),
			('COLLECTION', "Collection", "Starts and respawns at empties found in the referenced Collection."),
		], default='VIEW')
	spawn_collection: bpy.props.PointerProperty(name="Collection", type=bpy.types.Collection)

	# Framerate
	custom_framerate: bpy.props.IntProperty(name="Set Fps",
					description="Current target framerate",
					default=60, min=1)
	target_framerate: bpy.props.EnumProperty(name="Framerate",
		description="Target Framerate for the Viewport. (independent from the recording framerate)",
		items=[
			('30', "30 fps", ""),
			('60', "60 fps", ""),
			('120', "120 fps", ""),
			('CUSTOM', "Custom", ""),
		], update=util.update_panel_values, default='60')
	current_framerate: bpy.props.FloatProperty(name="Current Framerate", default=0)	# internal!

	# Scale
	custom_scale: bpy.props.FloatProperty(name="Set Scale", precision=3, default=1, min=0.0001)
	target_scale: bpy.props.EnumProperty(name="Scene Scale",
		items=[
			('M', "Meters", ""),
			('CM', "Centimeters", ""),
			('INCH', "Inches", ""),
			('FEET', "Feet", ""),
			('CUSTOM', "Custom", ""),
		], update=util.update_panel_values, default='M')
	current_scale: bpy.props.FloatProperty(name="Current Scale", default=1.0)

	# Physics
	custom_gravity: bpy.props.FloatProperty(name="Set Gravity [m/s²]", soft_min=0.0, soft_max=100, default=20.0)
	target_gravity: bpy.props.EnumProperty(name="Gravity", description='Player Gravity',
		items=[
			('20.00', "Fps Games", "20 m/s². It isn't realistic, but used by many engines as it 'feels right'"),
			('15.24', "Source Engine", "15.24 m/s²"),
			('9.81', "Earth", "9.81 m/s²"),
			('CUSTOM', "Custom", ""),
		], update=util.update_panel_values, default='20.00')
	current_gravity: bpy.props.FloatProperty(name="Current Gravity", default=20.0)
	# endregion

	# region COLLISION
	collide_set: bpy.props.EnumProperty(name="Collision Set",
					items=[
						('ALL', "Everything", ""),
						('INCLUDE', "Include Collections", ""),
						('EXCLUDE', "Exclude Collections", ""),
					], update=util.update_panel_values, default='ALL')
	collide_collections: bpy.props.CollectionProperty(type=OMNISTEP_CollectionItem)
	ignore_wireframes: bpy.props.BoolProperty(name="Ignore Wireframes",
					description="Don't collide with Objects that have their display mode set to 'Wire' or 'Bounds'",
					default=True)
	ignore_animated: bpy.props.BoolProperty(name="Ignore Animated",
					description=("Don't collide with objects that are animated or "
					"have active rigid body physics. This includes the object itself, "
					"any of its parents and any enabled constraints"),
					default=False)
	collide_collection_instances: bpy.props.BoolProperty(name="Collection Instances",
					description="Includes Collection Instances in the Collision. This includes Linked Libraries and nested Collections",
					default=False)
	collide_evaluate: bpy.props.BoolProperty(
					name="Full Evaluation",
					description=("Slow, but comprehensive. Evaluate the objects considering modifiers, constraints, and other procedural edits. "
					"When disabled, only the base mesh data will be used (Faster)"),
					default=True)
	collision_samples: bpy.props.IntProperty(name="Samples",
					description="Collision substeps",
					min=1, soft_min=4, soft_max=64, max=128, default=16)


	# endregion

	# region DISPLAY
	# Panels
	n_panel_hide: bpy.props.BoolProperty(name="Hide N-Panel", default=True) # should we hide it?
	n_panel_visible: bpy.props.BoolProperty(name="internal N-Panel", default=False) # is it visible when op starts?

	t_panel_hide: bpy.props.BoolProperty(name="Hide T-Panel", default=True)
	t_panel_visible: bpy.props.BoolProperty(name="internal T-Panel", default=False)

	# Overlays
	gizmos_hide: bpy.props.BoolProperty(name="Hide Gizmos", default=True)
	gizmos_visible: bpy.props.BoolProperty(name="internal Gizmos", default=False)

	overlays_hide: bpy.props.BoolProperty(name="Hide Overlays", default=True)
	overlays_visible: bpy.props.BoolProperty(name="internal Overlays", default=False)

	header_hide: bpy.props.BoolProperty(name="Hide Header", default=False)
	header_visible: bpy.props.BoolProperty(name="internal Header", default=False)

	show_reticle: bpy.props.BoolProperty(name="Show Reticle",
						description="Show center reticle (configure the appearance in the addon prefs)",
						default=True)

	show_message: bpy.props.BoolProperty(name="Show Messages",
						description="Show info messages as overlay (configure the appearance in the addon prefs)",
						default=True)
	#reticle_thickness:

	# endregion

	# region PLAYER
	# Mode
	play_mode: bpy.props.EnumProperty(name="Mode", description='Play Mode. Press [Tab] while running to switch',
		items=[
			('WALK', "Walk", ""),
			('FLY', "Fly", ""),
		], default='WALK')

	# Player Props
	walk_mouse_damping: bpy.props.FloatProperty(name="Look Damping",
						description="Smooths the mouse input [Walk]",
						min=0.0, max=1.0, default=0.1)
	fly_mouse_damping: bpy.props.FloatProperty(name="Look Damping",
						description="Smooths the mouse input [Fly]",
						min=0.0, max=1.0, default=0.6)

	teleport_speed: bpy.props.FloatProperty(name="Teleport Speed [m/s]",
						description="",
						min=0.01, default=20.0)
	teleport_time: bpy.props.FloatProperty(name="Teleport Max. Time [s]",
						description="",
						min=0.1, default=5.0)

	player_height: bpy.props.FloatProperty(name="Player Height [m]",
					description="The actual camera height is 'Player Height' - 0.1. The range is limited to keep physics stable. (Use Scene Scale if needed)",
					min=0.8, max=2.0, default=1.6)
	player_head_offset: bpy.props.FloatProperty(name="Eye Depth [m]",
					description="Forward offset between the view's rotation point and the camera position",
					min=-0.3, max=0.3, default=0.08)

	run_speed: bpy.props.FloatProperty(name="Run Speed [m/s]",  min=0.01, default=4.5)
	walk_speed: bpy.props.FloatProperty(name="Walk Speed [m/s]", min=0.01, default=2.25)
	always_run: bpy.props.BoolProperty(name="Always Run", default=True)

	jump_speed: bpy.props.FloatProperty(name="Jump [m/s²]",
					description="Jump Acceleration in m/s²",
					soft_min=0.001, soft_max= 100, default=6.5)
	wall_jump: bpy.props.BoolProperty(name="Wall Jump",
					description="Allow Jumps while the Player is in contact with a wall",
					default=True)
	air_jump: bpy.props.BoolProperty(name="Air Jump",
					description="Allow Jumps while the Player is in the air",
					default=False)
	coyote_time: bpy.props.FloatProperty(name="Coyote Time", min=0.0, soft_max=0.5, default=0.15)

	ground_friction: bpy.props.FloatProperty(name="Friction",
					description="Ground friction coefficient affecting how the player slows down or accelerates, especially on slopes",
					min=0, default=5.0)
	ground_acceleration: bpy.props.FloatProperty(name="Acceleration",
					description="Controls how quickly the player gains speed on the ground",
					min=0.01, default=5.0)

	cam_inertia: bpy.props.BoolProperty(name="Motion Damping",
					description="Adds damping to camera movement for a more natural feel, smoothing transitions over stairs and uneven terrain",
					default=True)

	walk_banking: bpy.props.FloatProperty(name="Walk Banking",
					description="Rolls the camera based on speed and direction",
					soft_min=-0.1, soft_max=0.1, default=-0.02)

	# Spring Systems
	cam_inertia_spring_vertical: bpy.props.FloatProperty(name="Motion Damping K Vertical",
						      description="[Spring Constant] Vertical camera inertia damping. Low values = High Damping",
							min=1.0, max=2000.0, default=100.0)
	cam_inertia_spring_horizontal: bpy.props.FloatProperty(name="Motion Damping K Horizontal",
							description="[Spring Constant] Horizontal camera inertia damping. Low values = High Damping",
							min=1.0, max=2000.0, default=1000.0)
	banking_spring: bpy.props.FloatProperty(name="Bank Damping K",
					description="[Spring Constant] Dampens the view banking. Low values = High Damping",
					min=1.0, max=2000.0, default=100.0)

	# internals
	player_radius: bpy.props.FloatProperty(name="internal Player Radius", default=0.4)
	ground_decceleration: bpy.props.FloatProperty(name="Walk Ground Deceleration", min=1.00, default=4.0)
	air_acceleration: bpy.props.FloatProperty(name="Walk Air Acceleration", min=0.01, default=2.0)
	air_decceleration: bpy.props.FloatProperty(name="Walk Air Deceleration", min=0.01, default=2.0)
	walk_slope: bpy.props.FloatProperty(name="Walk Slope", default=45)
	stair_slope: bpy.props.FloatProperty(name="Stair Slope", default=85)
	wishjump_timeout: bpy.props.FloatProperty(name="internal Wishjump Timeout", default=0.3)

	# Fly
	fly_collisions: bpy.props.BoolProperty(name="Collisions", default=False)
	fly_radius: bpy.props.FloatProperty(name="Player Radius [m]", min=0.01, default=0.25)
	fly_speed: bpy.props.FloatProperty(name="Speed [m/s]", min=0.01,
					description="Maximum flying speed in meters per second",
					default=6.0)
	fly_acceleration: bpy.props.FloatProperty(name="Accel. [m/s²]",
					description="Acceleration: Determines how quickly the player reaches the desired speed",
					min=0.01, default=12.0)
	fly_air_friction: bpy.props.FloatProperty(name="Friction [m/s²]",
					description="Friction / Deceleration. Determines how quickly the player stops",
					min=0.01, default=4.0)
	fly_banking: bpy.props.FloatProperty(name="Banking",
					description="Rolls the camera based on speed and direction",
					soft_min=0.0, soft_max=1.0, default=0.15)
	radial_view_control: bpy.props.BoolProperty(name="Radial View Control",
					description=("Enables a radial-based mouse input where distance and direction from the screen's"
					" center determine the camera's rotation speed and direction, providing smoother and continuous"
					" camera movement"),
					default=False)
	trackball_rotation: bpy.props.BoolProperty(name="Trackball Rotation",
					description=("Free rotation around all axes. Set the 'trackball_balance' in advanced settings adjust roll vs. yaw"),
					default=False)
	trackball_balance: bpy.props.FloatProperty(name="Trackball Balance",
					description="Balance roll vs. yaw for horizontal mouse movement",
					min=0.0, max=1.0, default=0.7)
	trackball_autolevel: bpy.props.FloatProperty(name="Trackball Leveling",
					description="Levels the view when no movement input is given. 0 to disable",
					min=0.0, soft_max=1.0, default=0.5)
	radial_view_maxturn: bpy.props.FloatProperty(name="Radial View Turn Speed",
					description="When 'Radial View' is enabled, this sets the maximum turn speed in radians per second. (When the cursor is at the edge of the circle)",
					min=0.1, soft_max=16.0, default=2.0)


	# General
	adjust_focal_sens: bpy.props.BoolProperty(name="Adjust Focal Sensitivity",
					description="Adjusts the mouse sensitvity for the focal length (when above 28mm)",
					default=True)
	# endregion

	# region ANIMATION
	enable_animation: bpy.props.BoolProperty(name="",
					description="",
					default=False)
	play_animation: bpy.props.BoolProperty(name="Play Timeline",
					description=("Play the active Timeline while recording. "
					"As this can be slow, it is optional. Recordings are not affected by this"),
					default=True)
	
	fixed_timestep: bpy.props.BoolProperty(name="Use Fixed Timestep",
					description=("Use a fixed timestep - avoids microstutters in animations. Use this with matching blender and scene framerates."
					" Note that, while this removes stutters from recorded animations, you will get more stutters and time stretching in the viewport while recording."),
					default=False)

	child_of:bpy.props.PointerProperty(name="Child of",
					description="Pick an empty from the scene to parent the player to it. (e.g. when recording look-direction, while the parent is pre-animated)",
					type=bpy.types.Object,
					poll=util.empty_poll)
	parent_rotation: bpy.props.EnumProperty(name="Parent Rotation", description="", items=[
					('NONE', "None", "Only movement is locked, rotation is free relative to world space"),
					('ZAXIS', "Z-Axis", "Additionally rotates the player in the Z-Axis with the parent"),
					('FULL', "Full", "All movement and rotations are transferred to the player"),
					], default='NONE')

	preroll_animation: bpy.props.IntProperty(name="Preroll Frames",
					description="How many Frames to play before the Recording / Playback starts",
					default=0, min=0, soft_max=120)
	loop_animation: bpy.props.BoolProperty(name="Loop Timeline",
					description="Loop the timeline",
					default=False)
	record_animation: bpy.props.BoolProperty(name="Record Animation",
					description="Record the Camera Movement. To enable this, the 'View' has to be set to 'Active Camera' or 'Current' while in a camera view",
					default=False)
	# endregion

	# region SCRIPTING
	enable_scripting: bpy.props.BoolProperty(name="",
					description="",
					default=False)
	script_source:bpy.props.PointerProperty(name="Script Source",
					description="Pick an Script Entity from the Scene",
					type=bpy.types.Text, update= util.refresh_inspector_op)
	script_items: bpy.props.CollectionProperty(type=OMNISTEP_DynamicItem) # custom inspector stuff
	# endregion