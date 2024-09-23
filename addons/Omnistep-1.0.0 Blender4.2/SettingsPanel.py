import bpy
from . import Utils as util
from bpy.types import Operator, Menu
from bl_operators.presets import AddPresetBase
from bl_ui.utils import PresetPanel

# ********************************************************* #
class OMNISTEP_PT_SettingsPanel(bpy.types.Panel):
	bl_label = "OmniStep"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	#bl_category = "OmniTools"

	def draw(self, context):
		layout = self.layout
		row = layout.row()
		row.scale_y = 1.75

		operator = row.operator("view3d.omnistep", text='Start OmniStep', icon='PLAY')
		#operator.command = 'run'
		settings = context.scene.omnistep_settings
		layout.use_property_split = True
		layout.use_property_decorate = False

		if settings.operator_error:
			layout = layout.column()
			layout.label(text="ERROR: ", icon='ERROR')
			layout.label(text=settings.operator_errorstate, icon='ERROR')

# ********************************************************* #
class OMNISTEP_PT_SettingsPanel_Scene(bpy.types.Panel):
	bl_label = "World"
	bl_parent_id = "OMNISTEP_PT_SettingsPanel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_options = {'DEFAULT_CLOSED'}

	
	def draw_header(self, context):		
		layout = self.layout

	def draw(self, context):
		settings = context.scene.omnistep_settings
		separation_factor = 1.0

		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		layout = layout.column()

		layout.prop(settings, "set_view")

		sub_layout = layout.column()
		sub_layout.enabled = settings.set_view != 'CAMERA' and context.space_data.region_3d.view_perspective != 'CAMERA'
		sub_layout.prop(settings, "set_focal")
		sub_layout_b = sub_layout.column()
		sub_layout_b.enabled = settings.set_focal
		sub_layout_b.prop(settings, "view_focal")

		layout.separator(factor=separation_factor)

		layout.prop(settings, "target_spawn")
		if settings.target_spawn == 'COLLECTION':
			row = layout.row()
			row.prop(settings, "spawn_collection")
			operator = row.operator("wm.omnistep_show_dialog", text="", icon='INFO')
			operator.messages.add().name = "Empties are used as Spawn Points."						
			operator.messages.add().name = "The Empty Z-Axis is 'Up' and Y-Axis is 'Forward'"			
			operator.messages.add().name = "'Respawn' will cycle through the Empties."
			operator.messages.add().name = " "
			operator.messages.add().name = "If no Empties are found or the Collection is removed,"
			operator.messages.add().name = "it will use the current view."
			layout.separator(factor=separation_factor)

		layout.prop(settings, "target_framerate")
		if settings.target_framerate == 'CUSTOM':
			sub_layout = layout.column()
			sub_layout.enabled = settings.target_framerate == 'CUSTOM'
			sub_layout.prop(settings, "custom_framerate")
			layout.separator(factor=separation_factor)

		row = layout.row()
		row.prop(settings, "target_scale")
		operator = row.operator("wm.omnistep_show_dialog", text="", icon='INFO')
		operator.messages.add().name = "Units in OmniStep default to meters."
		operator.messages.add().name = "If you set a custom scale, all related properties"
		operator.messages.add().name = "(such as 'Gravity', 'Player Height', etc.) will be"
		operator.messages.add().name = "internally adjusted to match that scale."
		operator.messages.add().name = " "
		operator.messages.add().name = "This means that even if you're using a custom scale,"
		operator.messages.add().name = "you should always treat these values as if they were"
		operator.messages.add().name = "in meters."
		operator.messages.add().name = " "
		operator.messages.add().name = "Length = Meters"
		operator.messages.add().name = "Velocity = m/s"
		operator.messages.add().name = "Acceleration = m/s²"

		if settings.target_scale == 'CUSTOM':
			sub_layout = layout.column()
			sub_layout.enabled = settings.target_scale == 'CUSTOM'
			sub_layout.prop(settings, "custom_scale")
			layout.separator(factor=separation_factor)

		layout.prop(settings, "target_gravity")
		if settings.target_gravity == 'CUSTOM':
			sub_layout = layout.column()
			sub_layout.enabled = settings.target_gravity == 'CUSTOM'
			sub_layout.prop(settings, "custom_gravity")

