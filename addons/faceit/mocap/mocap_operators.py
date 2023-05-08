from .mocap_importers import A2FMocapImporter, FaceCapImporter, EpicMocapImporter
from .mocap_base import MocapImporterBase
from ..core.shape_key_utils import get_all_shape_key_actions, get_enum_shape_key_actions, has_shape_keys, get_shape_key_names_from_objects, set_rest_position_shape_keys
from ..core import retarget_list_utils as rutils
from ..core import faceit_utils as futils
from ..core import faceit_data as fdata
from ..core.retarget_list_base import FaceRegionsBaseProperties

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, FloatProperty
from mathutils import Matrix
from .mocap_utils import add_zero_keyframe, remove_frame_range
from .osc_operators import get_head_base_transform


class FACEIT_OT_ResetExpressionValues(bpy.types.Operator):
    '''Reset all expression values to 0'''
    bl_idname = 'faceit.reset_expression_values'
    bl_label = 'Reset Face Expression'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        scene = context.scene
        all_target_shapes = rutils.get_all_set_target_shapes(scene.faceit_arkit_retarget_shapes)
        all_target_shapes.extend(rutils.get_all_set_target_shapes(scene.faceit_a2f_retarget_shapes))
        set_rest_position_shape_keys(expressions_filter=all_target_shapes)
        return {'FINISHED'}


class FACEIT_OT_ResetHeadPose(bpy.types.Operator):
    '''Reset the head bone / object'''
    bl_idname = "faceit.reset_head_pose"
    bl_label = "Reset Head Pose"

    def execute(self, context):
        scene = context.scene
        auto_kf = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False
        scene = context.scene
        head_obj = scene.faceit_head_target_object
        if head_obj:
            if head_obj.type == 'ARMATURE':
                pb = head_obj.pose.bones.get(scene.faceit_head_sub_target)
                # Reset pose
                if pb:
                    pb.matrix_basis = Matrix()
            else:
                head_base_rotation, head_base_location = get_head_base_transform()
                if head_obj.rotation_mode == 'QUATERNION':
                    head_obj.rotation_quaternion = head_base_rotation
                elif head_obj.rotation_mode == 'AXIS_ANGLE':
                    head_obj.rotation_axis_angle = head_base_rotation
                else:
                    head_obj.rotation_euler = head_base_rotation
                head_obj.location = head_base_location
                # print(scene.faceit_head_base_location)
        scene.tool_settings.use_keyframe_insert_auto = auto_kf
        return {'FINISHED'}


class FACEIT_OT_ImportFaceCapMocap(MocapImporterBase, bpy.types.Operator):
    bl_idname = 'faceit.import_face_cap_mocap'
    bl_label = 'Import TXT'
    engine_settings_prop_name = "faceit_face_cap_mocap_settings"
    target_shapes_prop_name = "faceit_arkit_retarget_shapes"
    engine_settings = None
    record_frame_rate = 1000

    def _get_mocap_importer(self):
        return FaceCapImporter()


class FACEIT_OT_ImportEpicMocap(MocapImporterBase, bpy.types.Operator):
    bl_idname = 'faceit.import_epic_mocap'
    bl_label = 'Import CSV'
    engine_settings_prop_name = "faceit_epic_mocap_settings"
    target_shapes_prop_name = "faceit_arkit_retarget_shapes"
    engine_settings = None
    record_frame_rate = 1 / 60
    can_import_head_location = False

    def _get_mocap_importer(self):
        return EpicMocapImporter()


