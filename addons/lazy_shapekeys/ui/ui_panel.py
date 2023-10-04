import bpy, re
from bpy.props import *
from bpy.types import Panel, Operator
from ..utils import *
from .ui_replace_sk_menu import *


class LAZYSHAPEKEYS_PT_main(Panel):
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'Addons'
	bl_label = "Lazy Shapekeys"
	bl_options = {'DEFAULT_CLOSED'}


	@classmethod
	def poll(cls, context):
	    if bpy.context.object:
	        obj = bpy.context.object
	        if obj.type in {"MESH", "CURVE", "SURFACE"}:
	            return True

	def draw(self, context):
		layout = self.layout
		LAZYSHAPEKEYS_PT_shape_keys_innner(self, context, False, layout, None,False)


class LAZYSHAPEKEYS_PT_misc_menu(Panel):
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'Addons'
	bl_label = "Lazy Shapekeys"
	bl_options = {'DEFAULT_CLOSED'}


	@classmethod
	def poll(cls, context):
		return False # 内部的でのみ使うので、パネルメニューは常に非表示
	# @classmethod
	# def poll(cls, context):
	#     if bpy.context.object:
	#         obj = bpy.context.object
	#         if obj.type in {"MESH", "CURVE", "SURFACE"}:
	#             return True

	def draw(self, context):
		layout = self.layout

		LAZYSHAPEKEYS_PT_shape_keys_innner(self, context, True, layout, None,False)


	def draw_innner(self, context, is_misc_menu, layout, tgt_obj):
		LAZYSHAPEKEYS_PT_shape_keys_innner(self, context, is_misc_menu, layout, tgt_obj,False)


#
class LAZYSHAPEKEYS_OT_main(Operator):
	bl_idname = "lazy_shapekeys.folder_move_sk_popup_menu"
	bl_label = "folder_move_sk_popup_menu"
	bl_description = ""
	bl_options = {'REGISTER', 'UNDO'}


	index : IntProperty()


	def invoke(self, context, event):
		return context.window_manager.invoke_popup(self)


	def draw(self, context):
		layout = self.layout
		obj = bpy.context.active_object
		sk_bl = obj.data.shape_keys.key_blocks

		for sk in sk_bl:
			if is_folder(sk):
				op = layout.operator("lazy_shapekeys.folder_move_sk",text=sk.name,icon="NONE")
				op.index = self.index
				op.folder_name = sk.name

	def execute(self, context):
		return {'FINISHED'}
