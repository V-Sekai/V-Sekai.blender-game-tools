import bpy
from ..utils import *


# リストのメニュー
def draw_replace_shapekeys_list(self, context, layout, data, item, icon, active_data, active_propname, index, is_defpanel, is_popup):
	addon_prefs = preference()
	obj = active_data
	key_block = item
	sks = active_data.data.shape_keys
	sk_bl = sks.key_blocks
	sk_pr = sks.lazy_shapekeys
	act_id = active_data.active_shape_key_index

	use_open_window = False
	if data.animation_data:
		if data.animation_data.action:
			if data.animation_data.action.fcurves:
				for fc in data.animation_data.action.fcurves:
					if fc.data_path == 'key_blocks["%s"].value' % item.name:
						use_open_window = True
			else:
				use_open_window = "no_fc"
		else:
			use_open_window = "no_fc"
	else:
		use_open_window = "no_fc"


	if is_folder(item):
		dic = convert_mini_text_to_dic(item.vertex_group)
		if dic["exp"] == 1:
			exp_icon = "TRIA_DOWN"
		else:
			exp_icon = "TRIA_RIGHT"

		sp = layout.split(align=True,factor=0.7)
		row = sp.row(align=True)
		op = row.operator("lazy_shapekeys.toggle_expand",text="",icon=exp_icon,emboss=False)
		op.index = index
		op.obj_name =  obj.name
		row.prop(key_block, "name", text="", emboss=False, icon="FILE_FOLDER")


		row = sp.row(align=True)
		row.alignment="RIGHT"

		rows = row.row(align=True)
		if not get_sk_batch_index(sk_pr):
			try:
				aff_folder_sk = get_affiliation_folder(sk_bl[act_id], act_id, sk_bl)
				rows.enabled = bool(not item == aff_folder_sk)
			except IndexError: pass

		op = rows.operator("lazy_shapekeys.folder_move_sk",text="",icon="IMPORT",emboss=False)
		op.index = -1
		op.folder_name = item.name
		op.obj_name =  obj.name


		op = row.operator("lazy_shapekeys.shapekeys_batch_keyframe_insert",text="",icon="DECORATE_KEYFRAME",emboss=False)
		op.obj_name = obj.name
		op.is_def_listmenu = True
		op.index = index
		op.is_batch=False
		# if not use_open_window == "no_fc":
		row.label(text="",icon="BLANK1")


		if dic["mute"] == 1:
			icon_val = "CHECKBOX_DEHLT"
		else:
			icon_val = "CHECKBOX_HLT"
		op = row.operator("lazy_shapekeys.shapekeys_batch_mute",text="",icon=icon_val,emboss=False)
		op.sks_name = data.name
		op.index = index

		return


	if self.layout_type in {'DEFAULT', 'COMPACT'}:
		# 一括設定用の選択リスト
		select_l = get_sk_batch_index(sk_pr)
		ic_val = "SHAPEKEY_DATA"
		split_active = True
		if select_l:
			if len(select_l):
				split_active = False
			if select_l and index in select_l:
				ic_val = "CHECKMARK"
				split_active = True


		# 分割表示
		split = layout.split(factor=addon_prefs.ui.sk_item_split, align=False)
		split.active = split_active
		row = split.row(align=True)


		# フォルダー用の空白
		use_folder_l = [sk for i,sk in enumerate(obj.data.shape_keys.key_blocks) if is_folder(sk)]
		if use_folder_l and is_defpanel:
			row.label(text="",icon="BLANK1")

		# 一括設定用の選択ボタン
		op = row.operator("lazy_shapekeys.batch_select_index",text="",icon=ic_val,emboss=False)
		op.index = index
		op.obj_name = obj.name

		# 名前
		row.prop(key_block, "name", text="",icon="NONE", emboss=False)



		# 区切りバー。選択で幅を左右に調整できる
		row_spbar = row.row(align=True)
		row_spbar.scale_x = .15
		row_spbar.prop(addon_prefs.ui,"sk_item_split",text="",emboss=False)


		row = split.row(align=True)
		if addon_prefs.ui.sk_menu_use_slider:
			row.emboss = "NORMAL"
		else:
			row.emboss = 'NONE_OR_STATUS'


		if key_block.mute or (obj.mode == 'EDIT' and not (obj.use_shape_key_edit_mode and obj.type == 'MESH')):
			row.active = False

		if not item.id_data.use_relative:
			row.prop(key_block, "frame", text="")

		elif index > 0:
			if is_popup:
				rows = row.row(align=True)
				rows.prop(key_block, "value", text="",slider=addon_prefs.ui.sk_menu_use_slider)

				use_cur_key_l, is_remove = check_use_keyframe(data, [item.name])

				if is_remove:
					icon_val = "KEYFRAME_HLT"
				else:
					icon_val = "KEYFRAME"

				op = rows.operator("lazy_shapekeys.shapekeys_one_keyframe_insert",text="",icon=icon_val,emboss=False)
				op.sk_name = item.name
				op.obj_name = obj.name
				op.is_def_listmenu = is_defpanel
				op.index = index

			else:
				rows = row.row(align=True)
				rows.use_property_split = True
				rows.use_property_decorate = True
				rows.prop(key_block, "value", text="",slider=addon_prefs.ui.sk_menu_use_slider)


		else:
			row.label(text="")


		if use_open_window == "no_fc":
			row.label(text="",icon="BLANK1")
		elif use_open_window:
			op = row.operator("lazy_shapekeys.shapekeys_open_window",text="",icon="WINDOW",emboss=False)
			op.sk_name = item.name

		else:
			row.label(text="",icon="BLANK1")


		row.prop(key_block, "mute", text="", emboss=False)



	elif self.layout_type == 'GRID':
		layout.alignment = 'CENTER'
		layout.label(text="", icon_value=icon)
