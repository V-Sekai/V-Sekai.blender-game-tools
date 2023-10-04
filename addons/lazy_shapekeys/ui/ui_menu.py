import bpy
from ..utils import *


def draw_replace_other_menu(self,context):
	layout = self.layout
	addon_prefs = preference()

	layout.separator()
	layout.operator("lazy_shapekeys.shape_keys_transfer_forced",icon="MOD_DATA_TRANSFER")
	layout.operator("lazy_shapekeys.shape_keys_create_obj_from_all",icon="DUPLICATE")
	if bpy.app.version >= (2,83,0):
		icon_val = "CHECKMARK"
	else:
		icon_val = "NONE"
	layout.operator("lazy_shapekeys.shape_keys_apply_modifier",icon=icon_val)
	layout.operator("lazy_shapekeys.shape_keys_sort",icon="SORTALPHA")
	layout.operator("lazy_shapekeys.shape_keys_separeate",icon="MOD_MIRROR")
	# layout.operator("lazy_shapekeys.shape_keys_apply_active_sk_to_base",icon="DOT")
