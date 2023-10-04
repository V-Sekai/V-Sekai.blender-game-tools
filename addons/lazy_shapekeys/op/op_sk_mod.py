import bpy
from bpy.props import *
from bpy.types import Operator

from .sk_utils import *


class OBJECT_OT_shape_keys_apply_modifier(Operator):
    bl_idname = "lazy_shapekeys.shape_keys_apply_modifier"
    bl_label = "Apply Modifier(Keep Shape Keys)"
    bl_description = "Apply modifiers even if you have a shape key.\nMake a duplicate for each shape key and run Combine as Shape Key.\nThis feature also preserves each shape key value and driver"
    bl_options = {'REGISTER', 'UNDO'}

    # items = [True]
    # for i in range(31):
    #     items += [False]
    # mod_target_index_list : BoolVectorProperty(name="Apply Modifier Target", description="", size=32,default=items)
    mod_target_index_list : BoolVectorProperty(name="Apply Modifier Target", description="", size=32)
    mod_count : IntProperty()


    @classmethod
    def poll(cls, context):
        obj = bpy.context.object
        return obj and obj.type == "MESH" and obj.modifiers


    def invoke(self, context, event):
        wm = context.window_manager
        obj = bpy.context.object
        self.mod_count = len(obj.modifiers)
        return wm.invoke_props_dialog(self,width=400)


    def draw(self, context):
        layout = self.layout
        col = layout.column()
        mod_enums = bpy.ops.object.modifier_add.get_rna_type().properties['type'].enum_items

        obj = bpy.context.object
        for i in range(self.mod_count):
            icon_val = "NONE"
            mod = obj.modifiers[i]
            if mod.type in mod_enums:
                icon_val = mod_enums[mod.type].icon
            col.prop(self, "mod_target_index_list", text=mod.name, index=i,icon=icon_val,translate=False)
            if mod.type == "BEVEL":
                if mod.limit_method == 'ANGLE':
                    row = col.row(align=True)
                    row.alert = True
                    row.label(text="How to limit: [Angle] fails to apply because the number of vertices changes depending on the shape!",icon="NONE")


    def execute(self, context):
        if not True in self.mod_target_index_list:
            self.report({'WARNING'}, "Select one or more modifiers to apply")
            return{'FINISHED'}

        src_obj = bpy.context.object
        old_data_name = src_obj.data.name
        sc = bpy.context.scene

        old_mode = bpy.context.object.mode
        bpy.ops.object.mode_set(mode="OBJECT")

        old_area_type = bpy.context.area.type
        bpy.context.area.type = 'VIEW_3D'


        # 選択解除
        old_sel = bpy.context.selected_objects
        for obj in bpy.context.selected_objects:
            obj.select_set(False)

        str_targets = []
        for i in range(self.mod_count):
            if self.mod_target_index_list[i]:
                str_targets.append(src_obj.modifiers[i].name)

        base_obj = None
        temp_obj_l = []
        # finished_l = []
        for i,sk in enumerate(src_obj.data.shape_keys.key_blocks):
            print("Start [%s]" % sk.name)
            # tempオブジェクトを作成
            tmp_obj = src_obj.copy()
            if i == 0:
                base_obj = tmp_obj
            sc.collection.objects.link(tmp_obj)
            tmp_obj.select_set(True)
            bpy.context.view_layer.objects.active = tmp_obj
            temp_obj_l += [tmp_obj]

            tmp_obj.name = "sk_tmp_" + src_obj.name + sk.name
            tmp_obj.data = src_obj.data.copy()
            tmp_obj.data.name = "sk_tmp_" + src_obj.name + sk.name
            tmp_sk_bk = tmp_obj.data.shape_keys.key_blocks

            # 他のシェイプキーのボリュームを0にする
            for i_temp,temp_sk in enumerate(tmp_sk_bk):
                temp_sk.value = 0

            # ターゲットのシェイプキーのみを有効にする
            tgt_sk = tmp_sk_bk[i]
            tgt_sk.value = 1
            tgt_sk.mute = False
            set_parent_key_value(tmp_sk_bk,tgt_sk)
            mute_shapekey_driver(tmp_obj.data.shape_keys)
            tmp_cmb_sk = tmp_obj.shape_key_add(name='temp_combine')
            for sk in tmp_sk_bk:
                # if len(tmp_sk_bk) >= 2:
                tmp_obj.shape_key_remove(sk)
            # bpy.ops.object.shape_key_remove(all=True)

            # シェイプキーの変更が反映されていないため、obj.dataのアップデートが必要
            # tmp_obj.update_tag()

            tmp_obj.data.update()

            for mod in tmp_obj.modifiers:
                if mod.name in str_targets:
                    bpy.ops.object.modifier_apply(modifier=mod.name)
            # finished_l += [1]

        # モディファイア適用済みのtempオブジェクトをシェイプキーとして結合
        bpy.context.view_layer.objects.active = base_obj
        try:
            bpy.ops.object.join_shapes()
            temp_act_obj = bpy.context.view_layer.objects.active
            tmp_sk_bk = temp_act_obj.data.shape_keys.key_blocks
        except Exception as e:
            print(e)
            self.report({'WARNING'}, "After applying, modifiers that change the number of vertices for each shape key shape cannot be applied!")
            end_process(self, temp_obj_l, old_sel, str_targets, src_obj)
            return{'FINISHED'}

        # data_name_list = ["interpolation", "mute", "name", "relative_key", "slider_max", "slider_min", "value", "vertex_group",]
        for i,sk in enumerate(src_obj.data.shape_keys.key_blocks):
            for ky in dir(sk):
                try:
                    setattr(tmp_sk_bk[i], ky, getattr(sk,ky))
                except (AttributeError, IndexError): pass

        if src_obj.data.shape_keys.animation_data:
            for dv in src_obj.data.shape_keys.animation_data.drivers:
                driver_copy_prop(self, temp_act_obj.data.shape_keys, src_obj.data.shape_keys, dv)


        # 新しいシェイプキーに入れ替え
        old_obj_data = src_obj.data
        src_obj.data = base_obj.data
        bpy.data.meshes.remove(old_obj_data)
        src_obj.data.name = old_data_name
        bpy.ops.object.mode_set(mode=old_mode)

        end_process(self, temp_obj_l, old_sel, str_targets, src_obj)

        # 元オブジェクトのモディファイアを削除
        for mod_name in str_targets:
            src_obj.modifiers.remove(src_obj.modifiers[mod_name])
        # self.report({'INFO'}, "Apply modifiers [%s]" % str(len(finished_l)))

        bpy.context.area.type = old_area_type
        self.report({'INFO'}, "Apply modifiers")
        return {'FINISHED'}


