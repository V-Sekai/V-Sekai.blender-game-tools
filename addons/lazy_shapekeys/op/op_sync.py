import bpy
from bpy.props import *
from bpy.types import Operator


# 全てのシェイプキーごとにオブジェクトを生成
class LAZYSHAPEKEYS_OT_shape_keys_sync_update(Operator):
	bl_idname = "lazy_shapekeys.shape_keys_sync_update"
	bl_label = "Update Shapekeys Sync"
	bl_description = "Create a list of shape key blocks with the same name for the objects in the target collection, and create a menu that can be operated collectively.\nUseful for manipulating the same shape key that is separated into objects"
	bl_options = {'REGISTER', 'UNDO'}

	set_active_obj_value : BoolProperty(name="Set Active Object Value",default=True)

	@classmethod
	def poll(cls, context):
		props = bpy.context.scene.lazy_shapekeys
		return props.tgt_colle
	# 	if bpy.context.active_object:
	# 		obj = bpy.context.active_object
	# 		return obj.data.shape_keys


	def execute(self, context):
		props = bpy.context.scene.lazy_shapekeys
		colle = bpy.context.scene.lazy_shapekeys_colle

		# 事前に古いアイテムをすべて消す
		colle.clear()
		# for i,item in enumerate(colle):
		# 	colle.remove(i)
		if not props.tgt_colle.objects:
			self.report({'WARNING'}, "No Collection Objects")
			return{'FINISHED'}

		# 名前を取得する
		sk_name_l = []
		for obj in props.tgt_colle.objects:
			if obj.type in {"MESH", "CURVE", "SURFACE","LATTICE"}:
				if obj.data.shape_keys:
					for sk in obj.data.shape_keys.key_blocks:
						if sk.name == "Basis":
							continue
						sk_name_l += [sk.name]

		if not sk_name_l:
			self.report({'WARNING'}, "No Shapekeys")
			return{'FINISHED'}

		# アイテムを作成する
		# print(sk_name_l)
		added_l = []
		for sk_name in sk_name_l:
			if sk_name in added_l:
				continue
			if sk_name_l.count(sk_name) >= 2:
				new_item = colle.add()
				new_item.name = sk_name
				added_l += [sk_name]


		if not added_l:
			self.report({'WARNING'}, "There are no multiple shape keys with the same name")
			return{'FINISHED'}

		if self.set_active_obj_value:
			obj = bpy.context.object
			if obj:
				if obj.type in {"MESH", "CURVE", "SURFACE","LATTICE"}:
					if obj.data.shape_keys:
						for item in colle:
							if item.name in obj.data.shape_keys.key_blocks:
								item.value = obj.data.shape_keys.key_blocks[item.name].value
								item.mute = obj.data.shape_keys.key_blocks[item.name].mute

		return{'FINISHED'}
