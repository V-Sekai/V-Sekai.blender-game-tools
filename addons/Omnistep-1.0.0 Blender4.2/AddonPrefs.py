import bpy
import sys
from . import Utils as util

# ********************************************************* #
class OmniStep_AddonPreferences(bpy.types.AddonPreferences):
	bl_idname = __package__

	save_counter: bpy.props.IntProperty(default=0)

	mouse_sensitivity: bpy.props.FloatProperty(name="Mouse Sensitivity", soft_min=0.0, soft_max=100.0, default=5)
	mouse_invert_y: bpy.props.BoolProperty(name="Invert Mouse Y", default=False)

	is_operator_running: bpy.props.BoolProperty(default=False)
	active_key: bpy.props.StringProperty(default='')

	key_forward: bpy.props.StringProperty(name="Forward", default='W')
	key_back: bpy.props.StringProperty(name="Backward", default='S')
	key_left: bpy.props.StringProperty(name="Left", default='A')
	key_right: bpy.props.StringProperty(name="Right", default='D')
	key_up: bpy.props.StringProperty(name="Left", default='Q')
	key_down: bpy.props.StringProperty(name="Right", default='E')

	key_jump: bpy.props.StringProperty(name="Jump", default='RIGHTMOUSE')

	key_toggle: bpy.props.StringProperty(name="Toggle Walk/Fly", default='TAB')
	key_speed: bpy.props.StringProperty(name="Change Speed", default='LEFT_SHIFT')

	key_speed_up: bpy.props.StringProperty(name="Increase Speed", default='WHEELUPMOUSE')
	key_speed_down: bpy.props.StringProperty(name="Decrease Speed", default='WHEELDOWNMOUSE')
	key_speed_reset: bpy.props.StringProperty(name="Reset Speed", default='MIDDLEMOUSE')

	key_respawn: bpy.props.StringProperty(name="Respawn", default='R')
	key_teleport: bpy.props.StringProperty(name="Teleport", default='SPACE')
	key_restart: bpy.props.StringProperty(name="Restart Recording", default='X')

	key_action1: bpy.props.StringProperty(name="Action 1", default='LEFTMOUSE')
	key_action2: bpy.props.StringProperty(name="Action 2", default='TWO')
	key_action3: bpy.props.StringProperty(name="Action 3", default='THREE')
	key_action4: bpy.props.StringProperty(name="Action 4", default='FOUR')

	# Gamepad
	pad_buttons = [
		('0', "None", ""),
		('1', "D-Pad Up", ""),
		('2', "D-Pad Down", ""),
		('4', "D-Pad Left", ""),
		('8', "D-Pad Right", ""),
		('16', "Start", ""),
		('32', "Back", ""),
		('64', "Left Thumbstick", ""),
		('128', "Right Thumbstick", ""),
		('256', "Left Bumper", ""),
		('512', "Right Bumper", ""),
		('4096', "Button A", ""),
		('8192', "Button B", ""),
		('16384', "Button X", ""),
		('32768', "Button Y", "")
	]


	pad_enabled: bpy.props.BoolProperty(name="Enable Gamepad", description="", default=False)

	pad_move_dead_zone: bpy.props.FloatProperty(name="Move Dead Zone", description="", min=0.0, max=20.0, subtype='PERCENTAGE', default=10.0)

	pad_look_sens: bpy.props.FloatProperty(name="Look Sensitivity", min=0.0, soft_max=10.0, default=2.5)
	pad_look_dead_zone: bpy.props.FloatProperty(name="Look Dead Zone", description="", min=0.0, max=20.0, subtype='PERCENTAGE', default=10.0)
	pad_look_exponent: bpy.props.FloatProperty(name="Look Curve Exponent", min=0.01, max=10.0, default=2.0)
	pad_look_invert_y: bpy.props.BoolProperty(name="Invert Look Y", description="Inverts the Y look axis", default=False)

	pad_jump: bpy.props.EnumProperty(name="Jump", description=(""), items=pad_buttons, default='4096')
	pad_toggle: bpy.props.EnumProperty(name="Toggle Walk / Fly", description=(""), items=pad_buttons, default='32768')
	pad_teleport: bpy.props.EnumProperty(name="Teleport", description=(""), items=pad_buttons, default='512')
	pad_respawn: bpy.props.EnumProperty(name="Respawn", description=(""), items=pad_buttons, default='256')
	pad_action1: bpy.props.EnumProperty(name="Action 1", description=(""), items=pad_buttons, default='8192')
	pad_action2: bpy.props.EnumProperty(name="Action 2", description=(""), items=pad_buttons, default='16384')
	pad_action3: bpy.props.EnumProperty(name="Action 3", description=(""), items=pad_buttons, default='64')
	pad_action4: bpy.props.EnumProperty(name="Action 4", description=(""), items=pad_buttons, default='128')

	# Display
	reticle_size: bpy.props.FloatProperty(name="Reticle Size",
						description="Size relative to the viewport",
						min=0.1, max=25.0, subtype='PERCENTAGE', default=4)
	reticle_color: bpy.props.FloatVectorProperty(name="Reticle Color",
						description="Color of the reticle",
						subtype='COLOR',
						default=(1.0, 1.0, 1.0, 0.250),
						min=0.0, max=1.0, size=4)
	reticle_thickness: bpy.props.IntProperty(name="Reticle Thickness",
						description="Thickness of the reticle in pixels",
						min=1, max=32, default=2)

	message_color: bpy.props.FloatVectorProperty(name="Message Color",
						description="Message Color",
						subtype='COLOR',
						default=(1.00, 1.00, 1.00, 0.75),
						min=0.0, max=1.0, size=4)
	message_size: bpy.props.IntProperty(name="Message Size",
						description="Message Size",
						min=6, max=32, default=14)
	message_duration: bpy.props.FloatProperty(name="Message Duration (s)",
						description="Message display duration in seconds",
						min=0.5, max=10.0, default=2.0)

	radial_view_size: bpy.props.FloatProperty(name="Radial View Size",
						description="Size relative to the viewport",
						min=25.0, max=100.0, subtype='PERCENTAGE', default=80)
	radial_view_cursor_size: bpy.props.FloatProperty(name="Radial View Cursor Size",
						description="Size relative to the viewport",
						min=0.1, max=25.0, subtype='PERCENTAGE', default=2)
	radial_view_color: bpy.props.FloatVectorProperty(name="Radial View Color",
						description="Radial View Color",
						subtype='COLOR',
						default=(1.00, 1.00, 1.00, 0.75),
						min=0.0, max=1.0, size=4)
	radial_view_thickness: bpy.props.FloatProperty(name="Radial View Thickness",
						description="Thickness of the Radial View in pixels",
						min=0.1, max=8.0, default=2.0)
	always_hide_cursor: bpy.props.BoolProperty(name="Always Hide Cursor [Experimental]",
						description="Always hides the Cursor (little dot). Hiding the cursor can lead to stutter on some systems, so its off by default",
						default=False,)

	# UI
	omnistep_panel: bpy.props.BoolProperty(name="OmniStep Panel in 'Tool' Tab [Restart]",
						description="Embed OmniStep inside the existing 'Tool' tab of the N-Panel. If unchecked, OmniStep gets its own top-level tab. Restart Blender to see changes",
						default=False)
	panel_location: bpy.props.EnumProperty(name="OmniStep Panel Location",
		description=("Choose the N-Panel tab for OmniStep: 'OmniTools' for its dedicated section,"
		" 'Tool' to integrate with Blender's default tools, or 'Custom' to specify your own tab "
		"name. Restart Blender to apply changes."),
		items=[
			('OMNI', "OmniTools", ""),
			('TOOL', "Tool", ""),
			('CUSTOM', "Custom", ""),
		], default='OMNI')
	panel_custom: bpy.props.StringProperty(name="Custom Panel", default="MyPanel")

	def draw(self, context):
		set_event_text = "Press a Key / Button"
		layout = self.layout
		layout.use_property_split = True
		sepfactor = 1.0

		# Mouse Settings Box
		box = layout.box()
		row = box.row()
		row.alignment = 'CENTER'
		row.label(text="Mouse Settings")

		self.int_entry(box, self.mouse_sensitivity, 'mouse_sensitivity', 5)
		self.bool_entry(box, self.mouse_invert_y, 'mouse_invert_y', False)

		# Keymap Box
		box = layout.box()
		row = box.row()
		row.alignment = 'CENTER'
		row.label(text="Keymap Settings")

		self.key_entry(box, "Forward", 'key_forward', self.key_forward, 'W', set_event_text)
		self.key_entry(box, "Backward", 'key_back', self.key_back, 'S', set_event_text)
		self.key_entry(box, "Left", 'key_left', self.key_left, 'A', set_event_text)
		self.key_entry(box, "Right", 'key_right', self.key_right, 'D', set_event_text)
		self.key_entry(box, "Up", 'key_up', self.key_up, 'Q', set_event_text)
		self.key_entry(box, "Down", 'key_down', self.key_down, 'E', set_event_text)

		box.separator(factor=sepfactor)

		self.key_entry(box, "Jump", 'key_jump', self.key_jump, 'RIGHTMOUSE', set_event_text)
		self.key_entry(box, "Toggle Walk/Fly", 'key_toggle', self.key_toggle, 'TAB', set_event_text)
		self.key_entry(box, "Change Speed (Walk/Run)", 'key_speed', self.key_speed, 'LEFT_SHIFT', set_event_text)

		box.separator(factor=sepfactor)

		self.key_entry(box, "Increase Speed", 'key_speed_up', self.key_speed_up, 'WHEELUPMOUSE', set_event_text)
		self.key_entry(box, "Decrease Speed", 'key_speed_down', self.key_speed_down, 'WHEELDOWNMOUSE', set_event_text)
		self.key_entry(box, "Reset Speed", 'key_speed_reset', self.key_speed_reset, 'MIDDLEMOUSE', set_event_text)

		box.separator(factor=sepfactor)

		self.key_entry(box, "Respawn", 'key_respawn', self.key_respawn, 'R', set_event_text)
		self.key_entry(box, "Teleport", 'key_teleport', self.key_teleport, 'SPACE', set_event_text)
		self.key_entry(box, "Restart Recording", 'key_restart', self.key_restart, 'X', set_event_text)

		box.separator(factor=sepfactor)

		self.key_entry(box, "Action 1", 'key_action1', self.key_action1, 'LEFTMOUSE', set_event_text)
		self.key_entry(box, "Action 2", 'key_action2', self.key_action2, 'TWO', set_event_text)
		self.key_entry(box, "Action 3", 'key_action3', self.key_action3, 'THREE', set_event_text)
		self.key_entry(box, "Action 4", 'key_action4', self.key_action4, 'FOUR', set_event_text)

		# Gamepad Box
		#if self.pad_enabled == True:
		if sys.platform == 'win32':
			box = layout.box()
			row = box.row()
			row.alignment = 'CENTER'
			row.label(text="Gamepad Settings")

			row = box.row()
			row.prop(self, "pad_enabled")

			sub_box = box.box()
			sub_box.enabled = self.pad_enabled  # Use this to control the enabled state of all elements in this box
			row = sub_box.row()

			row.prop(self, "pad_move_dead_zone")
			row = sub_box.row()
			row.prop(self, "pad_look_sens")
			row = sub_box.row()
			row.prop(self, "pad_look_dead_zone")
			row = sub_box.row()
			row.prop(self, "pad_look_exponent")
			row = sub_box.row()
			row.prop(self, "pad_look_invert_y")

			sub_box.separator(factor=sepfactor)

			row = sub_box.row()
			row.prop(self, "pad_jump")
			row = sub_box.row()
			row.prop(self, "pad_toggle")
			row = sub_box.row()
			row.prop(self, "pad_teleport")
			row = sub_box.row()
			row.prop(self, "pad_respawn")
			row = sub_box.row()
			row.prop(self, "pad_action1")
			row = sub_box.row()
			row.prop(self, "pad_action2")
			row = sub_box.row()
			row.prop(self, "pad_action3")
			row = sub_box.row()
			row.prop(self, "pad_action4")


		# Display Box
		box = layout.box()
		row = box.row()
		row.alignment = 'CENTER'
		row.label(text="Display Settings")

		self.float_entry(box, self.reticle_size, 'reticle_size', 4)
		self.color_entry(box, self.reticle_color, 'reticle_color', (1.00, 1.00, 1.00, 0.25), "(1.00, 1.00, 1.00, 0.25)")
		self.int_entry(box, self.reticle_thickness, 'reticle_thickness', 2)

		box.separator(factor=sepfactor)

		self.float_entry(box, self.radial_view_size, 'radial_view_size', 80)
		self.float_entry(box, self.radial_view_cursor_size, 'radial_view_cursor_size', 2.0)
		self.color_entry(box, self.radial_view_color, 'radial_view_color', (1.00, 1.00, 1.00, 0.75), "(1.00, 1.00, 1.00, 0.75)")
		self.float_entry(box, self.radial_view_thickness, 'radial_view_thickness', 2.0)

		box.separator(factor=sepfactor)

		self.color_entry(box, self.message_color, 'message_color', (1.00, 1.00, 1.00, 0.75), "(1.00, 1.00, 1.00, 0.75)")
		self.int_entry(box, self.message_size, 'message_size', 14)
		self.float_entry(box, self.message_duration, 'message_duration', 2.0)

		box.separator(factor=sepfactor)

		self.bool_entry(box, self.always_hide_cursor, 'always_hide_cursor', False)

		# Display Box
		box = layout.box()
		row = box.row()
		row.alignment = 'CENTER'
		row.label(text="System Settings")

		row = box.row()
		row.prop(self, "panel_location")
		#row.alignment = 'RIGHT'
		row.label(text='  Restart required')

		row = box.row()
		row.enabled = True if self.panel_location == 'CUSTOM' else False
		row.prop(self, 'panel_custom')



	def bool_entry(self, box, item, item_string, item_default):
		row = box.row()
		sublayout = row.split()
		sublayout.prop(self, item_string)
		reset_row = row.row(align=True)
		reset_row.enabled = (item != item_default)
		op = reset_row.operator("wm.context_set_boolean", text="", icon='BACK')
		op.data_path = f"preferences.addons['{__package__}'].preferences." + item_string
		op.value = item_default  # Default value

	# ---------------------------------------------------------------- #
	def float_entry(self, box, item, item_string, item_default):
		row = box.row()
		sublayout = row.split()
		sublayout.prop(self, item_string)
		reset_row = row.row(align=True)
		reset_row.enabled = not self.is_close(item, item_default)
		op = reset_row.operator("wm.context_set_float", text="", icon='BACK')
		op.data_path = f"preferences.addons['{__package__}'].preferences." + item_string
		op.value = item_default  # Default value

	# ---------------------------------------------------------------- #
	def color_entry(self, box, item, item_string, item_default, item_default_string):
		row = box.row()
		sublayout = row.split()
		sublayout.prop(self, item_string)
		reset_row = row.row(align=True)
		reset_row.enabled = not self.is_close_tuple(item, item_default)
		op = reset_row.operator("wm.context_set_value", text="", icon='BACK')
		op.data_path = f"preferences.addons['{__package__}'].preferences." + item_string
		op.value = item_default_string

	# ---------------------------------------------------------------- #
	def int_entry(self, box, item, item_string, item_default):
		row = box.row()
		sublayout = row.split()
		sublayout.prop(self, item_string)
		reset_row = row.row(align=True)
		reset_row.enabled = item != item_default
		op = reset_row.operator("wm.context_set_int", text="", icon='BACK')
		op.data_path = f"preferences.addons['{__package__}'].preferences." + item_string
		op.value = item_default  # Default value

	# ---------------------------------------------------------------- #
	def key_entry(self, box, text, key_string, key, key_default, event_text):
		# Teleport
		row = box.row()
		split = row.split(factor=0.5, align=True)
		split.alignment = 'RIGHT'
		split.label(text=text)
		sub_row = split.row(align=True)
		if self.is_operator_running and self.active_key == key_string:
			sub_row.operator("wm.omnistep_keymapper", text=event_text, depress=True)
		else:
			sub_row.operator("wm.omnistep_keymapper", text=key).key_name = key_string
		reset_row = sub_row.row(align=True)
		reset_row.enabled = (key != key_default)
		#op = reset_row.operator("wm.context_set_string", text="", icon='BACK')
		op = reset_row.operator("wm.omnistep_resetkey", text="", icon='BACK')
		op.data_path = f"preferences.addons['{__package__}'].preferences." + key_string
		op.value = key_default

	# ---------------------------------------------------------------- #
	def is_close(self, a, b, threshold=0.0001):
		return abs(a - b) < threshold

	# ---------------------------------------------------------------- #
	def is_close_tuple(self, color_a, color_b, threshold=0.0001):
		return all(abs(a - b) < threshold for a, b in zip(color_a, color_b))


