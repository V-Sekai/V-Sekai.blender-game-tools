import bpy
from ..utils import *


# シェイプキーリストのサイドバー
def draw_sidebar(self, context, layout, tgt_obj, is_in_folder, is_misc_menu):
	addon_prefs = preference()
	col = layout
	ob = tgt_obj
	key = ob.data.shape_keys
	kb = ob.active_shape_key

	op = col.operator("lazy_shapekeys.sk_item_add", icon='ADD', text="")
	op.obj_name = ob.name
	op.is_in_folder = is_in_folder
	# col.operator("object.shape_key_remove", icon='REMOVE', text="").all = False
	op = col.operator("lazy_shapekeys.sk_item_remove", icon='REMOVE', text="")
	op.obj_name = ob.name
	op.is_folder_remove = False


	col.separator()

	col.menu("MESH_MT_shape_key_context_menu", icon='DOWNARROW_HLT', text="")

	if kb:
		col.separator()

		sub = col.column(align=True)
		op = sub.operator("lazy_shapekeys.item_move_item", icon='TRIA_UP', text="")
		op.direction = 'UP'
		op.is_def_list = True
		op.obj_name = tgt_obj.name
		op = sub.operator("lazy_shapekeys.item_move_item", icon='TRIA_DOWN', text="")
		op.direction = 'DOWN'
		op.is_def_list = True
		op.obj_name = tgt_obj.name

	col.separator()
	op = col.operator("lazy_shapekeys.item_add", icon='NEWFOLDER', text="")
	op.obj_name = ob.name
	op.move_to_act_pos = True


	if addon_prefs.ui.list_mode == "FOLDER":
		if is_misc_menu:
			for i in range(3):
				col.label(text="",icon="BLANK1")
			col_sp= col.column(align=True)
			col_sp.active = False
			col_sp.scale_y = 2
			row = col_sp.row(align=True)
			row.scale_x = .13
			row.alignment="RIGHT"
			row.prop(addon_prefs.ui,"folder_split",text="")

			col_sp.separator()

			row = col_sp.row(align=True)
			row.scale_x = .13
			row.alignment="RIGHT"
			row.prop(addon_prefs.ui,"sk_item_split",text="")


# 同期
def draw_sync(self, context ,layout, is_misc_menu):
	props = bpy.context.scene.lazy_shapekeys
	colle = bpy.context.scene.lazy_shapekeys_colle

	layout.operator("lazy_shapekeys.shape_keys_sync_update",icon="NONE")
	layout.prop(props,"tgt_colle")
	layout.separator()


	if is_misc_menu:
		misc_menu_prefs = bpy.context.preferences.addons['misc_menu'].preferences
		list_rows = misc_menu_prefs.folder_sk_rows
		rows_num = list_rows
	else:
		rows_num = 5

	layout.template_list("LAZYSHAPEKEYS_UL_sync_list", "", bpy.context.scene, "lazy_shapekeys_colle", props, "sync_colle_index", rows=rows_num)
