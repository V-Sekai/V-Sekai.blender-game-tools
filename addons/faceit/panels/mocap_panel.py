import bpy

from ..properties.mocap_scene_properties import Mocap_Engine_Properties

from ..core.faceit_data import get_engine_settings

from .draw_utils import draw_eye_targets_layout, draw_head_targets_layout, draw_shapes_action_layout
from .ui import FACEIT_PT_Base, FACEIT_PT_BaseSub
from ..mocap.osc_receiver import osc_queue
from ..panels.draw_utils import draw_text_block
from ..ctrl_rig.control_rig_utils import is_control_rig_connected


class FACEIT_PT_BaseMocap(FACEIT_PT_Base):
    UI_TABS = ('MOCAP',)


class FACEIT_PT_MocapSetup(FACEIT_PT_BaseMocap, bpy.types.Panel):
    '''Setup / Head Targets / Actions / Control Rig'''
    bl_label = 'Setup'
    bl_idname = 'FACEIT_PT_MocapSetup'
    weblink = "https://faceit-doc.readthedocs.io/en/latest/mocap_setup/"

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row(align=True)
        row.operator("faceit.reset_expression_values", icon='LOOP_BACK')
        head_obj = scene.faceit_head_target_object
        if head_obj is not None:
            row.operator("faceit.reset_head_pose", icon='LOOP_BACK')
        eye_rig = scene.faceit_eye_target_rig
        if eye_rig:
            if eye_rig is not head_obj:
                row.operator("faceit.reset_eye_pose", icon='LOOP_BACK')


