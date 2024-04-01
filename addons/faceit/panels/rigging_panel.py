
import bpy


from ..properties.rig_scene_properties import get_enum_vgroups
from ..rigging.rig_utils import is_metarig
from ..core import faceit_utils as futils
from . import draw_utils
from .ui import FACEIT_PT_Base, FACEIT_PT_BaseSub


class FACEIT_PT_BaseRig(FACEIT_PT_Base):
    UI_TABS = ('CREATE')

    @classmethod
    def poll(cls, context):
        return super().poll(context)


class FACEIT_PT_Landmarks(FACEIT_PT_BaseRig, bpy.types.Panel):
    bl_label = 'Landmarks'
    bl_options = set()
    bl_idname = 'FACEIT_PT_Landmarks'
    UI_TABS = ('CREATE', 'CONTROL')
    weblink = "https://faceit-doc.readthedocs.io/en/latest/landmarks/"

    @classmethod
    def poll(cls, context):
        if super().poll(context):
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
            main_obj = futils.get_main_faceit_object(clear_invalid_objects=False)
            if scene.faceit_workspace.active_tab == 'CONTROL':
                row.label(text="Helpers")
                row = col.row(align=True)
                picker_running = context.scene.faceit_picker_options.picking_group == "main"
                op = row.operator('faceit.vertex_group_picker', text='Set Main Group',
                                  icon='EYEDROPPER', depress=picker_running)
                op.additive_group = True
                op.single_surface = True
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
            row = col.row(align=True)
            row.operator('faceit.reset_facial_landmarks', icon='BACK')
            row = col.row(align=True)
            row.operator('faceit.edit_landmarks', icon='EDITMODE_HLT')
            row.operator('faceit.finish_edit_landmarks', text='', icon='CHECKMARK')


class FACEIT_OT_SearchVertexGroups(bpy.types.Operator):
    '''Invoke a search popup for all vertex groups and store the selection in a specific property.'''
    bl_idname = 'faceit.search_vertex_groups'
    bl_label = 'Search Vertex Groups'
    bl_options = {'REGISTER', 'UNDO'}
    bl_property = 'my_enum'

    my_enum: bpy.props.EnumProperty(
        items=get_enum_vgroups
    )
    vgroup_property_name: bpy.props.StringProperty(
        options={'HIDDEN'}
    )
    is_pivot_group: bpy.props.BoolProperty(
        default=True,
        options={'HIDDEN'}
    )

    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}

    def execute(self, context):
        scene = context.scene
        setattr(scene, self.vgroup_property_name, self.my_enum)
        if self.is_pivot_group:
            pass
        return {'FINISHED'}


class FACEIT_OT_ClearVertexGroup(bpy.types.Operator):
    '''Clear the vertex group of the selected object.'''
    bl_idname = 'faceit.clear_vertex_group'
    bl_label = 'Clear Vertex Group'
    bl_options = {'REGISTER', 'UNDO'}

    vgroup_property_name: bpy.props.StringProperty(
        options={'HIDDEN'}
    )

    def execute(self, context):
        scene = context.scene
        grp_name = getattr(scene, self.vgroup_property_name)
        if grp_name in ('faceit_left_eyeball', 'faceit_right_eyeball'):
            for obj in futils.get_faceit_objects_list():
                vgroup = obj.vertex_groups.get(grp_name)
                if vgroup:
                    obj.vertex_groups.remove(vgroup)
        setattr(scene, self.vgroup_property_name, '')
        return {'FINISHED'}


