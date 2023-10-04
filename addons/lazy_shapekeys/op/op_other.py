import bpy, re, bmesh
from bpy.props import *
from bpy.types import Operator
from ..utils import *


class LAZYSHAPEKEYS_OT_shapekeys_open_window(Operator):
	bl_idname = "lazy_shapekeys.shapekeys_open_window"
	bl_label = "Open Shapekey FCurve in New Graph Editor"
	bl_description = ""
	bl_options = {'REGISTER', 'UNDO'}

	sk_name : StringProperty(name="Name")

	def invoke(self, context, event):
		if not self.get_tgt_window():
			bpy.ops.screen.area_dupli("INVOKE_DEFAULT")

		return self.execute(context)

	def get_tgt_window(self):
		for win in bpy.context.window_manager.windows:
			if len(win.screen.areas) == 1:
				if win.screen.areas[0].type == "GRAPH_EDITOR" and win.screen.areas[0].ui_type == "FCURVES":
					return win

		return None

	def execute(self, context):
		is_tgt_win = self.get_tgt_window()
		if is_tgt_win:
			win = is_tgt_win
		else:
			win = bpy.context.window

		for ar in win.screen.areas:
			ar.type = 'GRAPH_EDITOR'
			ar.ui_type = 'FCURVES' # ドライバーなら'DRIVERS'

			ar.spaces.active.dopesheet.show_only_selected = False
			ar.spaces.active.dopesheet.filter_text = "(%s)" % self.sk_name


		return {'FINISHED'}


class LAZYSHAPEKEYS_OT_shapekeys_one_keyframe_insert(Operator):
	bl_idname = "lazy_shapekeys.shapekeys_one_keyframe_insert"
	bl_label = "Keyframe Insert"
	bl_description = ""
	bl_options = {'REGISTER', 'UNDO'}

	sk_name : StringProperty()
	obj_name : StringProperty()
	is_def_listmenu : BoolProperty()
	index : IntProperty()

	def execute(self, context):
		sc = bpy.context.scene
		obj = get_target_obj(self.obj_name)

		sks = obj.data.shape_keys
		props = obj.lazy_shapekeys
		sk_bl = obj.data.shape_keys.key_blocks
		if self.is_def_listmenu:
			folder_index = self.index
		else:
			folder_index = props.folder_colle_index
		item = sk_bl[folder_index]

		name_l = [self.sk_name]

		use_cur_key_l, is_remove = check_use_keyframe(sks, name_l)



		for sk_name in name_l:
			sk = sk_bl[sk_name]
			if sk.name == "Basis":
				continue
			if is_remove:
				sk.keyframe_delete(data_path = "value")
			else:
				sk.keyframe_insert(data_path = "value")

		for ar in bpy.context.screen.areas:
			ar.tag_redraw()
		return {'FINISHED'}


class LAZYSHAPEKEYS_OT_shapekeys_batch_keyframe_insert(Operator):
	bl_idname = "lazy_shapekeys.shapekeys_batch_keyframe_insert"
	bl_label = "Batch Keyframe Insert"
	bl_description = "Insert keyframes into all shape keys in the folder at once.\nIf all the shape keys in the folder are keyframed in the current frame, delete all the keys in the current frame"
	bl_options = {'REGISTER', 'UNDO'}

	obj_name : StringProperty()
	is_def_listmenu : BoolProperty()
	index : IntProperty()
	is_batch : BoolProperty()


	def execute(self, context):
		sc = bpy.context.scene
		obj = get_target_obj(self.obj_name)

		sks = obj.data.shape_keys
		sk_pr = sks.lazy_shapekeys
		props = obj.lazy_shapekeys
		sk_bl = obj.data.shape_keys.key_blocks
		if self.is_def_listmenu:
			folder_index = self.index
		else:
			folder_index = props.folder_colle_index
		item = sk_bl[folder_index]
		folder_innner_l = get_folder_innner_sk_list(folder_index, obj.data.shape_keys)

		name_l = [sk.name for sk in sks.key_blocks if not sk.name == "Basis" and sk.name in folder_innner_l]

		if self.is_batch:
			tgt_index_l = get_sk_batch_index(sk_pr)
			name_l = [sk.name for i,sk in enumerate(sk_bl) if i in tgt_index_l]


		use_cur_key_l, is_remove = check_use_keyframe(sks, name_l)

		for i,sk in enumerate(sk_bl):
			if sk.name == "Basis":
				continue
			if self.is_batch:
				if not i in tgt_index_l:
					continue
			else:
				if not sk.name in folder_innner_l:
					continue


			if is_remove:
				sk.keyframe_delete(data_path = "value")
			else:
				sk.keyframe_insert(data_path = "value")


		for ar in bpy.context.screen.areas:
			ar.tag_redraw()
		return {'FINISHED'}


