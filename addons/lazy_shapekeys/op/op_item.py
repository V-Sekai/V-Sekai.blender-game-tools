import bpy, subprocess, os
from bpy.props import *
from bpy.types import Operator
import ast
from ..utils import *


class LAZYSHAPEKEYS_OT_folder_toggle_expand(Operator):
	bl_idname = "lazy_shapekeys.toggle_expand"
	bl_label = "Toggle Expand"
	bl_description = ""
	bl_options = {'REGISTER', 'UNDO'}

	index : IntProperty()
	obj_name : StringProperty()

	@classmethod
	def poll(cls, context):
		 obj = bpy.context.active_object
		 if obj:
			 return True


	def execute(self, context):
		obj = get_target_obj(self.obj_name)

		sk_bl = obj.data.shape_keys.key_blocks
		item = sk_bl[self.index]

		dic = convert_mini_text_to_dic(item.vertex_group)
		if dic["exp"] == 1:
			dic["exp"] = 0
		else:
			dic["exp"] = 1

		item.vertex_group = convert_dic_to_mini_text(dic)

		return{'FINISHED'}


class LAZYSHAPEKEYS_OT_folder_move_sk(Operator):
	bl_idname = "lazy_shapekeys.folder_move_sk"
	bl_label = "Move Shapekey to Other Folder"
	bl_description = ""
	bl_options = {'REGISTER', 'UNDO'}

	index : IntProperty()
	folder_name : StringProperty()
	sks_name : StringProperty()
	obj_name : StringProperty()


	@classmethod
	def poll(cls, context):
		 obj = bpy.context.active_object
		 if obj and not obj.mode == "EDIT":
			 return True


	def execute(self, context):
		old_act = bpy.context.view_layer.objects.active
		obj = get_target_obj(self.obj_name)
		if not obj == bpy.context.object:
			bpy.context.view_layer.objects.active = obj

		sks = obj.data.shape_keys
		sk_pr = sks.lazy_shapekeys
		sk_bl = sks.key_blocks
		old_index = obj.active_shape_key_index
		old_folder_index = obj.lazy_shapekeys.folder_colle_index
		old_folder_item = sk_bl[old_folder_index]


		batch_id_list = get_sk_batch_index(sk_pr)


		# アクティブのみ、または複数選択のインデックス
		if self.index == -1:
			if batch_id_list:
				# 複数選択の場合は一括
				name_l = [sk_bl[i].name for i in batch_id_list]
				old_sk_name_l = name_l
			else:
				name_l = [sk_bl[old_index].name] # 単一のアイテム

		else:
			# 指定のインデックス
			name_l = [sk_bl[self.index].name]


		# 一括処理を行う
		for tgt_name in name_l:
			folder_index = sk_bl.find(self.folder_name) # 入れるフォルダーのインデックス
			tgt_id = sk_bl.find(tgt_name)
			obj.active_shape_key_index = tgt_id # 対象のシェイプキーをアクティブにする

			# 並び順を変える数を把握する
			inner_items = get_folder_innner_sk_list(folder_index, sks) # フォルダー内のアイテム
			move_num = len(inner_items) + folder_index

			if tgt_id < folder_index:
				move_num -= 1


			# 一番上に移動した後、フォルダ下に移動する
			bpy.ops.object.shape_key_move(type='TOP') # 一番上に移動
			for i in range(move_num):
				bpy.ops.object.shape_key_move(type='DOWN')



		# インデックスを修正する
		obj.lazy_shapekeys.folder_colle_index = sk_bl.find(old_folder_item.name)
		if is_folder(sk_bl[old_index]) and not (len(sk_bl)-1 < old_index):
			obj.active_shape_key_index = old_index + 1
		else:
			obj.active_shape_key_index = old_index


		# 移動するとインデックスがずれるので、複数選択のインデックスを新しいものに修正する
		if self.index == -1:
			if batch_id_list:
				batch_id_list = [i for i,sk in enumerate(sk_bl) if sk.name in old_sk_name_l]
				sks.lazy_shapekeys.multi_select_data = str(batch_id_list)


		# アクティブを戻す
		bpy.context.view_layer.objects.active = old_act

		self.report({'INFO'}, "Move [%s] Item to '%s'" % (str(len(name_l)) ,self.folder_name))
		return{'FINISHED'}


