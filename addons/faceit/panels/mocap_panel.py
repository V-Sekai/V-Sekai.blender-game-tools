import bpy
from bpy.types import Panel
from addon_utils import check

from . import draw_utils
# from . import retarget_fbx_ui
from .ui import FACEIT_PT_Base, FACEIT_PT_BaseSub


class FACEIT_PT_BaseMocap(FACEIT_PT_Base):
    UI_TAB = 'MOCAP'


class FACEIT_PT_MocapSettings(FACEIT_PT_BaseMocap, bpy.types.Panel):
    bl_label = 'Mocap Settings'
    bl_idname = 'FACEIT_PT_MocapSettings'

    @classmethod
    def poll(cls, context):
        return super().poll(context)


class FACEIT_PT_MocapAction(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Action'
    bl_idname = 'FACEIT_PT_MocapAction'
    bl_parent_id = 'FACEIT_PT_MocapSettings'
    # bl_options = set()

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # col = layout.column(align=True)
        box = layout.box()
        col = box.column(align=True)
        # box = col_mocap.box()

        # row = box.row()
        # draw_utils.draw_panel_dropdown_expander(row, scene, 'faceit_mocap_general_expand_ui', 'Mocap Settings')
        # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/arkit_setup/#general-mocap-settings')

        # if scene.faceit_mocap_general_expand_ui:

        # box_action = col.box()
        # col = box_action.column(align=True)
        # row = col.row(align=True)

        # draw_utils.draw_panel_dropdown_expander(row, scene, 'faceit_mocap_action_expand_ui', 'Action')
        # if scene.faceit_mocap_action_expand_ui:
        # row = col.row(align=True)
        # row.label(text='Activate Action')

        row = col.row(align=True)
        row.prop(scene, 'faceit_mocap_action', text='')
        op = row.operator('faceit.populate_action', icon='ACTION_TWEAK')
        row = col.row(align=True)
        row.operator('faceit.new_action', icon='ADD')


class FACEIT_PT_MocapMotionTypes(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Motion Types'
    bl_idname = 'FACEIT_PT_MocapMotionTypes'
    bl_parent_id = 'FACEIT_PT_MocapSettings'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_MocapAction'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # col = layout.column(align=True)
        box = layout.box()
        col = box.column(align=True)
        # box_targets = col.box()
        # col = box_targets.column(align=True)
        # row = col.row()

        motion_types_setup = scene.faceit_mocap_motion_types
        # draw_utils.draw_panel_dropdown_expander(
        #     row, motion_types_setup, 'expand', 'Motion Types (Experimental)')
        # if motion_types_setup.expand:
        # row = col.row(align=True)
        # row.label(text='Choose Motion Types')
        row = col.row(align=True)
        row.prop(motion_types_setup, 'blendshapes_target', icon='SHAPEKEY_DATA')
        row = col.row(align=True)
        row.prop(motion_types_setup, 'head_target_rotation', icon='CON_ROTLIKE')
        row.prop(motion_types_setup, 'eye_target_rotation', icon='CON_ROTLIKE')
        # row.prop(motion_types_setup, 'head_target_location', icon='ORIENTATION_VIEW')

        if motion_types_setup.head_target_rotation:

            col.separator()

            row = col.row(align=True)
            op = row.operator('faceit.face_cap_empty', text='Create Head Target')
            op.face_cap_empty = 'HEAD'
            row = col.row(align=True)
            row.prop_search(scene, 'faceit_mocap_target_head', bpy.data, 'objects', text='')
            op_populate = row.operator('faceit.populate_face_cap_empty', text='', icon='EYEDROPPER')
            op_populate.face_cap_empty = 'HEAD'
            obj = scene.objects.get(scene.faceit_mocap_target_head)
            if obj:
                row = col.row(align=True)
                row.popover('FACEIT_PT_DeltaTransformHead')

        if motion_types_setup.eye_target_rotation:

            col.separator()

            row = col.row(align=True)
            op = row.operator('faceit.face_cap_empty', text='Create Eye Targets')
            op.face_cap_empty = 'EYES'
            row = col.row(align=True)
            row.prop_search(scene, 'faceit_mocap_target_eye_l', bpy.data, 'objects', text='')
            op_populate = row.operator('faceit.populate_face_cap_empty', text='', icon='EYEDROPPER')
            op_populate.face_cap_empty = 'EYE_L'

            row.prop_search(scene, 'faceit_mocap_target_eye_r', bpy.data, 'objects', text='')
            op_populate = row.operator('faceit.populate_face_cap_empty', text='', icon='EYEDROPPER')
            op_populate.face_cap_empty = 'EYE_R'
            obj = scene.objects.get(
                scene.faceit_mocap_target_eye_r) or scene.objects.get(
                scene.faceit_mocap_target_eye_l)
            if obj:
                row = col.row(align=True)
                row.popover('FACEIT_PT_DeltaTransformEyeLeft')
                row.popover('FACEIT_PT_DeltaTransformEyeRight')


class FACEIT_PT_MocapFaceCap(FACEIT_PT_BaseMocap, bpy.types.Panel):
    bl_label = 'Face Cap'
    bl_idname = 'FACEIT_PT_MocapFaceCap'
    # bl_options = set()
    # bl_parent_id = 'FACEIT_PT_MainPanel'
    faceit_predecessor = 'FACEIT_PT_RetargetFBX'

    @classmethod
    def poll(cls, context):
        return super().poll(context)


class FACEIT_PT_FaceCapLive(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Live Mode'
    bl_idname = 'FACEIT_PT_FaceCapLive'
    bl_parent_id = 'FACEIT_PT_MocapFaceCap'
    # bl_options = set()

    @classmethod
    def poll(cls, context):
        return super.poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # col = layout.column(align=True)
        box = layout.box()
        col = box.column(align=True)
        row = col.row()

        # draw_utils.draw_web_link(
        #     row, 'https://faceit-doc.readthedocs.io/en/latest/face_cap_utils/#live-capturing-osc')

        if check(module_name="AddRoutes")[1]:
            row = col.row(align=True)
            row.operator('faceit.add_routes')
            row = col.row(align=True)
            row.operator('faceit.clear_routes')
            if not scene.MOM_Items:
                row.enabled = False

            row = col.row(align=True)
            row.prop(scene, 'faceit_record_face_cap', text='Record', icon='REC')
            if not scene.MOM_Items:
                row.enabled = False
        else:
            row = col.row(align=True)
            draw_utils.draw_web_link(
                row,
                'https://faceit-doc.readthedocs.io/en/latest/face_cap_utils/#addroutes-add-on',
                text_ui='Install AddRoutes First...', show_always=True)


class FACEIT_PT_FaceCapText(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Import TXT'
    bl_idname = 'FACEIT_PT_FaceCapText'
    bl_parent_id = 'FACEIT_PT_MocapFaceCap'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_FaceCapLive'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # col = layout.column(align=False)
        box = layout.box()
        col = box.column(align=True)

        face_cap_mocap_settings = scene.faceit_face_cap_mocap_settings

        row = col.row(align=True)
        row.prop(face_cap_mocap_settings, 'filename', text='')
        op = row.operator('faceit.custom_path', text='Load FaceCap TXT', icon='FILE_FOLDER')
        op.engine = 'FACECAP'

        row = col.row(align=True)
        # row.prop(face_cap_mocap_settings, 'load_to_new_action', icon='ACTION_TWEAK')
        # if not face_cap_mocap_settings.load_to_new_action:
        #     row.prop(scene, 'faceit_mocap_action', text='')

        row = col.row(align=True)
        row.operator_context = 'INVOKE_DEFAULT'

        # row.prop(face_cap_mocap_settings, 'frame_start')
        op = row.operator('faceit.import_mocap', icon='IMPORT')
        op.engine = 'FACECAP'

        row.enabled = (face_cap_mocap_settings.filename != '')


class FACEIT_PT_MocapEpic(FACEIT_PT_BaseMocap, bpy.types.Panel):
    bl_label = 'Live Link Face'
    bl_idname = 'FACEIT_PT_MocapEpic'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_MocapFaceCap'

    @classmethod
    def poll(cls, context):
        return super().poll(context)


class FACEIT_PT_MocapCsv(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Import CSV'
    bl_idname = 'FACEIT_PT_MocapCsv'
    bl_parent_id = 'FACEIT_PT_MocapEpic'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_MocapFaceCap'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # col = layout.column(align=False)
        box = layout.box()
        col = box.column(align=True)

        ue_mocap_settings = scene.faceit_epic_mocap_settings
        # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/epic_utils/')

        row = col.row(align=True)
        row.prop(ue_mocap_settings, 'filename', text='')
        op = row.operator('faceit.custom_path', text='Load UE4 CSV', icon='FILE_FOLDER')
        op.engine = 'EPIC'

        row = col.row(align=True)
        row.operator_context = 'INVOKE_DEFAULT'

        op = row.operator('faceit.import_mocap', icon='IMPORT')
        op.engine = 'EPIC'

        row.enabled = (ue_mocap_settings.filename != '')


class FACEIT_PT_Deltas():
    bl_label = "Deltas"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'


class FACEIT_PT_DeltaTransformHead(FACEIT_PT_Deltas, Panel):
    bl_label = "Delta Transformation Head"

    @classmethod
    def poll(cls, context):
        return (context.scene.faceit_mocap_target_head is not None)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        scene = context.scene

        ob = scene.objects.get(scene.faceit_mocap_target_head)

        col = layout.column()
        # col.prop(ob, 'name')
        col.prop(ob, "delta_location", text="Location")

        rotation_mode = ob.rotation_mode
        if rotation_mode == 'QUATERNION':
            col.prop(ob, "delta_rotation_quaternion", text="Rotation")
        elif rotation_mode == 'AXIS_ANGLE':
            pass
        else:
            col.prop(ob, "delta_rotation_euler", text="Rotation")


class FACEIT_PT_DeltaTransformEyeLeft(FACEIT_PT_Deltas, Panel):
    bl_label = "Delta Transformation Eye Left"

    @classmethod
    def poll(cls, context):
        return (context.scene.faceit_mocap_target_head is not None)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        scene = context.scene

        ob = scene.objects.get(scene.faceit_mocap_target_eye_l)

        col = layout.column()
        # col.prop(ob, 'name')
        col.prop(ob, "delta_location", text="Location")

        rotation_mode = ob.rotation_mode
        if rotation_mode == 'QUATERNION':
            col.prop(ob, "delta_rotation_quaternion", text="Rotation")
        elif rotation_mode == 'AXIS_ANGLE':
            pass
        else:
            col.prop(ob, "delta_rotation_euler", text="Rotation")


class FACEIT_PT_DeltaTransformEyeRight(FACEIT_PT_Deltas, Panel):
    bl_label = "Delta Transformation Eye Right"

    @classmethod
    def poll(cls, context):
        return (context.scene.faceit_mocap_target_head is not None)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        scene = context.scene

        ob = scene.objects.get(scene.faceit_mocap_target_eye_r)

        col = layout.column()
        # col.prop(ob, 'name')
        col.prop(ob, "delta_location", text="Location")

        rotation_mode = ob.rotation_mode
        if rotation_mode == 'QUATERNION':
            col.prop(ob, "delta_rotation_quaternion", text="Rotation")
        elif rotation_mode == 'AXIS_ANGLE':
            pass
        else:
            col.prop(ob, "delta_rotation_euler", text="Rotation")


class SHAPE_AMPLIFY_MOCAP_UL_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            row = layout.row(align=True)

            if item.use_animation == True:
                icon = 'CHECKBOX_HLT'
            else:
                icon = 'CHECKBOX_DEHLT'

            row.prop(item, 'use_animation', text='', expand=False, icon=icon)

            target_shapes = item.target_shapes
            row.active = expression_enabled = item.use_animation and len(target_shapes) > 0

            if expression_enabled:
                row.prop(item, 'amplify', emboss=True, text=item.name)
            else:
                row.prop(item, 'amplify', emboss=False, text=item.name)


def draw(context, layout):
    scene = context.scene

    col_mocap = layout.column()

    # retarget_fbx_ui.draw(context, col_mocap)

    box = col_mocap.box()
    col = box.column(align=True)
