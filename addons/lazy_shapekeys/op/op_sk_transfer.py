import bpy
from bpy.props import *
from bpy.types import Operator


# 形状を転送(強制)
class LAZYSHAPEKEYS_OT_shape_keys_transfer_forced(Operator):
	bl_idname = "lazy_shapekeys.shape_keys_transfer_forced"
	bl_label = "Transfer Shape(Forced)"
	bl_description = "Transfers the shape of the selected object. Even if the number of vertices does not match, it is forcibly transferred between vertex indexes"
	bl_options = {'REGISTER', 'UNDO'}

	# type : EnumProperty(default="BASE_MESH",name = "Type", items= [
	# ("BASE_MESH","by Base Mesh ","ソースオブジェクトのベースシェイプから転送します"),
	# ("ACTIVE","Active","ソースオブジェクトのアクティブなシェイプキーから転送します"),
	# ("ALL","All","ソースオブジェクトのシェイプキー形状全てを転送します"),
	# ])
	use_Iteration_index : BoolProperty(name="Evenly distributed",description="If the number of vertices in the source object is less than the number of vertices in the target object, repeat the index again so that the remaining shape keys do not come together at the last vertex position",default=True)

	@classmethod
	def poll(cls, context):
		return len(bpy.context.selected_objects) >= 2

	def invoke(self, context,event):
		dpi_value = bpy.context.preferences.system.dpi
		return context.window_manager.invoke_props_dialog(self, width=dpi_value*3)


	def draw(self, context):
		layout = self.layout
		layout.prop(self,"use_Iteration_index")


	def execute(self, context):
		tgt_obj = bpy.context.active_object

		for src_obj in bpy.context.selected_objects:
			if src_obj == tgt_obj:
				continue
			if not src_obj.type in {"MESH","CURVE"}:
				continue

			# 頂点等のデータを定義
			if src_obj.type == "MESH":
				src_objdata = src_obj.data.vertices
			elif src_obj.type == "CURVE":
				src_objdata = [p for sp in src_obj.data.splines for p in sp.points]

			if tgt_obj.data.shape_keys == None:
				tgt_obj.shape_key_add(name="Basis")

			# シェイプキーを作成
			sk = tgt_obj.shape_key_add(name=src_obj.name)
			sk.value = 1
			tgt_obj.active_shape_key_index = tgt_obj.data.shape_keys.key_blocks.find(sk.name)

			sk_l = sk.data
			v_l = src_objdata
			if self.use_Iteration_index:
				# シェイプキー頂点の方が多いならくり返しリストを作る
				# print(111111111111111111,len(sk_l),len(v_l))
				if len(sk_l) >= len(v_l):
				    new_v_l = []
				    for i in range(len(sk_l) // len(v_l) + 1):
				        new_v_l += v_l
				    v_l = new_v_l

				for i,sk_co in enumerate(sk_l):
					sk_co.co = (v_l[i].co[0],v_l[i].co[1],v_l[i].co[2])
			else:
				for i,sk_co in enumerate(sk_l):
					if i >= len(v_l):
						end_index = len(v_l) - 1
						sk_co.co = (v_l[end_index].co[0],v_l[end_index].co[1],v_l[end_index].co[2])
					else:
						sk_co.co = (v_l[i].co[0],v_l[i].co[1],v_l[i].co[2])



			# for i,v in enumerate(sk.data):
			# 	if i >= len(src_objdata):
			# 		b_c = i -1 - back_count
			# 		if src_obj.type == "MESH":
			# 			v.co = src_objdata[b_c].co
			# 		elif src_obj.type == "CURVE":
			# 			v.co = (src_objdata[b_c].co[0],src_objdata[b_c].co[1],src_objdata[b_c].co[2])
			# 		back_count += 1
			# 	else:
			# 		if src_obj.type == "MESH":
			# 			v.co = src_objdata[i].co
			# 		elif src_obj.type == "CURVE":
			# 			v.co = (src_objdata[i].co[0],src_objdata[i].co[1],src_objdata[i].co[2])


		bpy.context.region.tag_redraw()
		return{'FINISHED'}
