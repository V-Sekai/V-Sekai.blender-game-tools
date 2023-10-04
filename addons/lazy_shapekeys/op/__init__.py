# op
import bpy

if "bpy" in locals():
	import importlib
	reloadable_modules = [
	"op_sk_transfer",
	"op_sk_create",
	"op_sk_mod",
	"sk_utils",
	"op_sync",
	"op_other",
	"op_item",
	"op_batch",
	]
	for module in reloadable_modules:
		if module in locals():
			importlib.reload(locals()[module])


from .op_sk_transfer import *
from .op_sk_create import *
from .op_sk_mod import *
from .sk_utils import *
from .op_sync import *
from .op_other import *
from .op_item import *
from .op_batch import *

classes = (
LAZYSHAPEKEYS_OT_fcurve_drag_move,
LAZYSHAPEKEYS_OT_folder_item_add,
LAZYSHAPEKEYS_OT_folder_item_duplicate,
LAZYSHAPEKEYS_OT_folder_item_move,
LAZYSHAPEKEYS_OT_folder_move_sk,
LAZYSHAPEKEYS_OT_folder_toggle_expand,
LAZYSHAPEKEYS_OT_shape_keys_act_sk_to_folder,
LAZYSHAPEKEYS_OT_shape_keys_create_obj_from_all,
LAZYSHAPEKEYS_OT_shape_keys_separeate,
LAZYSHAPEKEYS_OT_shape_keys_sort,
LAZYSHAPEKEYS_OT_shape_keys_sync_update,
LAZYSHAPEKEYS_OT_shape_keys_transfer_forced,
LAZYSHAPEKEYS_OT_shapekeys_batch_keyframe_insert,
LAZYSHAPEKEYS_OT_shapekeys_batch_mute,
LAZYSHAPEKEYS_OT_shapekeys_batch_value_reset,
LAZYSHAPEKEYS_OT_shapekeys_one_keyframe_insert,
LAZYSHAPEKEYS_OT_shapekeys_open_window,
LAZYSHAPEKEYS_OT_sk_item_add,
LAZYSHAPEKEYS_OT_sk_item_remove,
OBJECT_OT_shape_keys_apply_modifier,
LAZYSHAPEKEYS_OT_shape_keys_apply_active_sk_to_base,
LAZYSHAPEKEYS_OT_batch_set,
LAZYSHAPEKEYS_OT_batch_select_all_index,
LAZYSHAPEKEYS_OT_batch_select_index,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	register()