# ********************************************************* #
class OMNISTEP_PT_SettingsPanel_Player(bpy.types.Panel):
	bl_label = "Player"
	bl_parent_id = "OMNISTEP_PT_SettingsPanel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_options = {'DEFAULT_CLOSED'}

	
	def draw_header_preset(self, context):
		layout = self.layout
		layout.emboss = 'NONE'

		layout.popover(
			panel="OMNISTEP_PT_hidden_presets",
			icon='PRESET',
			text="",)

	def draw(self, context):
		settings = context.scene.omnistep_settings
		layout = self.layout

		layout.use_property_split = False
		layout.use_property_decorate = False  # No animation.
		sepfactor = 0.5

		row = layout.row()
		row.scale_y = 1.25
		row.prop(settings, "play_mode", expand=True)

		layout.separator(factor=sepfactor / 1.5)

		layout = layout.column()
		layout.use_property_split = True
		if settings.play_mode == 'WALK':
			col = layout.column(align=True)
			col.prop(settings, "walk_mouse_damping", slider=True)

			layout.separator(factor=sepfactor)

			col = layout.column(align=True)
			col.prop(settings, "run_speed")
			col.prop(settings, "walk_speed")
			col.prop(settings, "jump_speed")

			layout.separator(factor=sepfactor)
			
			col = layout.column(align=True)
			col.prop(settings, "ground_acceleration")
			col.prop(settings, "ground_friction")			
			
			layout.separator(factor=sepfactor)

			col = layout.column(align=True)
			col.prop(settings, "always_run")		
			col.prop(settings, "wall_jump")
			col.prop(settings, "air_jump")
			

		if settings.play_mode == 'FLY':
			col = layout.column(align=True)
			col.prop(settings, "fly_mouse_damping", slider=True)
			col.prop(settings, "radial_view_control")
			row = col.row()
			row.enabled = settings.radial_view_control
			row.prop(settings, "trackball_rotation")

			layout.separator(factor=sepfactor)

			col = layout.column(align=True)
			col.prop(settings, "fly_speed")
			col.prop(settings, "fly_acceleration")
			col.prop(settings, "fly_air_friction")

			layout.separator(factor=sepfactor)
			
			row = layout.row()
			row.enabled = settings.fly_collisions
			row.prop(settings, "fly_radius")
			layout.prop(settings, "fly_collisions")

			layout.separator(factor=sepfactor)

			layout.prop(settings, "fly_banking", slider=True)

# ********************************************************* #
class OMNISTEP_PT_SettingsPanel_Advanced(bpy.types.Panel):
	bl_label = "Advanced Player Settings"
	#bl_parent_id = "OMNISTEP_PT_SettingsPanel"
	bl_parent_id = "OMNISTEP_PT_SettingsPanel_Player"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_options = {'DEFAULT_CLOSED'}

	
	def draw_header(self, context):
		layout = self.layout

	def draw(self, context):
		settings = context.scene.omnistep_settings

		layout = self.layout
		#layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		layout = layout.column()

		layout.label(text="General")
		layout.prop(settings, "banking_spring")
		col = layout.column(align=True)
		col.prop(settings, "teleport_speed")
		col.prop(settings, "teleport_time")
		layout.prop(settings, "adjust_focal_sens")

		layout.separator(factor=0.5)

		layout.label(text="Walk")
		col = layout.column(align=True)
		col.prop(settings, "player_height")
		col.prop(settings, "player_head_offset")
		col.prop(settings, "walk_banking", slider=True)
		
		layout.separator(factor=0.5)

		col = layout.column(align=True)
		col.prop(settings, "ground_decceleration")
		col.prop(settings, "air_acceleration")
		col.prop(settings, "air_decceleration")

		layout.separator(factor=0.5)

		col = layout.column(align=True)
		col.prop(settings, "cam_inertia")
		col = layout.column(align=True)
		col.enabled = settings.cam_inertia
		col.prop(settings, "cam_inertia_spring_vertical")
		col.prop(settings, "cam_inertia_spring_horizontal")

		layout.separator(factor=0.5)

		layout.label(text="Fly")
		layout.prop(settings, "radial_view_maxturn")

		col = layout.column(align=True)
		col.prop(settings, "trackball_balance", slider=True)
		col.prop(settings, "trackball_autolevel", slider=True)