# ********************************************************* #
class OMNISTEP_OT_Keymap(bpy.types.Operator):
	bl_idname = "wm.omnistep_keymapper"
	bl_label = "OmniStep Keymap Operator"
	bl_description = "Assign Custom Key / Button"
	bl_options = {'INTERNAL'}

	key_name: bpy.props.StringProperty()

	def modal(self, context, event):
		if event.type is None:
			context.preferences.addons[__package__].preferences.is_operator_running = False
			context.area.tag_redraw()
			return {'FINISHED'} # CANCELLED leaves it in a buggy state

		if event.type in { 'ESC' }: # 'RIGHTMOUSE' # Cancel
			context.preferences.addons[__package__].preferences.is_operator_running = False
			context.area.tag_redraw()
			return {'FINISHED'} # CANCELLED leaves it in a buggy state

		if event.type in { 'RET' } and event.value =='PRESS':
			context.area.tag_redraw()
			return {'RUNNING_MODAL'}

		if event.type in { 'RET' } and event.value =='RELEASE':
			context.preferences.addons[__package__].preferences.is_operator_running = False
			context.area.tag_redraw()
			self.report({'WARNING'}, "Return Key is reserved.")
			return {'FINISHED'} # CANCELLED leaves it in a buggy state

		if event.type not in  { 'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE',
		 'TRACKPADPAN', 'TRACKPADZOOM', 'MOUSEROTATE', 'MOUSESMARTZOOM',
		 'WINDOW_DEACTIVATE', 'TIMER', 'TIMER0', 'TIMER1', 'TIMER2',
		 'TIMER_JOBS', 'TIMER_AUTOSAVE', 'TIMER_REPORT', 'TIMERREGION',
		 'TEXTINPUT', 'NDOF_MOTION', 'RET'}:
			if event.type in bpy.types.Event.bl_rna.properties['type'].enum_items.keys():
				setattr(context.preferences.addons[__package__].preferences, self.key_name, event.type)
				bpy.context.preferences.use_preferences_save = True
				context.preferences.addons[__package__].preferences.is_operator_running = False
				context.area.tag_redraw()
				return {'FINISHED'}
			else:
				print("Invalid key: " + str(event.type))
				context.preferences.addons[__package__].preferences.is_operator_running = False
				context.area.tag_redraw()
				self.report({'WARNING'}, "Input not supported")
				return {'FINISHED'} # CANCELLED leaves it in a buggy state

		return {'PASS_THROUGH'}

	def invoke(self, context, event):
		context.preferences.addons[__package__].preferences.is_operator_running = True
		context.preferences.addons[__package__].preferences.active_key = self.key_name
		context.window_manager.modal_handler_add(self)
		return {'RUNNING_MODAL'}

# ********************************************************* #
class OMNISTEP_OT_ResetKey(bpy.types.Operator):
	"""Set a string property and mark preferences as needing to save."""
	bl_idname = "wm.omnistep_resetkey"
	bl_label = "Set String and Save"
	bl_options = {'INTERNAL' }

	data_path: bpy.props.StringProperty()
	value: bpy.props.StringProperty()

	def execute(self, context):
		# Evaluate the data_path to find the property and set its value
		exec(f"context.{self.data_path} = '{self.value}'")
		# Mark preferences as needing to be saved
		context.preferences.use_preferences_save = True
		return {'FINISHED'}

