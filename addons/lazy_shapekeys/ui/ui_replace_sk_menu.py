import bpy
from bpy.props import *
from bpy.types import UIList
from ..utils import *
from .ui_core import LAZYSHAPEKEYS_PT_shape_keys_innner
from .ui_one_item import draw_replace_shapekeys_list

# シェイプキーリスト
class LAZYSHAPEKEYS_UL_replace_menu(UIList):
	filter_by_name: StringProperty(default='')
	sort_invert: BoolProperty(default=False)
	order_by_random_prop: BoolProperty(default=False)

	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		draw_replace_shapekeys_list(self, context, layout, data, item, icon, active_data, active_propname, index, True, False)


	def filter_items(self, context, data, propname):
		filtered, ordered = filter_items_replace_menu(self, context, data, propname)
		return filtered,ordered


# シェイプキーリスト
class LAZYSHAPEKEYS_UL_replace_menu_misc_menu(UIList):
	filter_by_name: StringProperty(default='')
	sort_invert: BoolProperty(default=False)
	order_by_random_prop: BoolProperty(default=False)

	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		draw_replace_shapekeys_list(self, context, layout, data, item, icon, active_data, active_propname, index, True, True)


	def filter_items(self, context, data, propname):
		filtered, ordered = filter_items_replace_menu(self, context, data, propname)
		return filtered,ordered


def filter_items_replace_menu(self, context, data, propname):
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
		# 除去
		sk_bl = data.key_blocks

		hide_sk_l = []
		all_count = len(items) -1
		# 非表示にするアイテムをまとめる
		for i, item in enumerate(items):
			if is_folder(item): # フォルダーアイテム
				dic = convert_mini_text_to_dic(item.vertex_group)

				if dic["exp"] == 0: # 開いていない
					hide_sk_l += get_folder_innner_sk_list(i, data) # フォルダー内のアイテム

		if hide_sk_l:
			for i,sk in enumerate(sk_bl):
				if sk.name in hide_sk_l:
					filtered[i] &= ~self.bitflag_filter_item


	return filtered,ordered
