import bpy, ast
from bpy.types import Operator
from bpy.props import *
from ..utils import *


# シェイプキーの一括設定
class LAZYSHAPEKEYS_OT_batch_set(Operator):
	bl_idname = 'lazy_shapekeys.batch_set'
	bl_label = 'Run Batch Processing'
	bl_description = 'Batch processing is performed for the multi selected shape keys.\nBy clicking the shape key icon, it will be in the selected state'
	bl_options = {'REGISTER'}

	obj_name : StringProperty()

	def execute(self, context):
		obj = get_target_obj(self.obj_name)
		key = obj.data.shape_keys
		sk_pr = key.lazy_shapekeys
		sks = obj.data.shape_keys
		sk_bl = sks.key_blocks
		skbl_index_l = [i for i,sk in enumerate(sk_bl)]
		batch = sk_pr.batch
		if not sk_pr.multi_select_data:
			self.report({'INFO'}, "No List")
			return {'CANCELLED'}


		select_l = list(ast.literal_eval(sk_pr.multi_select_data))
		used_l = []

		for index in select_l:
			if not index in skbl_index_l:
				continue
			sk = obj.data.shape_keys.key_blocks[index]

			# 値
			if 0 <= batch.value <=1:
				sk.value = batch.value
				if not sk in used_l: used_l += [sk]

			# 最大値
			if not batch.slider_max == -11:
				sk.slider_max = batch.slider_max
				if not sk in used_l: used_l += [sk]

			# 最小値
			if not batch.slider_min == -11:
				sk.slider_min = batch.slider_min
				if not sk in used_l: used_l += [sk]

			# 基準の対象
			if batch.relative_key:
				if not sk == key.key_blocks[batch.relative_key]:
					sk.relative_key = key.key_blocks[batch.relative_key]
					if not sk in used_l: used_l += [sk]


		self.report({'INFO'}, "Run Batch Processing [%s]" % len(used_l))
		return {'FINISHED'}


# アイテムを一括選択
class LAZYSHAPEKEYS_OT_batch_select_all_index(Operator):
	bl_idname = "lazy_shapekeys.batch_select_all_index"
	bl_label = "Batch　Select Item"
	bl_description = "Toggles all selections.\nWhen selecting all and in the folder tab, only the shape keys in the active folder are selected"
	bl_options = {'REGISTER', 'UNDO'}

	items = [
	("SELECT","",""),
	("DESELECT","",""),
	]
	type : EnumProperty(default="SELECT",name="Select Type",items= items)
	obj_name : StringProperty()



	def invoke(self, context, event):
		addon_prefs = preference()
		obj = get_target_obj(self.obj_name)

		sks = obj.data.shape_keys
		sk_bl = sks.key_blocks
		sk_pr = obj.data.shape_keys.lazy_shapekeys
		batch = sk_pr.batch


		# 選択解除
		if self.type == "DESELECT":
			if not event.alt:
				sk_pr.multi_select_data = ""
				return{'FINISHED'}


		# 選択indexの文字列をリスト化
		if sk_pr.multi_select_data:
			select_l = list(ast.literal_eval(sk_pr.multi_select_data))
		else:
			select_l = []


		# フォルダータブの場合は、フォルダー内のシェイプキーを使用
		if addon_prefs.ui.list_mode == "FOLDER":
			folder_inner_name_bl = get_folder_innner_sk_list(obj.lazy_shapekeys.folder_colle_index, sks)



		is_already = None
		for i, sk in enumerate(sk_bl):
			if addon_prefs.ui.list_mode == "FOLDER":
				if not sk.name in folder_inner_name_bl:
					continue
			if is_folder(sk) or sk.name == "Basis":
				continue

			if is_already == None:
				if i in select_l: # すでにリストにある場合はスルー
					is_already = True

			if not i in select_l: # 選択リストに追加
				select_l += [i]
				is_already = False # 1つでも選択リストになければ、全削除処理はしない


		# # すべてリストにある場合は、全オフ
		# if is_already == True:
		# 	for i, sk in enumerate(sk_bl):
		# 		if addon_prefs.ui.list_mode == "FOLDER":
		# 			if not sk.name in folder_inner_name_bl:
		# 				continue
		# 		if is_folder(sk) or sk.name == "Basis":
		# 			continue
		#
		# 		select_l.remove(i)



		select_l = list(list(sorted(set(select_l))))
		sk_pr.multi_select_data = str(select_l)
		return {'FINISHED'}


# アイテムを選択
class LAZYSHAPEKEYS_OT_batch_select_index(Operator):
	bl_idname = "lazy_shapekeys.batch_select_index"
	bl_label = "Select Item(for Batch Operation)"
	bl_description = "Make a selection.\nDoes a multiple selection for the add-on's batch processing feature instead of the normal selection.\nAlt + Click: Deselect All"
	bl_options = {'REGISTER', 'UNDO'}

	index : IntProperty()
	obj_name : StringProperty()


	def invoke(self, context, event):
		obj = get_target_obj(self.obj_name)
		sk_pr = obj.data.shape_keys.lazy_shapekeys
		batch = sk_pr.batch

		if event.alt:
			sk_pr.multi_select_data = ""
			return{'FINISHED'}


		if sk_pr.multi_select_data:
			select_l = get_sk_batch_index(sk_pr)
		else:
			select_l = []

		if self.index in select_l: # すでにあるなら削除
			select_l.remove(self.index)
		else: # 同じインデックス番号が無いなら追加
			select_l += [self.index]


		sk_pr.multi_select_data = str(sorted(select_l))
		return {'FINISHED'}
