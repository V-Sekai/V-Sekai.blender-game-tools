
import bpy

from ..core import faceit_utils as futils
from ..landmarks import landmarks_data as lm_data
from . import draw_utils
from .ui import FACEIT_PT_Base, FACEIT_PT_BaseSub

from ..setup.assign_groups_operators import is_picker_running


class FACEIT_PT_BaseRig(FACEIT_PT_Base):
    UI_TABS = ('CREATE')

    @classmethod
    def poll(cls, context):
        return super().poll(context)
        # var = (futils.get_faceit_armature(force_original=True) or not futils.get_faceit_armature()
        #        ) or not context.scene.faceit_use_rigify_armature
        # print(var)
        # return var


class FACEIT_PT_Landmarks(FACEIT_PT_BaseRig, bpy.types.Panel):
    bl_label = 'Landmarks'
    bl_options = set()
    bl_idname = 'FACEIT_PT_Landmarks'
    UI_TABS = ('CREATE', 'CONTROL')

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            # lm_obj = futils.get_object('facial_landmarks')
            # if lm_obj.get("state", 0) > 4:
            #     return False
            scene = context.scene
            active_tab = scene.faceit_workspace.active_tab
            if scene.faceit_face_objects:
                is_ctrl_lm = scene.faceit_show_landmarks_ctrl_rig and active_tab == 'CONTROL'
                is_rig_lm = not futils.get_faceit_armature(force_original=True) and active_tab == 'CREATE'
                return is_rig_lm or is_ctrl_lm

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        lm_obj = futils.get_object('facial_landmarks')

        adaption_state = 0

        col = layout.column(align=True)

        # landmarks setup
        text = 'Generate Landmarks'
        if lm_obj:
            if lm_obj.get("state") and lm_obj["state"] == -1:
                layout.row().label(text='Landmarks need to be updated!')
                layout.row().operator('faceit.update_landmarks', text='Update Landmarks')
                return
            adaption_state = 1
            adaption_state += lm_obj["state"]
            if adaption_state:
                if adaption_state == 1:
                    text = 'Align to Chin'
                elif adaption_state == 11:
                    text = 'Align Rotation'
                elif adaption_state == 2:
                    text = 'Match Face Height'
                elif adaption_state == 3:
                    text = 'Match Face Width'
        if adaption_state == 0:
            row = col.row()
            row.prop(scene, 'faceit_asymmetric', text='Asymmetry', icon='MOD_MIRROR')
        if adaption_state in (0, 1, 11, 2, 3):
            row = col.row()
            row.operator('faceit.facial_landmarks', text=text, icon='TRACKER')
        if adaption_state == 0:
            row = col.row(align=True)
            main_obj = futils.get_main_faceit_object()
            if scene.faceit_workspace.active_tab == 'CONTROL':
                row.label(text="Helpers")
                row = col.row(align=True)
                picker_running = is_picker_running()
                row.operator('faceit.assign_main_modal', text='Set Main Group',
                             icon='EYEDROPPER', depress=picker_running)
                if main_obj:
                    row = col.row(align=True)
                    mod = main_obj.modifiers.get("Main Mask")
                    if mod:
                        row.operator('faceit.unmask_main', icon='X')
                    else:
                        row.operator('faceit.mask_main', icon='MOD_MASK')
            else:
                if main_obj:
                    row.label(text="Helpers")
                    row = col.row(align=True)
                    row = col.row(align=True)
                    mod = main_obj.modifiers.get("Main Mask")
                    if mod:
                        row.operator('faceit.unmask_main', icon='X')
                    else:
                        row.operator('faceit.mask_main', icon='MOD_MASK')
        # if adaption_state >= 4:
        if adaption_state == 4:
            row = col.row()
            row.label(text='Return')
            row = col.row(align=True)
            row.operator('faceit.reset_facial_landmarks', icon='BACK')
            col.label(text='Landmarks')
            col.operator('faceit.project_landmarks', icon='CHECKMARK')
        elif adaption_state == 5:
            row = col.row()
            row.label(text='Return')
            # row = col.row(align=True)
            # row.operator('faceit.revert_projection', text='Revert Projection', icon='BACK')
            row = col.row(align=True)
            row.operator('faceit.reset_facial_landmarks', icon='BACK')
            row = col.row(align=True)
            row.operator('faceit.edit_landmarks', icon='EDITMODE_HLT')
            row.operator('faceit.finish_edit_landmarks', text='', icon='CHECKMARK')