class FACEIT_PT_ShapesSetup(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Shapes Setup'
    bl_idname = 'FACEIT_PT_ShapesSetup'
    bl_parent_id = 'FACEIT_PT_MocapSetup'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        draw_shapes_action_layout(layout, context)
        row = layout.row()
        sub = row.split(factor=0.4)
        sub.alignment = 'RIGHT'
        sub.label(text="Target Objects")
        sub.operator("faceit.go_to_tab", text="Setup Tab", icon='TRIA_LEFT').tab = "SETUP"
        row = layout.row()
        sub = row.split(factor=0.4)
        sub.alignment = 'RIGHT'
        sub.label(text="Target Shapes")
        sub.operator("faceit.go_to_tab", text="Shapes Tab", icon='TRIA_LEFT').tab = "SHAPES"
        row = layout.row()
        sub = row.split(factor=0.4)
        sub.alignment = 'RIGHT'
        sub.label(text="Control Rig")
        sub.operator("faceit.go_to_tab", text="Control Tab", icon='TRIA_LEFT').tab = "CONTROL"


class FACEIT_PT_MocapMotionTargets(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Head Setup'
    bl_idname = 'FACEIT_PT_MocapMotionTargets'
    bl_parent_id = 'FACEIT_PT_MocapSetup'
    faceit_predecessor = 'FACEIT_PT_ShapesSetup'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.
        col = layout.column()
        draw_head_targets_layout(col, scene=scene)


class FACEIT_PT_MocapEyeSetup(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Eye Setup'
    bl_idname = 'FACEIT_PT_MocapEyeSetup'
    bl_parent_id = 'FACEIT_PT_MocapSetup'
    faceit_predecessor = 'FACEIT_PT_MocapMotionTargets'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        col = layout.column(align=True)
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Experimental", icon='ERROR')
        draw_eye_targets_layout(col, context)
        col.separator()
        draw_text_block(
            context,
            col,
            heading="Experimental",
            text="Currently the eye bones are not compatible with the control rig.",)
        col.separator()
        col = draw_text_block(
            context,
            col,
            text="Remove or disable the target shapes on the eye objects to avoid double deformation from shape keys and bone rotation.",)
        row = col.row(align=False)
        row.operator('faceit.disable_eye_look_shape_keys_from_selected_objects', icon='HIDE_OFF')


class FACEIT_PT_MocapImporters(FACEIT_PT_BaseMocap, bpy.types.Panel):
    bl_label = 'Import (Recorded)'
    bl_idname = 'FACEIT_PT_MocapImporters'
    faceit_predecessor = 'FACEIT_PT_MocapSetup'
    weblink = "https://faceit-doc.readthedocs.io/en/latest/mocap_importers/"

    @classmethod
    def poll(cls, context):
        return super().poll(context)


class FACEIT_PT_MocapA2F(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Audio2Face'
    bl_idname = 'FACEIT_PT_MocapA2F'
    bl_parent_id = 'FACEIT_PT_MocapImporters'
    faceit_predecessor = 'FACEIT_PT_MocapEpic'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)

        a2f_mocap_settings = scene.faceit_live_mocap_settings.get('A2F')
        # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/epic_utils/')

        row = col.row(align=True)
        row.prop(a2f_mocap_settings, 'audio_filename', text='')
        row.operator('faceit.load_audio_file', icon='FILE_FOLDER').engine = 'A2F'
        row.operator('faceit.clear_audio_file', text='', icon='X').engine = 'A2F'
        row = col.row(align=True)
        row.prop(a2f_mocap_settings, 'filename', text='')
        row.operator('faceit.load_audio2face_json_file', text='Load Json', icon='FILE_FOLDER')
        row.operator('faceit.clear_motion_file', text='', icon='X').engine = 'A2F'

        row = col.row(align=True)
        row.operator_context = 'INVOKE_DEFAULT'

        row.operator('faceit.import_a2f_mocap', icon='IMPORT')
        row.enabled = (a2f_mocap_settings.filename != '')


class FACEIT_PT_MocapFaceCap(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Face Cap'
    bl_idname = 'FACEIT_PT_MocapFaceCap'
    bl_parent_id = 'FACEIT_PT_MocapImporters'
    # faceit_predecessor = 'FACEIT_PT_MocapImporters'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)

        face_cap_mocap_settings = scene.faceit_live_mocap_settings.get('FACECAP')

        row = col.row(align=True)
        row.prop(face_cap_mocap_settings, 'audio_filename', text='')
        row.operator('faceit.load_audio_file', icon='FILE_FOLDER').engine = 'FACECAP'
        row.operator('faceit.clear_audio_file', text='', icon='X').engine = 'FACECAP'
        row = col.row(align=True)
        row.prop(face_cap_mocap_settings, 'filename', text='')
        row.operator('faceit.load_face_cap_txt_file', text='Load TXT', icon='FILE_FOLDER')
        row.operator('faceit.clear_motion_file', text='', icon='X').engine = 'FACECAP'
        row = col.row(align=True)
        row.operator_context = 'INVOKE_DEFAULT'

        row.operator('faceit.import_face_cap_mocap', icon='IMPORT')
        row.enabled = (face_cap_mocap_settings.filename != '')


class FACEIT_PT_MocapEpic(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Live Link Face'
    bl_idname = 'FACEIT_PT_MocapEpic'
    bl_parent_id = 'FACEIT_PT_MocapImporters'
    faceit_predecessor = 'FACEIT_PT_MocapFaceCap'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)

        ue_mocap_settings = scene.faceit_live_mocap_settings.get('EPIC')
        # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/epic_utils/')
        row = col.row(align=True)
        row.prop(ue_mocap_settings, 'audio_filename', text='')
        row.operator('faceit.load_audio_file', icon='FILE_FOLDER').engine = 'EPIC'
        row.operator('faceit.clear_audio_file', text='', icon='X').engine = 'EPIC'
        row = col.row(align=True)
        row.prop(ue_mocap_settings, 'filename', text='')
        row.operator('faceit.load_live_link_face_csv_file', text='Load CSV', icon='FILE_FOLDER')
        row.operator('faceit.clear_motion_file', text='', icon='X').engine = 'EPIC'
        row = col.row(align=True)
        row.operator_context = 'INVOKE_DEFAULT'

        row.operator('faceit.import_epic_mocap', icon='IMPORT')
        row.enabled = (ue_mocap_settings.filename != '')


class FACEIT_PT_MocapLive(FACEIT_PT_BaseMocap, bpy.types.Panel):
    bl_label = 'Live Recorder'
    bl_idname = 'FACEIT_PT_MocapLive'
    faceit_predecessor = 'FACEIT_PT_MocapImporters'
    weblink = "https://faceit-doc.readthedocs.io/en/latest/mocap_live/"

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        recorded_data_found = bool(osc_queue)
        receiver_enabled = scene.faceit_osc_receiver_enabled
        col = layout.column(align=True)
        row = col.row(align=False)
        col.use_property_split = True
        col.use_property_decorate = False
        row.prop(scene, 'faceit_live_source', expand=True)
        engine_settings: Mocap_Engine_Properties = get_engine_settings(scene.faceit_live_source)
        col.separator(factor=2)
        row = col.row(align=True)
        row.prop(engine_settings, 'address')
        row = col.row(align=True)
        row.prop(engine_settings, 'port')
        col.separator()
        row = col.row(align=True)
        row.prop(engine_settings, 'mirror_x', text="Mirror X", icon='MOD_MIRROR')
        col.separator()
        # if hasattr(engine_settings, 'rotation_units'):
        if engine_settings.rotation_units_variable:
            row = col.row(align=True)
            row.prop(engine_settings, 'rotation_units')
        col.separator(factor=2)
        col = layout.column(align=True)
        row = col.row(align=True)
        if not receiver_enabled:
            row.operator("faceit.receiver_start", icon='PLAY')
            row.enabled = not recorded_data_found
        else:
            row.operator("faceit.receiver_stop", icon='PAUSE')

        if osc_queue and not receiver_enabled:
            row = col.row(align=True)
            row.operator("faceit.import_live_mocap", icon='IMPORT')
            row.operator("faceit.clear_live_data", icon='X')

        recorder_settings_box = col.box()
        recorder_settings_box.enabled = not (recorded_data_found or receiver_enabled)
        col = recorder_settings_box.column(align=True)
        col.use_property_split = False
        col.use_property_decorate = False
        # col.separator()
        row = col.row(align=True)
        if engine_settings.show_record_options:
            icon = 'TRIA_DOWN'
        else:
            icon = 'TRIA_RIGHT'
        row.prop(engine_settings, "show_record_options", icon=icon, emboss=False)
        if not engine_settings.show_record_options:
            return
        # col.separator()
        animate_loc = engine_settings.animate_head_location and engine_settings.can_animate_head_location
        animate_rot = engine_settings.animate_head_rotation and engine_settings.can_animate_head_rotation
        # animate_eye_rot = engine_settings.can_animate_eye_rotation
        animate_shapes = engine_settings.animate_shapes

        row = col.row(align=True)
        row.label(text="Shapes Animation")
        row = col.row(align=True)
        row.prop(engine_settings, "animate_shapes", icon="BLANK1")

        if animate_shapes:
            row = col.row(align=True)
            if engine_settings.use_regions_filter:
                icon = 'TRIA_DOWN'
            else:
                icon = 'TRIA_RIGHT'
            row.prop(engine_settings, "use_regions_filter", icon=icon)
            if engine_settings.use_regions_filter:
                # col.use_property_split = False
                face_regions = engine_settings.region_filter
                row = col.row(align=True)
                icon_value = 'HIDE_OFF' if face_regions.brows else 'HIDE_ON'
                row.prop(face_regions, 'brows', icon=icon_value)
                # row = col.row(align=True)
                # icon_value = 'HIDE_OFF' if face_regions.eyes else 'HIDE_ON'
                # row.prop(face_regions, 'eyes', icon=icon_value)
                icon_value = 'HIDE_OFF' if face_regions.eyelids else 'HIDE_ON'
                row.prop(face_regions, 'eyelids', icon=icon_value)
                row = col.row(align=True)
                icon_value = 'HIDE_OFF' if face_regions.cheeks else 'HIDE_ON'
                row.prop(face_regions, 'cheeks', icon=icon_value)
                icon_value = 'HIDE_OFF' if face_regions.nose else 'HIDE_ON'
                row.prop(face_regions, 'nose', icon=icon_value)
                row = col.row(align=True)
                icon_value = 'HIDE_OFF' if face_regions.mouth else 'HIDE_ON'
                row.prop(face_regions, 'mouth', icon=icon_value)
                icon_value = 'HIDE_OFF' if face_regions.tongue else 'HIDE_ON'
                row.prop(face_regions, 'tongue', icon=icon_value)
                # row = col.row(align=True)
                # icon_value = 'HIDE_OFF' if face_regions.other else 'HIDE_ON'
                # row.prop(face_regions, 'other', icon=icon_value)
            row = col.row(align=True)
            row.prop(engine_settings, 'use_smooth_face_filter', icon='MOD_SMOOTH')
            if engine_settings.use_smooth_face_filter:
                col.use_property_split = True
                col.separator()
                row = col.row()
                row.prop(engine_settings, 'smooth_window_face')
                # self._draw_region_filter_ui(self.smooth_regions, col)
                col.separator()
                smooth_regions = engine_settings.smooth_regions
                face_regions = engine_settings.region_filter
                if face_regions.brows or not engine_settings.use_smooth_face_filter:
                    row = col.row(align=True)
                    icon_value = 'CHECKBOX_HLT' if smooth_regions.brows else 'CHECKBOX_DEHLT'
                    row.prop(engine_settings.smooth_regions, 'brows', icon=icon_value)
                # if face_regions.eyes or not engine_settings.use_smooth_face_filter:
                #     row = col.row(align=True)
                #     icon_value = 'CHECKBOX_HLT' if smooth_regions.eyes else 'CHECKBOX_DEHLT'
                #     row.prop(engine_settings.smooth_regions, 'eyes', icon=icon_value)
                if face_regions.eyelids or not engine_settings.use_smooth_face_filter:
                    row = col.row(align=True)
                    icon_value = 'CHECKBOX_HLT' if smooth_regions.eyelids else 'CHECKBOX_DEHLT'
                    row.prop(engine_settings.smooth_regions, 'eyelids', icon=icon_value)
                if face_regions.cheeks or not engine_settings.use_smooth_face_filter:
                    row = col.row(align=True)
                    icon_value = 'CHECKBOX_HLT' if smooth_regions.cheeks else 'CHECKBOX_DEHLT'
                    row.prop(engine_settings.smooth_regions, 'cheeks', icon=icon_value)
                if face_regions.nose or not engine_settings.use_smooth_face_filter:
                    row = col.row(align=True)
                    icon_value = 'CHECKBOX_HLT' if smooth_regions.nose else 'CHECKBOX_DEHLT'
                    row.prop(engine_settings.smooth_regions, 'nose', icon=icon_value)
                if face_regions.mouth or not engine_settings.use_smooth_face_filter:
                    row = col.row(align=True)
                    icon_value = 'CHECKBOX_HLT' if smooth_regions.mouth else 'CHECKBOX_DEHLT'
                    row.prop(engine_settings.smooth_regions, 'mouth', icon=icon_value)
                if face_regions.tongue or not engine_settings.use_smooth_face_filter:
                    row = col.row(align=True)
                    icon_value = 'CHECKBOX_HLT' if smooth_regions.tongue else 'CHECKBOX_DEHLT'
                    row.prop(engine_settings.smooth_regions, 'tongue', icon=icon_value)
                col.use_property_split = False

        ctrl_rig = scene.faceit_control_armature
        if ctrl_rig:
            col.use_property_split = False
            row = col.row(align=True)
            row.label(text="Control Rig")
            if is_control_rig_connected(ctrl_rig):
                if not scene.faceit_auto_disconnect_ctrl_rig:
                    draw_text_block(context, col, text="Live Preview is disabled while the control rig is connected.",
                                    heading="WARNING")
                    col.separator()
                row = col.row(align=True)
                row.prop(scene, "faceit_auto_disconnect_ctrl_rig", icon='UNLINKED')
        # HEAD
        row = col.row(align=True)
        row.label(text="Head Animation")
        row = col.row(align=True)
        if engine_settings.can_animate_head_rotation:
            row.prop(engine_settings, 'animate_head_rotation', icon='BLANK1')
        if engine_settings.can_animate_head_location:
            row.prop(engine_settings, 'animate_head_location', icon='BLANK1')

        col = col.column(align=True)
        col.use_property_split = True
        if animate_loc or animate_rot:
            draw_head_targets_layout(col, scene=scene)
            col.separator()
            row = col.row(align=True)
            row.prop(engine_settings, 'smooth_head', icon='MOD_SMOOTH')
            if engine_settings.smooth_head:
                col.use_property_split = True
                row = col.row(align=True)
                row.prop(engine_settings, 'smooth_window_head')

            # row = col.row()
        if animate_loc:
            col.separator()
            row = col.row(align=True)
            row.prop(engine_settings, "head_location_multiplier")
            # row = col.row(align=True)
            if scene.faceit_head_target_object:
                if scene.faceit_head_target_object.type != 'ARMATURE':
                    # if scene.faceit_head_sub_target
                    row.prop(engine_settings, "use_head_location_offset", icon='TRANSFORM_ORIGINS')
        # col.use_property_split = False
        if not (animate_loc or animate_rot or animate_shapes):
            row = col.row()
            row.label(text="WARNING! Enable at least one type of motion")
        if engine_settings.can_animate_eye_rotation:
            row = col.row(align=True)
            row.label(text="Eye Rotation")
            col.use_property_split = False
            row = col.row(align=True)
            row.prop(engine_settings, 'animate_eye_rotation_shapes', icon='BLANK1')
            row.prop(engine_settings, 'animate_eye_rotation_bones', icon='BLANK1')
            col.separator()

            if engine_settings.animate_eye_rotation_bones:
                draw_eye_targets_layout(col, context)
                col.separator()

            if engine_settings.animate_eye_rotation_shapes or engine_settings.animate_eye_rotation_bones:
                col.use_property_split = True
                row = col.row(align=True)
                row.prop(engine_settings, 'smooth_eye_look_animation', icon='MOD_SMOOTH')
                if engine_settings.smooth_eye_look_animation:
                    row = col.row(align=True)
                    row.prop(engine_settings, 'smooth_window_eye_bones')


# class FACEIT_PT_MocapUtils(FACEIT_PT_BaseMocap, bpy.types.Panel):
#     bl_label = 'Other Tools and Utilities'
#     bl_idname = 'FACEIT_PT_MocapUtils'
#     # bl_parent_id = 'FACEIT_PT_MocapSettings'
#     # bl_options = set()
#     faceit_predecessor = 'FACEIT_PT_MocapLive'
#     weblink = ""

#     @classmethod
#     def poll(cls, context):
#         return super().poll(context)


# class FACEIT_PT_MocapKeyframesOps(FACEIT_PT_BaseSub, bpy.types.Panel):
#     bl_label = 'Manipulate Keyframes'
#     bl_idname = 'FACEIT_PT_MocapKeyframesOps'
#     bl_parent_id = 'FACEIT_PT_MocapUtils'
#     faceit_predecessor = 'FACEIT_PT_MocapMotionTargets'

#     def draw(self, context):
#         layout = self.layout
#         # box = layout.box()
#         col = layout.column(align=True)
#         row = col.row()
#         row.operator('faceit.add_zero_keyframe', icon='KEYFRAME')
#         row = col.row()
#         row.operator('faceit.remove_frame_range', icon='KEYFRAME')