class LAZYSHAPEKEYS_OT_folder_item_add(Operator):
	bl_idname = "lazy_shapekeys.item_add"
	bl_label = "Add Folder Shapekey Item"
	bl_description = "Add a shape key for the folder.\nThe folder information is stored in the shape key's vertex group option"
	bl_options = {'REGISTER', 'UNDO'}

	obj_name : StringProperty()
	move_to_act_pos : BoolProperty()

	@classmethod
	def poll(cls, context):
		 obj = bpy.context.active_object
		 if obj and not obj.mode == "EDIT":
			 return True

	def execute(self, context):
		old_act = bpy.context.view_layer.objects.active
		obj = get_target_obj(self.obj_name)

		if not obj.data.shape_keys:
			sk = obj.shape_key_add(name = 'Basis')
			sk.interpolation = 'KEY_LINEAR'


		sk_bl = obj.data.shape_keys.key_blocks
		old_index = obj.active_shape_key_index

		# フォルダーがない場合は、最初の位置に移動する
		is_first_add = False
		folder_l = [sk for sk in sk_bl if is_folder(sk)]
		if not folder_l:
			is_first_add = True

		# フォルダー名の設定
		count = [i for i in sk_bl if i.name.startswith("Folder")]
		if count:
			item_name = "Folder " + str(len(count))
		else:
			item_name = "Folder"


		# シェイプキーブロックを追加
		new_item = obj.shape_key_add(name=item_name)

		# フォルダーの情報を頂点グループオプション内に追加する
		dic = {}
		dic["folder"] = 1
		dic["exp"] = 1
		dic["mute"] = 0
		new_item.vertex_group = convert_dic_to_mini_text(dic)
		obj.active_shape_key_index = sk_bl.find(new_item.name)

		# アクティブオブジェクトを切り替える
		if not obj == bpy.context.object:
			bpy.context.view_layer.objects.active = obj


		# 並び替え
		if is_first_add:
			bpy.ops.object.shape_key_move(type='TOP')
		else:
			if self.move_to_act_pos:
				bpy.ops.object.shape_key_move(type='TOP')
				for i in range(old_index):
					bpy.ops.object.shape_key_move(type='DOWN')





		obj.lazy_shapekeys.folder_colle_index = sk_bl.find(new_item.name)

		# アクティブオブジェクトを戻す
		bpy.context.view_layer.objects.active = old_act

		return{'FINISHED'}


class LAZYSHAPEKEYS_OT_sk_item_add(Operator):
	bl_idname = "lazy_shapekeys.sk_item_add"
	bl_label = "Add Item"
	bl_description = ""
	bl_options = {'REGISTER', 'UNDO'}

	obj_name : StringProperty()
	is_in_folder : BoolProperty()

	@classmethod
	def poll(cls, context):
		 obj = bpy.context.active_object
		 if obj and not obj.mode == "EDIT":
			 return True


	def execute(self, context):
		old_act = bpy.context.view_layer.objects.active
		obj = get_target_obj(self.obj_name)

		is_no_sk = False
		if obj.data.shape_keys:
			is_no_sk = True
		if not obj.data.shape_keys:
			sk = obj.shape_key_add(name = 'Basis')
			sk.interpolation = 'KEY_LINEAR'

		sk_bl = obj.data.shape_keys.key_blocks
		old_index = obj.active_shape_key_index


		# 最も下のアイテムだった場合、あとで並び替えしない
		is_bottom_folder = False
		folder_name = None
		if is_no_sk:
			if obj.lazy_shapekeys.folder_colle_index > len(sk_bl)-1:
				obj.lazy_shapekeys.folder_colle_index = 0

			folder_name = sk_bl[obj.lazy_shapekeys.folder_colle_index].name
			folder_l = [i for i in sk_bl if is_folder(i)]
			if folder_l:
				if folder_l[-1].name == folder_name:
					is_bottom_folder = True
			else:
				is_bottom_folder = True
		else:
			is_bottom_folder = True


		# 新規作成
		count = [i for i in sk_bl if i.name.startswith("Key ")]
		if count:
			item_name = "Key " + str(len(count))
		else:
			item_name = "Key"
		new_item = obj.shape_key_add(name=item_name,from_mix=False)



		if not obj == bpy.context.object:
			bpy.context.view_layer.objects.active = obj

		# 並び順調整
		new_id = sk_bl.find(new_item.name)
		obj.active_shape_key_index = new_id
		if self.is_in_folder:
			# フォルダー内アイテムを取得
			inner_items = get_folder_innner_sk_list(obj.lazy_shapekeys.folder_colle_index, obj.data.shape_keys)
			if inner_items:
				tgt_id = sk_bl.find(inner_items[-1])
			else:
				# フォルダー内アイテムがない場合は、そのフォルダーの位置に移動
				tgt_id = obj.lazy_shapekeys.folder_colle_index

		else:
			tgt_id = old_index

		if not is_bottom_folder:
			bpy.ops.object.shape_key_move(type='TOP')
			for i in range(tgt_id):
				bpy.ops.object.shape_key_move(type='DOWN')

		bpy.context.view_layer.objects.active = old_act
		if self.is_in_folder:
			if folder_name:
				obj.lazy_shapekeys.folder_colle_index = sk_bl.find(folder_name)
			obj.active_shape_key_index = sk_bl.find(new_item.name)

		return{'FINISHED'}


