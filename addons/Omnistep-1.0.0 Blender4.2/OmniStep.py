from .AddonPrefs import OMNISTEP_OT_Keymap, OMNISTEP_OT_ResetKey
from .AddonPrefs import OmniStep_AddonPreferences
from .SettingsProps import OmniStep_Settings
import bpy

import traceback
from . import Utils as util
from .OverlayConsole import OverlayConsole
from .OverlayGraph import OverlayGraph
from .OverlayMain import Overlay
from .SettingsPanel import *
from .InputManager import *
from .Scene import *
from .Player import *
from .Animation import *
from .UserScript import *


# ********************************************************* #
class VIEW3D_OT_OmniStep(bpy.types.Operator):
	bl_idname = "view3d.omnistep"
	bl_label = "OmniStep"
	bl_description = ("Start OmniStep Operator. Press 'Enter' or 'Esc' to exit")
	bl_options = {"BLOCKING", "GRAB_CURSOR"}

	# ---------------------------------------------------------------- #
	def invoke(self, context, event):
		try:
			if context.region_data is not None and context.area.type == "VIEW_3D":
				self.init_scene(context)
				self.init_view(context)

				self.console = OverlayConsole(context, 8, 12, False)
				#self.graph = OverlayGraph(context, 128, 255, self.scenestate.target_timestep)
				self.overlay = Overlay(context, self.scenestate)

				self.input = OmniStep_InputManager(context, self.console, self.scenestate)
				self.input.process_mousemove(event, True)  # inital reset

				self.player = OmniStep_Player(context, self.overlay, self.console, self.scenestate, self.input.state)
				self.player.spawn(True)

				self.animation = OmniStep_Animation(context, self.overlay, self.console, self.player.state, self.scenestate, self.input.state)
				
				self.init_display(context)

				self.userscript = UserScript(context, self.overlay, self.player.state, self.scenestate, self.input.state, self.player)

				context.window_manager.modal_handler_add(self)
				return {"RUNNING_MODAL"}
			else:
				self.report({"ERROR"}, "Active space must be a 3D View")
				return {"CANCELLED"}

		except Exception as e:
			self.settings.operator_error = True
			self.settings.operator_errorstate = str(e)
			self.cancel_omnistep(context)
			self.end_omnistep(context)
			return {"CANCELLED"}

	# ---------------------------------------------------------------- #
	def modal(self, context, event):
		try:
			# ========================= #
			if event.type == "ESC":
				self.cancel_omnistep(context)
				self.end_omnistep(context)
				return {"CANCELLED"}

			# ========================= #
			if event.type == "RET" and event.value == "PRESS":
				self.end_omnistep(context)
				return {"FINISHED"}

			# ========================= #
			if event.type not in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE"}:
				self.input.process_event(event)

			# ========================= #
			if event.type == "TIMER":
				self.update_scene(context)
				self.input.process_mousemove(event, False)
				self.input.update_direction()
				self.input.update_gamepad()

				self.userscript.update()
				self.player.update()
				self.animation.update()
				self.animation.update_timeline()
				self.userscript.late_update()

				
				#self.graph.write(self.scenestate.timer.time_delta)
				self.input.clear_triggers()
				context.area.tag_redraw()
			return {"RUNNING_MODAL"}

		except Exception as e:
			self.settings.operator_error = True
			self.settings.operator_errorstate = str(e)
			print(e)
			traceback.print_exc()
			self.cancel_omnistep(context)
			self.end_omnistep(context)
			return {"CANCELLED"}

	# ---------------------------------------------------------------- #
	def execute(self, context):
		self.report({"ERROR"}, "OmniStep does not support this operation")
		return {"FINISHED"}

	# ---------------------------------------------------------------- #
	def init_scene(self, context):
		# Init Vars
		self.settings = context.scene.omnistep_settings
		self.scenestate = SceneState()

		# Init Scene
		self.settings.operator_running = True
		self.settings.operator_error = False

		# Set View
		self.scenestate.camera_view = False # make sure, in case of crash residual
		if self.settings.set_view == 'CURRENT' and context.region_data.view_perspective == 'CAMERA':
			self.scenestate.camera_view = True
		if self.settings.set_view == 'CAMERA' and context.scene.camera is not None:
			self.scenestate.camera_view = True

		# Mute Camera Animation
		if self.scenestate.camera_view:
			self.camera_mute_states = {}  # Dictionary to store original mute states
			if context.space_data.camera.animation_data and context.space_data.camera.animation_data.action:
				for fcurve in context.space_data.camera.animation_data.action.fcurves:
					# Check if the fcurve corresponds to location or rotation
					if fcurve.data_path in ['location', 'rotation_euler', 'rotation_quaternion']:						
						fcurve.mute = True
						fcurve.lock = False
						if fcurve.sampled_points:
							start_frame, end_frame = fcurve.range()
							fcurve.convert_to_keyframes(int(start_frame), int(end_frame))

		# Autokey Disable
		self.settings.original_autokey = bpy.context.scene.tool_settings.use_keyframe_insert_auto		
		
		if self.settings.enable_animation and self.settings.play_animation:
			bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
			bpy.ops.screen.animation_cancel(restore_frame=False)  # stop playback if running
			context.scene.frame_current = context.scene.frame_start

		# Make sure data is up to date from here on out
		depsgraph = context.evaluated_depsgraph_get()
		depsgraph.update()

		# Collision Data
		self.scenestate.collision_samples = self.settings.collision_samples
		
		if self.settings.collide_collection_instances:
			self.scenestate.bvhtree = SceneBVH(context, util.create_bvhtree_from_visible_objects_instances(context.scene, self.settings.ignore_wireframes, self.settings.ignore_animated, self.settings.collide_evaluate, self.settings.collide_collections, self.settings.collide_set))
		else:
			self.scenestate.bvhtree = SceneBVH(context, util.create_bvhtree_from_visible_objects(context.scene, self.settings.ignore_wireframes, self.settings.ignore_animated, self.settings.collide_evaluate, self.settings.collide_collections, self.settings.collide_set))

		# Scale
		if self.settings.target_scale == 'CUSTOM':
			self.settings.current_scale = self.settings.custom_scale

		# Gravity
		if self.settings.target_gravity == 'CUSTOM':
			self.settings.current_gravity = self.settings.custom_gravity

		# Timing
		target = None
		if self.settings.target_framerate == 'CUSTOM':
			target = self.settings.custom_framerate
		else:
			target = int(self.settings.target_framerate)

		if self.scenestate.use_fixed_timestep and self.animation.enable_animation and self.animation.record_animation:
			pass
		else:
			target = 61 if target == 60 else target
			target = 121 if target == 120 else target

		self.scenestate.target_timestep = 1.0 / target
		self.scenestate.timer = context.window_manager.event_timer_add(self.scenestate.target_timestep, window=context.window)
		self.scenestate.physics_timestep = 1.0 / 120.0
		self.scenestate.scene_framerate = context.scene.render.fps / context.scene.render.fps_base
		self.scenestate.use_fixed_timestep = self.settings.fixed_timestep

		self.scenestate.max_timestep = self.scenestate.target_timestep * 5.0	# 5.0 is arbitrary for now

	# ---------------------------------------------------------------- #
	def init_view(self, context):
		# Disable Quadview if active
		if context.space_data.region_quadviews:
			bpy.ops.screen.region_quadview()

		# Prepare Viewport
		# save original state
		self.backup_view_enum = context.region_data.view_perspective
		self.backup_view = context.region_data.view_matrix.copy()
		if self.scenestate.camera_view:
			self.backup_camera_view = context.space_data.camera.matrix_world.copy()

		if self.scenestate.camera_view:
			context.region_data.view_perspective = 'CAMERA'
			context.region_data.view_camera_offset = (0.0, 0.0)
			bpy.ops.view3d.view_center_camera()
		else:
			context.region_data.view_perspective = 'PERSP'
			if self.settings.set_focal:
				self.settings.original_focal = context.space_data.lens
				context.space_data.lens = self.settings.view_focal

		context.space_data.lock_object = None
		context.space_data.lock_camera = False
		context.space_data.lock_cursor = False

		context.region_data.update()

	# ---------------------------------------------------------------- #
	def init_display(self, context):
		# Set Cursor
		self.cursor_hidden = context.preferences.addons[__package__].preferences.always_hide_cursor
		if self.cursor_hidden:
			context.window.cursor_set('NONE')
		else:
			context.window.cursor_set('DOT')

		# Set N-Panel
		if self.settings.n_panel_hide and context.area.spaces.active.show_region_ui:
			self.settings.n_panel_visible = True
			context.area.spaces.active.show_region_ui = not context.area.spaces.active.show_region_ui
		else:
			self.settings.n_panel_visible = False
		# Set T-Panel
		if self.settings.t_panel_hide and context.area.spaces.active.show_region_toolbar:
			self.settings.t_panel_visible = True
			context.area.spaces.active.show_region_toolbar = not context.area.spaces.active.show_region_toolbar
		else:
			self.settings.t_panel_visible = False
		# Set Header
		if self.settings.header_hide and context.area.spaces.active.show_region_header:
			self.settings.header_visible = True
			context.area.spaces.active.show_region_header = not context.area.spaces.active.show_region_header
		else:
			self.settings.header_visible = False

		# Set Gizmos
		if self.settings.gizmos_hide and context.area.spaces.active.show_gizmo:
			self.settings.gizmos_visible = True
			context.area.spaces.active.show_gizmo = False
		else:
			self.settings.gizmos_visible = False
		# Set Overlays
		if self.settings.overlays_hide and context.area.spaces.active.overlay.show_overlays:
			self.settings.overlays_visible = True
			context.area.spaces.active.overlay.show_overlays = False
		else:
			self.settings.overlays_visible = False

		# Full Redraw before start
		for area in bpy.context.screen.areas:
			area.tag_redraw()

	# ---------------------------------------------------------------- #
	def update_scene(self, context):
		self.scenestate.current_timestep = self.scenestate.timer.time_delta
		
		if self.scenestate.use_fixed_timestep and self.animation.enable_animation and self.animation.record_animation:
			self.scenestate.current_timestep = self.scenestate.target_timestep
		
		if self.scenestate.current_timestep <= 0:
			self.scenestate.current_timestep = self.scenestate.target_timestep
			self.report({'WARNING'}, "current_timestep was 0 or negative")
		
		if self.scenestate.framecount == 0:				# fix startup lag, especially with scripts
			self.scenestate.current_timestep = self.scenestate.target_timestep
		
		# Limit timestep
		if self.scenestate.current_timestep > self.scenestate.max_timestep:
			self.scenestate.current_timestep = self.scenestate.target_timestep
			#self.report({'WARNING'}, "max_timestep reached")

		# Loop Recording stutter fix
		if self.animation.enable_animation:
			if self.animation.record_animation and self.animation.loop_animation:
				if context.scene.frame_current == context.scene.frame_end or context.scene.frame_current == context.scene.frame_start:
					self.scenestate.current_timestep = self.scenestate.target_timestep

		self.scenestate.framecount += 1

		if not self.cursor_hidden:
			if self.scenestate.framecount % 60:	# revive every second, occasionally the OS hides it
				context.window.cursor_set('DOT')

	# ---------------------------------------------------------------- #
	def cancel_omnistep(self, context):
		if hasattr(self, 'userscript') and self.userscript is not None:
			self.userscript.cancel()
		# Restore original state
		# View
		context.region_data.view_perspective = self.backup_view_enum
		context.region_data.view_matrix = self.backup_view
		if self.scenestate.camera_view:		# move camera back to start (only works if not keyed!)
			context.space_data.camera.matrix_world = self.backup_camera_view
		else:
			if self.settings.set_focal:
				context.space_data.lens = self.settings.original_focal

		bpy.context.scene.tool_settings.use_keyframe_insert_auto = self.settings.original_autokey

		# Full Redraw at end
		for area in bpy.context.screen.areas:
			area.tag_redraw()

	# ---------------------------------------------------------------- #
	def end_omnistep(self, context):
		self.settings.operator_running = False
		if hasattr(self, 'userscript') and self.userscript is not None:	# Script Cleanup
			self.userscript.disable()
		
		self.animation.cleanup()
		self.console.disable()
		# self.graph.disable()
		self.overlay.disable()
		
		self.scenestate.bvhtree.dynamic_bvh_clear_all()	# remove all dynamic mesh data blocks
		context.window_manager.event_timer_remove(self.scenestate.timer)
		# Set Cursor
		context.window.cursor_modal_restore()
		# Restore N-Panel
		if self.settings.n_panel_hide and self.settings.n_panel_visible:
			context.area.spaces.active.show_region_ui = not context.area.spaces.active.show_region_ui
		# Restore T-Panel
		if self.settings.t_panel_hide and self.settings.t_panel_visible:
			context.area.spaces.active.show_region_toolbar = not context.area.spaces.active.show_region_toolbar
		# Restore Header
		if self.settings.header_hide and self.settings.header_visible:
			context.area.spaces.active.show_region_header = not context.area.spaces.active.show_region_header
		# Restore Gizmos
		if self.settings.gizmos_hide and self.settings.gizmos_visible:
			context.area.spaces.active.show_gizmo = True
		# Restore Overlays
		if self.settings.overlays_hide and self.settings.overlays_visible:
			context.area.spaces.active.overlay.show_overlays = True
		# Unmute Camera
		if self.scenestate.camera_view:
			if context.space_data.camera.animation_data and context.space_data.camera.animation_data.action:
				for fcurve in context.space_data.camera.animation_data.action.fcurves:
					if fcurve.data_path in ['location', 'rotation_euler', 'rotation_quaternion']:
						fcurve.mute = False
		
		# Redraw UI
		for area in context.screen.areas:
			if area.type == 'VIEW_3D':
				area.tag_redraw()



