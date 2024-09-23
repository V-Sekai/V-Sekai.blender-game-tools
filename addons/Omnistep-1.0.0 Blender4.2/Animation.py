import bpy
import bmesh
from dataclasses import dataclass, field
import math
import bl_math
from .InputManager import InputState
from .OverlayConsole import OverlayConsole
from .OverlayMain import Overlay
from .TransformNode import TransformNode
from .Scene import SceneState
from .Player import PlayerState
from . import Utils as util
from mathutils import Matrix, Vector, Euler, Quaternion

# ******************************************************************** #
class OmniStep_Animation:
	# ---------------------------------------------------------------- #
	def __init__(self, context, overlay: Overlay, console: OverlayConsole, playerstate: PlayerState, scenestate: SceneState, inputstate: InputState):
		self.context = context
		self.console = console
		self.overlay = overlay
		self.scene = scenestate
		self.player = playerstate
		self.settings = context.scene.omnistep_settings
		self.input = inputstate

		self.enable_animation = self.settings.enable_animation
		if not self.enable_animation:
			return

		# Animation
		self.init()

	# ---------------------------------------------------------------- #
	def init(self):
		self.preroll = self.settings.preroll_animation
		self.preroll_count = 0
		self.loop_animation = self.settings.loop_animation
		self.record_animation = self.settings.record_animation
		self.play_animation = self.settings.play_animation

		self.scene_timestep = 1.0 / self.scene.scene_framerate
		self.scene_time_accumulator = 0.0

		self.record_counter = 0		# for cleanup
		self.scene.write_frame = False	# for the updateTimeline
		self.scene.scene_state = SceneState.IDLE

		if self.play_animation:
			self.context.scene.frame_set(self.context.scene.frame_start)

		if self.record_animation and self.scene.camera_view:
			self.scene.scene_frame = self.context.scene.frame_start
			self.scene.scene_frame_fraction = self.context.scene.frame_start
			# Delete active range first
			# Remove keyframes from the camera in a separate loop
			if self.context.space_data.camera.animation_data and self.context.space_data.camera.animation_data.action:
				for fcurve in self.context.space_data.camera.animation_data.action.fcurves:
					keyframes_to_remove = [kf for kf in fcurve.keyframe_points if self.context.scene.frame_start <= kf.co.x <= self.context.scene.frame_end]
					for kf in reversed(keyframes_to_remove):
						fcurve.keyframe_points.remove(kf)
			# Insert some keyframes at start to mute the tracks - otherwise they might not exist
			# insert at start, they get overwritten anyway next frame
			self.context.space_data.camera.keyframe_insert(data_path="location", frame=self.context.scene.frame_start)
			if self.context.space_data.camera.rotation_mode == 'QUATERNION':
				self.context.space_data.camera.keyframe_insert(data_path="rotation_quaternion", frame=self.context.scene.frame_start)
			else:
				self.context.space_data.camera.keyframe_insert(data_path="rotation_euler", frame=self.context.scene.frame_start)

			if self.context.space_data.camera.animation_data and self.context.space_data.camera.animation_data.action:
				for fcurve in self.context.space_data.camera.animation_data.action.fcurves:
					# Check if the fcurve corresponds to location or rotation
					if fcurve.data_path in ['location', 'rotation_euler', 'rotation_quaternion']:
						fcurve.mute = True	# Mute the fcurve

	# ---------------------------------------------------------------- #
	def update(self):
		if not self.enable_animation:
			return

		if not self.play_animation and not self.record_animation:
			return

		# Restart
		if self.input.restart:
			self.init()

		if self.scene.scene_state == SceneState.END:
			return

		# ========================= #
		# Update Time
		frame_progress = self.scene.current_timestep / self.scene_timestep	# Calculate how much of a frame has passed
		self.scene_time_accumulator += frame_progress
		self.scene.write_frame = False

		if self.scene.use_fixed_timestep:	# force write frame here
			self.scene_time_accumulator = 1.0

		if self.scene_time_accumulator >= 1.0:
			# Record and Play (+Loop)
			if self.play_animation:
				# Preroll phase
				if self.preroll_count < self.preroll:
					self.preroll_count += 1
					self.overlay.write(f"Preroll: {self.preroll - self.preroll_count}")
					self.scene.scene_state = SceneState.PREROLL
				# Main animation
				else:
					self.scene.scene_state = SceneState.RECORDING
					self.scene.write_frame = True		# signal to all modules and updateTimeline

					if self.context.scene.frame_current == self.context.scene.frame_start:
						if self.scene.camera_view:
							if self.record_animation:
								self.overlay.write("Recording Animation")
							else:
								self.overlay.write("Playing Animation [NOT RECORDING]")
						else:
							self.overlay.write("Playing Animation [NOT RECORDING]")

			else:
				self.scene.scene_state = SceneState.RECORDING
				self.scene.write_frame = True		# signal to all modules and updateTimeline

			self.scene_time_accumulator -= 1.0	# Decrement the accumulator for the next iteration

			# ========================= #
			# Recording
			if self.record_animation and self.scene.scene_state == SceneState.RECORDING:
				self.record()

	# ---------------------------------------------------------------- #
	def record(self):
		if not self.enable_animation:
			return
		if not self.scene.camera_view:
			return
		if self.play_animation:
			# Insert Keyframes
			self.context.space_data.camera.keyframe_insert(data_path="location")
			if self.context.space_data.camera.rotation_mode == 'QUATERNION':
				self.context.space_data.camera.keyframe_insert(data_path="rotation_quaternion")
			else:
				self.context.space_data.camera.keyframe_insert(data_path="rotation_euler")
		else:
			self.context.space_data.camera.keyframe_insert(data_path="location", frame=self.scene.scene_frame)
			if self.context.space_data.camera.rotation_mode == 'QUATERNION':
				self.context.space_data.camera.keyframe_insert(data_path="rotation_quaternion", frame=self.scene.scene_frame)
			else:
				self.context.space_data.camera.keyframe_insert(data_path="rotation_euler", frame=self.scene.scene_frame)
		self.record_counter += 1

	# ---------------------------------------------------------------- #
	def update_timeline(self):
		if not self.enable_animation:
			return

		if self.play_animation and self.scene.write_frame:
			# Handle looping or non-looping animation
			if self.loop_animation:
				if self.context.scene.frame_current < self.context.scene.frame_end:
					self.context.scene.frame_set(self.context.scene.frame_current + 1)
				else:
					self.context.scene.frame_set(self.context.scene.frame_start)
					self.scene.scene_loop_count += 1
					if self.record_animation and self.scene.scene_loop_count > 0:
						if self.scene:
							self.transfer_animation_to_empty()

			elif self.context.scene.frame_current < self.context.scene.frame_end:
				self.context.scene.frame_set(self.context.scene.frame_current + 1)
			else:
				self.scene.scene_state = SceneState.END
				self.overlay.write("Timeline End. Press '" + str(bpy.context.preferences.addons[__package__].preferences.key_restart) + "' to restart")

			# set internal frame counter
			self.scene.scene_frame = self.context.scene.frame_current
			# self.scene.write_frame = False	# keep it running to the next loop for the userscript

		if not self.play_animation and self.scene.write_frame:
			if self.record_animation:
				if self.record_counter == 1:
					self.overlay.write("Recording Buffered Animation (No Playback)")
			# Record, but no playback
			self.scene.scene_frame += 1
			# self.scene.write_frame = False		# keep it running to the next loop for the userscript

	# ---------------------------------------------------------------- #
	def transfer_animation_to_empty(self):
		camera = self.context.space_data.camera
		# Create a new empty and link it to the first collection of the camera
		empty = bpy.data.objects.new("OmniStep.Camera", None)
		camera.users_collection[0].objects.link(empty)
		# Set rotation mode of empty to match the camera's rotation mode
		empty.rotation_mode = camera.rotation_mode

		# Check if camera has animation data
		if camera.animation_data and camera.animation_data.action:
			action = camera.animation_data.action
			# Ensure target object has animation data
			empty.animation_data_create()
			empty.animation_data.action = bpy.data.actions.new(name="EmptyAction")
			# Transfer keyframes to the empty
			for fcurve in action.fcurves:
				if fcurve.data_path in {'location', 'rotation_quaternion', 'rotation_euler'}:
					new_fcurve = empty.animation_data.action.fcurves.new(data_path=fcurve.data_path, index=fcurve.array_index)
					first_kf = None		# for blender cycle fix
					last_kf = None		# for blender cycle fix
		
					for kf in fcurve.keyframe_points:
						if self.context.scene.frame_start <= kf.co.x <= self.context.scene.frame_end:
							# Insert the keyframe directly to the new fcurve
							new_kf = new_fcurve.keyframe_points.insert(frame=kf.co.x, value=kf.co.y, options={'FAST'})
							
							# Insert first key after the last, loop stutter fix
							if first_kf is None or kf.co.x < first_kf.co.x:
								first_kf = kf
							if last_kf is None or kf.co.x > last_kf.co.x:
								last_kf = kf
							if first_kf and last_kf and first_kf != last_kf:
								new_fcurve.keyframe_points.insert(frame=last_kf.co.x + 1, value=first_kf.co.y, options={'FAST'})


	# ---------------------------------------------------------------- #
	def cleanup(self):
		if not self.enable_animation:
			return

		if self.record_counter > 0:
			if self.context.space_data.camera.animation_data and self.context.space_data.camera.animation_data.action:
				for fcurve in self.context.space_data.camera.animation_data.action.fcurves:
					# Check if the fcurve corresponds to location or rotation
					if fcurve.data_path in ['location', 'rotation_euler', 'rotation_quaternion']:
						fcurve.mute = False