class LAZYSHAPEKEYS_OT_sk_item_remove(Operator):
	bl_idname = "lazy_shapekeys.sk_item_remove"
	bl_label = "Remove"
	bl_description = "Remove item"
	bl_options = {'REGISTER', 'UNDO'}

	obj_name : StringProperty()
	is_folder_remove : BoolProperty()

	@classmethod
	def poll(cls, context):
		 obj = bpy.context.active_object
		 if obj and not obj.mode == "EDIT":
			 return True


	def execute(self, context):
		old_act = bpy.context.view_layer.objects.active
		obj = get_target_obj(self.obj_name)
		if not obj.data.shape_keys:
			return{'FINISHED'}
		if not obj.data.shape_keys.key_blocks:
			return{'FINISHED'}
		sk_bl = obj.data.shape_keys.key_blocks

		if not obj == bpy.context.object:
			bpy.context.view_layer.objects.active = obj

		if self.is_folder_remove:
			props = obj.lazy_shapekeys
			folder_remove(self, obj, props.folder_colle_index)
		else:
			act_item = sk_bl[obj.active_shape_key_index]
			if is_folder(act_item):
				folder_remove(self, obj, obj.active_shape_key_index)
			else:
				bpy.ops.object.shape_key_remove()

		bpy.context.view_layer.objects.active = old_act

		return{'FINISHED'}


def folder_remove(self, obj, folder_index):
	props = obj.lazy_shapekeys
	old_index = obj.active_shape_key_index
	sk_bl = obj.data.shape_keys.key_blocks
	item = sk_bl[folder_index]
	folder_name = item.name


	folder_item_l = [(i,sk) for i,sk in enumerate(sk_bl) if is_folder(sk)]
	new_folder_index = -1
	if folder_item_l:
		new_folder_index = folder_item_l[0][1]

	for i,sk in folder_item_l:
		if props.folder_colle_index > i:
			new_folder_index = sk


	# 中身のアイテムを全て上に移動する
	inner_sk_l = get_folder_innner_sk_list(folder_index, obj.data.shape_keys)
	if not inner_sk_l:
		bpy.ops.object.shape_key_remove()
		return

	for sk_name in reversed(inner_sk_l):
		obj.active_shape_key_index = sk_bl.find(sk_name)
		bpy.ops.object.shape_key_move(type='TOP')


	# アクティブなフォルダーを削除する
	obj.active_shape_key_index = sk_bl.find(folder_name)
	bpy.ops.object.shape_key_remove()


	# インデックス設定
	if not new_folder_index == -1:
		obj.lazy_shapekeys.folder_colle_index = sk_bl.find(new_folder_index.name)


class LAZYSHAPEKEYS_OT_folder_item_duplicate(Operator):
	bl_idname = "lazy_shapekeys.item_duplicate"
	bl_label = "Duplicate Active Item"
	bl_description = "Duplicate Active Item"
	bl_options = {'REGISTER', 'UNDO'}

	obj_name : StringProperty()



	@classmethod
	def poll(cls, context):
		 obj = bpy.context.active_object
		 if obj and not obj.mode == "EDIT":
			 return True


	def execute(self, context):
		obj = get_target_obj(self.obj_name)

		colle = obj.data.shape_keys.lazy_shapekeys.folder_colle
		old_item = colle[obj.lazy_shapekeys.folder_colle_index]
		count =  str(len(colle))

		# item
		new_item = colle.add()
		for prop in dir(new_item):
			try:
				attr = getattr(old_item,prop)
				setattr(new_item, prop, attr)
			except:
				pass

		new_item.name = old_item.name + " " + count

		self.report({'INFO'}, "Duplicate")
		return{'FINISHED'}


