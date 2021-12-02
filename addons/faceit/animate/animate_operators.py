import io
import re
import os
import bpy
import time
import json
import numpy as np
from mathutils import Vector
from contextlib import redirect_stdout
from bpy_extras.io_utils import ExportHelper
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, StringProperty
from numpy.lib.npyio import save

from . import animate_utils as a_utils
from ..core import shape_key_utils as sk_utils
from ..core import faceit_utils as futils
from ..core import faceit_data as fdata
from ..core import fc_dr_utils


def check_expression_valid(self, context):
    self.expression_sk_exists = self.expression_name in sk_utils.get_shape_key_names_from_objects()
    self.expression_item_exists = self.expression_name in context.scene.faceit_expression_list
    if 'left' in self.expression_name.lower() or \
            'right' in self.expression_name.lower() or \
            self.expression_name.lower().endswith('_l') or \
            self.expression_name.lower().endswith('_r'):
        self.can_mirror = True
        self.is_mirror = True


class FACEIT_OT_AddExpressionItem(bpy.types.Operator):
    ''' Add a new Expression to the expression list and action'''
    bl_idname = 'faceit.add_expression_item'
    bl_label = 'Add Expression'
    bl_options = {'UNDO', 'INTERNAL'}

    expression_name: StringProperty(
        name='Expression Name',
        default='Expression',
        options={'SKIP_SAVE'},
        update=check_expression_valid
    )

    new_exp_index: IntProperty(
        name='Index',
        default=-1,
        options={'SKIP_SAVE'},
    )

    expression_sk_exists: BoolProperty(
        name='Index',
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    expression_item_exists: BoolProperty(
        name='Index',
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    mirror_name_overwrite: StringProperty(
        name='Mirror Expression Name',
        default='',
        description='force side L/R/N',
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    side_overwrite: StringProperty(
        name='Expression Side',
        default='',
        description='Automatically Generate a Mirror Expression if this value is set!',
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    can_mirror: BoolProperty(
        name='Create Mirror Expression',
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    is_mirror: BoolProperty(
        name='Is Mirror Expression',
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    custom_shape: BoolProperty(
        name='Single Custom Shape',
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    auto_mirror: BoolProperty(
        name='Create Mirror Expression',
        default=False,
        options={'SKIP_SAVE'},
    )

    corr_sk: BoolProperty(
        name='Corrective Shape Keys exist',
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):

        self.expression_item_exists = self.expression_name in context.scene.faceit_expression_list
        self.expression_sk_exists = self.expression_name in sk_utils.get_shape_key_names_from_objects()
        self.corr_sk = any([sk_name.startswith('faceit_cc_')
                            for sk_name in sk_utils.get_shape_key_names_from_objects()])

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, 'expression_name')
        if self.expression_sk_exists:
            layout.alert = True
            row = layout.row()
            row.label(text='WARNING: Expression Name already in Shape Keys')
        if self.expression_item_exists:
            layout.alert = True
            row = layout.row()
            row.label(text='WARNING: Expression Name already in List.')
        if self.can_mirror:
            row = layout.row()
            row.prop(self, 'is_mirror', text='Left/Right', icon='MOD_MIRROR')
            if self.is_mirror:
                row = layout.row()
                row.prop(self, 'auto_mirror', text='Generate Mirror Expression', icon='MOD_MIRROR')

    def execute(self, context):
        scene = context.scene

        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = True

        expression_list = scene.faceit_expression_list

        if self.new_exp_index == -1:
            index = len(expression_list)
        frame = int(index+1)*10

        all_shape_key_names = sk_utils.get_shape_key_names_from_objects()

        expression_name = self.expression_name

        # ADD trailing number to double entries!
        if expression_name in expression_list:
            max_integer_found = 0
            for item_name in [item.name for item in expression_list if expression_name in item.name]:
                if len(item_name) >= 3:
                    if item_name[-3:].isdigit():
                        if item_name[:-3].strip('.') == expression_name:
                            digits = int(item_name[-3:])
                            max_integer_found = max(max_integer_found, digits)

            if max_integer_found > 0:
                new_digits = '.' + str(max_integer_found + 1).zfill(3)
            else:
                new_digits = '.001'

            expression_name += new_digits

        if self.auto_mirror:
            expression_name = re.sub(r'left', 'Left', expression_name, flags=re.IGNORECASE)
            expression_name = re.sub(r'right', 'Right', expression_name, flags=re.IGNORECASE)

        item = expression_list.add()
        item.name = expression_name
        item.frame = frame

        # corrective shape keys exist on any registered object
        if self.corr_sk:

            sk_name = 'faceit_cc_'+expression_name

            if sk_name in all_shape_key_names:
                faceit_objects = futils.get_faceit_objects_list()
                corrective_sk_action = bpy.data.actions.get('faceit_corrective_shape_keys', None)

                for obj in faceit_objects:
                    if sk_utils.has_shape_keys(obj):

                        sk = obj.data.shape_keys.key_blocks.get(sk_name)
                        if sk:
                            item.corr_shape_key = True
                            sk.mute = False
                            if corrective_sk_action:
                                if not obj.data.shape_keys.animation_data:
                                    obj.data.shape_keys.animation_data_create()
                                obj.data.shape_keys.animation_data.action = corrective_sk_action
                            continue

                        if len(obj.data.shape_keys.key_blocks) == 1:
                            obj.shape_key_clear()

        if self.mirror_name_overwrite:
            item.side = self.side_overwrite
            item.mirror_name = self.mirror_name_overwrite

        shape_action = bpy.data.actions.get('faceit_shape_action')
        ow_action = bpy.data.actions.get('overwrite_shape_action')

        if self.custom_shape:

            if self.is_mirror:
                if 'Left' in expression_name:
                    item.side = 'L'
                    item.mirror_name = expression_name.replace('Left', 'Right')
                elif 'Right' in expression_name:
                    item.side = 'R'
                    item.mirror_name = expression_name.replace('Right', 'Left')

                elif expression_name.lower().endswith('_l'):
                    item.side = 'L'
                    if expression_name[-1].islower():
                        item.mirror_name = expression_name[:-1]+'r'
                    else:
                        item.mirror_name = expression_name[:-1]+'R'

                elif expression_name.lower().endswith('_r'):
                    item.side = 'R'
                    if expression_name[-1].islower():
                        item.mirror_name = expression_name[:-1]+'l'
                    else:
                        item.mirror_name = expression_name[:-1]+'L'
            else:
                item.side = 'N'
                item.mirror_name = ''

            if not shape_action:
                shape_action = bpy.data.actions.new('faceit_shape_action')
            if not ow_action:
                ow_action = bpy.data.actions.new('overwrite_shape_action')

            rig = futils.get_faceit_armature()

            if not rig.animation_data:
                rig.animation_data_create()

            for b in rig.pose.bones:
                b.location = Vector()
                b.rotation_euler = Vector()
                b.scale = Vector((1, 1, 1))

                if 'MCH' in b.name:
                    continue
                if 'DEF' in b.name:
                    continue
                # if not shape_action.fcurves:
                # add fcurves for all possible bone data_paths
                base_dp = 'pose.bones["{}"].'.format(b.name)
                data_paths = [base_dp+'location', base_dp+'scale', base_dp+'rotation_euler']
                for dp in data_paths:
                    for i in range(3):
                        if not shape_action.fcurves.find(dp, index=i):
                            shape_action.fcurves.new(dp, index=i)
                        if not ow_action.fcurves.find(dp, index=i):
                            ow_action.fcurves.new(dp, index=i)
                        # rig.keyframe_insert()

            if shape_action:
                rig.animation_data.action = shape_action
                a_utils.add_expression_keyframes(rig, frame)

            if ow_action:
                rig.animation_data.action = ow_action
                a_utils.add_expression_keyframes(rig, frame)

            if self.auto_mirror and self.is_mirror:
                bpy.ops.faceit.add_expression_item(
                    'EXEC_DEFAULT', expression_name=item.mirror_name, custom_shape=True, corr_sk=self.corr_sk)

            scene.faceit_expression_list_index = index

        scene.tool_settings.use_keyframe_insert_auto = auto_key
        if shape_action:
            scene.frame_start, scene.frame_end = shape_action.frame_range

        return {'FINISHED'}


class FACEIT_OT_MoveExpressionItem(bpy.types.Operator):
    '''Move a specific Expression Item index in the list. Also effects the expression actions '''
    bl_idname = 'faceit.move_expression_item'
    bl_label = 'Move'
    bl_options = {'UNDO', 'INTERNAL'}

    # the name of the facial part
    direction: bpy.props.EnumProperty(
        items=(
            ('UP', 'Up', ''),
            ('DOWN', 'Down', ''),
        ),
        options={'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        idx = context.scene.faceit_expression_list_index
        expression_list = context.scene.faceit_expression_list

        # if idx > 0 and idx <= len(context.scene.faceit_expression_list):
        #     return True
        return expression_list and idx >= 0 and idx < len(expression_list)

    def move_index(self, context, flist, index):
        list_length = len(flist) - 1
        new_index = index + (-1 if self.direction == 'UP' else 1)
        context.scene.faceit_expression_list_index = max(0, min(new_index, list_length))

    def execute(self, context):
        scene = context.scene
        index = scene.faceit_expression_list_index
        expression_list = scene.faceit_expression_list
        expression_item = expression_list[index]

        add_index = -1 if self.direction == 'UP' else 1
        new_index = index + add_index
        add_frame = add_index * 10

        if new_index == len(expression_list) or new_index == -1:
            return{'CANCELLED'}
            # self.report({'ERROR'},)

        new_index_item = expression_list[new_index]

        ow_action = bpy.data.actions.get('overwrite_shape_action')
        sh_action = bpy.data.actions.get('faceit_shape_action')
        cc_action = bpy.data.actions.get('faceit_corrective_shape_keys')

        # original frame
        expression_frame = expression_item.frame
        new_index_frame = new_index_item.frame

        actions = [ow_action, sh_action]

        for action in actions:
            if action:
                for curve in action.fcurves:
                    for key in curve.keyframe_points:
                        if key.co[0] == new_index_frame:
                            key.co[0] -= add_frame/2
                    for key in curve.keyframe_points:
                        if key.co[0] == expression_frame:
                            key.co[0] += add_frame
                    for key in curve.keyframe_points:
                        if key.co[0] == new_index_frame - add_frame/2:
                            key.co[0] -= add_frame/2

                for curve in action.fcurves:
                    curve.update()
        if cc_action:
            exp_fc = cc_action.fcurves.find('key_blocks["{}"].value'.format('faceit_cc_'+expression_item.name))
            if exp_fc:
                for key in exp_fc.keyframe_points:
                    key.co[0] += add_frame
                exp_fc.update()

            new_index_fc = cc_action.fcurves.find('key_blocks["{}"].value'.format('faceit_cc_'+new_index_item.name))
            if new_index_fc:
                for key in new_index_fc.keyframe_points:
                    key.co[0] -= add_frame
                new_index_fc.update()

        expression_item.frame = new_index_frame
        new_index_item.frame = expression_frame

        expression_list.move(new_index, index)
        self.move_index(context, expression_list, index)
        return{'FINISHED'}


# def update_load_method(self, context):
#     if self.load_custom_path == True:
#         self.


class FACEIT_OT_AppendActionToFaceitRig(bpy.types.Operator):
    ''' Load a compatible Faceit Expression Action to the Faceit Armature Object. Creates two actions (faceit_shape_action, overwrite_shape_action) '''
    bl_idname = 'faceit.append_action_to_faceit_rig'
    bl_label = 'Load Faceit Expression Action'
    bl_options = {'UNDO', 'INTERNAL'}

    force_rotation_mode: BoolProperty(
        name='Force Euler Rotation (XYZ)',
        description='This is necessary for the action to work properly!',
        default=True,
    )

    expressions_type: EnumProperty(
        name='Expressions',
        items=(
            ('ARKIT', 'ARKit', 'The ARKit Expressions'),
            ('TONGUE', 'Tongue', 'The Tongue Expressions'),
            ('PHONEMES', 'Phonemes', 'Add Phoneme Expressions'),
            # ('CUSTOM', 'None', 'Custom Expressions'),
        ),
        default='ARKIT'
    )

    expression_presets = {
        'ARKIT': 'arkit_expressions.face',
        'TONGUE': 'tongue_expressions.face',
        'PHONEMES': 'phoneme_expressions.face',
    }

    scale_method: EnumProperty(
        name='Scale Method',
        items=(
            ('AUTO', 'Auto Scale', 'Do automatically scale by matching the rig size to the scene'),
            ('OVERWRITE', 'Overwrite Scale', 'Manually overwrite scale of the action'),
            ('NONE', 'No Scale', 'Don\'t scale the Action at all'),
        ),
        default='AUTO',
    )

    auto_scale_method: EnumProperty(
        name='Auto Scale Method',
        items=(
            ('GLOBAL', 'XYZ', 'Scale Pose Translations in XYZ (World Space).'),
            ('AVERAGE', 'Average', 'Scale Poses by an Average factor.'),
        ),
        default='GLOBAL',
    )

    new_action_scale: FloatVectorProperty(
        name='New Scale',
        default=(1.0, 1.0, 1.0),
    )

    armature_apply: BoolProperty(
        name='Apply Rest Pose',
        default=True
    )

    auto_scale_eyes: BoolProperty(
        name='Scale Eye Dimensions',
        default=True
    )

    apply_existing_corrective_shape_keys: BoolProperty(
        name='Apply Corrective Shape Keys',
        description='Try to apply the existing corrective shape keys to the new expressions.',
        default=True,
    )

    load_custom_path: BoolProperty(
        name='Load Custom Expressions',
        description='Load a custom expression set. (.face)',
        default=False,
        options={'SKIP_SAVE', },
    )

    load_method: EnumProperty(
        name='Load Method',
        items=(
            ('APPEND', 'Append', 'Append to existing ExpressionsList'),
            ('OVERWRITE', 'Overwrite', 'Overwrite existing ExpressionsList'),

        ),
        default='APPEND'
    )

    zero_kf_method: EnumProperty(
        name='Auto Zero',
        items=(
            ('FAST', 'Fast', 'Numpy'),
            ('SAFE', 'Safe', 'Blender Keyframes'),

        ),
        default='FAST'
    )

    filepath: StringProperty(
        subtype="FILE_PATH",
        default='face'
    )

    filter_glob: StringProperty(
        default='*.face;',
        options={'HIDDEN'},
    )

    corr_sk = False
    custom_rig = False

    @ classmethod
    def poll(cls, context):
        if context.mode not in ['POSE', 'OBJECT']:
            return False
        rig = futils.get_faceit_armature()
        if rig:
            if rig.hide_viewport == False:
                return True

    def invoke(self, context, event):

        self.filepath = 'faceit_expressions.face'

        self.corr_sk = any([sk_name.startswith('faceit_cc_')
                            for sk_name in sk_utils.get_shape_key_names_from_objects()])

        rig = futils.get_faceit_armature()
        if rig.name != 'FaceitRig':
            self.custom_rig = True
            self.scale_method = 'NONE'

        # if context.scene.faceit_use_corrective_shapes:
        if self.load_custom_path:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        else:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)

    # def invoke(self, context, event):

    def draw(self, context):
        layout = self.layout
        if not self.load_custom_path:
            row = layout.row()
            row.prop(self, 'expressions_type')
        row = layout.row()
        row.label(text='Choose Scale Method')
        row = layout.row()
        row.prop(self, 'scale_method', expand=True)
        row = layout.row()
        if self.scale_method == 'OVERWRITE':
            row = layout.row()
            row.prop(self, 'new_action_scale')
        elif self.scale_method == 'AUTO':
            row = layout.row()
            row.prop(self, 'auto_scale_method', expand=True)

        row = layout.row()
        row.prop(self, 'auto_scale_eyes', icon='CON_DISTLIMIT')

        row = layout.row()
        row.label(text='Choose Append Method')
        row = layout.row()
        row.prop(self, 'load_method', expand=True)

        if self.corr_sk:
            row = layout.row()
            row.prop(self, 'apply_existing_corrective_shape_keys')
        # layout.separator()
        if self.custom_rig:
            row = layout.row()
            row.label(text='Rig Settings')
            row = layout.row()
            row.prop(self, 'force_rotation_mode')
            # row = layout.row()
            row.prop(self, 'armature_apply')
        # row = layout.row()
        # row.label(text='Base Keyframes method')
        # row = layout.row()
        # row.prop(self, 'zero_kf_method', expand=True)

    def execute(self, context):

        if self.load_custom_path:
            filename, extension = os.path.splitext(self.filepath)
            if extension != '.face':
                self.report({'ERROR'}, 'You need to provide a file of type .face')
                return{'CANCELLED'}
            # if '.face'

        scene = context.scene
        save_frame = scene.frame_current
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False
        expression_list = scene.faceit_expression_list

        warnings = False

        mode_save = context.mode
        if mode_save != 'OBJECT':
            bpy.ops.object.mode_set()

        rig = futils.get_faceit_armature()

        if not rig.animation_data:
            rig.animation_data_create()

        ow_action = bpy.data.actions.get('overwrite_shape_action')
        shape_action = bpy.data.actions.get('faceit_shape_action')

        if self.load_method == 'APPEND':
            if not expression_list:
                self.report(
                    {'INFO'},
                    'Could not append the expressions, because there are no shapes. Using Overwrite method instead')
                self.load_method = 'OVERWRITE'

            if not shape_action or not ow_action:
                self.report(
                    {'INFO'},
                    'Could not append the action, because no Action was found. Using Overwrite method instead')
                self.load_method = 'OVERWRITE'

        if self.load_method == 'OVERWRITE':

            expression_list.clear()

            if shape_action:
                bpy.data.actions.remove(shape_action)
                shape_action = None
            if ow_action:
                bpy.data.actions.remove(ow_action)
                ow_action = None

        # Reset all bone transforms!

        futils.set_active_object(rig.name)

        layer_state = rig.data.layers[:]
        for i in range(len(rig.data.layers)):
            rig.data.layers[i] = True

        bpy.ops.object.mode_set(mode='POSE')

        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.transforms_clear()

        if self.armature_apply:

            bpy.ops.pose.armature_apply(selected=False)

        ############################## Load New Expressions Data ###############################
        # | - Load Expressions Data
        # | - Keyframes, Rig Dimensions, Rest Pose,
        ###########################################################################

        new_shape_action = None

        if not self.load_custom_path:
            self.filepath = fdata.get_expression_presets() + self.expression_presets[self.expressions_type]

        action_dict = {}
        eye_dimensions = []

        with open(self.filepath, 'r') as f:
            data = json.load(f)
            if isinstance(data, dict):

                # new_expression_names = data['expressions']
                expression_data_loaded = data['expressions']
                import_rig_dimesion = data['action_scale']
                action_dict = data['action']
                eye_dimensions = data.get('eye_dimensions')

        if self.force_rotation_mode:
            for bone in rig.pose.bones:
                bone.rotation_mode = 'XYZ'

        new_shape_action = bpy.data.actions.new(name='temp')
        rig.animation_data.action = new_shape_action

        new_expression_count = len(expression_data_loaded.keys())

        zero_frames = set()
        new_frames = []
        for i in range(new_expression_count):
            frame = (i + 1) * 10
            new_frames.append(frame)
            zero_frames.update((frame + 1, frame - 9))

        zero_frames = sorted(list(zero_frames))

        start_time = time.time()

        missing_dps = []

        for dp, data_per_array_index in action_dict.items():
            bone_name = dp[dp.find('bones["')+7: dp.find('"]')]
            if bone_name not in rig.pose.bones:
                if bone_name not in missing_dps:
                    missing_dps.append(bone_name)
            else:
                # Make sure all channels are animated to avoid non-zeroed-out keyframes
                if 'rotation_quaternion' in dp:
                    channels = 4
                elif any(x in dp for x in ['scale', 'rotation_euler', 'location']):
                    channels = 3
                else:
                    channels = 1
                for i in range(channels):

                    data = data_per_array_index.get(str(i))
                    fc = new_shape_action.fcurves.new(data_path=dp, index=i)

                    if data:
                        kf_data = np.array(data)
                    else:
                        kf_data = np.empty(2)

                    if self.zero_kf_method == 'FAST' and not 'influence' in dp:
                        # Adding Zero Keyframes for all rest poses inbetween expressions!
                        base_value = 0
                        if 'scale' in dp:
                            base_value = 1
                        elif 'rotation_quaternion' in dp and i == 0:
                            base_value = 1

                        kf_data_base = np.array([(f, base_value) for f in zero_frames])
                        if kf_data.ndim == 1:
                            kf_data = kf_data_base
                        else:
                            kf_data = np.concatenate((kf_data,  kf_data_base), axis=0)

                        # Sort kf_data by frame (all rows, first column)
                        kf_data[kf_data[:, 0].argsort()]

                    fc_dr_utils.populate_keyframe_points_from_np_array(fc, kf_data, add=True)

        for fc in new_shape_action.fcurves:
            for kf in fc.keyframe_points:
                kf.interpolation = 'LINEAR'

        if self.zero_kf_method == 'SAFE':
            # Adding Zero Keyframes for all rest poses inbetween expressions!

            zero_ref_frame = zero_frames[0]
            scene.frame_set(zero_ref_frame)

            for pb in rig.pose.bones:
                layers = pb.bone.layers
                if layers[0] or layers[1] or layers[2]:
                    pb.bone.select = True
                else:
                    pb.bone.select = False

            bpy.ops.pose.transforms_clear()
            bpy.ops.anim.keyframe_insert(type='Location', confirm_success=False)
            bpy.ops.anim.keyframe_insert(type='Rotation', confirm_success=False)
            bpy.ops.anim.keyframe_insert(type='Scaling', confirm_success=False)

            for fcurve in new_shape_action.fcurves:
                kf_zero_value = 0
                for kf in fcurve.keyframe_points:
                    if kf.co[0] == zero_ref_frame:
                        kf_zero_value = kf.co[1]
                        break

                # for f in sorted(zero_frames+new_frames):
                for f in zero_frames:
                    if 'influence' in fc.data_path:
                        continue
                    fcurve.keyframe_points.insert(f, kf_zero_value, options={'FAST'})

        print('Added new Keyframes in {}'.format(round(time.time() - start_time, 2)))

        for b in missing_dps:
            self.report(
                {'WARNING'},
                'An Fcurve has been loaded for the bone {} which is missing in the Faceit Rig. Regenerate the Rig!'.format(b))
            warnings = True

        ############################## Load Expressions ###############################
        # | - Load Expressions Items to list.
        ###########################################################################

        for expression_name, expression_data in expression_data_loaded.items():
            # expression_name = expression_item.get('name')
            mirror_name = expression_data.get('mirror_name')
            side = expression_data.get('side')
            bpy.ops.faceit.add_expression_item(
                'EXEC_DEFAULT',
                expression_name=expression_name,
                side_overwrite=side,
                mirror_name_overwrite=mirror_name,
                corr_sk=self.corr_sk and self.apply_existing_corrective_shape_keys
            )

        ################## Scale new Poses and restore rig properties ###################

        ############################## SCALE ACTION ###############################
        # | - Scale Action to new rig dimensions.
        # | - Eyelid is calculated and skaled separately.
        ###########################################################################

        skip_lid_bones = [
            'lid.T.L.003',
            'lid.T.L.002',
            'lid.T.L.001',
            'lid.B.L.001',
            'lid.B.L.002',
            'lid.B.L.003',
            'lid.B.L',
            'lid.T.L',
            'lid.T.R.003',
            'lid.T.R.002',
            'lid.T.R.001',
            'lid.B.R.001',
            'lid.B.R.002',
            'lid.B.R.003',
            'lid.B.R',
            'lid.T.R',
        ]

        skip_double_constraint = [
            'nose.005',
            'chin.002',
            'nose.003',

        ]

        skip_scale_bones = skip_double_constraint

        if eye_dimensions and self.auto_scale_eyes:
            skip_scale_bones += skip_lid_bones

        action_scale = [1.0, ]*3

        if self.scale_method == 'AUTO':

            rig_dim = list(rig.dimensions.copy())
            for i in range(3):
                action_scale[i] = rig_dim[i] / import_rig_dimesion[i]

            if not all([x == 1 for x in action_scale]):

                if self.auto_scale_method == 'GLOBAL':
                    a_utils.scale_poses_to_new_dimensions_slow(
                        rig,
                        scale=action_scale,
                        filter_skip=skip_scale_bones,
                        frames=new_frames
                    )

                else:
                    a_utils.scale_action_to_rig(
                        new_shape_action,
                        action_scale,
                        filter_skip=skip_lid_bones,
                        frames=new_frames
                    )

        elif self.scale_method == 'OVERWRITE':
            action_scale = self.new_action_scale
            if not all([x == 1 for x in action_scale]):
                a_utils.scale_poses_to_new_dimensions_slow(
                    rig,
                    scale=action_scale,
                    frames=new_frames
                )

        # Scale eyelid expressions to new dimensions!
        if eye_dimensions and self.auto_scale_eyes:
            a_utils.scale_eye_animation(rig, *eye_dimensions)
            pass

        if self.expressions_type == 'ARKIT' and not self.load_custom_path:
            bpy.ops.faceit.procedural_arkit_shapes('INVOKE_DEFAULT', shape='ALL', get_frame_by_index=True)

        # elif self.expressions_type == 'TONGUE':
        # Check if bones exist

        if self.load_method == 'APPEND':
            if shape_action:
                frame_offset = shape_action.frame_range[1] - 1
                for fc in new_shape_action.fcurves:

                    kf_data = fc_dr_utils.kf_data_to_numpy_array(fc)
                    # Apply frame offset to the fcurve data and apply to existing shape action
                    kf_data[:, 0] += frame_offset
                    dp = fc.data_path
                    a_index = fc.array_index
                    existing_fc = shape_action.fcurves.find(dp, index=a_index)
                    if not existing_fc:
                        existing_fc = fc_dr_utils.get_fcurve(dp=dp, array_index=a_index, action=shape_action)
                    fc_dr_utils.populate_keyframe_points_from_np_array(existing_fc, kf_data, add=True)
                    if ow_action:
                        existing_fc = ow_action.fcurves.find(dp, index=a_index)
                        if not existing_fc:
                            existing_fc = fc_dr_utils.get_fcurve(dp=dp, array_index=a_index, action=ow_action)
                        fc_dr_utils.populate_keyframe_points_from_np_array(existing_fc, kf_data, add=True)
            else:
                self.report({'WARNING'}, 'Could not find the Faceit Shape Action. Failed to append')
                warnings = True

            bpy.data.actions.remove(new_shape_action)

        else:
            shape_action = new_shape_action
            shape_action.name = 'faceit_shape_action'

        # if shape_action:
        #     rig.animation_data.action = shape_action
        #     shape_action.use_fake_user = True

        a_utils.restore_constraints_to_default_values(rig)

        if self.load_method == 'OVERWRITE':
            ow_action = a_utils.create_overwrite_animation(rig)

        if ow_action:
            rig.animation_data.action = ow_action
            ow_action.use_fake_user = True
        if shape_action:
            shape_action.use_fake_user = True

        scene.frame_start, scene.frame_end = ow_action.frame_range

        scene.frame_set(save_frame)
        scene.tool_settings.use_keyframe_insert_auto = auto_key

        # scene.faceit_workspace.active_tab = 'EXPRESSIONS'
        rig.data.layers = layer_state[:]

        bpy.ops.pose.select_all(action='DESELECT')
        try:
            bpy.ops.object.mode_set(mode=mode_save)
        except:
            pass

        if warnings:
            self.report(
                {'WARNING'},
                'Operator finished with Warnings. Take a look at the console output for more information.')
        else:
            self.report({'INFO'}, 'New Expressions.')

        if self.corr_sk:
            expression_list = scene.faceit_expression_list

            corrective_sk_action = bpy.data.actions.get('faceit_corrective_shape_keys', None)
            faceit_objects = futils.get_faceit_objects_list()
            for obj in faceit_objects:
                if sk_utils.has_shape_keys(obj):
                    # for item in expression_list:
                    for sk in obj.data.shape_keys.key_blocks:
                        # prefix, expr_name =
                        if sk.name.startswith('faceit_cc_'):
                            expr_name = sk.name.removeprefix('faceit_cc_')
                            # unmute corrective shapes!

                            if self.apply_existing_corrective_shape_keys:
                                expression_item = expression_list
                                sk.mute = False
                            else:
                                obj.shape_key_remove(sk)
                                # scene.faceit_corrective_sk_restorable = False
                    if self.apply_existing_corrective_shape_keys:
                        if len(obj.data.shape_keys.key_blocks) == 1:
                            obj.shape_key_clear()
                        else:
                            if corrective_sk_action:
                                if not obj.data.shape_keys.animation_data:
                                    obj.data.shape_keys.animation_data_create()
                                obj.data.shape_keys.animation_data.action = corrective_sk_action

        return{'FINISHED'}


class FACEIT_OT_ForceZeroFrames(bpy.types.Operator):
    ''' Adds Zero Keyframes for all rest poses inbetween expressions! Effects pose bones and constraints.'''
    bl_idname = 'faceit.force_zero_frames'
    bl_label = 'Force Zero Frames'
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    @ classmethod
    def poll(cls, context):
        scene = context.scene
        rig = futils.get_faceit_armature()
        if rig and scene.faceit_expression_list and context.mode in ['OBJECT', 'POSE']:
            if rig.animation_data:
                if rig.animation_data.action:
                    return True

    def execute(self, context):

        scene = context.scene
        rig = futils.get_faceit_armature()

        scene = context.scene
        save_frame = scene.frame_current
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False
        expression_list = scene.faceit_expression_list
        mode_save = context.mode

        if not context.active_object == rig:
            futils.set_active_object(rig.name)

        layer_state = rig.data.layers[:]
        for i in range(len(rig.data.layers)):
            rig.data.layers[i] = True

        bpy.ops.object.mode_set(mode='POSE')

        bpy.ops.pose.select_all(action='DESELECT')

        expression_count = len(expression_list)

        zero_frames = set()
        # for i in range(expression_count):
        #     frame = (i + 1) * 10
        #     zero_frames.update((frame + 1, frame - 9))
        for exp in expression_list:
            zero_frames.update((exp.frame + 1, exp.frame - 9))

        zero_frames = sorted(list(zero_frames))

        zero_ref_frame = zero_frames[0]
        scene.frame_set(zero_ref_frame)

        for pb in rig.pose.bones:
            layers = pb.bone.layers
            if layers[0] or layers[1] or layers[2]:
                pb.bone.select = True
            else:
                pb.bone.select = False

        bpy.ops.pose.transforms_clear()
        bpy.ops.anim.keyframe_insert(type='Location', confirm_success=False)
        bpy.ops.anim.keyframe_insert(type='Rotation', confirm_success=False)
        bpy.ops.anim.keyframe_insert(type='Scaling', confirm_success=False)

        bpy.ops.object.mode_set()

        bpy.ops.object.mode_set(mode='POSE')
        for fc in rig.animation_data.action.fcurves:
            if 'constraints' in fc.data_path or 'influence' in fc.data_path:
                continue
            kf_zero_value = 0
            # found = False
            # for kf in fc.keyframe_points:
            #     if kf.co[0] == zero_ref_frame:
            #         kf_zero_value = kf.co[1]
            #         found = True
            #         break

            # if not found:
            #     continue

            if 'scale' in fc.data_path:
                kf_zero_value = 1
            elif 'rotation_quaternion' in fc.data_path and i == 0:
                kf_zero_value = 1

            # for f in sorted(zero_frames+new_frames):
            for f in zero_frames:
                fc.keyframe_points.insert(f, kf_zero_value, options={'FAST'})

            fc.update()

        for b_name, constraints_dict in a_utils.bone_constraint_dp_value_dict.items():
            pbone = rig.pose.bones.get(b_name)
            if pbone:
                for c, influence in constraints_dict.items():
                    constraint = pbone.constraints.get(c)
                    if constraint:
                        # constraint.influence = influence
                        fc = fc_dr_utils.get_fcurve(
                            dp='pose.bones["{}"].constraints["{}"].influence'.format(b_name, c),
                            action=rig.animation_data.action)
                        for f in zero_frames:
                            fc.keyframe_points.insert(f, influence, options={'FAST'})

        scene.frame_current = save_frame

        bpy.ops.pose.select_all(action='DESELECT')
        rig.data.layers = layer_state[:]
        scene.tool_settings.use_keyframe_insert_auto = auto_key
        try:
            bpy.ops.object.mode_set(mode=mode_save)
        except:
            pass

        return{'FINISHED'}

# START ####################### VERSION 2 ONLY #######################


class FACEIT_OT_ExportExpressionsToJson(bpy.types.Operator, ExportHelper):
    ''' Export the current Expression file to json format '''
    bl_idname = 'faceit.export_expressions'
    bl_label = 'Export Expressions'
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    filepath: StringProperty(
        subtype="FILE_PATH",
        default='faceit_expressions'
    )

    filter_glob: StringProperty(
        default='*.face;',
        options={'HIDDEN'},
    )

    filename_ext = '.face'
    adjust_scale = True

    @ classmethod
    def poll(cls, context):
        scene = context.scene
        rig = futils.get_faceit_armature()
        if rig and scene.faceit_expression_list:
            if rig.animation_data:
                if rig.animation_data.action:
                    return True

    def execute(self, context):

        scene = context.scene
        rig = futils.get_faceit_armature()

        scene = context.scene
        save_frame = scene.frame_current
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False
        expression_list = scene.faceit_expression_list

        # Get Scale ratio:
        mode_save = context.mode
        if mode_save != 'OBJECT':
            bpy.ops.object.mode_set()
        # Reset all bone transforms!

        futils.set_active_object(rig.name)

        layer_state = rig.data.layers[:]
        for i in range(len(rig.data.layers)):
            rig.data.layers[i] = True

        bpy.ops.object.mode_set(mode='POSE')

        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.transforms_clear()

        bpy.ops.pose.select_all(action='DESELECT')
        try:
            bpy.ops.object.mode_set(mode=mode_save)
        except:
            pass

        rig.data.layers = layer_state[:]

        action_scale = list(rig.dimensions.copy())

        eye_dim_L, eye_dim_R = a_utils.get_eye_dimensions(rig)

        action = rig.animation_data.action

        data = {}
        expression_list_data = {}

        expression_list = scene.faceit_expression_list

        for exp in expression_list:
            expression_list_data[exp.name] = {
                'mirror_name': exp.mirror_name,
                'side': exp.side
            }

        rest_pose_dict = {}
        for pb in rig.pose.bones:
            layers = pb.bone.layers
            if layers[0] == True or layers[1] == True or layers[2] == True:
                rest_pose_dict[pb.name] = list(pb.bone.matrix_local.translation)

        action_dict = {}
        remove_zero_keyframes = True
        remove_zero_poses = True

        for fc in action.fcurves:
            dp = fc.data_path

            array_index = fc.array_index
            kf_data = fc_dr_utils.kf_data_to_numpy_array(fc)

            if remove_zero_poses:
                if 'influence' in fc.data_path or 'mouth_lock' in fc.data_path:
                    pass
                else:
                    kf_data = kf_data[np.logical_not(kf_data[:, 0] % 10 != 0)]

            if remove_zero_keyframes:
                if 'influence' in fc.data_path or 'mouth_lock' in fc.data_path:
                    pass
                else:
                    if 'location' in fc.data_path or 'rotation_euler' in fc.data_path:
                        # delete zero values
                        kf_data = kf_data[np.logical_not(kf_data[:, 1] == 0.0)]
                    elif 'scale' in fc.data_path:
                        kf_data = kf_data[np.logical_not(kf_data[:, 1] == 1.0)]

            kf_anim_data = kf_data.tolist()
            # if kf_anim_data:
            dp_dict = action_dict.get(dp)
            if dp_dict:
                dp_dict[array_index] = kf_anim_data
            else:
                action_dict[dp] = {array_index: kf_anim_data}

        data['action_scale'] = list(action_scale)
        data['eye_dimensions'] = [eye_dim_L, eye_dim_R]
        data['expressions'] = expression_list_data
        data['rest_pose'] = rest_pose_dict
        data['action'] = action_dict

        if not self.filepath.endswith('.face'):
            self.filepath += '.face'

        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        scene.frame_current = save_frame
        scene.tool_settings.use_keyframe_insert_auto = auto_key

        return{'FINISHED'}


class FACEIT_OT_ClearFaceitExpressions(bpy.types.Operator):
    '''Clear all Faceit Expressions'''
    bl_idname = 'faceit.clear_faceit_expressions'
    bl_label = 'Clear Expressions'
    bl_options = {'UNDO', 'INTERNAL'}

    keep_corrective_shape_keys: BoolProperty(
        name='Keep Corrective Shape Keys',
        description='Keep all corrective Shape Keys and try to apply them on a new expression.',
        default=True,
    )

    corr_sk = True

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        self.corr_sk = any([sk_name.startswith('faceit_cc_')
                            for sk_name in sk_utils.get_shape_key_names_from_objects()])

        if self.corr_sk:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def execute(self, context):
        scene = context.scene
        scene.faceit_expression_list.clear()
        scene.faceit_expression_list_index = -1
        shape_action = bpy.data.actions.get('faceit_shape_action')
        ow_action = bpy.data.actions.get('overwrite_shape_action')
        if shape_action:
            bpy.data.actions.remove(shape_action)
        if ow_action:
            bpy.data.actions.remove(ow_action)

        rig = futils.get_faceit_armature()

        if rig:
            if rig.animation_data:
                rig.animation_data.action = None

            for b in rig.pose.bones:
                b.location = Vector()
                b.rotation_euler = Vector()
                b.scale = Vector((1, 1, 1))

        if self.corr_sk:
            faceit_objects = futils.get_faceit_objects_list()

            for obj in faceit_objects:

                if sk_utils.has_shape_keys(obj):
                    for sk in obj.data.shape_keys.key_blocks:
                        if sk.name.startswith('faceit_cc_'):
                            # mute corrective shapes!
                            if self.keep_corrective_shape_keys:
                                sk.mute = True
                                scene.faceit_corrective_sk_restorable = True
                            else:
                                obj.shape_key_remove(sk)
                                scene.faceit_corrective_sk_restorable = False

                    if obj.data.shape_keys.animation_data:
                        a = obj.data.shape_keys.animation_data.action
                        if a:
                            if a.name == 'faceit_corrective_shape_keys':
                                obj.data.shape_keys.animation_data.action = None

                    if len(obj.data.shape_keys.key_blocks) == 1:
                        obj.shape_key_clear()

        a_utils.restore_constraints_to_default_values(rig)

        return{'FINISHED'}


class FACEIT_OT_RemoveExpressionItem(bpy.types.Operator):
    '''Remove the selected Character Geometry from Registration.'''
    bl_idname = 'faceit.remove_expression_item'
    bl_label = 'Remove Expression'
    bl_options = {'UNDO', 'INTERNAL'}

    remove_item: bpy.props.StringProperty(
        default='',
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    @classmethod
    def poll(cls, context):
        idx = context.scene.faceit_expression_list_index

        if idx >= 0 and idx < len(context.scene.faceit_expression_list):
            return True

    def execute(self, context):

        scene = context.scene
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = True

        expression_list = scene.faceit_expression_list
        expression_list_index = scene.faceit_expression_list_index

        ow_action = bpy.data.actions.get('overwrite_shape_action')
        sh_action = bpy.data.actions.get('faceit_shape_action')

        if len(expression_list) <= 1:
            bpy.ops.faceit.clear_faceit_expressions()
            scene.frame_start, scene.frame_end = 1, 250
            return{'FINISHED'}

        def _remove_faceit_item(item):

            item_index = expression_list.find(item.name)

            frame = item.frame

            actions = [ow_action, sh_action]
            for action in actions:
                if action:
                    for curve in action.fcurves:
                        for key in curve.keyframe_points:
                            if key.co[0] == frame:
                                curve.keyframe_points.remove(key, fast=True)
                    for curve in action.fcurves:
                        for key in curve.keyframe_points:
                            if key.co[0] > frame:
                                key.co[0] -= 10

            cc_action = bpy.data.actions.get('faceit_corrective_shape_keys')
            if cc_action:
                for curve in cc_action.fcurves:
                    for key in curve.keyframe_points:
                        if key.co[0] == frame:
                            curve.keyframe_points.remove(key, fast=True)
                for curve in cc_action.fcurves:
                    for key in curve.keyframe_points:
                        if key.co[0] > frame:
                            key.co[0] -= 10

            expression_list.remove(item_index)
            for item in expression_list:
                if item.frame > frame:
                    item.frame -= 10

        # def _remove_expression_keyframes(item):

        # remove from face objects
        if len(expression_list) > 0:
            if self.remove_item:
                item = expression_list[self.remove_item]
            else:
                item = expression_list[expression_list_index]

            # if len(expression_list) > 1 and expression_list.find(item.name) == 0:
            #     self.report({'WARNING'}, 'You should not remove the main facial object')
            # else:
            _remove_faceit_item(item)

        scene.faceit_expression_list_index -= 1

        if expression_list_index <= 0:
            expression_list_index = 0
        if expression_list_index > len(expression_list):
            expression_list_index = len(expression_list) - 1

        # scene.faceit_workspace.active_tab = 'SETUP'
        scene.tool_settings.use_keyframe_insert_auto = auto_key
        if ow_action:
            scene.frame_start, scene.frame_end = ow_action.frame_range

        return {'FINISHED'}


# END ######################### VERSION 2 ONLY #######################


class FACEIT_OT_PoseAmplify(bpy.types.Operator):
    '''Relax Pose of active Expression'''
    bl_idname = 'faceit.pose_amplify'
    bl_label = 'Amplify Pose'
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    expression_index: IntProperty(
        name='Expression to effect',
        options={'HIDDEN', 'SKIP_SAVE'},
        default=-1,
    )

    percentage: FloatProperty(
        name='Percentage',
        default=1.0,
        options={'SKIP_SAVE'},
        # subtype='',
    )

    selected_bones_only: BoolProperty(
        name='Selected Bones only',
        description='Amplify only the selected pose bones, instead of all posed bones.',
        default=False,
        options={'SKIP_SAVE'},
    )

    @ classmethod
    def poll(cls, context):
        scene = context.scene
        rig = futils.get_faceit_armature()
        if rig and scene.faceit_expression_list:
            if rig.animation_data:
                if rig.animation_data.action:
                    return True

    def invoke(self, context, event):
        wm = context.window_manager
        if self.expression_index != -1:
            return wm.invoke_props_popup(self, event)
        else:
            return wm.invoke_props_dialog(self)

    def execute(self, context):

        scene = context.scene
        rig = futils.get_faceit_armature()
        action = rig.animation_data.action

        # effect all expressions if frame -1
        frame = -1
        # Effect specific expression:
        if self.expression_index != -1:
            scene.faceit_expression_list_index = self.expression_index
            expression_list = scene.faceit_expression_list
            expression = expression_list[self.expression_index]
            frame = expression.frame

        if self.selected_bones_only:
            selected_pbones = []
            for pb in rig.pose.bones:
                if pb.bone.select == True:
                    selected_pbones.append(pb.name)
            a_utils.amplify_pose(action, filter_pose_bone_names=selected_pbones,
                                 frame=frame, scale_factor=self.percentage)
        else:
            a_utils.amplify_pose(action, frame=frame, scale_factor=self.percentage)

        self.report({'INFO'}, 'scaled by {}'.format(self.percentage))

        return{'FINISHED'}


class FACEIT_OT_GoToFrame(bpy.types.Operator):
    '''Snap Timeline Cursor to the nearest Expression'''
    bl_idname = 'faceit.set_timeline'
    bl_label = 'Snap Timeline Cursor to Expression'
    bl_options = {'UNDO', 'INTERNAL'}

    @ classmethod
    def poll(cls, context):
        scene = context.scene
        current_expression = scene.faceit_expression_list[scene.faceit_expression_list_index]
        if futils.get_faceit_armature() and current_expression.frame != scene.frame_current:
            return True

    def execute(self, context):

        a_utils.set_pose_from_timeline(context)

        return{'FINISHED'}


class FACEIT_OT_ResetExpression(bpy.types.Operator):
    '''Reset Pose to the originally generated Pose'''
    bl_idname = 'faceit.reset_expression'
    bl_label = 'Reset Expression'
    bl_options = {'UNDO', 'INTERNAL'}

    remove_corrective_shape_keys: bpy.props.BoolProperty(
        name='Remove Corrective Shapes',
        description='Removes the corrective Shape Keys.',
        default=True,
    )

    expression_to_reset: bpy.props.StringProperty(
        name='Expression to Reset',
        default='ALL'
    )

    @ classmethod
    def poll(cls, context):
        rig = futils.get_faceit_armature()
        if rig:
            return rig.hide_viewport == False

    def invoke(self, context, event):
        if context.scene.faceit_use_corrective_shapes and any(
                ['faceit_cc_'+self.expression_to_reset in sk_utils.get_shape_key_names_from_objects()]) or self.expression_to_reset == 'ALL':

            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        if self.expression_to_reset == 'ALL':
            row.prop(self, 'remove_corrective_shape_keys', text='Remove all Corrective Shape Keys', icon='TRASH')
        else:
            row.prop(self, 'remove_corrective_shape_keys', text='Remove Corrective Shape Key?', icon='TRASH')

    def execute(self, context):
        scene = context.scene
        rig = futils.get_faceit_armature()
        if not rig:
            self.report({'WARNING'}, 'The Armature could not be found. Cancelled')
            return{'CANCELLED'}
        mode = context.mode
        save_obj = None
        if context.object == rig:
            pass
        else:
            if mode != 'OBJECT':
                save_obj = context.object
                bpy.ops.object.mode_set(mode='OBJECT')
                futils.clear_object_selection()
                futils.set_active_object(rig.name)

        expression_list = scene.faceit_expression_list
        curr_expression = scene.faceit_expression_list_index

        if self.expression_to_reset == 'ALL':
            if self.remove_corrective_shape_keys:
                bpy.ops.faceit.clear_all_corrective_shapes()
            expressions_operate = expression_list
        else:
            expressions_operate = [expression_list[self.expression_to_reset]]

        for exp in expressions_operate:
            frame = exp.frame
            if self.remove_corrective_shape_keys:
                bpy.ops.faceit.clear_all_corrective_shapes(
                    'EXEC_DEFAULT', expression=exp.name)
            scene.frame_current = frame

            a_utils.reset_key_frame(context, rig, frame)

        scene.faceit_expression_list_index = curr_expression

        if save_obj:
            futils.clear_object_selection()
            futils.set_active_object(save_obj.name)
            if self.remove_corrective_shape_keys and mode == 'SCULPT':
                bpy.ops.object.mode_set()
            else:
                bpy.ops.object.mode_set(mode=mode)
        return{'FINISHED'}


class FACEIT_OT_MirrorOverwriteAnimation(bpy.types.Operator):
    '''Mirror the selected Expression to the opposite side (onyl L and R expressions)'''
    bl_idname = 'faceit.mirror_overwrite'
    bl_label = 'Mirror Expression'
    bl_options = {'UNDO', 'INTERNAL'}

    expression_to_mirror: bpy.props.StringProperty(
        name='Expression to Mirror',
        default='ACTIVE',
    )

    @ classmethod
    def poll(cls, context):
        rig = futils.get_faceit_armature()
        if rig is not None:
            if rig.hide_viewport == False:
                return True

    def execute(self, context):
        # create additive or overwrite animation
        scene = context.scene
        mode_save = context.mode
        frame_save = scene.frame_current

        if context.object:
            obj_save_name = context.object.name

        rig = futils.get_faceit_armature()
        faceit_objects = futils.get_faceit_objects_list()

        if context.object != rig:
            bpy.ops.object.mode_set(mode='OBJECT')

            futils.clear_object_selection()
            futils.set_active_object(rig.name)

        if context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        expression_list = scene.faceit_expression_list

        if self.expression_to_mirror == 'ALL':
            expressions_to_mirror = expression_list
        else:
            expressions_to_mirror = [expression_list[self.expression_to_mirror]]

        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = True

        layer_state = rig.data.layers[:]
        for i in range(len(rig.data.layers)):
            rig.data.layers[i] = True
        for exp in expressions_to_mirror:

            scene.frame_set(exp.frame)

            if exp.mirror_name:
                # mirror_expression = expression_list[exp.mirror_name]
                # mirror_expression = expression_list.get(exp.mirror_name)
                mirror_expression_idx = expression_list.find(exp.mirror_name)
                if mirror_expression_idx == -1:
                    self.report({'WARNING'}, 'The expression {} could not be found'.format(exp.mirror_name))
                    continue

                mirror_expression = expression_list[mirror_expression_idx]

                bpy.ops.pose.reveal(select=False)
                bpy.ops.pose.select_all(action='SELECT')

                bpy.ops.pose.copy()

                scene.frame_set(mirror_expression.frame)

                bpy.ops.pose.paste(flipped=True)

                # bpy.ops.action.keyframe_insert(type='ALL')
                # bpy.ops.anim.keyframe_insert()
                # a_utils.mirror_key_frame(context, exp.frame, mirror_expression.frame)

                bpy.ops.pose.select_all(action='DESELECT')

                scene.faceit_expression_list_index = mirror_expression_idx

        rig.data.layers = layer_state[:]

        scene.tool_settings.use_keyframe_insert_auto = auto_key

        bpy.ops.object.mode_set(mode='OBJECT')

        if scene.faceit_try_mirror_corrective_shapes:

            rig.data.pose_position = 'REST'
            warning_key_words = ['Warning: ', 'failed']

            for exp in expressions_to_mirror:
                if exp.mirror_name:
                    # Try to Mirror Shape Keys
                    # mirror_expression = expression_list[exp.mirror_name]
                    mirror_expression = expression_list.get(exp.mirror_name)
                    if not mirror_expression:
                        self.report({'WARNING'}, 'The expression {} could not be found'.format(exp.mirror_name))
                        continue

                    action_name = 'faceit_corrective_shape_keys'

                    action = bpy.data.actions.get(action_name)

                    if action:

                        for obj in faceit_objects:

                            if sk_utils.has_shape_keys(obj):

                                vert_count = len(obj.data.vertices)

                                futils.clear_object_selection()
                                futils.set_active_object(obj.name)

                                futils.set_hide_obj(obj, False)

                                shape_keys = obj.data.shape_keys.key_blocks

                                for exp in expressions_to_mirror:

                                    sk_name = 'faceit_cc_'+exp.name

                                    sk = obj.data.shape_keys.key_blocks.get(sk_name)

                                    if sk:
                                        # Get mirror expression
                                        # mirror_expression = expression_list[exp.mirror_name]

                                        sk_mirror_name = 'faceit_cc_'+mirror_expression.name
                                        sk_mirror = shape_keys.get(sk_mirror_name)
                                        if sk_mirror:
                                            obj.shape_key_remove(sk_mirror)

                                        new_shape = obj.shape_key_add(name=sk_mirror_name, from_mix=False)

                                        obj.active_shape_key_index = len(shape_keys) - 1
                                        bpy.ops.object.mode_set(mode='EDIT')
                                        bpy.ops.mesh.select_all(action='SELECT')
                                        bpy.ops.mesh.blend_from_shape(shape=sk.name, blend=1.0, add=False)
                                        bpy.ops.object.mode_set(mode='OBJECT')

                                        _stdout_warning = ''

                                        stdout = io.StringIO()

                                        with redirect_stdout(stdout):

                                            bpy.ops.object.shape_key_mirror(
                                                use_topology=scene.faceit_shape_key_mirror_use_topology)

                                        stdout.seek(0)
                                        _stdout_warning = stdout.read()
                                        del stdout

                                        if all([w in _stdout_warning for w in warning_key_words]):
                                            self.report(
                                                {'WARNING'},
                                                '{} for the corrective Shape Key on {} expression'.format(
                                                    _stdout_warning, exp.name))

                                        mirror_expression.corr_shape_key = True
                                        frame = mirror_expression.frame

                                        new_shape.value = 0
                                        new_shape.keyframe_insert(data_path='value', frame=frame - 9)
                                        new_shape.keyframe_insert(data_path='value', frame=frame + 1)
                                        new_shape.value = 1
                                        new_shape.keyframe_insert(data_path='value', frame=frame)

            rig.data.pose_position = 'POSE'

        if obj_save_name:
            futils.clear_object_selection()
            futils.set_active_object(obj_save_name)

            bpy.ops.object.mode_set(mode=mode_save)
        # scene.frame_set(frame_save)

        return{'FINISHED'}


class FACEIT_OT_ProceduralARKitShapes(bpy.types.Operator):
    # tooltip
    '''
    Procedurally create the animations that need to be adapted to character style
    - mouth close is the delta animation between jaw open and lips closed
    - eye blink is the blinking animation that needs to adapted to eye shape
    '''

    bl_idname = 'faceit.procedural_arkit_shapes'
    bl_label = 'Procedurally Generate ARKit Poses'
    bl_options = {'UNDO', 'INTERNAL'}

    shape: EnumProperty(
        name='Expression',
        items=[
            ('ALL', 'All procedural Expressions', 'All procedurally generated Expressions'),
            ('MOUTHCLOSE', 'MouthClose Expression', 'MouthClose Expressions (Opposite of JawOpen'),
            ('EYEBLINK', 'EyeBlink Expression', 'EyeBlink Expressions'),
        ],
        default='ALL',
        description='The Expression to procedurally generate',
    )

    get_frame_by_index: BoolProperty(
        name='Get Expression Frame by index in the initial arkit order',
        default=False,
        options={'SKIP_SAVE'},
    )
    expression_name: StringProperty(
        name='The expression to animate',
        default='',
    )

    @ classmethod
    def poll(cls, context):
        if futils.get_faceit_armature():
            return True

    def execute(self, context):

        scene = context.scene
        rig = futils.get_faceit_armature()

        if rig.animation_data:
            action = rig.animation_data.action
        else:
            action = bpy.data.actions.get('faceit_shape_action')

        mode_save = context.mode
        if context.object != rig:
            bpy.ops.object.mode_set()
            futils.set_active_object(rig.name)

        bpy.ops.object.mode_set(mode='POSE')

        # scene settings
        if scene.is_nla_tweakmode:
            futils.exit_nla_tweak_mode(context)

        expression_list = scene.faceit_expression_list

        def _get_bone_delta(bone1, bone2):
            '''returns object space vector between two pose bones'''
            pos1 = bone1.matrix.translation
            pos2 = bone2.matrix.translation
            vec = pos1 - pos2
            return vec

        if self.shape in ['MOUTHCLOSE', 'ALL']:

            jaw_open_shape = expression_list.get('jawOpen')
            mouth_close_shape = expression_list.get('mouthClose')

            jaw_open_shape_frame = jaw_open_shape.frame
            mouth_close_shape_frame = mouth_close_shape.frame
            if self.get_frame_by_index:
                jaw_open_shape_frame = 180
                mouth_close_shape_frame = 190

            if jaw_open_shape and mouth_close_shape:

                a_utils.ensure_mouth_lock_rig_drivers(rig)

                # for each pose bone: get the delta vector that should be applied to the mouth close shape
                lip_pose_bones = [
                    'lip.T.L.001',
                    'lip.T',
                    'lip.T.R.001',
                    'lip.B.L.001',
                    'lip.B',
                    'lip.B.R.001',
                    'lips.L',
                    'lips.R',
                ]

                a_utils.remove_all_animation_for_frame(action, mouth_close_shape.frame)

                scene.frame_set(mouth_close_shape_frame)
                bpy.ops.pose.select_all(action='SELECT')
                bpy.ops.pose.transforms_clear()
                bpy.ops.pose.select_all(action='DESELECT')

                for b_name in lip_pose_bones:
                    rig.keyframe_insert(
                        data_path='pose.bones["{}"].location'.format(b_name),
                        frame=mouth_close_shape_frame)

                a_utils.copy_keyframe(
                    action, frame_from=jaw_open_shape_frame, frame_to=mouth_close_shape_frame,
                    dp_filter=['pose.bones["jaw_master"]'])

                frames_value_dict = {
                    'original': [-10, 1],
                    'new': [-9, 0],
                }

                jaw_pb = rig.pose.bones.get('jaw_master')
                for value, frames in frames_value_dict.items():
                    if value == 'new':
                        jaw_pb['mouth_lock'] = 1
                    else:
                        jaw_pb['mouth_lock'] = 0

                    for f in frames:
                        rig.keyframe_insert(
                            data_path='pose.bones["jaw_master"]["mouth_lock"]',
                            frame=mouth_close_shape_frame + f)

        if self.shape in ['EYEBLINK', 'ALL']:

            ######################## EYE BLINK ANIM #########################

            top_lid_pose_bones = ['lid.T.L.003', 'lid.T.L.002', 'lid.T.L.001', ]
            bot_lid_pose_bones = ['lid.B.L.001', 'lid.B.L.002', 'lid.B.L.003', ]
            sides = ['L', 'R']  # Left Right
            vec = None

            for side in sides:
                if side == 'L':
                    eye_blink = scene.faceit_expression_list['eyeBlinkLeft']
                    frame = eye_blink.frame
                    if self.get_frame_by_index:
                        frame = 10
                else:
                    eye_blink = scene.faceit_expression_list['eyeBlinkRight']
                    frame = eye_blink.frame
                    if self.get_frame_by_index:
                        frame = 80

                    top_lid_pose_bones = [bone.replace('.L', '.R') for bone in top_lid_pose_bones]
                    bot_lid_pose_bones = [bone.replace('.L', '.R') for bone in bot_lid_pose_bones]

                a_utils.remove_all_animation_for_frame(action, frame)
                bpy.ops.pose.select_all(action='SELECT')
                bpy.ops.pose.transforms_clear()

                for bone in top_lid_pose_bones:
                    bone = rig.pose.bones.get(bone)
                    # remove any constraint influence so the bones can be directly animated
                    a_utils._remove_constraint_influence_for_frame(rig, bone, frame, action=action)

                scene.frame_set(frame)

                for bones in list(zip(top_lid_pose_bones, bot_lid_pose_bones)):
                    top_lid_bone = rig.pose.bones.get(bones[0])
                    bot_lid_bone = rig.pose.bones.get(bones[1])  # the target

                    vec = _get_bone_delta(top_lid_bone, bot_lid_bone)

                    new_pos = top_lid_bone.matrix.translation - vec * 0.9

                    top_lid_bone.matrix.translation = new_pos
                    top_lid_bone.keyframe_insert(data_path='location', frame=frame)

        bpy.ops.object.mode_set(mode=mode_save)

        scene.frame_current = scene.frame_start
        return {'FINISHED'}
