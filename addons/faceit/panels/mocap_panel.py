import bpy

from .draw_utils import draw_head_targets_layout
from .ui import FACEIT_PT_Base, FACEIT_PT_BaseSub
from ..mocap.osc_receiver import osc_queue
from ..panels.draw_utils import draw_text_block
from ..ctrl_rig.control_rig_utils import is_control_rig_connected


class FACEIT_PT_BaseMocap(FACEIT_PT_Base):
    UI_TABS = ('MOCAP',)


class FACEIT_PT_MocapUtils(FACEIT_PT_BaseMocap, bpy.types.Panel):
    bl_label = 'Other Tools and Utilities'
    bl_idname = 'FACEIT_PT_MocapUtils'
    # bl_parent_id = 'FACEIT_PT_MocapSettings'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_MocapOSC'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row(align=True)
        row.operator("faceit.reset_expression_values", icon='LOOP_BACK')
        if scene.faceit_head_target_object:
            row.operator("faceit.reset_head_pose", icon='LOOP_BACK')


class FACEIT_PT_MocapKeyframesOps(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Manipulate Keyframes'
    bl_idname = 'FACEIT_PT_MocapKeyframesOps'
    bl_parent_id = 'FACEIT_PT_MocapUtils'
    faceit_predecessor = 'FACEIT_PT_MocapMotionTargets'

    def draw(self, context):
        layout = self.layout
        # box = layout.box()
        col = layout.column(align=True)
        row = col.row()
        row.operator('faceit.add_zero_keyframe', icon='KEYFRAME')
        row = col.row()
        row.operator('faceit.remove_frame_range', icon='KEYFRAME')


class FACEIT_PT_MocapMotionTargets(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Head Setup'
    bl_idname = 'FACEIT_PT_MocapMotionTargets'
    bl_parent_id = 'FACEIT_PT_MocapUtils'
    faceit_predecessor = 'FACEIT_PT_MocapAction'

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


class FACEIT_PT_MocapAction(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Active Action'
    bl_idname = 'FACEIT_PT_MocapAction'
    bl_parent_id = 'FACEIT_PT_MocapUtils'
    # faceit_predecessor = 'FACEIT_PT_RetargetFBX'
    # bl_options = set()

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=True)
        row = col.row(align=True)
        row.prop(scene, 'faceit_mocap_action', text='')
        mocap_action = scene.faceit_mocap_action
        row = col.row(align=True)
        if mocap_action:
            row.prop(mocap_action, "use_fake_user", text="", icon='FAKE_USER_OFF')
        row.operator('faceit.new_action', icon='ADD')

        head_obj = scene.faceit_head_target_object
        if head_obj:
            row = col.row(align=True)
            row.prop(scene, "faceit_head_action", text="")
            row = col.row(align=True)
            head_action = scene.faceit_head_action
            if head_action:
                row.prop(head_action, "use_fake_user", text="", icon='FAKE_USER_OFF')
            row.operator('faceit.new_head_action', icon='ADD')
        ctrl_rig = scene.faceit_control_armature
        if ctrl_rig:
            row = col.row(align=True)
            if ctrl_rig.animation_data:
                row.prop(ctrl_rig.animation_data, 'action', text='')
                mocap_action = ctrl_rig.animation_data.action
                row = col.row(align=True)
                if mocap_action:
                    row.prop(mocap_action, "use_fake_user", text="", icon='FAKE_USER_OFF')
                # row.prop_search(head_obj.animation_data,
                #                 'action', bpy.data, 'actions', text="")
                row.operator('faceit.new_ctrl_rig_action', text="New Ctrl Rig Action", icon='ADD')
            else:
                row.operator('faceit.new_ctrl_rig_action', text="Create Ctrl Rig Action", icon='ADD')


class FACEIT_PT_MocapImporters(FACEIT_PT_BaseMocap, bpy.types.Panel):
    bl_label = 'Import (Recorded)'
    bl_idname = 'FACEIT_PT_MocapImporters'
    # faceit_predecessor = 'FACEIT_PT_MocapUtils'

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

        a2f_mocap_settings = scene.faceit_a2f_mocap_settings
        # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/epic_utils/')

        row = col.row(align=True)
        row.prop(a2f_mocap_settings, 'audio_filename', text='')
        row.operator('faceit.load_audio_file', icon='FILE_FOLDER').engine = 'A2F'
        row.operator('faceit.clear_audio_file', text='', icon='X').engine = 'A2F'
        row = col.row(align=True)
        row.prop(a2f_mocap_settings, 'filename', text='')
        row.operator('faceit.load_motion_file', text='Load A2F Json', icon='FILE_FOLDER').engine = 'A2F'
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

        face_cap_mocap_settings = scene.faceit_face_cap_mocap_settings

        row = col.row(align=True)
        row.prop(face_cap_mocap_settings, 'audio_filename', text='')
        row.operator('faceit.load_audio_file', icon='FILE_FOLDER').engine = 'FACECAP'
        row.operator('faceit.clear_audio_file', text='', icon='X').engine = 'FACECAP'
        row = col.row(align=True)
        row.prop(face_cap_mocap_settings, 'filename', text='')
        row.operator('faceit.load_motion_file', text='Load FaceCap TXT', icon='FILE_FOLDER').engine = 'FACECAP'
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

        ue_mocap_settings = scene.faceit_epic_mocap_settings
        # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/epic_utils/')
        row = col.row(align=True)
        row.prop(ue_mocap_settings, 'audio_filename', text='')
        row.operator('faceit.load_audio_file', icon='FILE_FOLDER').engine = 'EPIC'
        row.operator('faceit.clear_audio_file', text='', icon='X').engine = 'EPIC'
        row = col.row(align=True)
        row.prop(ue_mocap_settings, 'filename', text='')
        row.operator('faceit.load_motion_file', text='Load UE4 CSV', icon='FILE_FOLDER').engine = 'EPIC'
        row.operator('faceit.clear_motion_file', text='', icon='X').engine = 'EPIC'
        row = col.row(align=True)
        row.operator_context = 'INVOKE_DEFAULT'

        row.operator('faceit.import_epic_mocap', icon='IMPORT')
        row.enabled = (ue_mocap_settings.filename != '')


class FACEIT_PT_MocapOSC(FACEIT_PT_BaseMocap, bpy.types.Panel):
    bl_label = 'OSC (Live)'
    bl_idname = 'FACEIT_PT_MocapOSC'
    faceit_predecessor = 'FACEIT_PT_MocapImporters'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        recorded_data_found = bool(osc_queue)
        receiver_enabled = scene.faceit_osc_receiver_enabled
        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        row = col.row(align=True)
        row.prop(scene, 'faceit_osc_address')
        row = col.row(align=True)
        row.prop(scene, 'faceit_osc_port')
        col.separator()
        row = col.row(align=True)
        row.prop(scene, 'faceit_osc_rotation_units')

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
            # op.animate_head_rotation = scene.faceit_osc_animate_head_rotation
            # op.animate_head_location = scene.faceit_osc_animate_head_location
            # op.animate_shapes = scene.faceit_osc_animate_shapes

            row.operator("faceit.clear_live_data", icon='X')

        col.separator()

        recorder_settings_box = col.box()
        recorder_settings_box.enabled = not (recorded_data_found or receiver_enabled)
        col = recorder_settings_box.column(align=True)
        col.use_property_split = False
        col.use_property_decorate = False

        animate_loc = scene.faceit_osc_animate_head_location
        animate_rot = scene.faceit_osc_animate_head_rotation
        animate_shapes = scene.faceit_osc_animate_shapes

        row = col.row(align=True)
        row.label(text="Shapes Animation")
        row = col.row(align=True)
        row.prop(scene, "faceit_osc_animate_shapes", icon="BLANK1")

        if animate_shapes:
            # TODO: check if the control rig is connected.
            # draw_text_block(col, text="Disconnect the Ctrl Rig for Live Preview of animations.")
            row = col.row(align=True)
            if scene.faceit_osc_use_region_filter:
                icon = 'TRIA_DOWN'
            else:
                icon = 'TRIA_RIGHT'
            row.prop(scene, "faceit_osc_use_region_filter", icon=icon)
            if scene.faceit_osc_use_region_filter:
                # col.use_property_split = False
                face_regions = scene.faceit_osc_face_regions
                row = col.row(align=True)
                icon_value = 'HIDE_OFF' if face_regions.brows else 'HIDE_ON'
                row.prop(face_regions, 'brows', icon=icon_value)
                icon_value = 'HIDE_OFF' if face_regions.eyes else 'HIDE_ON'
                row.prop(face_regions, 'eyes', icon=icon_value)
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
        ctrl_rig = scene.faceit_control_armature
        if ctrl_rig:
            col.use_property_split = False
            row = col.row(align=True)
            row.label(text="Control Rig")
            if is_control_rig_connected(ctrl_rig):
                if not scene.faceit_auto_disconnect_ctrl_rig:
                    draw_text_block(col, text="Live Preview is disabled while the control rig is connected.",
                                    heading="WARNING", chars_per_row=100)
                    col.separator()
                row = col.row(align=True)
                row.prop(scene, "faceit_auto_disconnect_ctrl_rig", icon='UNLINKED')
        # HEAD
        row = col.row(align=True)
        row.label(text="Head Animation")
        row = col.row(align=True)
        row.prop(scene, 'faceit_osc_animate_head_rotation', icon="BLANK1")
        row.prop(scene, 'faceit_osc_animate_head_location', icon="BLANK1")
        col = col.column(align=True)
        col.use_property_split = True
        if animate_loc or animate_rot:
            draw_head_targets_layout(col, scene=scene)

            # row = col.row()
        if animate_loc:
            col.separator()
            row = col.row(align=True)
            row.prop(scene, "faceit_osc_head_location_multiplier")
            # row = col.row(align=True)
            if scene.faceit_head_target_object:
                if scene.faceit_head_target_object.type != 'ARMATURE':
                    # if scene.faceit_head_sub_target
                    row.prop(scene, "faceit_use_head_location_offset", icon='TRANSFORM_ORIGINS')
        # col.separator()
        row = col.row(align=True)
        row.label(text="Animation Settings")
        col.use_property_split = False
        row = col.row(align=True)
        row.prop(scene, "faceit_osc_flip_animation", text="Mirror X", icon='MOD_MIRROR')
        if not (animate_loc or animate_rot or animate_shapes):
            row = col.row()
            row.label(text="WARNING! Enable at least one type of motion")