class FACEIT_OT_ImportA2FMocap(MocapImporterBase, bpy.types.Operator):
    bl_idname = 'faceit.import_a2f_mocap'
    bl_label = 'Import JSON'
    engine_settings_prop_name = "faceit_a2f_mocap_settings"
    target_shapes_prop_name = "faceit_a2f_retarget_shapes"
    engine_settings = None
    record_frame_rate = 60
    can_bake_control_rig = False

    a2f_frame_rate: FloatProperty(
        name='Export Frame Rate',
        default=60,
        description='Only change this if you changed the default framerate for audio2face exports',
        options={'SKIP_SAVE', }
    )

    def _get_mocap_importer(self):
        return A2FMocapImporter()

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        row = col.row(align=True)
        row.label(text="Shapes Animation")
        self._draw_region_filter_ui(col)

        row = col.row(align=True)
        self._draw_load_to_action_ui(col, context)

        row = col.row()
        row.label(text='Audio2Face Frame Rate')
        row = col.row()
        row.prop(self, 'a2f_frame_rate')

        self._draw_load_audio_ui(col)


class FACEIT_OT_AddZeroKeyframe(FaceRegionsBaseProperties, bpy.types.Operator):
    '''Add a 0.0 keyframe for all target shapes in the specified list(s)'''
    bl_idname = 'faceit.add_zero_keyframe'
    bl_label = 'Add Zero Keyframe'
    bl_options = {'UNDO'}

    expression_sets: EnumProperty(
        name='Expression Sets',
        items=(
            ('ALL', 'All', 'Search for all available expressions'),
            ('ARKIT', 'ARKit', 'The 52 ARKit Expressions that are used in all iOS motion capture apps'),
            ('A2F', 'Audio2Face', 'The 46 expressions that are used in Nvidias Audio2Face app by default.'),
        ),
        default='ALL'
    )

    use_region_filter: BoolProperty(
        name='Filter Face Regions',
        default=True,
        description='Filter face regions that should be animated.'
        # options={'SKIP_SAVE', }
    )

    existing_action: EnumProperty(
        name='Action',
        items=get_enum_shape_key_actions,
        options={'SKIP_SAVE', }
    )

    data_paths: EnumProperty(
        name='Fcurves',
        items=(
            ('EXISTING', 'Existing', 'Add a zero keyframe to all fcurves that are currently found in the specified action'),
            ('ALL', 'All', 'Add a Keyframe for all target shapes in the specified list(s). Create a new fcurve if it doesn\'t exist')
        ),
        default='EXISTING',
        options={'SKIP_SAVE', }
    )

    frame: IntProperty(
        name='Frame',
        default=0,
        options={'SKIP_SAVE', }
    )

    def invoke(self, context, event):

        # Check if the main object has a Shape Key Action applied
        main_obj = futils.get_main_faceit_object()
        sk_action = None
        if has_shape_keys(main_obj):
            if main_obj.data.shape_keys.animation_data:
                sk_action = main_obj.data.shape_keys.animation_data.action

        if sk_action:
            self.existing_action = sk_action.name

        self.frame = context.scene.frame_current

        # face_regions_prop = context.scene.faceit_face_regions
        # props = [x for x in face_regions_prop.keys()]
        # for p in props:
        #     face_regions_prop.property_unset(p)

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text='Affect Expressions')
        row = layout.row()
        row.prop(self, 'expression_sets', expand=True)

        row = layout.row()
        row.label(text='Choose a Shape Key Action:')
        row = layout.row()
        row.prop(self, 'existing_action', text='', icon='ACTION')

        row = layout.row()
        row.prop(self, 'frame', icon='KEYTYPE_KEYFRAME_VEC')

        row = layout.row(align=True)
        row.label(text='Region Filter')
        row = layout.row(align=True)
        row.prop(self, 'use_region_filter', icon='USER')

        if self.use_region_filter:

            col = layout.column(align=True)

            row = col.row(align=True)

            icon_value = 'CHECKBOX_HLT' if self.brows else 'CHECKBOX_DEHLT'
            row.prop(self, 'brows', icon=icon_value)

            icon_value = 'CHECKBOX_HLT' if self.eyes else 'CHECKBOX_DEHLT'
            row.prop(self, 'eyes', icon=icon_value)

            row = col.row(align=True)
            icon_value = 'CHECKBOX_HLT' if self.cheeks else 'CHECKBOX_DEHLT'
            row.prop(self, 'cheeks', icon=icon_value)

            icon_value = 'CHECKBOX_HLT' if self.nose else 'CHECKBOX_DEHLT'
            row.prop(self, 'nose', icon=icon_value)

            row = col.row(align=True)
            icon_value = 'CHECKBOX_HLT' if self.mouth else 'CHECKBOX_DEHLT'
            row.prop(self, 'mouth', icon=icon_value)

            icon_value = 'CHECKBOX_HLT' if self.tongue else 'CHECKBOX_DEHLT'
            row.prop(self, 'tongue', icon=icon_value)

    @classmethod
    def poll(cls, context):
        return get_all_shape_key_actions() and futils.get_faceit_objects_list()

    def execute(self, context):

        scene = context.scene

        shape_names = []
        if self.expression_sets in ('ALL', 'ARKIT'):
            retarget_list = scene.faceit_arkit_retarget_shapes
            for region, active in self.get_active_regions().items():
                if active:
                    shape_names.extend(rutils.get_all_set_target_shapes(retarget_list=retarget_list, region=region))
        if self.expression_sets in ('ALL', 'A2F'):
            retarget_list = scene.faceit_a2f_retarget_shapes
            for region, active in self.get_active_regions().items():
                if active:
                    shape_names.extend(rutils.get_all_set_target_shapes(retarget_list=retarget_list, region=region))

        action = bpy.data.actions.get(self.existing_action)
        if not action:
            self.report({'WARNING'}, f'Couldn\'t find the action {self.existing_action}')
            return {'CANCELLED'}
        fcurves_to_operate_on = [fc for fc in action.fcurves if any(
            shape_name in fc.data_path for shape_name in shape_names)]
        add_zero_keyframe(fcurves=fcurves_to_operate_on, frame=self.frame)
        scene.frame_set(scene.frame_current)

        return {'FINISHED'}


