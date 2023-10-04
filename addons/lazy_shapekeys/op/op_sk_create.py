import bpy
from bpy.props import *
from bpy.types import Operator
from .sk_utils import *


# 全てのシェイプキーごとにオブジェクトを生成
class LAZYSHAPEKEYS_OT_shape_keys_create_obj_from_all(Operator):
	bl_idname = "lazy_shapekeys.shape_keys_create_obj_from_all"
	bl_label = "Create Objects for All Shape Keys"
	bl_description = "Create a new object of that shape for each shape key.\nIt is convenient to display all shape keys in a list, or to make them into separate objects, edit them individually, and then combine them as shape keys again"
	bl_options = {'REGISTER', 'UNDO'}

	use_translate : BoolProperty(name="Use Translate",default=True)
	translate_x : FloatProperty(name="X",default=3)
	translate_z : FloatProperty(name="Z",default=0)
	translate_z_column : IntProperty(name="Number to column",default=10,min=1)
	new_obj_name : StringProperty(name="New Object Name",description="{obj_name} is replaced with the source object name and {sk_name} is replaced with the shape key name")

	@classmethod
	def poll(cls, context):
		if bpy.context.active_object:
			obj = bpy.context.active_object
			if obj.type == "MESH":
				return obj.data.shape_keys

	def invoke(self, context,event):
		dpi_value = bpy.context.preferences.system.dpi

		return context.window_manager.invoke_props_dialog(self, width=dpi_value*3)


	def draw(self, context):
		layout = self.layout
		layout.prop(self,"use_translate")
		if self.use_translate:
			layout.prop(self,"translate_x")

			col = layout.column(align=True)
			col.active = bool(not self.translate_z == 0)
			col.prop(self,"translate_z")
			col.prop(self,"translate_z_column")
		layout.separator()
		layout.prop(self,"new_obj_name")


	def execute(self, context):
		act_obj = bpy.context.object
		old_act = act_obj

		# 選択を無効化
		for obj in bpy.context.selected_objects:
			obj.select_set(False)

		new_obj_l = []

		z_value = 0
		x_trans_count = 1
		finished_l = []
		for i,sk in enumerate(act_obj.data.shape_keys.key_blocks):
			if i == 0:
				continue
			new_obj_l, z_value, x_trans_count, finished_l = create_new_shape_key_obj(self, i, old_act, new_obj_l, z_value, x_trans_count, finished_l)


		for obj in new_obj_l:
			obj.select_set(True)

		bpy.context.view_layer.objects.active = obj

		self.report({'INFO'}, "Create Objects [%s]" % len(finished_l))
		return{'FINISHED'}


def create_new_shape_key_obj(self, i, old_act, new_obj_l, z_value, x_trans_count, finished_l):
	if not self.translate_z == 0:
		if (i -1) % self.translate_z_column == 0:
			z_value += self.translate_z
			x_trans = -self.translate_x * self.translate_z
			x_trans_count = 0

	bpy.context.view_layer.objects.active = old_act
	old_act.select_set(True)

	# 複製
	bpy.ops.object.duplicate_move()

	# 新規オブジェクト設定
	if self.use_translate:
		bpy.ops.transform.translate(value=(self.translate_x*x_trans_count, 0, z_value),constraint_axis=(True, False, False),)
		x_trans_count += 1

	new_obj = bpy.context.selected_objects[0]
	new_obj_l += [new_obj]
	tgt_new_skeys = new_obj.data.shape_keys
	for i_temp,temp_sk in enumerate(tgt_new_skeys.key_blocks):
		temp_sk.value = 0

	tgt_sk = tgt_new_skeys.key_blocks[i]
	if self.new_obj_name:
		nw_obj_name = self.new_obj_name.replace("{obj_name}",act_obj.name).replace("{sk_name}",tgt_sk.name)
	else:
		nw_obj_name = tgt_sk.name
	new_obj.name = nw_obj_name
	tgt_sk.value = 1
	tgt_sk.mute = False
	set_parent_key_value(tgt_new_skeys.key_blocks,tgt_sk)
	mute_shapekey_driver(tgt_new_skeys)

	new_obj.shape_key_add(name='temp_combine')
	for shapeKey in new_obj.data.shape_keys.key_blocks:
		new_obj.shape_key_remove(shapeKey)
	finished_l += [new_obj]
	new_obj.select_set(False)
	print("Create [%s]" % nw_obj_name)


	return new_obj_l, z_value, x_trans_count, finished_l