class FACEIT_PT_PivotSetup(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Pivot Setup'
    bl_options = set()
    bl_parent_id = 'FACEIT_PT_Landmarks'
    bl_idname = 'FACEIT_PT_PivotSetup'
    faceit_predecessor = 'FACEIT_PT_LandmarkHelpers'
    weblink = "https://faceit-doc.readthedocs.io/en/latest/landmarks/#pivot-settings"

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            lm_obj = futils.get_object('facial_landmarks')
            if lm_obj:
                if lm_obj["state"] >= 4:
                    return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        row = col.row(align=True)
        row.label(text="Eye Pivots")
        row = col.row(align=True)
        is_manual = scene.faceit_eye_pivot_placement == 'MANUAL'
        row.operator('faceit.remove_manual_pivot_vertex', text='Auto', depress=not is_manual)
        row.operator('faceit.add_manual_pivot_vertex', text='Manual', depress=is_manual)
        if scene.faceit_eye_pivot_placement == 'AUTO':
            col.separator()
            row = col.row(align=True)
            row.prop(scene, 'faceit_eye_geometry_type', expand=True)
            if scene.faceit_eye_geometry_type == 'SPHERE':
                picking_group = context.scene.faceit_picker_options.picking_group
                # EYEBALLS / SHPERES
                row = col.row(align=True)
                sub = row.split(factor=0.4)
                sub.alignment = 'RIGHT'
                sub.label(text='Find from Vertex Groups')
                sub.separator()
                # Left Eye
                row = col.row(align=True)
                sub = row.split(factor=0.4)
                sub.alignment = 'RIGHT'
                sub.label(text='Left Eye')
                row = sub.row(align=True)
                row.operator('faceit.search_vertex_groups', text=scene.faceit_eye_pivot_group_L or 'No Group Selected',
                             icon='VIEWZOOM', emboss=True).vgroup_property_name = 'faceit_eye_pivot_group_L'
                picker_running = picking_group == "left_eyeball"
                op = row.operator('faceit.vertex_group_picker', text='',
                                  icon='EYEDROPPER', depress=picker_running)
                op.vertex_group_name = 'left_eyeball'
                op.is_pivot_group = True
                op.additive_group = True
                # op.single_surface = True
                op = row.operator('faceit.draw_faceit_vertex_group', text='', icon='HIDE_OFF')
                op.faceit_vertex_group_name = scene.faceit_eye_pivot_group_L
                op = row.operator('faceit.assign_group', text='', icon='GROUP_VERTEX')
                op.vertex_group = 'left_eyeball'
                op.is_pivot_group = True
                op = row.operator('faceit.clear_vertex_group', text='', icon='X')
                op.vgroup_property_name = 'faceit_eye_pivot_group_L'
                # Right Eye
                row = col.row(align=True)
                sub = row.split(factor=0.4)
                sub.alignment = 'RIGHT'
                sub.label(text='Right Eye')
                row = sub.row(align=True)
                row.operator('faceit.search_vertex_groups', text=scene.faceit_eye_pivot_group_R or 'No Group Selected',
                             icon='VIEWZOOM', emboss=True).vgroup_property_name = 'faceit_eye_pivot_group_R'
                picker_running = picking_group == "right_eyeball"
                op = row.operator('faceit.vertex_group_picker', text='',
                                  icon='EYEDROPPER', depress=picker_running)
                op.vertex_group_name = 'right_eyeball'
                op.is_pivot_group = True
                op.additive_group = True
                # op.single_surface = True
                op = row.operator('faceit.draw_faceit_vertex_group', text='', icon='HIDE_OFF')
                op.faceit_vertex_group_name = scene.faceit_eye_pivot_group_R
                op = row.operator('faceit.assign_group', text='', icon='GROUP_VERTEX')
                op.vertex_group = 'right_eyeball'
                op.is_pivot_group = True
                op = row.operator('faceit.clear_vertex_group', text='', icon='X')
                op.vgroup_property_name = 'faceit_eye_pivot_group_R'
                if not scene.faceit_eye_pivot_group_L or not scene.faceit_eye_pivot_group_R:
                    row = col.row(align=True)
                    sub = row.split(factor=0.4)
                    sub.separator()
                    row = sub.row(align=True)
                    row.label(text='No vertex groups found')
            else:
                # FLAT EYE GEOMETRY (ANIME)
                row = col.row(align=True)
                sub = row.split(factor=0.4)
                sub.alignment = 'RIGHT'
                sub.label(text='Copy Pivots From Existing Bones')
                sub.separator()
                row = col.row(align=True)
                sub = row.split(factor=0.4)
                sub.alignment = 'RIGHT'
                sub.label(text='Reference Armature')
                row = sub.row(align=True)
                row.prop(scene, 'faceit_pivot_ref_armature', text='', icon='ARMATURE_DATA')
                ref_rig = scene.faceit_pivot_ref_armature
                if not ref_rig:
                    row = col.row(align=True)
                    sub = row.split(factor=0.4)
                    sub.separator()
                    row = sub.row(align=True)
                    row.label(text='No existing rig assigned.', icon='ERROR')
                else:
                    row = col.row(align=True)
                    row.prop_search(scene, 'faceit_eye_pivot_bone_L',
                                    ref_rig.data, 'bones', text='Left Eye Bone')
                    row = col.row(align=True)
                    row.prop_search(scene, 'faceit_eye_pivot_bone_R',
                                    ref_rig.data, 'bones', text='Right Eye Bone')
        else:
            row = col.row(align=True)
            sub = row.split(factor=0.4)
            sub.separator()
            row = sub.row(align=True)
            row.label(text="Place Pivot Vertex", icon='EMPTY_AXIS')
            row = col.row(align=True)
            sub = row.split(factor=0.4)
            sub.separator()
            row = sub.row(align=True)
            row.operator('faceit.reset_manual_pivots', text='Reset', icon='LOOP_BACK')
            row = col.row(align=True)
            row.prop(scene, 'faceit_pivot_vertex_auto_snap', text='Auto Snap')
        row = col.row(align=True)
        row.prop(scene, 'faceit_draw_pivot_locators')
        row = col.row(align=True)
        row.label(text="Jaw Pivot")
        row = col.row(align=True)
        row.operator('faceit.add_jaw_pivot_empty', text='Add Jaw Pivot', icon='SPHERE')
        jaw_pivot_object = context.scene.objects.get('Jaw Pivot')
        if jaw_pivot_object:
            row.operator('faceit.remove_jaw_pivot_empty', text='', icon='X')
            row = col.row(align=True)
            sub = row.split(factor=0.4)
            sub.separator()
            sub.label(text='Place Pivot Empty', icon='SPHERE')
            row = col.row(align=True)
            sub = row.split(factor=0.4)
            sub.separator()
            sub.alignment = 'RIGHT'
            sub.operator('faceit.reset_jaw_pivot_empty', text='Reset', icon='LOOP_BACK')


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
    weblink = "https://faceit-doc.readthedocs.io/en/latest/rigging/"

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
            row = col.row()
            row.label(text='Experimental')
            row = col.row()
            row.operator('faceit.generate_new_rigify_rig', text='Generate Rigify Rig', icon='ARMATURE_DATA')
            if is_metarig(context.object):
                row = col.row()
                row.operator('faceit.generate_rig_from_meta_rig',
                             text='Generate Rig From Meta Rig', icon='ARMATURE_DATA')


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
