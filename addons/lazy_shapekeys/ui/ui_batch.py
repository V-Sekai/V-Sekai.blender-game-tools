import bpy
from ..utils import *


# 一括処理
def draw_batch(self,layout,tgt_obj):
	sc = bpy.context.scene
	props = sc.lazy_shapekeys
	kb = tgt_obj.active_shape_key
	key = tgt_obj.data.shape_keys
	if not key: return
	sk_pr = key.lazy_shapekeys
	batch = sk_pr.batch
	sk_bl = key.key_blocks

	addon_prefs = preference()

	# 復数選択の数
	tgt_item_num = 0
	select_l = get_sk_batch_index(sk_pr)
	if select_l:
		tgt_item_num = len(select_l)


	layout.separator()
	row = layout.row(align=True)
	rows = row.row(align=True)
	rows.alignment="LEFT"
	rows.prop(addon_prefs.ui,"batch",icon="TRIA_DOWN" if addon_prefs.ui.batch else "TRIA_RIGHT", emboss=False)

	rows = row.row(align=True)
	rows.alignment="RIGHT"
	op = rows.operator("lazy_shapekeys.batch_select_all_index",text="",icon="CHECKBOX_HLT")
	op.type = "SELECT"
	op.obj_name = tgt_obj.name
	row_deselect = rows.row(align=True)
	row_deselect.active = bool(select_l)
	op = row_deselect.operator("lazy_shapekeys.batch_select_all_index",text="",icon="CHECKBOX_DEHLT")
	op.type = "DESELECT"
	op.obj_name = tgt_obj.name


	rows.separator()
	row_value = rows.row(align=True)
	row_value.ui_units_x = 5
	row_value.active = bool(0 <= batch.value <=1)
	row_value.active = bool(select_l)
	row_value.prop(batch,"value")
	rows.separator()
	row_misc = rows.row(align=True)
	row_misc.active = bool(select_l)

	op = row_misc.operator("lazy_shapekeys.shapekeys_batch_keyframe_insert",text="",icon="REC")
	op.obj_name=tgt_obj.name
	op.is_batch=True
	op = row_misc.operator("lazy_shapekeys.shapekeys_batch_value_reset",text="",icon="X")
	op.obj_name=tgt_obj.name
	op.is_batch=True



	row_num = rows.row(align=True)
	row_num.ui_units_x = 2
	row_num.active=False
	row_num.alignment="RIGHT"
	row_num.label(text=str(tgt_item_num))



	if not addon_prefs.ui.batch:
		return

	if not tgt_obj.data.shape_keys:
		return


	box = layout.box()
	box.active = bool(select_l)


	row = box.row()
	# row_sel = row.row(align=True)
	# op = row_sel.operator("lazy_shapekeys.batch_select_all_index",text="",icon="CHECKBOX_HLT")
	# op.type = "SELECT"
	# row_deselect = row_sel.row(align=True)
	# row_deselect.active = bool(select_l)
	# op = row_deselect.operator("lazy_shapekeys.batch_select_all_index",text="",icon="CHECKBOX_DEHLT")
	# op.type = "DESELECT"
	op = row.operator("lazy_shapekeys.batch_set",icon="PLAY")
	op.obj_name = tgt_obj.name

	# op = row.operator("lazy_shapekeys.shapekeys_batch_keyframe_insert",text="",icon="REC")
	# op.obj_name=tgt_obj.name
	# op.is_batch=True
	# op = row.operator("lazy_shapekeys.shapekeys_batch_value_reset",text="",icon="X")
	# op.obj_name=tgt_obj.name
	# op.is_batch=True


	col = box.column()
	col.use_property_split = True
	col.use_property_decorate = False

	row = col.row(align=True)
	row.active = bool(0 <= batch.value <=1)
	row.prop(batch,"value")

	row = col.row(align=True)
	row.active = bool(not batch.slider_min == -11)
	row.prop(batch,"slider_min")

	row = col.row(align=True)
	row.active = bool(not batch.slider_max == -11)
	row.prop(batch,"slider_max",text="Max")

	row = col.row(align=True)
	row.active = bool(batch.relative_key)
	row.prop_search(batch,"relative_key", key, "key_blocks",text="Relative To")



	row = col.row(align=True)
	rows = row.row(align=True)
	rows.ui_units_x = .7
	row.active=False
	rows.label(text=str(tgt_item_num))

	skbl_index_l = [i for i,sk in enumerate(sk_bl)]
	tgt_name_l = [sk_bl[i].name for i in select_l if i in skbl_index_l]
	row.label(text=str(tgt_name_l),icon="NONE")
	# col.prop(key.lazy_shapekeys,"multi_select_data")