class LAZYSHAPEKEYS_OT_folder_item_move(Operator):
	bl_idname = "lazy_shapekeys.item_move_item"
	bl_label = "Move an item in the list"
	bl_options = {'REGISTER', 'UNDO'}

	direction : EnumProperty(items=(('UP', 'Up', ""), ('DOWN', 'Down', ""),))
	is_def_list : BoolProperty()
	obj_name : StringProperty()

	@classmethod
	def poll(cls, context):
		 obj = bpy.context.active_object
		 if obj and not obj.mode == "EDIT":
			 return True


	def execute(self, context):
		old_act = bpy.context.view_layer.objects.active
		obj = get_target_obj(self.obj_name)
		sks = obj.data.shape_keys
		sk_pr = sks.lazy_shapekeys
		sk_bl = obj.data.shape_keys.key_blocks
		index = obj.active_shape_key_index
		old_index = index


		if not obj == bpy.context.object:
			bpy.context.view_layer.objects.active = obj

		if self.is_def_list:
			batch_id_list = get_sk_batch_index(sk_pr)
			old_sk_name_l = [sk_bl[i].name for i in batch_id_list]

			# 複数選択移動の場合
			if batch_id_list:
				# 下に移動する場合は、逆順処理にする
				if self.direction == "UP":
					batch_id_list = batch_id_list
				else:
					batch_id_list = reversed(batch_id_list)


				for i in batch_id_list:
					obj.active_shape_key_index = i
					bpy.ops.object.shape_key_move(type=self.direction)


				obj.active_shape_key_index = old_index
				# 移動するとインデックスがずれるので、複数選択のインデックスを新しいものに修正する
				if batch_id_list:
					batch_id_list = [i for i,sk in enumerate(sk_bl) if sk.name in old_sk_name_l]
					sks.lazy_shapekeys.multi_select_data = str(batch_id_list)



			else: # 単一アイテムの場合
				bpy.ops.object.shape_key_move(type=self.direction)


		elif is_folder(sk_bl[index]) or not self.is_def_list:
			folder_items_move(self,context, obj)


		bpy.context.view_layer.objects.active = old_act
		return{'FINISHED'}


def folder_items_move(self,context, obj):
	old_id = obj.active_shape_key_index
	if self.is_def_list:
		cll_index = obj.active_shape_key_index
	else:
		cll_index = obj.lazy_shapekeys.folder_colle_index

	sk_bl = obj.data.shape_keys.key_blocks
	tgt_folder_item = sk_bl[cll_index]
	old_def_list_item = sk_bl[old_id]

	# フォルダーアイテム
	folder_item_l = [(i,sk) for i,sk in enumerate(sk_bl) if is_folder(sk)]

	# 上の場合は、リストを逆順にする
	is_check = False
	prev_folder_item = []
	if self.direction == "UP":
		folder_item_l = reversed(folder_item_l)

	# 次の項目を登録する
	for i,sk in folder_item_l:
		if is_check:
			prev_folder_item = (i,sk)
			break

		if tgt_folder_item == sk:
			is_check = True

	if prev_folder_item:
		# 次の項目のフォルダー内のアイテムを取得
		prev_fol_inner_l = get_folder_innner_sk_list(prev_folder_item[0], obj.data.shape_keys)
		move_num = len(prev_fol_inner_l)
		# print(prev_folder_item[1],move_num)

		# 対象のフォルダー内のアイテムを取得
		fol_inner_l = [tgt_folder_item.name]
		fol_inner_l += get_folder_innner_sk_list(cll_index, obj.data.shape_keys)

		# 対象フォルダー内アイテムを、すべて移動
		if self.direction == "UP":
			num = 1
		elif self.direction == "DOWN":
			num = 1 + len(fol_inner_l) - 1


		for sk_name in fol_inner_l:
			obj.active_shape_key_index = sk_bl.find(sk_name)
			for i in range(move_num + num):
				bpy.ops.object.shape_key_move(type=self.direction)


	obj.lazy_shapekeys.folder_colle_index = sk_bl.find(tgt_folder_item.name)
	obj.active_shape_key_index = sk_bl.find(old_def_list_item.name)
