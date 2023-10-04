import bpy
from ..utils import *
from .ui_batch import draw_batch
from .ui_misc import draw_sidebar, draw_sync
from .ui_folder import draw_folder


# シェイプキーメニューのメイン
def LAZYSHAPEKEYS_PT_shape_keys_innner(self, context, is_misc_menu, layout, tgt_obj, is_propeditor):
	sc = bpy.context.scene
	props = sc.lazy_shapekeys
	if not tgt_obj:
		tgt_obj = bpy.context.object

	if not tgt_obj.type in {"MESH", "CURVE", "SURFACE"}:
		return

	key = tgt_obj.data.shape_keys
	kb = tgt_obj.active_shape_key
	addon_prefs = preference()

	enable_edit = tgt_obj.mode != 'EDIT'
	enable_edit_value = False
	enable_pin = False

	if enable_edit or (tgt_obj.use_shape_key_edit_mode and tgt_obj.type == 'MESH'):
		enable_pin = True
		if tgt_obj.show_only_shape_key is False:
			enable_edit_value = True

	row = layout.row(align=True)
	row.prop(addon_prefs.ui,"list_mode",expand=True)

	if addon_prefs.ui.list_mode == "FOLDER":
		draw_folder(self, context, layout, tgt_obj, is_misc_menu)

	elif addon_prefs.ui.list_mode == "SYNC":
		draw_sync(self, context ,layout, is_misc_menu)

	else:
		rows_num = 3
		if kb:
			rows_num = 6

		row = layout.row()
		if is_misc_menu:
			misc_menu_prefs = bpy.context.preferences.addons['misc_menu'].preferences
			list_rows = misc_menu_prefs.folder_sk_rows
			if kb:
				rows_num = list_rows

			row.template_list("LAZYSHAPEKEYS_UL_replace_menu_misc_menu", "", key, "key_blocks", tgt_obj, "active_shape_key_index", rows=rows_num)
		else:
			row.template_list("LAZYSHAPEKEYS_UL_replace_menu", "", key, "key_blocks", tgt_obj, "active_shape_key_index", rows=rows_num)

		col = row.column(align=True)

		draw_sidebar(self, context, col, tgt_obj,False, is_misc_menu)



	if kb and not is_misc_menu:

		split = layout.split(factor=0.4)
		row = split.row()
		row.enabled = enable_edit
		row.prop(key, "use_relative")

		row = split.row()
		row.alignment = 'RIGHT'

		sub = row.row(align=True)
		sub.label()  # XXX, for alignment only
		subsub = sub.row(align=True)
		subsub.active = enable_pin
		subsub.prop(tgt_obj, "show_only_shape_key", text="")
		sub.prop(tgt_obj, "use_shape_key_edit_mode", text="")

		sub = row.row()
		if key.use_relative:
			sub.operator("object.shape_key_clear", icon='X', text="")
		else:
			sub.operator("object.shape_key_retime", icon='RECOVER_LAST', text="")


		if not is_folder(kb) or addon_prefs.ui.display_folder_sk_option:
			if key.use_relative:
				if tgt_obj.active_shape_key_index != 0:
					row = layout.row()
					row.active = enable_edit_value
					row.prop(kb, "value")

					col = layout.column()
					sub.active = enable_edit_value
					sub = col.column(align=True)
					sub.prop(kb, "slider_min", text="Range Min")
					sub.prop(kb, "slider_max", text="Max")

					col.prop_search(kb, "vertex_group", tgt_obj, "vertex_groups", text="Vertex Group")
					col.prop_search(kb, "relative_key", key, "key_blocks", text="Relative To")

			else:
				layout.prop(kb, "interpolation")
				row = layout.column()
				row.active = enable_edit_value
				row.prop(key, "eval_time")


	if not is_propeditor:
		if bpy.context.mode == "EDIT_MESH":
			if tgt_obj.data.shape_keys:
				layout.separator()
				layout.operator("mesh.blend_from_shape",icon="AUTOMERGE_ON")
				layout.operator("mesh.shape_propagate_to_all",icon="INDIRECT_ONLY_ON")
			# layout.operator("lazy_shapekeys.shape_keys_separeate",icon="MOD_MIRROR")



	draw_batch(self,layout,tgt_obj)