class FACEIT_PT_LandmarkHelpers(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Landmark Helpers'
    bl_options = set()
    bl_parent_id = 'FACEIT_PT_Landmarks'
    bl_idname = 'FACEIT_PT_LandmarkHelpers'

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            lm_obj = futils.get_object('facial_landmarks')
            if lm_obj:
                if lm_obj["state"] >= 3:
                    if context.mode == 'EDIT_MESH':  # context.view_layer.objects.active == lm_obj and
                        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.column(align=True)
        lm_obj = futils.get_object('facial_landmarks')
        adaption_state = lm_obj["state"]
        if scene.faceit_asymmetric and not futils.get_hide_obj(lm_obj):
            row = col.row(align=True)
            row.label(text="Asymmetry")
            row = col.row(align=True)
            row.prop(lm_obj.data, 'use_mirror_x', text='', icon='MOD_MIRROR')
            row.separator()
            row.operator('faceit.mirror_selected_verts', icon='ARROW_LEFTRIGHT')
            if context.mode != 'EDIT_MESH':
                row.enabled = False
        main_obj = futils.get_main_faceit_object()
        if main_obj:
            # row = col.row(align=True)
            # row.label(text="Mask")
            row = col.row(align=True)
            mod = main_obj.modifiers.get("Main Mask")
            if mod:
                row.operator('faceit.unmask_main', icon='X')
            else:
                row.operator('faceit.mask_main', icon='MOD_MASK')
        row = col.row(align=True)
        row.label(text="Settings")
        if adaption_state in range(0, 4):
            row = col.row(align=True)
            prefs = context.preferences.addons['faceit'].preferences
            row.prop(prefs, "auto_lock_3d_view", icon='RESTRICT_VIEW_ON')
            if futils.get_any_view_locked():
                row = col.row(align=True)
                row.operator("faceit.unlock_3d_view", icon='LOCKED', depress=True)
            else:
                row = col.row(align=True)
                row.operator("faceit.lock_3d_view_front", icon='UNLOCKED')

        if adaption_state == 4:
            if context.view_layer.objects.active == lm_obj and context.mode == 'EDIT_MESH':
                row = col.row(align=True)
                row.prop(scene.tool_settings, "use_snap", icon='SNAP_OFF')
                row.operator("faceit.reset_snap_settings", text="", icon='LOOP_BACK')
        row = col.row(align=True)
        row.operator("faceit.landmark_vertex_size", text="Vertex Size Settings")


class FACEIT_OT_LandmarkVertexSize(bpy.types.Operator):
    bl_label = 'Landmark Vertex Size'
    bl_idname = 'faceit.landmark_vertex_size'
    bl_options = {'UNDO', 'INTERNAL'}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self)

    def draw(self, context):
        col = self.layout.column(align=True)
        prefs = context.preferences.addons['faceit'].preferences

        row = col.row(align=True)
        context.preferences.themes[0].view_3d.vertex_size
        row.prop(context.preferences.themes[0].view_3d, 'vertex_size', text="Theme Vertex Size")
        col.separator()
        row = col.row(align=True)
        row.prop(prefs, 'use_vertex_size_scaling', icon='PROP_OFF')
        if prefs.use_vertex_size_scaling:
            row = col.row(align=True)
            row.label(text='Vertex Size Defaults')
            col.use_property_split = True
            col.use_property_decorate = False
            row = col.row(align=True)
            row.prop(prefs, 'default_vertex_size')
            row = col.row(align=True)
            row.prop(prefs, 'landmarks_vertex_size')

    def execute(self, context):
        return {'FINISHED'}


class FACEIT_PT_Rigging(FACEIT_PT_BaseRig, bpy.types.Panel):
    bl_label = 'Rig & Bind'
    bl_options = set()
    bl_idname = 'FACEIT_PT_Rigging'

    faceit_predecessor = 'FACEIT_PT_Landmarks'

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            lm_obj = futils.get_object('facial_landmarks')
            rig = futils.get_faceit_armature(force_original=True)
            if lm_obj:
                if lm_obj.get("state") == 4 or futils.get_hide_obj(lm_obj):
                    return True
            elif rig is not None:
                return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.faceit_shapes_generated:
            col_reset = layout.column(align=True)
            row = col_reset.row()
            row.operator('faceit.back_to_rigging', icon='BACK')
            col_reset.separator(factor=2)
        col = layout.column(align=True)
        col.enabled = not scene.faceit_shapes_generated or scene.faceit_armature_missing

        if futils.get_faceit_armature(force_original=True):

            row = col.row()
            row.label(text='Return')

            # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/rigging/#1-generate-rig')

            # else:
            row = col.row(align=True)
            row.operator('faceit.reset_to_landmarks', icon='BACK')
            row = col.row()
            row.label(text='Bind')

            draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/rigging/#2-bind-weights')

            row = col.row(align=True)
            row.operator('faceit.smart_bind', text='Bind', icon='OUTLINER_OB_ARMATURE')

        else:
            row = col.row()
            row.label(text='Generate')

            # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/rigging/')

            row = col.row()
            col.operator('faceit.generate_rig', text='Generate Faceit Rig', icon='ARMATURE_DATA')


class FACEIT_PT_RigHelpers(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Rig Helpers'
    bl_options = set()
    bl_parent_id = 'FACEIT_PT_Rigging'
    bl_idname = 'FACEIT_PT_RigHelpers'

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            lm_obj = futils.get_object('facial_landmarks')
            if lm_obj:
                if lm_obj["state"] == 4:
                    return not futils.get_faceit_armature(force_original=True)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('faceit.generate_locator_empties', icon='EMPTY_DATA')
        row = col.row(align=True)
        if any([n in bpy.data.objects for n in lm_data.LOCATOR_NAMES]):
            if not scene.show_locator_empties:
                op = row.operator('faceit.edit_locator_empties', text='Show Locators',
                                  icon='HIDE_ON')
                op.hide_value = False
            else:
                op = row.operator('faceit.edit_locator_empties', text='Hide Locators',
                                  icon='HIDE_OFF')
                op.hide_value = True

            op_remove = row.operator('faceit.edit_locator_empties', text='Remove Locators', icon='X')
            op_remove.remove = True
        if scene.faceit_body_armature:
            draw_utils.draw_anime_style_eyes(col, scene)

        col.use_property_split = False


class FACEIT_PT_ModifierOptions(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Other Modifiers'
    bl_parent_id = 'FACEIT_PT_Rigging'
    bl_idname = 'FACEIT_PT_ModifierOptions'

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            lm_obj = futils.get_object('facial_landmarks')
            if lm_obj:
                if lm_obj["state"] >= 4:
                    return futils.get_faceit_armature(force_original=True)

    def draw(self, context):
        col = self.layout.column()
        col.operator("faceit.smooth_correct", icon='MOD_SMOOTH')