def end_process(self, temp_obj_l, old_sel, str_targets, src_obj):
    # tempオブジェクトを削除
    for obj in temp_obj_l:
        obj_data = obj.data
        bpy.data.objects.remove(obj)
        if not src_obj.data == obj_data:
            bpy.data.meshes.remove(obj_data)

    # 選択を戻す
    for o in old_sel:
        o.select_set(True)
    bpy.context.view_layer.objects.active = src_obj


#
def driver_copy_prop(self, tgt_data, src_data, src_div):
    div = None
    # ドライバーを作成
    try:
        div = tgt_data.driver_add(src_div.data_path,src_div.array_index)
    except (TypeError,AttributeError):
        div = tgt_data.driver_add(src_div.data_path)
    if not div:
        print("no driver")
        return

    # ドライバーのプロパティのコピー
    for prop in dir(src_div):
        try:
            attr = getattr(src_div,prop)
            setattr(div.driver, prop, attr)
        except (TypeError,AttributeError):
            pass


    # 式をコピー
    div.driver.expression = src_div.driver.expression


    # 入力値の追加
    # バリュー
    if src_div.driver.variables:
        for i,src_var in enumerate(src_div.driver.variables):
            var = div.driver.variables.new()
            for prop in dir(src_var):
                try:
                    attr = getattr(src_var,prop)
                    setattr(var, prop, attr)
                except (TypeError,AttributeError):
                    pass

            # ターゲット
            if src_var.targets:
                for tg in src_var.targets:
                    for prop in dir(tg):
                        try:
                            attr = getattr(tg,prop)
                            setattr(var.targets[0], prop, attr)
                        except (TypeError,AttributeError):
                            pass
