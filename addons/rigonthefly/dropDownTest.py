#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy 

# Here comes the bl-info later. 

class ADD_OT_say_hi(bpy.types.Operator):
	bl_idname = 'add.say_hi'
	bl_description = 'Look in the console'
	bl_category = 'Usefill addon'
	bl_label = 'Say Hi'

	def execute(self, context):
		print('hi') 	
		return {"FINISHED"}

class ADD_OT_say_bye(bpy.types.Operator):
	bl_idname = 'add.say_bye'
	bl_description = 'Look in the console'
	bl_category = 'Usefill addon'
	bl_label = 'Say Bye'

	def execute(self, context):
		print('bye')		
		return {"FINISHED"}

# I want the above 2 classes to be in a drop-down-menu.  
# The class below not included in the drop down, but a button.  

class ADD_OT_say_nothing(bpy.types.Operator):
	bl_idname = 'add.say_nothing'
	bl_description = 'Look in the console'
	bl_category = 'Usefill addon'
	bl_label = 'Say nothing'

	def execute(self, context):
		print('Nothing')		
		return {"FINISHED"}


class ADD_MT_menu(bpy.types.Menu):
	bl_label = "StoryTelling Menu"
	bl_idname = "ADD_MT_menu"

	def draw(self, context):
		layout = self.layout

		layout.operator("add.say_hi")
		layout.operator("add.say_bye")

# Below the menu I get so far, but shows only buttons. 


class ADD_PT_panel(bpy.types.Panel):
	bl_space_type = "VIEW_3D"
	bl_region_type = 'UI'
	bl_label = 'The Usefill addon'
	bl_category = 'Usefill addon'

	def draw(self, context):
		layout = self.layout
		row = layout.row()
		row.label(text="Usefill addon")
		row = layout.row()
		row.menu("ADD_MT_menu")
		row = layout.row()
		row.operator("add.say_nothing", icon="SNAP_GRID")

#Register and unregister classes	

classes = (
	ADD_OT_say_hi,
	ADD_OT_say_bye,
	ADD_MT_menu,
	ADD_PT_panel,
	ADD_OT_say_nothing)  

def register():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)

def unregister():
	from bpy.utils import unregister_class
	for cls in classes:
		unregister_class(cls)

if __name__ == "__main__":
	register()
