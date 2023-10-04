'''
Lazy Shapekeys Addon (C) 2021-2023 Bookyakuno
Created by Bookyakuno
License : GNU General Public License version3 (http://www.gnu.org/licenses/)
'''

bl_info = {
	"name" : "Lazy Shapekeys",
	"author" : "Bookyakuno",
	"version" : (1, 0, 56),
	"blender" : (3, 6, 0),
	"location" : "3D View",
	"description" : "Shapekeys Utility. Transfer Shape(Forced) / Create Objects for All Shape Keys.",
	"warning" : "",
	"wiki_url" : "",
	"tracker_url" : "",
	"category" : "UI"
}


if "bpy" in locals():
	import importlib
	reloadable_modules = [
	"op",
	"ui",
	"utils",
	"props",

	]
	for module in reloadable_modules:
		if module in locals():
			importlib.reload(locals()[module])

from . import (
op,
ui,
utils,
props,
)
from .ui.ui_core import LAZYSHAPEKEYS_PT_shape_keys_innner
from .ui.ui_panel import LAZYSHAPEKEYS_PT_main
from .utils import *
from .props import *
from .props import LAZYSHAPEKEYS_ui
from .ui.ui_menu import draw_replace_other_menu

import bpy
import rna_keymap_ui # キーマップリストに必要
from bpy.props import *
from bpy.types import AddonPreferences, UIList


keep_DATA_PT_shape_keys = bpy.types.DATA_PT_shape_keys.draw


def LAZYSHAPEKEYS_PT_shape_keys(self, context):
	layout = self.layout
	LAZYSHAPEKEYS_PT_shape_keys_innner(self, context, False, layout, None, True)


# シェイプキーパネルメニュー内を、フォルダーメニューに置き換える
lmda = lambda s,c:s.layout;None
def update_use_folder(self,context):
	addon_prefs = preference()

	if addon_prefs.use_folder:
		bpy.types.DATA_PT_shape_keys.draw = lmda
		bpy.types.DATA_PT_shape_keys.prepend(LAZYSHAPEKEYS_PT_shape_keys)
	else:
		bpy.types.DATA_PT_shape_keys.draw = keep_DATA_PT_shape_keys
		bpy.types.DATA_PT_shape_keys.remove(LAZYSHAPEKEYS_PT_shape_keys)


def update_panel(self, context):
	message = ": Updating Panel locations has failed"
	try:
		cate = context.preferences.addons[__name__.partition('.')[0]].preferences.category
		if cate:
			for panel in panels:
				if "bl_rna" in panel.__dict__:
					bpy.utils.unregister_class(panel)

			for panel in panels:
				panel.bl_category = cate
				bpy.utils.register_class(panel)

		else:
			for panel in panels:
				if "bl_rna" in panel.__dict__:
					bpy.utils.unregister_class(panel)

	except Exception as e:
		print("\n[{}]\n{}\n\nError:\n{}".format(__name__, message, e))
	pass



class LAZYSHAPEKEYS_MT_AddonPreferences(AddonPreferences):
	bl_idname = __name__
	category : StringProperty(name="Tab Category", description="Choose a name for the category of the panel", default="Addons", update=update_panel)
	tab_addon_menu : EnumProperty(name="Tab", description="", items=[('OPTION', "Option", "","DOT",0),
	 ('LINK', "Link", "","URL",1)], default='OPTION')
	use_folder : BoolProperty(name="Use Folder in List Menu",description="Make the shape key block with '@' at the beginning of the name line into a folder.\nAdd a step to the shape key list menu to make it easier to classify",update=update_use_folder,default=True)


	ui : PointerProperty(type=LAZYSHAPEKEYS_ui)
	debug : BoolProperty(name="Debug",default=True)


	def draw(self, context):
		layout = self.layout
		row = layout.row(align=True)
		row.prop(self,"tab_addon_menu",expand=True)

		if self.tab_addon_menu == "OPTION":
			layout.prop(self,"category")
			layout.prop(self,"use_folder")

			if self.use_folder:
				box = layout.box()
				box.prop(self.ui,"sk_menu_use_slider")

				box.prop(self.ui,"display_folder_sk_option")



			layout.separator()
			layout.prop(self,"debug")


		elif self.tab_addon_menu == "LINK":
			row = layout.row()
			row.label(text="Link:")
			row.operator( "wm.url_open", text="gumroad", icon="URL").url = "https://gum.co/VLdwV"


def draw_drag_move_in_graph_editor(self,context):
	layout = self.layout
	sc = bpy.context.scene
	props = sc.lazy_shapekeys
	layout.separator()
	layout.prop(props,"drag_move_multply_value")



panels = (
LAZYSHAPEKEYS_PT_main,
)

classes = (
LAZYSHAPEKEYS_sk_batch,
LAZYSHAPEKEYS_PR_main,
LAZYSHAPEKEYS_sync_colle,
LAZYSHAPEKEYS_sk_folder,
LAZYSHAPEKEYS_sk_data,
LAZYSHAPEKEYS_obj_sk_data,
LAZYSHAPEKEYS_ui,


LAZYSHAPEKEYS_MT_AddonPreferences,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)


	op.register()
	ui.register()
	update_panel(None, bpy.context)

	bpy.types.Scene.lazy_shapekeys = PointerProperty(type=LAZYSHAPEKEYS_PR_main)
	bpy.types.Key.lazy_shapekeys = PointerProperty(type=LAZYSHAPEKEYS_sk_data)
	bpy.types.Object.lazy_shapekeys = PointerProperty(type=LAZYSHAPEKEYS_obj_sk_data)
	bpy.types.Scene.lazy_shapekeys_colle = CollectionProperty(type=LAZYSHAPEKEYS_sync_colle)
	bpy.types.MESH_MT_shape_key_context_menu.append(draw_replace_other_menu)
	# bpy.types.GRAPH_MT_key.append(draw_drag_move_in_graph_editor)
	bpy.types.ShapeKey.lazy_shapekeys = PointerProperty(type=LAZYSHAPEKEYS_sk_folder)
	update_use_folder(None,bpy.context)

	try:
		bpy.app.translations.register(__name__, GetTranslationDict())
	except Exception as e: print(e)




def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)


	op.unregister()
	ui.unregister()

	bpy.types.DATA_PT_shape_keys.draw = keep_DATA_PT_shape_keys
	bpy.types.DATA_PT_shape_keys.remove(LAZYSHAPEKEYS_PT_shape_keys)
	# bpy.types.GRAPH_MT_key.remove(draw_drag_move_in_graph_editor)
	bpy.types.MESH_MT_shape_key_context_menu.remove(draw_replace_other_menu)


	try:
		bpy.app.translations.unregister(__name__)
	except Exception as e: print(e)


	del bpy.types.Scene.lazy_shapekeys
	del bpy.types.Key.lazy_shapekeys
	del bpy.types.Object.lazy_shapekeys
	del bpy.types.Scene.lazy_shapekeys_colle


if __name__ == "__main__":
	register()