# ********************************************************* #
class OMNISTEP_PT_SettingsPanel_Animation(bpy.types.Panel):
	bl_label = "Animation"
	bl_parent_id = "OMNISTEP_PT_SettingsPanel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_options = {'DEFAULT_CLOSED'}

	
	def draw_header(self, context):
		layout = self.layout
		settings = context.scene.omnistep_settings
		layout.prop(settings, "enable_animation", text="")

	def draw(self, context):
		settings = context.scene.omnistep_settings
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.
		layout.enabled = settings.enable_animation
		sepfactor = 1.0


		layout = layout.column()
		row = layout.row()
		row.enabled = settings.set_view == 'CAMERA' or context.space_data.region_3d.view_perspective == 'CAMERA'
		row.prop(settings, "record_animation")
		
		row = layout.row()
		row.enabled = settings.record_animation
		row.prop(settings, "fixed_timestep")

		layout.separator(factor=sepfactor)

		layout.prop(settings, "play_animation")
		row = layout.row()
		row.enabled = settings.play_animation
		row.prop(settings, "loop_animation")
		if settings.loop_animation and settings.record_animation and settings.play_animation:
			operator = row.operator("wm.omnistep_show_dialog", text="", icon='INFO')
			operator.messages.add().name = "Loop Recording: In each loop iteration, the"
			operator.messages.add().name = "camera's latest movements are recorded. The"
			operator.messages.add().name = "previous recording is then transferred to"
			operator.messages.add().name = "a new empty within the same collection."

		row = layout.row()
		row.enabled = settings.play_animation
		row.prop(settings, "preroll_animation")

		layout.separator(factor=sepfactor)

		row = layout.row()
		row.enabled = settings.play_animation		
		row.prop(settings, "child_of")
		row = layout.row()
		row.enabled = settings.child_of is not None
		row.prop(settings, "parent_rotation")

		layout.separator(factor=sepfactor)
		
				
		

# ********************************************************* #
class OMNISTEP_PT_SettingsPanel_Scripting(bpy.types.Panel):
	bl_label = "Scripting"
	bl_parent_id = "OMNISTEP_PT_SettingsPanel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_options = {'DEFAULT_CLOSED'}

	
	def draw_header(self, context):
		layout = self.layout
		settings = context.scene.omnistep_settings
		layout.prop(settings, "enable_scripting", text="")

	def draw(self, context):
		settings = context.scene.omnistep_settings
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.
		layout.enabled = settings.enable_scripting
		
		layout = layout.column()
		layout.prop(settings, "script_source")

		if settings.script_source is not None:
			layout = layout.column()
			operator = layout.operator("view3d.omnistep_userscript", text='Read Parameters', icon='IMPORT')
			#operator = layout.operator("view3d.omnistep", text='Read Parameters', icon='IMPORT')
			operator.command = 'refresh'

			box = layout.box()
			for item in settings.script_items:
				name = item.name
				if item.changed:
					name += '*'
				box = box.column()
				if item.data_type == 'FLOAT':
					box.prop(item, "float_value", text=name)
				elif item.data_type == 'INT':
					box.prop(item, "int_value", text=name)
				elif item.data_type == 'STRING':
					box.prop(item, "string_value", text=name)
				elif item.data_type == 'VECTOR':
					box.prop(item, "vector_value", text=name)
				elif item.data_type == 'COLOR':
					box.prop(item, "color_value", text=name)
				elif item.data_type == 'BOOLEAN':
					box.prop(item, "boolean_value", text=name)
				elif item.data_type == 'OBJECT':
					box.prop(item, "object_reference", text=name)
				elif item.data_type == 'COLLECTION':
					box.prop(item, "collection_reference", text=name)
				elif item.data_type == 'ACTION':
					box.prop(item, "action_reference", text=name)
			
			layout = layout.column()
			operator = layout.operator("view3d.omnistep_userscript", text='Write Parameters', icon='EXPORT')
			#operator = layout.operator("view3d.omnistep", text='Write Parameters', icon='EXPORT')
			operator.command = 'write'
		else:
			layout = layout.column()
			operator = layout.operator("view3d.omnistep_userscript", text='Create Template', icon='ADD')
			#operator = layout.operator("view3d.omnistep", text='Create Template', icon='ADD')
			operator.command = 'create'
			
