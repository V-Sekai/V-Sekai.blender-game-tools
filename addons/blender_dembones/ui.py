import bpy
from bl_operators.presets import AddPresetBase
from bpy.types import Menu
from .operators import DEMBONES_OT_settings_preset_add

class DEMBONES_MT_display_presets(Menu):
    bl_label = "Preset..."
    bl_idname = "DEMBONES_MT_display_presets"
    preset_subdir = "blender_dembones"
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset

class DEMBONES_PT_panel_container(bpy.types.Panel):
    bl_label = "Dem Bones"
    bl_idname = "DEMBONES_PT_panel_container"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Dem Bones"

    def draw(self, context):
        layout = self.layout

        execute_row = layout.row()
        execute_row.scale_y = 2
        execute_row.operator("dembones.execute")

class DEMBONES_PT_bones_panel(bpy.types.Panel):
    bl_label = "Bones Tools"
    bl_idname = "DEMBONES_PT_bones_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Dem Bones"
    bl_parent_id = "DEMBONES_PT_panel_container"
    bl_order = 1

    def draw(self, context):
        layout = self.layout

        layout.operator("dembones.set_dem_lock")
        layout.operator("dembones.delete_dem_lock")


class DEMBONES_PT_main_panel(bpy.types.Panel):
    bl_label = "Settings: Main"
    bl_idname = "DEMBONES_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Dem Bones"
    bl_parent_id = "DEMBONES_PT_panel_container"
    bl_order = 2

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.menu(DEMBONES_MT_display_presets.__name__, text=DEMBONES_MT_display_presets.bl_label, icon='FILE_CACHE')
        row.operator(DEMBONES_OT_settings_preset_add.bl_idname, text="", icon='ADD')
        row.operator(DEMBONES_OT_settings_preset_add.bl_idname, text="", icon='REMOVE').remove_active = True

        layout.separator()

        layout.prop(context.scene.dembones, "n_bones")
        layout.prop(context.scene.dembones, "n_init_iters")
        layout.prop(context.scene.dembones, "n_iters")
        layout.prop(context.scene.dembones, "tolerance")
        layout.prop(context.scene.dembones, "patience")
        layout.prop(context.scene.dembones, "n_trans_iters")
        layout.prop(context.scene.dembones, "bind_update")
        layout.prop(context.scene.dembones, "trans_affine")
        layout.prop(context.scene.dembones, "trans_affine_norm")
        layout.prop(context.scene.dembones, "n_weights_iters")
        layout.prop(context.scene.dembones, "nnz")
        layout.prop(context.scene.dembones, "weights_smooth")
        layout.prop(context.scene.dembones, "weights_smooth_step")

# bpy.utils.register_class(DEMBONES_PT_panel_container)
# bpy.utils.register_class(DEMBONES_PT_bones_panel)
# bpy.utils.register_class(DEMBONES_PT_main_panel)
# bpy.utils.register_class(DEMBONES_MT_display_presets)