def update_frame_start(self, context):
    if self.frame_start >= self.frame_end:
        self.frame_end = self.frame_start + 1


def update_frame_end(self, context):
    if self.frame_end <= self.frame_start:
        self.frame_start = self.frame_end - 1


class FACEIT_OT_RemoveFrameRange(FaceRegionsBaseProperties, bpy.types.Operator):
    '''Remove a range of frames from the specified Shape Key action'''
    bl_idname = 'faceit.remove_frame_range'
    bl_label = 'Remove Keyframes Filter'
    bl_options = {'UNDO'}

    expression_sets: EnumProperty(
        name='Expression Sets',
        items=(
            ('ALL', 'All', 'Search for all available expressions'),
            ('ARKIT', 'ARKit', 'The 52 ARKit Expressions that are used in all iOS motion capture apps'),
            ('A2F', 'Audio2Face', 'The 46 expressions that are used in Nvidias Audio2Face app by default.'),
        ),
        default='ALL'
    )

    use_region_filter: BoolProperty(
        name='Filter Face Regions',
        default=True,
        description='Filter face regions that should be animated.'
        # options={'SKIP_SAVE', }
    )

    existing_action: EnumProperty(
        name='Action',
        items=get_enum_shape_key_actions,
        options={'SKIP_SAVE', }
    )

    frame_range: EnumProperty(
        name='Effect Frames',
        items=(
            ('CUSTOM', 'Custom', 'Specify a frame range that should be affected'),
            ('ALL', 'All', 'Affect all keys in the specified action'),
        )
    )

    frame_start: IntProperty(
        name='Frame Start',
        default=0,
        soft_min=0,
        soft_max=50000,
        update=update_frame_start
        # options={'SKIP_SAVE', }
    )
    frame_end: IntProperty(
        name='Frame End',
        default=10,
        soft_min=0,
        soft_max=50000,
        update=update_frame_end
        # options={'SKIP_SAVE', }
    )

    def invoke(self, context, event):

        # Check if the main object has a Shape Key Action applied
        main_obj = futils.get_main_faceit_object()
        sk_action = None
        if has_shape_keys(main_obj):
            if main_obj.data.shape_keys.animation_data:
                sk_action = main_obj.data.shape_keys.animation_data.action

        if sk_action:
            self.existing_action = sk_action.name

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text='Affect Expressions')
        row = layout.row()
        row.prop(self, 'expression_sets', expand=True)

        row = layout.row()
        row.label(text='Choose a Shape Key Action:')
        row = layout.row()
        row.prop(self, 'existing_action', text='', icon='ACTION')

        row = layout.row()
        row.label(text='Frame Range:')
        row = layout.row()
        row.prop(self, 'frame_range', expand=True)

        if self.frame_range == 'CUSTOM':
            row = layout.row(align=True)
            row.prop(self, 'frame_start', icon='KEYTYPE_KEYFRAME_VEC')
            row.prop(self, 'frame_end', icon='KEYTYPE_KEYFRAME_VEC')

        row = layout.row(align=True)
        row.label(text='Region Filter')
        row = layout.row(align=True)
        row.prop(self, 'use_region_filter', icon='USER')

        if self.use_region_filter:

            col = layout.column(align=True)

            row = col.row(align=True)

            icon_value = 'CHECKBOX_HLT' if self.brows else 'CHECKBOX_DEHLT'
            row.prop(self, 'brows', icon=icon_value)

            icon_value = 'CHECKBOX_HLT' if self.eyes else 'CHECKBOX_DEHLT'
            row.prop(self, 'eyes', icon=icon_value)

            row = col.row(align=True)
            icon_value = 'CHECKBOX_HLT' if self.cheeks else 'CHECKBOX_DEHLT'
            row.prop(self, 'cheeks', icon=icon_value)

            icon_value = 'CHECKBOX_HLT' if self.nose else 'CHECKBOX_DEHLT'
            row.prop(self, 'nose', icon=icon_value)

            row = col.row(align=True)
            icon_value = 'CHECKBOX_HLT' if self.mouth else 'CHECKBOX_DEHLT'
            row.prop(self, 'mouth', icon=icon_value)

            icon_value = 'CHECKBOX_HLT' if self.tongue else 'CHECKBOX_DEHLT'
            row.prop(self, 'tongue', icon=icon_value)

    @classmethod
    def poll(cls, context):
        return get_all_shape_key_actions() and futils.get_faceit_objects_list()

    def execute(self, context):

        scene = context.scene

        shape_names = []
        if self.expression_sets in ('ALL', 'ARKIT'):
            retarget_list = scene.faceit_arkit_retarget_shapes
            for region, active in self.get_active_regions().items():
                if active:
                    shape_names.extend(rutils.get_all_set_target_shapes(retarget_list=retarget_list, region=region))
        if self.expression_sets in ('ALL', 'A2F'):
            retarget_list = scene.faceit_a2f_retarget_shapes
            for region, active in self.get_active_regions().items():
                if active:
                    shape_names.extend(rutils.get_all_set_target_shapes(retarget_list=retarget_list, region=region))

        action = bpy.data.actions.get(self.existing_action)
        if not action:
            self.report({'WARNING'}, f'Couldn\'t find the action {self.existing_action}')
            return {'CANCELLED'}
        fcurves_to_operate_on = [fc for fc in action.fcurves if any(
            shape_name in fc.data_path for shape_name in shape_names)]
        if self.frame_range == 'CUSTOM':
            remove_frame_range(action=action, fcurves=fcurves_to_operate_on,
                               frame_start=self.frame_start, frame_end=self.frame_end)
        else:
            # Just remove the entire fcurves
            for fc in fcurves_to_operate_on:
                action.fcurves.remove(fc)

        set_rest_position_shape_keys(expressions_filter=shape_names)

        scene.frame_set(scene.frame_current)

        return {'FINISHED'}