# ********************************************************* #
class OMNISTEP_PT_SettingsPanel_Collision(bpy.types.Panel):
	bl_label = "Collisions"
	bl_parent_id = "OMNISTEP_PT_SettingsPanel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_options = {'DEFAULT_CLOSED'}

	
	def draw_header(self, context):
		layout = self.layout

	def draw(self, context):
		settings = context.scene.omnistep_settings

		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		layout = layout.column()
		layout.prop(settings, "collide_set")
		sub_layout = layout.column()
		if settings.collide_set != 'ALL':
			row = sub_layout.row()
			add_op = row.operator("omnistep.collection_item_action", text="Add Collection Slot", icon='ADD')
			add_op.action = 'ADD'

			for index, item in enumerate(settings.collide_collections):
				row = sub_layout.row()
				row.prop(item, "collection", text="")
				remove_op = row.operator("omnistep.collection_item_action", text="", icon='REMOVE')
				remove_op.action = 'REMOVE'
				remove_op.index = index

		layout.separator(factor=1.0)

		layout.prop(settings, "ignore_wireframes")
		row = layout.row()
		row.prop(settings, "ignore_animated")
		if settings.ignore_animated:
			operator = row.operator("wm.omnistep_show_dialog", text="", icon='INFO')
			operator.messages.add().name = "OmniSteps collision system does not support animations."
			operator.messages.add().name = "In order to avoid 'ghost' collisions, you can exclude "
			operator.messages.add().name = "all animated objects using this toggle."
			operator.messages.add().name = "This includes the object itself, any of its parents,"
			operator.messages.add().name = "any active physics and any enabled constraints."
			operator.messages.add().name = "NOTE:"
			operator.messages.add().name = "White the Scripting Module you have access to a"
			operator.messages.add().name = "'Dynamic BVH'. This allows for the programmatic"
			operator.messages.add().name = "updating of collisions for objects in real-time."

		layout.separator(factor=1.0)

		layout.prop(settings, "collide_evaluate")
		row = layout.row()
		row.prop(settings, "collide_collection_instances")
		if settings.collide_collection_instances:
			operator = row.operator("wm.omnistep_show_dialog", text="", icon='ERROR')
			operator.messages.add().name = "Including Collection Instances in the Collision System"
			operator.messages.add().name = "can be resource intensive, as each instance will be part"
			operator.messages.add().name = "of the collsion data!"
			operator.messages.add().name = "This also includes linked Libraries. "
		layout.prop(settings, "collision_samples")

# ********************************************************* #
class OMNISTEP_PT_SettingsPanel_Display(bpy.types.Panel):
	bl_label = "Display"
	bl_parent_id = "OMNISTEP_PT_SettingsPanel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_options = {'DEFAULT_CLOSED'}

	
	def draw_header(self, context):
		layout = self.layout

	def draw(self, context):
		settings = context.scene.omnistep_settings

		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		col = layout.column(align=True)
		col.prop(settings, "n_panel_hide")
		col.prop(settings, "t_panel_hide")
		col.prop(settings, "header_hide")

		#layout.separator(factor=1.0)
		
		col = layout.column(align=True)
		col.prop(settings, "gizmos_hide")
		col.prop(settings, "overlays_hide")

		#layout.separator(factor=1.0)

		col = layout.column(align=True)
		col.prop(settings, "show_reticle")
		col.prop(settings, "show_message")

# ********************************************************* #
class OMNISTEP_PT_SettingsPanel_Overrides(bpy.types.Panel):
	bl_label = "Overrides"
	bl_parent_id = "OMNISTEP_PT_SettingsPanel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_options = {'DEFAULT_CLOSED'}

	def draw_header(self, context):
		layout = self.layout
		settings = context.scene.omnistep_settings
		layout.prop(settings, "override_addon_settings", text="")


	def draw(self, context):
		settings = context.scene.omnistep_settings

		layout = self.layout

		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.
		layout.enabled = settings.override_addon_settings

		layout = layout.column()
		layout.prop(settings, "mouse_sensitivity", text="Mouse Sens.")
		layout.prop(settings, "mouse_invert_y")

# ********************************************************* #
class WM_OT_ShowDialog(bpy.types.Operator):
	bl_idname = "wm.omnistep_show_dialog"
	bl_label = "OmniStep Info"
	bl_description = "Shows additional information"
	bl_options = {'INTERNAL'} 

	# this is a bit convoluted, collection of groups, but the AI said it is
	# the only way if the list length is not known
	messages: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)

	def execute(self, context):
		return {'FINISHED'}

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)

	def draw(self, context):
		layout = self.layout
		for message_item in self.messages:
			row = layout.row()
			row.scale_y = 0.75
			row.label(text=message_item.name)

# ********************************************************* #
class OMNISTEP_CollectionItem(bpy.types.PropertyGroup):
	collection: bpy.props.PointerProperty(name="Collection", type=bpy.types.Collection)

# ********************************************************* #
class OMNISTEP_OT_CollectionItemAction(bpy.types.Operator):
	bl_idname = "omnistep.collection_item_action"
	bl_label = "Collection Item Action"
	bl_options = {'INTERNAL'} 

	action: bpy.props.StringProperty()
	index: bpy.props.IntProperty(default=-1)  # Add this line

	def execute(self, context):
		settings = context.scene.omnistep_settings
		if self.action == 'ADD':
			settings.collide_collections.add()
		elif self.action == 'REMOVE' and self.index >= 0:  # Check the index
			settings.collide_collections.remove(self.index)
		return {'FINISHED'}