class VIEW3D_OT_OmniStep_UserScript(bpy.types.Operator):
	bl_idname = "view3d.omnistep_userscript"
	bl_label = "OmniStep UserScript"
	bl_description = ("OmniStep UserScript")
	bl_options = {"REGISTER", "INTERNAL"}
	
	command: bpy.props.StringProperty(default="") # Command Line Parameters

	def execute(self, context):
		try:
			if self.command == 'refresh':	# Script Inspector Refresh
				UserScriptInspector(context, 'refresh')
				return {"FINISHED"}
			if self.command == 'create':
				UserScriptInspector(context, 'create')
				return {"FINISHED"}
			if self.command == 'write':
				UserScriptInspector(context, 'write')
				return {"FINISHED"}

		except Exception as e:
			self.settings.operator_error = True
			self.settings.operator_errorstate = str(e)
			print(e)
			traceback.print_exc()
			return {"CANCELLED"}
		return {'FINISHED'}

# ========================================================= #


classes = (
	OmniStep_AddonPreferences,
	OMNISTEP_CollectionItem,
	OMNISTEP_OT_CollectionItemAction,
	OMNISTEP_DynamicItem,
	OmniStep_Settings,
	OMNISTEP_OT_Keymap,
	OMNISTEP_OT_ResetKey,
	OMNISTEP_PT_SettingsPanel,
	OMNISTEP_PT_SettingsPanel_Scene,
	OMNISTEP_PT_SettingsPanel_Player,
	OMNISTEP_PT_SettingsPanel_Advanced,
	OMNISTEP_PT_SettingsPanel_Animation,
	OMNISTEP_PT_SettingsPanel_Scripting,
	OMNISTEP_PT_SettingsPanel_Collision,
	OMNISTEP_PT_SettingsPanel_Display,
	OMNISTEP_PT_SettingsPanel_Overrides,
	OMNISTEP_MT_DisplayPresets,
	OMNISTEP_AddPreset,
	OMNISTEP_PT_Presets,
	WM_OT_ShowDialog,
	VIEW3D_OT_OmniStep,
	VIEW3D_OT_OmniStep_UserScript,
)


def register():
	for cls in classes:
		if cls == OMNISTEP_PT_SettingsPanel:
			if bpy.context.preferences.addons[__package__].preferences.panel_location == 'TOOL':
				OMNISTEP_PT_SettingsPanel.bl_category = "Tool"
			if bpy.context.preferences.addons[__package__].preferences.panel_location == 'OMNI':
				OMNISTEP_PT_SettingsPanel.bl_category = "OmniTools"
			if bpy.context.preferences.addons[__package__].preferences.panel_location == 'CUSTOM':
				OMNISTEP_PT_SettingsPanel.bl_category = bpy.context.preferences.addons[__package__].preferences.panel_custom

		bpy.utils.register_class(cls)
	bpy.types.Scene.omnistep_settings = bpy.props.PointerProperty(type=OmniStep_Settings)

def unregister():
	for cls in classes:
		bpy.utils.unregister_class(cls)
	del bpy.types.Scene.omnistep_settings