class FACEIT_OT_LoadMotionFile(bpy.types.Operator):
    '''Choose a catured file to import as keyframes'''
    bl_idname = 'faceit.load_motion_file'
    bl_label = 'Load mocap'
    bl_options = {'UNDO', 'INTERNAL'}

    engine: bpy.props.EnumProperty(
        name='mocap engine',
        items=(
            ('FACECAP', 'Face Cap', 'Face Cap TXT'),
            ('EPIC', 'Live Link Face', 'Live Link Face CSV'),
            ('A2F', 'Audio2Face', 'Nvidia Audio2Face'),
        ),
        options={'HIDDEN', },
    )

    filter_glob: bpy.props.StringProperty(
        default='*.txt',
        options={'HIDDEN'}
    )

    filepath: bpy.props.StringProperty(
        name='File Path',
        description='Filepath used for importing txt files',
        maxlen=1024,
        default='',
    )

    files: bpy.props.CollectionProperty(
        name='File Path',
        type=bpy.types.OperatorFileListElement,
    )

    def execute(self, context):

        fdata.get_engine_settings(self.engine).filename = self.filepath

        # Update UI
        for region in context.area.regions:
            if region.type == 'UI':
                region.tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):

        if self.engine == 'FACECAP':
            self.filter_glob = '*.txt'
        elif self.engine == 'EPIC':
            self.filter_glob = '*.csv'
        elif self.engine == 'A2F':
            self.filter_glob = '*.json'

        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class FACEIT_OT_LoadAudioFile(bpy.types.Operator):
    '''Choose a audio file to import into sequencer'''
    bl_idname = 'faceit.load_audio_file'
    bl_label = 'Load Audio'
    bl_options = {'UNDO', 'INTERNAL'}

    engine: bpy.props.EnumProperty(
        name='mocap engine',
        items=(
            ('FACECAP', 'Face Cap', 'Face Cap TXT'),
            ('EPIC', 'Live Link Face', 'Live Link Face CSV'),
            ('A2F', 'Audio2Face', 'Nvidia Audio2Face'),
        ),
        options={'HIDDEN', },
    )

    filter_glob: bpy.props.StringProperty(
        default='*.mp3;*.wav',
        options={'HIDDEN'}
    )

    filepath: bpy.props.StringProperty(
        name='File Path',
        description='Filepath used for importing txt files',
        maxlen=1024,
        default='',
    )

    files: bpy.props.CollectionProperty(
        name='File Path',
        type=bpy.types.OperatorFileListElement,
    )

    def execute(self, context):

        fdata.get_engine_settings(self.engine).audio_filename = self.filepath

        # Update UI
        for region in context.area.regions:
            if region.type == 'UI':
                region.tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):

        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class FACEIT_OT_ClearAudioFile(bpy.types.Operator):
    '''Clear the specified audio file'''
    bl_idname = 'faceit.clear_audio_file'
    bl_label = 'Clear Audio'
    bl_options = {'UNDO', 'INTERNAL'}

    engine: bpy.props.EnumProperty(
        name='mocap engine',
        items=(
            ('FACECAP', 'Face Cap', 'Face Cap TXT'),
            ('EPIC', 'Live Link Face', 'Live Link Face CSV'),
            ('A2F', 'Audio2Face', 'Nvidia Audio2Face'),
        ),
        options={'HIDDEN', },
    )

    def execute(self, context):

        fdata.get_engine_settings(self.engine).audio_filename = ''

        # Update UI
        # for region in context.area.regions:
        #     if region.type == 'UI':
        #         region.tag_redraw()
        return {'FINISHED'}


class FACEIT_OT_ClearMotionFile(bpy.types.Operator):
    '''Clear the specified motion file'''
    bl_idname = 'faceit.clear_motion_file'
    bl_label = 'Clear File'
    bl_options = {'UNDO', 'INTERNAL'}

    engine: bpy.props.EnumProperty(
        name='mocap engine',
        items=(
            ('FACECAP', 'Face Cap', 'Face Cap TXT'),
            ('EPIC', 'Live Link Face', 'Live Link Face CSV'),
            ('A2F', 'Audio2Face', 'Nvidia Audio2Face'),
        ),
        options={'HIDDEN', },
    )

    def execute(self, context):

        fdata.get_engine_settings(self.engine).filename = ''
        return {'FINISHED'}