class LAZYSHAPEKEYS_OT_shapekeys_batch_mute(Operator):
	bl_idname = "lazy_shapekeys.shapekeys_batch_mute"
	bl_label = "Batch Mute"
	bl_description = ""
	bl_options = {'REGISTER', 'UNDO'}

	sks_name : StringProperty()
	index : IntProperty()


	def execute(self, context):
		sc = bpy.context.scene
		sks = bpy.data.shape_keys[self.sks_name]
		props = sks.lazy_shapekeys
		sk_bl = sks.key_blocks
		folder_index = self.index

		item = sk_bl[folder_index]
		dic = convert_mini_text_to_dic(item.vertex_group)

		folder_innner_l = get_folder_innner_sk_list(folder_index, sks)

		if dic["mute"] == 1:
			dic["mute"] = 0
		else:
			dic["mute"] = 1

		for sk in sks.key_blocks:
			if not sk.name == "Basis" and sk.name in folder_innner_l:
				sk.mute = dic["mute"]


		item.vertex_group = convert_dic_to_mini_text(dic)

		return {'FINISHED'}


class LAZYSHAPEKEYS_OT_shapekeys_batch_value_reset(Operator):
	bl_idname = "lazy_shapekeys.shapekeys_batch_value_reset"
	bl_label = "Batch Reset Value"
	bl_description = "Resets the values of the items in the shape key folder at once"
	bl_options = {'REGISTER', 'UNDO'}

	obj_name : StringProperty()
	is_batch : BoolProperty()

	def execute(self, context):
		sc = bpy.context.scene
		obj = get_target_obj(self.obj_name)
		sks = obj.data.shape_keys
		sk_pr = sks.lazy_shapekeys
		props = obj.lazy_shapekeys
		sk_bl = obj.data.shape_keys.key_blocks
		folder_index = props.folder_colle_index
		item = sk_bl[folder_index]
		folder_innner_l = get_folder_innner_sk_list(folder_index, obj.data.shape_keys)

		for i, sk in enumerate(sks.key_blocks):
			if self.is_batch:
				if i in get_sk_batch_index(sk_pr):
					sk.value = 0
			else:
				if not sk.name == "Basis" and sk.name in folder_innner_l:
					sk.value = 0

		return {'FINISHED'}


class LAZYSHAPEKEYS_OT_shape_keys_sort(Operator):
	bl_idname = "lazy_shapekeys.shape_keys_sort"
	bl_label = "Sort by Name"
	bl_description = ""
	bl_options = {'REGISTER', 'UNDO'}

	reversed : IntProperty(name="Reversed")

	def execute(self, context):
		# 元オブジェクトをアクティブ選択
		obj = bpy.context.object
		sk_bl = obj.data.shape_keys.key_blocks
		old_index = obj.active_shape_key_index

		ky_name_l = []
		for sk in sk_bl:
			ky_name_l += [sk.name]

		ky_name_l.sort(key=str.casefold, reverse = self.reversed)
		print(ky_name_l)
		# このようなリストができる
		# ky_name_l = ['Basis', 'あ', 'い', 'う', 'え', 'お', '□', '□1', '□2', 'ω', 'にやり', 'にやり２', 'ぺろっ', 'てへぺろ', '口角上げ', '口角下げ', '口横広げ', '口横缩·げ', '真面目', '困る', 'にこり', '眉上', '上', '下', '前', 'ウィンク', 'ウィンク右', 'ウィンク２', 'ｳｨﾝｸ２右', 'なごみ1', 'びっくり', 'じと目', 'じと目1', 'じと目2', 'ｷﾘｯ', 'なごみ', 'はちゅ目', 'はぅ', '眼角上', '眼角下', '眼睑上', '瞳小', '恐ろしい子！', '照れ',]
		# add_new_l = ky_name_l

		# 並び替え
		for name in ky_name_l:
			obj.active_shape_key_index  = sk_bl.find(name)
			bpy.ops.object.shape_key_move(type='BOTTOM')

		# Basisを一番上に移動
		if "Basis" in sk_bl:
			obj.active_shape_key_index  = sk_bl.find("Basis")
			bpy.ops.object.shape_key_move(type="TOP")

		obj.active_shape_key_index = old_index

		return {'FINISHED'}


