import bpy
from bpy.props import *
from bpy.types import PropertyGroup
from .utils import *


# コレクション
def update_tgt_colle(self,context):
	if not bpy.context.scene.lazy_shapekeys.tgt_colle:
		return
	bpy.ops.lazy_shapekeys.shape_keys_sync_update()


# 値
def update_sync_value(self,context):
	props = bpy.context.scene.lazy_shapekeys
	if not props.tgt_colle:
		return
	for obj in props.tgt_colle.objects:
		if obj.type in {"MESH", "CURVE", "SURFACE","LATTICE"}:
			if obj.data.shape_keys:
				if self.name in obj.data.shape_keys.key_blocks:
					obj.data.shape_keys.key_blocks[self.name].value = self.value


# ミュート
def update_sync_mute(self,context):
	props = bpy.context.scene.lazy_shapekeys
	if not props.tgt_colle:
		return
	for obj in props.tgt_colle.objects:
		if obj.type in {"MESH", "CURVE", "SURFACE","LATTICE"}:
			if obj.data.shape_keys:
				if self.name in obj.data.shape_keys.key_blocks:
					obj.data.shape_keys.key_blocks[self.name].mute = self.mute



# アクティブフォルダーの変更時
def update_obj_folder_index(self, context):
	obj = self.id_data

	if not obj:
		return
	if not obj.type in {"MESH","CURVE","SURFACE"}:
		return

	# フォルダーリストでもインデックスに参照できるように、シェイプキーの方の値に同じ値になるようにしておく
	tgt_index = obj.lazy_shapekeys.folder_colle_index
	sks = obj.data.shape_keys
	sks.lazy_shapekeys.folder_colle_sks_index = tgt_index
	colle = sks.key_blocks

	try:
		sk_l = get_folder_innner_sk_list(tgt_index, obj.data.shape_keys)
		if sk_l:
			obj.active_shape_key_index = colle.find(sk_l[0])

	except IndexError:
		obj.active_shape_key_index = len(colle) - 1


# 一括処理での値の自動更新
def update_batch_value(self, context):
	sks = self.id_data.id_data
	sk_pr = sks.lazy_shapekeys
	sk_bl = sks.key_blocks
	batch = sk_pr.batch

	select_l = get_sk_batch_index(sk_pr)
	skbl_index_l = [i for i,sk in enumerate(sk_bl)]

	for index in select_l:
		if not index in skbl_index_l:
			continue
		sk = sk_bl[index]

		# 値
		if 0 <= batch.value <=1:
			sk.value = batch.value



class LAZYSHAPEKEYS_sk_batch(PropertyGroup):
	value : FloatProperty(name="Value",description="Value of shape key at the current frame",default=-1,min=-1,max=1,update=update_batch_value)
	slider_min : FloatProperty(name="Range Min",description="Minimum for slider",min=-11,max=10,default=-11)
	slider_max : FloatProperty(name="Range Max",description="Maximum for slider",min=-11,max=10,default=-11)
	# relative_key : PointerProperty(name="Relative Key",description="Shape used as a relative key",type=bpy.types.ShapeKey)
	relative_key : StringProperty(name="Relative Key",description="Shape used as a relative key")


class LAZYSHAPEKEYS_PR_main(PropertyGroup):
	tgt_colle : PointerProperty(name="Target",type=bpy.types.Collection,update=update_tgt_colle)
	sync_colle_index : IntProperty(min=0)

	items = [
	("DEFAULT","Default","Default Shape keys list.\nBy adding a shape key for the folder, you can collapse the item with the ▼ button","SORTSIZE",0),
	("FOLDER","Folder","Displayed in two columns, [List of folders] and [Shape keys in folders].\nIf you don't see anything, add a folder","FILE_FOLDER",1),
	("SYNC","Objects Sync","Synchronize the shape keys with the same name of different objects and operate them all at once","LINK_BLEND",2),
	]
	list_mode : EnumProperty(default="DEFAULT",name="List Mode",items= items)
	drag_move_multply_value : FloatProperty(default=1,name="Movement amount with the drag movement function",description="Value multiplied by the amount of mouse movement in the drag movement function (Lazy Shapekeys add-on)",min=0.001)


class LAZYSHAPEKEYS_sync_colle(PropertyGroup):
	name : StringProperty()
	# slider_min : FloatProperty()
	# slider_max : FloatProperty()
	value : FloatProperty(name="Value",update=update_sync_value,min=0,max=1)
	mute : BoolProperty(name="Mute",update=update_sync_mute)


class LAZYSHAPEKEYS_sk_folder(PropertyGroup):
	name          : StringProperty(name="Name")
	cindex        : IntProperty(name='Index')
	sk_key : PointerProperty(type=bpy.types.Key)
	key_name_l : StringProperty(name="Name List")


class LAZYSHAPEKEYS_obj_sk_data(PropertyGroup):
	folder_colle_index : IntProperty(update=update_obj_folder_index)


class LAZYSHAPEKEYS_sk_data(PropertyGroup):
	folder_colle_sks_index : IntProperty() # フォルダーの検索フィルター用の同期インデックス。基本的に直接利用しない。
	folder_colle : CollectionProperty(type=LAZYSHAPEKEYS_sk_folder)

	items = [
	("ALL","All",""),
	("OTHER","Other",""),
	("FOLDER","Folder",""),
	]
	sk_list_mode : EnumProperty(default="ALL",name="sk_list_mode",items= items)

	multi_select_data : StringProperty()
	batch : PointerProperty(type=LAZYSHAPEKEYS_sk_batch)


class LAZYSHAPEKEYS_ui(PropertyGroup):
   sk_menu_use_slider : BoolProperty(name="Use Slider Display",default=True)
   display_folder_sk_option : BoolProperty(name="Display Folder Option",description="Display hidden shape key info when folder shape key is active (for debugging)")


   items = [
   ("DEFAULT","Default","Default Shape keys list.\nBy adding a shape key for the folder, you can collapse the item with the ▼ button","SORTSIZE",0),
   ("FOLDER","Folder","Displayed in two columns, [List of folders] and [Shape keys in folders].\nIf you don't see anything, add a folder","FILE_FOLDER",1),
   ("SYNC","Objects Sync","Synchronize the shape keys with the same name of different objects and operate them all at once","LINK_BLEND",2),
   ]
   list_mode : EnumProperty(default="DEFAULT",name="List Mode",items= items)

   folder_split : FloatProperty(name="Folder List Split Width",default=0.3,min=0.01,max=.85,step=1)
   sk_item_split : FloatProperty(name="List Item Menu Split Width",default=0.4,min=0.01,max=.85,step=1)
   batch : BoolProperty(name="Batch Processing",description="Batch processing is performed for the multi selected shape keys.\nBy clicking the shape key icon, it will be in the selected state")