# ********************************************************* # SCRIPTING
class OMNISTEP_DynamicItem(bpy.types.PropertyGroup):
	# Name of the value
	name: bpy.props.StringProperty(name="Name")
	# Enum to determine the type of value stored
	data_type: bpy.props.EnumProperty(
		name="Type",
		items=[
			('FLOAT', "Float", ""),
			('INT', "Integer", ""),
			('STRING', "String", ""),
			('VECTOR', "Vector", ""),
			('COLOR', "Color", ""),
			('BOOLEAN', "Boolean", ""),
			('MATERIAL', "Material", ""),
			('OBJECT', "Object", ""),
			('COLLECTION', "Collection", ""),
			('ACTION', "Action", "")
		],
		default='FLOAT'
	)	
	# Properties for each type
	float_value: bpy.props.FloatProperty(name="Float Value", update=util.inspector_change)
	int_value: bpy.props.IntProperty(name="Int Value", update=util.inspector_change)
	string_value: bpy.props.StringProperty(name="String Value", update=util.inspector_change)
	vector_value: bpy.props.FloatVectorProperty(name="Vector Value", size=3, default=(0.00, 0.00, 0.00), update=util.inspector_change)
	color_value: bpy.props.FloatVectorProperty(name="Color Value", subtype='COLOR', default=(1.00, 1.00, 1.00, 1.00), min=0.0, max=1.0, size=4, update=util.inspector_change)
	boolean_value: bpy.props.BoolProperty(name="Boolean Value", default=False, update=util.inspector_change)
	material_reference: bpy.props.PointerProperty(name="Material Reference", type=bpy.types.Material, update=util.inspector_change)
	object_reference: bpy.props.PointerProperty(name="Object Reference", type=bpy.types.Object, update=util.inspector_change)
	collection_reference: bpy.props.PointerProperty(name="Collection Reference", type=bpy.types.Collection, update=util.inspector_change)
	action_reference: bpy.props.PointerProperty(name="Action Reference", type=bpy.types.Action, update=util.inspector_change)
	# special bool to check if user change
	changed: bpy.props.BoolProperty(name="Changed", default=False)

# ********************************************************* #
class OMNISTEP_AddPreset(AddPresetBase, Operator):
	bl_idname = "omnistep.add_preset"
	bl_label = "Add OmniStepPreset"
	preset_menu = "OMNISTEP_MT_DisplayPresets"

	preset_defines = ["settings = bpy.context.scene.omnistep_settings"]
	preset_values = [
		# Walk
		"settings.walk_mouse_damping",

		"settings.run_speed",
		"settings.walk_speed",
		"settings.jump_speed",

		"settings.ground_acceleration",
		"settings.ground_friction",
		
		"settings.always_run",		
		"settings.wall_jump",
		"settings.air_jump",
		
		#Fly
		"settings.fly_mouse_damping",
		"settings.radial_view_control",
		"settings.trackball_rotation",

		"settings.fly_speed",
		"settings.fly_acceleration",
		"settings.fly_air_friction",

		"settings.fly_radius",
		"settings.fly_collisions",

		"settings.fly_banking",

		# Advanced
		"settings.banking_spring",
		
		"settings.teleport_speed",
		"settings.teleport_time",
		
		"settings.adjust_focal_sens",

		"settings.player_height",
		"settings.player_head_offset",
		"settings.walk_banking",

		"settings.ground_decceleration",
		"settings.air_acceleration",
		"settings.air_decceleration",

		"settings.cam_inertia",
		"settings.cam_inertia_spring_vertical",
		"settings.cam_inertia_spring_horizontal",

		"settings.radial_view_maxturn",
		"settings.trackball_balance",
		"settings.trackball_autolevel"
	]
	# where to store the preset
	preset_subdir = "omnistep_presets"

# ********************************************************* #
class OMNISTEP_MT_DisplayPresets(Menu):
	bl_label = "Player Presets"
	preset_subdir = "omnistep_presets"
	preset_operator = "script.execute_preset"
	draw = Menu.draw_preset

# ********************************************************* #
class OMNISTEP_PT_Presets(PresetPanel, bpy.types.Panel):
	bl_label = "OmniStep Presets"
	bl_idname = "OMNISTEP_PT_hidden_presets"

	preset_subdir = "omnistep_presets"
	preset_operator = "script.execute_preset"
	preset_add_operator = "omnistep.add_preset"


	def draw(self, context):
		layout = self.layout
		layout.emboss = 'PULLDOWN_MENU'
		layout.operator_context = 'EXEC_DEFAULT'
		Menu.draw_preset(self, context)
		context.area.tag_redraw()	# ugly, but works