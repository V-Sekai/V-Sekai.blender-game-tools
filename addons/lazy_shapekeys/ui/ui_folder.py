import bpy
from ..utils import *
from .ui_misc import draw_sidebar

# フォルダー
def draw_folder(self,context,layout, tgt_obj, is_misc_menu):
	addon_prefs = preference()
	ob = tgt_obj
	key = ob.data.shape_keys
	kb = ob.active_shape_key

	list_rows = 15
	if is_misc_menu:
		misc_menu_prefs = bpy.context.preferences.addons['misc_menu'].preferences
		list_rows = misc_menu_prefs.folder_sk_rows


	is_use_folder = False
	folder_l = []
	if key:
		folder_l = [ky for ky in key.key_blocks if is_folder(ky)]
	if folder_l:
		is_use_folder = True


	sp = layout.split(align=True,factor=0.3)
	row = sp.row(align=True)
	op = row.operator("lazy_shapekeys.item_add", icon='NEWFOLDER', text="")
	op.obj_name = ob.name
	op.move_to_act_pos = False
	rows = row.row(align=True)
	rows.active = is_use_folder
	op = rows.operator("lazy_shapekeys.sk_item_remove", icon='REMOVE', text="")
	op.obj_name = ob.name
	op.is_folder_remove = True
	rows.separator()
	op = rows.operator("lazy_shapekeys.item_move_item", icon='TRIA_UP', text="")
	op.direction = 'UP'
	op.is_def_list = False
	op.obj_name = tgt_obj.name
	op = rows.operator("lazy_shapekeys.item_move_item", icon='TRIA_DOWN', text="")
	op.direction = 'DOWN'
	op.is_def_list = False
	op.obj_name = tgt_obj.name
	row.separator()


	row = sp.row()
	row.active = is_use_folder

	row_sel = row.row(align=True)
	op = row_sel.operator("lazy_shapekeys.batch_select_all_index",text="",icon="CHECKBOX_HLT")
	op.type = "SELECT"
	row_deselect = row_sel.row(align=True)
	if key:
		sk_pr = key.lazy_shapekeys
		select_l = get_sk_batch_index(sk_pr)
		row_deselect.active = bool(select_l)
	op = row_deselect.operator("lazy_shapekeys.batch_select_all_index",text="",icon="CHECKBOX_DEHLT")
	op.type = "DESELECT"
	row.separator()

	op = row.operator("lazy_shapekeys.shapekeys_batch_keyframe_insert",icon="DECORATE_KEYFRAME")
	op.obj_name = tgt_obj.name
	op.is_def_listmenu = False
	op.is_batch=False

	op = row.operator("lazy_shapekeys.shapekeys_batch_value_reset",text="",icon="X")
	op.obj_name = tgt_obj.name
	row.label(text="",icon="BLANK1")



	# UIリスト
	sp = layout.split(align=True,factor=addon_prefs.ui.folder_split)
	row = sp.row(align=True)

	# if is_misc_menu:
	# 	col_sp= row.column(align=True)
	# 	col_sp.scale_x = .2
	# 	col_sp.scale_y = 2
	# 	for i in range(10):
	# 		col_sp.separator()
	# 	col_sp.prop(addon_prefs.ui,"folder_split",text="")


	# if key:
	row.template_list("LAZYSHAPEKEYS_UL_folder_colle", "", key, "key_blocks", tgt_obj.lazy_shapekeys, "folder_colle_index",rows=list_rows)
	# else:
	# 	row.label(text="",icon="NONE")

	# 幅調整
	col_sp= row.column(align=True)
	col_sp.active = False
	col_sp.scale_x = .12
	col_sp.scale_y = 2
	for i in range(10):
		col_sp.separator()
	col_sp.prop(addon_prefs.ui,"folder_split",text="")

	row = sp.row(align=True)
	if is_misc_menu:
		row.template_list("LAZYSHAPEKEYS_UL_folder_inner_sk_misc_menu", "", key, "key_blocks", ob, "active_shape_key_index",rows=list_rows)
	else:
		row.template_list("LAZYSHAPEKEYS_UL_folder_inner_sk", "", key, "key_blocks", ob, "active_shape_key_index",rows=list_rows)

	#
	# if is_misc_menu:
	# 	col_sp= row.column(align=True)
	# 	col_sp.scale_x = .2
	# 	col_sp.scale_y = 2
	# 	for i in range(10):
	# 		col_sp.separator()
	# 	col_sp.prop(addon_prefs.ui,"sk_item_split",text="")

		row.separator()

	row.separator()



	col = row.column(align=True)
	draw_sidebar(self, context, col, tgt_obj, True,is_misc_menu)