class LAZYSHAPEKEYS_OT_fcurve_drag_move(Operator):
	bl_idname = "lazy_shapekeys.fcurve_drag_move"
	bl_label = "Drag Move of Fcurve Keyframe"
	bl_description = ""
	bl_options = {'REGISTER', 'UNDO'}

	items = [
	("ctrl","ctrl",""),
	("shift","shift",""),
	("alt","alt",""),
	]
	modify_key_type : EnumProperty(default="ctrl",name="Modify Key Type",items= items)


	def invoke(self, context, event):
		self.orig_x = event.mouse_region_x

		# self.old_ky_co = [(
		# 		ky,
		# 		ky.co,
		# 		(ky.handle_left.x, ky.handle_left.y),
		# 		(ky.handle_right.x, ky.handle_right.y)
		# 		)
		# 	for ky in bpy.context.selected_editable_keyframes
		# 	]
		self.main_event_type = event.type


		wm = bpy.context.window_manager
		self._timer = wm.event_timer_add(0.5, window=bpy.context.window)
		wm.modal_handler_add(self)
		return {"RUNNING_MODAL"} # モーダルへ


	def modal(self, context, event):
		sc = bpy.context.scene
		props = sc.lazy_shapekeys


		if event.type == 'MOUSEMOVE':
			mouse_move = event.mouse_region_x - self.orig_x
			# print(mouse_move)
			# if (event.mouse_region_x - self.orig_x / 5):
			# 	return {'RUNNING_MODAL'}
			if getattr(event, self.modify_key_type): # X 移動
				# if event.ctrl:
				if mouse_move < 0:
					num = (-1 * props.drag_move_multply_value,0,0)
				else:
					num = (1 * props.drag_move_multply_value,0,0)
			else: # Y 移動
				if mouse_move < 0:
					num = (0,-0.01 * props.drag_move_multply_value,0)
				else:
					num = (0,0.01 * props.drag_move_multply_value,0)

			bpy.ops.transform.translate(value=num)


			# return {'RUNNING_MODAL'}

			# add_num = ((event.mouse_region_x - self.orig_x) * 0.005)
			#
			# if event.ctrl:
			# 	val = (add_num * 2, 0, 0)
			# 	axis = 0
			# 	axis_text = "X"
			# else:
			# 	val = (0, add_num  * 0.1, 0)
			# 	axis = 1
			# 	axis_text = "Y"
			#
			#
			# # for ky, old_co, hand_l_co, hand_r_co in self.old_ky_co:
			# # 	ky.co[axis] = old_co[axis]
			# # 	ky.handle_left.x = hand_l_co[axis]
			# # 	ky.handle_right.x = hand_r_co[axis]
			#
			#
			# # for ky, old_co, hand_l_co, hand_r_co in self.old_ky_co:
			# # 	ky.co[axis] = old_co[axis] + add_num
			# # 	ky.handle_left.x = hand_l_co[axis] + add_num
			# # 	ky.handle_right.x = hand_r_co[axis] + add_num
			#
			#
			# print(self.orig_x,  event.mouse_region_x,val)
			#
			# bpy.ops.transform.translate(value=val)

			return {'RUNNING_MODAL'}

		if event.type == self.main_event_type and event.value == 'RELEASE':
			return{'FINISHED'}

		return {'RUNNING_MODAL'}


class LAZYSHAPEKEYS_OT_shape_keys_act_sk_to_folder(Operator):
	bl_idname = "lazy_shapekeys.shape_keys_act_sk_to_folder"
	bl_label = "Change Active Shapekey to Folder"
	bl_description = "Change the active shape key to be treated as a folder shape key.\nAdds a string recognized for folders to vertex group options"
	bl_options = {'REGISTER', 'UNDO'}

	to_folder : BoolProperty("To Folder",default=True)

	@classmethod
	def poll(cls, context):
		return bpy.context.object and bpy.context.object.type == "MESH"


	def execute(self, context):
		obj = bpy.context.active_object
		kb = obj.data.shape_keys.key_blocks
		id = obj.active_shape_key_index
		if self.to_folder:
			kb[id].vertex_group = "folder:1,exp:1,mute:0"
		else:
			kb[id].vertex_group = ""

		return{'FINISHED'}

class LAZYSHAPEKEYS_OT_shape_keys_apply_active_sk_to_base(Operator):
	bl_idname = "lazy_shapekeys.shape_keys_apply_active_sk_to_base"
	bl_label = "shape_keys_apply_active_sk_to_base"
	bl_description = ""
	bl_options = {'REGISTER', 'UNDO'}

	tgt_sk_name : StringProperty(default="Adjust")

	@classmethod
	def poll(cls, context):
		return bpy.context.object and bpy.context.object.type == "MESH"


	def execute(self, context):
		obj = bpy.context.active_object
		kb = obj.data.shape_keys.key_blocks
		old_id = obj.active_shape_key_index

		for i,sk in enumerate(kb):
			if i == 0: continue
			if sk.name == self.tgt_sk_name: continue

			obj.active_shape_key_index = i

			bpy.ops.mesh.blend_from_shape(shape=self.tgt_sk_name, blend=1.0, add=True)

		return{'FINISHED'}


