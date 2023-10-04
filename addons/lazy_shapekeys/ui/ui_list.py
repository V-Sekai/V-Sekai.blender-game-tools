import bpy
from bpy.props import *
from bpy.types import UIList
from ..utils import *
from .ui_one_item import draw_replace_shapekeys_list


# 同期
class LAZYSHAPEKEYS_UL_sync_list(UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		row = layout.row()
		row.prop(item,"mute",text="",icon="CHECKBOX_DEHLT" if item.mute else "CHECKBOX_HLT",emboss=False)
		row.prop(item,"value",text=item.name,slider=True)


# フォルダー
class LAZYSHAPEKEYS_UL_folder_colle(UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		row = layout.row(align=True)
		row.prop(item,"name",text="",icon="FILE_FOLDER",emboss=False)
		obj = active_data

		rows = row.row(align=True)
		if not get_sk_batch_index(item.id_data.lazy_shapekeys):
			rows.enabled = (not active_data.folder_colle_index == index)
		op = rows.operator("lazy_shapekeys.folder_move_sk",text="",icon="IMPORT",emboss=False)
		op.index = -1
		op.folder_name = item.name
		op.obj_name =  obj.id_data.name

		dic = convert_mini_text_to_dic(item.vertex_group)

		if dic["mute"] == 1:
			icon_val = "CHECKBOX_DEHLT"
		else:
			icon_val = "CHECKBOX_HLT"
		op = row.operator("lazy_shapekeys.shapekeys_batch_mute",text="",icon=icon_val,emboss=False)
		op.sks_name = data.name
		op.index = index


	def filter_items(self, context, data, propname):
		filtered = []
		ordered = []
		items = getattr(data, propname)
		helper_funcs = bpy.types.UI_UL_list


		# Initialize with all items visible
		filtered = [self.bitflag_filter_item] * len(items)

		# 文字列でのフィルター
		if self.filter_name:
			filtered = helper_funcs.filter_items_by_name(
			self.filter_name,
			self.bitflag_filter_item,
			items,
			"name",
			reverse=self.use_filter_sort_reverse)


		# 名前順にソート
		if self.use_filter_sort_alpha:
			ordered = helper_funcs.sort_items_by_name(items, "name")


		# 除去
		for i, item in enumerate(items):
			if not is_folder(item):
				filtered[i] &= ~self.bitflag_filter_item


		return filtered,ordered


# インナーのシェイプキー
class LAZYSHAPEKEYS_UL_folder_inner_sk(UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		draw_replace_shapekeys_list(self, context, layout, data, item, icon, active_data, active_propname, index, False, False)

	def filter_items(self, context, data, propname):

		filtered,ordered = folder_filter_items(self, context, data, propname)
		return filtered,ordered


# インナーのシェイプキー misc_menu
class LAZYSHAPEKEYS_UL_folder_inner_sk_misc_menu(UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		draw_replace_shapekeys_list(self, context, layout, data, item, icon, active_data, active_propname, index, False, True)

	def filter_items(self, context, data, propname):
		filtered,ordered = folder_filter_items(self, context, data, propname)
		return filtered,ordered


def folder_filter_items(self, context, data, propname):
	filtered = []
	ordered = []
	items = getattr(data, propname)
	helper_funcs = bpy.types.UI_UL_list


	# Initialize with all items visible
	filtered = [self.bitflag_filter_item] * len(items)

	# 文字列でのフィルター
	if self.filter_name:
		filtered = helper_funcs.filter_items_by_name(
		self.filter_name,
		self.bitflag_filter_item,
		items,
		"name",
		reverse=self.use_filter_sort_reverse)


	# [名前順にソート]オプションとフォルダー機能は共存できないので、有効化すると折りたたみや並び順は無視されます
	if self.use_filter_sort_alpha:
		ordered = helper_funcs.sort_items_by_name(items, "name")

	else:
		# シェイプキーの方のインデックスを参照する
		tgt_index = data.lazy_shapekeys.folder_colle_sks_index
		sk_bl = data.key_blocks

		# 除去
		folder_l = [i for i in items if is_folder(i)]

		if folder_l:
			new_l = []
			for i,sk in enumerate(sk_bl):
				if i > tgt_index:
					if is_folder(sk):
						break
					new_l += [sk.name]


			for i,sk in enumerate(sk_bl):
				if not sk.name in new_l:
					filtered[i] &= ~self.bitflag_filter_item


	return filtered,ordered