class LAZYSHAPEKEYS_OT_shape_keys_separeate(Operator):
	bl_idname = "lazy_shapekeys.shape_keys_separeate"
	bl_label = "Separate shape keys L/R"
	bl_description = ""
	bl_options = {'REGISTER', 'UNDO'}

	items = [
		("x", "X Axis", "", 1),
		("y", "Y Axis", "", 2),
		("z", "Z Axis", "", 3),
		]
	axis : EnumProperty(items=items, name="Axis")
	items = [
		("-1", "Negative", "","REMOVE", 1),
		("1", "Positive", "","ADD", 2),
		]
	offset : FloatProperty(name="Offset", default=0, step=10, precision=3)
	threshold : FloatProperty(name="Threshold", default=0.0000001, step=0.1, precision=10)

	@classmethod
	def poll(cls, context):
		return bpy.context.object and bpy.context.object.type == "MESH"

	def draw(self, context):
		layout = self.layout
		row = layout.row(align=True)
		row.prop(self,"axis",expand=True)
		layout.separator()
		layout.prop(self,"offset")
		layout.prop(self,"threshold")


	def execute(self, context):
		obj = bpy.context.active_object
		kb = obj.data.shape_keys.key_blocks
		old_index = obj.active_shape_key_index
		old_item = obj.active_shape_key
		old_mode = bpy.context.object.mode
		bpy.ops.object.mode_set(mode="OBJECT")


		# half R
		bpy.ops.object.shape_key_add(from_mix=False)
		obj.active_shape_key.name = old_item.name + ".R"
		item_R = obj.active_shape_key
		R_index = obj.active_shape_key_index

		# half L
		bpy.ops.object.shape_key_add(from_mix=False)
		obj.active_shape_key.name = old_item.name + ".L"
		item_L = obj.active_shape_key
		L_index = obj.active_shape_key_index


		bpy.ops.object.mode_set(mode="EDIT")
		old_sel_vert_l = [vert for vert in obj.data.vertices if vert.select]
		sel_mode = bpy.context.tool_settings.mesh_select_mode[:]
		bpy.context.tool_settings.mesh_select_mode = [True, False, False]


		# half Select R
		bpy.ops.mesh.select_all(action="DESELECT")
		self.select_half(obj,1)
		bpy.ops.mesh.select_all(action='INVERT')
		obj.active_shape_key_index = R_index
		bpy.ops.mesh.blend_from_shape(shape=old_item.name, blend=1.0, add=False)


		self.select_center(obj, old_item.name, R_index)


		# half Select L
		bpy.ops.mesh.select_all(action="DESELECT")
		self.select_half(obj,-1)
		bpy.ops.mesh.select_all(action='INVERT')
		obj.active_shape_key_index = L_index
		bpy.ops.mesh.blend_from_shape(shape=old_item.name, blend=1.0, add=False)


		self.select_center(obj,old_item.name, L_index)


		bpy.context.tool_settings.mesh_select_mode = sel_mode
		bpy.ops.object.mode_set(mode="OBJECT")


		old_item.value = 0
		item_R.value = 1
		item_L.value = 1


		# restore
		for vert in obj.data.vertices:
			vert.select = False
		for vert in old_sel_vert_l:
			vert.select = True

		old_index = obj.active_shape_key_index
		bpy.ops.object.mode_set(mode=old_mode)

		return {'FINISHED'}


	def select_center(self, obj, base_item_name, index):
		bpy.ops.mesh.select_all(action="DESELECT")
		bpy.ops.object.mode_set(mode="OBJECT")
		for vert in obj.data.vertices:
			co = getattr(vert.co,self.axis)
			if self.threshold >= abs(co) >= 0:
				vert.select = True

		bpy.ops.object.mode_set(mode="EDIT")
		obj.active_shape_key_index = index

		try:
			bpy.ops.mesh.blend_from_shape(shape=base_item_name, blend=0.5, add=False)
		except  RuntimeError: pass

	def select_half(self,obj,direction):
		bpy.ops.object.mode_set(mode="OBJECT")
		for vert in obj.data.vertices:
			co = getattr(vert.co,self.axis)
			direct = direction
			if (self.offset * direct <= co * direct + self.threshold):
				vert.select = True

		bpy.ops.object.mode_set(mode="EDIT")
