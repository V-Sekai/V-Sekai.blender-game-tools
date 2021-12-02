import bpy
import time
import numpy as np
from typing import Iterable
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty


from . import control_rig_utils
from . import control_rig_data as ctrl_data
from ..core import fc_dr_utils
from ..core import shape_key_utils
from ..core import faceit_utils as futils
from ..retargeting import retarget_list_utils

CRIG_ACTION_SUFFIX = '_control_rig'


def get_enum_shape_key_actions(self, context):
    global actions
    actions = []
    for a in bpy.data.actions:
        if any(['key_block' in fc.data_path for fc in a.fcurves]) or not a.fcurves:
            actions.append((a.name,)*3)

    if not actions:
        actions.append(("None", "None", "None"))

    return actions


def update_enum(self, context):
    if self.action_source:
        new_action_name = self.action_source + CRIG_ACTION_SUFFIX
        self.new_action_name = new_action_name


def update_new_action_name(self, context):
    self.new_action_exists = bool(bpy.data.actions.get(self.new_action_name))


class FACEIT_OT_BakeShapeKeysToControlRig(bpy.types.Operator):
    '''Bake a Shape Key Action to the Control Rig'''
    bl_idname = 'faceit.bake_shape_keys_to_control_rig'
    bl_label = 'Bake Shape Key Action to Control Rig'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    action_source: EnumProperty(
        name='Action',
        items=get_enum_shape_key_actions,
        update=update_enum,
    )

    action_target: EnumProperty(
        name='Action',
        items=(
            ('NEW', 'Create New Action', 'Create a new action on the control rig'),
            ('ACTIVE', 'Active Action', 'Use the current action from the control rig'),
        ),
        default='NEW'
    )
    new_action_name: bpy.props.StringProperty(
        name='Action',
        default='controls_action',
        update=update_new_action_name,
    )
    new_action_exists: bpy.props.BoolProperty(
        name='Action Exists',
        default=False,
    )
    active_action_name: bpy.props.StringProperty(
        name='Action',
        default=''
    )

    c_rig_has_action: bpy.props.BoolProperty(
        name='Action Found',
        default=False,
    )

    overwrite_action: EnumProperty(
        name='Overwrite Action',
        items=(
            ('OVERWRITE', 'Overwrite', 'Overwrite the entire Action. All existing keyframes will be removed.'),
            ('APPEND', 'Append', 'Append the new keyframes. All existing keyframes will be preserved.'),
        ),
    )

    resample_fcurves: bpy.props.BoolProperty(
        name='Resample Keyframes',
        default=False,
        description='Resampling the keyframes will result in better results for some sparse fcurves. The framerate of the animation will change to the scene framerate'
    )

    compensate_amplify_values: bpy.props.BoolProperty(
        name='Compensate Amplify Values',
        default=False,
        description='If this is enabled the amplify values will be inverted during bake, resulting in a one to one bake, even though amplify values are set to non-default values.'
    )

    ignore_use_animation: BoolProperty(
        name='Ignore Mute Property',
        description='Bake all Animation, regardless of the use_animation property in the arkit expressions list',
        default=False,
    )

    remove_sk_action: BoolProperty(
        name='Remove Shape Key Action',
        default=False,
        description='Remove the shape key action. Only used when directly imported to the control rig.',
        options={'SKIP_SAVE', }
    )

    show_advanced_settings: BoolProperty(
        name='Show Advanced Settings',
        default=False,
        description='Blend in the advanced settings for this operator'
    )

    frame_start: IntProperty(
        name='Start Frame',
        default=0,
        options={'SKIP_SAVE', }
    )

    @classmethod
    def poll(self, context):
        if context.mode in ('OBJECT', 'POSE'):
            c_rig = futils.get_faceit_control_armature()
            if c_rig:
                return c_rig.faceit_crig_objects
                # or context.scene.faceit_face_objects
            # return futils.get_faceit_control_armature()

    def invoke(self, context, event):

        if self.remove_sk_action:
            sk_action = None
            pass
        else:
            # Check if the main object has a Shape Key Action applied
            main_obj = futils.get_main_faceit_object()
            sk_action = None
            if shape_key_utils.has_shape_keys(main_obj):
                if main_obj.data.shape_keys.animation_data:
                    sk_action = main_obj.data.shape_keys.animation_data.action

        if sk_action:
            self.action_source = sk_action.name
            self.new_action_name = sk_action.name + CRIG_ACTION_SUFFIX

        # Get current Control Rig action
        rig = futils.get_faceit_control_armature()
        if rig.animation_data:
            a = rig.animation_data.action
            if a:
                self.active_action_name = a.name
                self.c_rig_has_action = True

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def cancel(self, context):
        # The operator got executed from mocap import, undo the import!
        if self.remove_sk_action:
            bpy.ops.ed.undo()

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.label(text='Source Action (Shape Keys)')

        if not self.action_source:
            row = layout.row(align=True)
            row.label(text='No suitable Shape Key Action found. Load Mocap first!')
        else:
            row = layout.row(align=True)
            row.prop(self, 'action_source', text='', icon='ACTION')
            row = layout.row(align=True)
            row.label(text='Target Action (Pose Bones)')

            row = layout.row(align=True)
            row.prop(self, 'action_target', icon='ACTION_TWEAK', expand=True)

            row = layout.row(align=True)
            if self.action_target == 'NEW':
                row.label(text='New Name:')
                row = layout.row(align=True)
                row.prop(self, 'new_action_name', text='', icon='ACTION')
                if self.new_action_exists:
                    row = layout.row(align=True)
                    row.label(text='WARNING! The Action exists already.')
                    row = layout.row(align=True)
                    row.prop(self, 'overwrite_action', expand=True)

            elif self.action_target == 'ACTIVE':
                if self.active_action_name:
                    row.prop(self, 'active_action_name', text='', emboss=False, icon='ACTION')
                    row = layout.row(align=True)
                    row.prop(self, 'overwrite_action', expand=True)
                else:
                    row.label(text='No Active Action on Control Rig')
        if self.overwrite_action == 'OVERWRITE':
            frame_start_txt = 'Frame Start'
        else:
            frame_start_txt = 'Frame Offset'

        row = layout.row()
        row.prop(self, 'frame_start', text=frame_start_txt, icon='CON_TRANSFORM')
        row = layout.row(align=True)
        row.prop(self, 'show_advanced_settings', icon='COLLAPSEMENU')
        if self.show_advanced_settings:
            row = layout.row(align=True)
            row.label(text='Options')
            row = layout.row(align=True)
            row.prop(self, 'resample_fcurves')
            row = layout.row(align=True)
            row.prop(self, 'compensate_amplify_values')

    def execute(self, context):

        scene = context.scene

        c_rig = futils.get_faceit_control_armature()
        futils.set_hide_obj(c_rig, False)

        target_objects = control_rig_utils.get_crig_objects_list(c_rig)
        # if not target_objects:
        #     target_objects = futils.get_faceit_objects_list()

        crig_targets = c_rig.faceit_crig_targets
        # if not crig_targets:
        #     crig_targets = scene.faceit_retarget_shapes

        all_shapes_on_target_objects = shape_key_utils.get_shape_key_names_from_objects(target_objects)
        if not all_shapes_on_target_objects:
            self.report({'ERROR'}, 'The target objects have no shape keys. Did you register the correct object(s)?')
            return{'CANCELLED'}

        # The shape key action
        sk_action = None

        if self.action_source:
            sk_action = bpy.data.actions.get(self.action_source)

        if not sk_action:
            self.report({'ERROR'}, 'Couldn\'t find a suitable action.')
            return{'CANCELLED'}

        if not any(['key_block' in fc.data_path for fc in sk_action.fcurves]):
            self.report(
                {'WARNING'},
                'You can only retarget Shape Key Actions to the control rig. The result may not be expected')

        if not sk_action.fcurves:
            self.report({'ERROR'}, 'There is no animation data in the source Action. Cancelled')
            return{'CANCELLED'}

        if self.resample_fcurves:

            sk_action = sk_action.copy()

        c_rig_action = None

        # Create a new action on the crig object or get active action
        if self.action_target == 'NEW':
            c_rig_action = bpy.data.actions.get(self.new_action_name)

            if not c_rig_action:
                c_rig_action = bpy.data.actions.new(self.new_action_name)
        else:
            c_rig_action = bpy.data.actions.get(self.active_action_name)
            if not c_rig_action:
                self.report({'ERROR'}, 'No Active Action on Control Rig.')
                return{'CANCELLED'}

        if self.overwrite_action == 'OVERWRITE':
            action_name = c_rig_action.name
            bpy.data.actions.remove(c_rig_action)
            c_rig_action = bpy.data.actions.new(action_name)
        else:
            # Add offset to framestart
            kf_end = c_rig_action.frame_range[1]
            self.frame_start = self.frame_start + kf_end

        if not c_rig.animation_data:
            c_rig.animation_data_create()

        c_rig.animation_data.action = c_rig_action

        def resample_fcurves(fc, start, end):
            fc.convert_to_samples(start, end)
            fc.convert_to_keyframes(start, end)

        # collect all existing fcurves that are relevant.
        arkit_curves_values = {}

        missing_animation = []

        frame_range = sk_action.frame_range

        for shape_item in crig_targets:

            if not self.ignore_use_animation:
                if getattr(shape_item, 'use_animation', True) == False:
                    continue

            for target_shape in shape_item.target_shapes:
                dp = 'key_blocks["{}"].value'.format(target_shape.name)
                fc = sk_action.fcurves.find(dp)
                if fc:
                    if not fc.is_empty:
                        if self.resample_fcurves:
                            resample_fcurves(fc, frame_range[0], frame_range[1])
                        # if target_shape.name not in all_shapes_on_target_objects:
                        #     self.report(
                        #         {'WARNING'},
                        #         'The shape key {} has not been found in registered objects.')  # .format(target_shape))

                        arkit_curves_values[shape_item.name] = {
                            'fcurve': fc,
                        }
                else:
                    missing_animation.append(target_shape.name)

        # if missing_animation:
        #     for shape in missing_animation:
        #         self.report(
        #             {'WARNING'},
        #             'Could not find Animation Data for ARKit Expression {} in Action {}.'.format(shape, sk_action.name))

        # c_rig_action = c_rig.animation_data.action

        def scale_to_new_range(
                kf_data, min_range, max_range, sk_max, sk_min, range, main_dir=1, is_scale=False,
                amplify_compensation=1.0):
            '''Scale the keyframe values from shapekeys min/max to the bone range min/max
            @kf_data: the keyframes on shapekey fcurve
            @min_range: new minimum - the minimum range of motion for the bone
            @max_range: new maximum - the max range of motion for the bone
            @sk_max: old maximum - shape_key.slider_max
            @sk_min: old minimum - shape_key.slider_min
            @main_dir: the direction of movement for the target bone. Needed to negate the values
            @amplify_compensation (float): Compensate Amplify values that are baked into the shape key animation
            '''
            # Split the frames from animation values
            # col 0 holds the frames
            frames = kf_data[:, 0]
            # col 1 holds the values
            data = kf_data[:, 1]
            data /= amplify_compensation

            # pos, neg, all bezieht isch auf bone direction
            # main_dir wird nur verwendet wenn all ist gesetzt

            if range == 'pos':
                pass
            elif range == 'neg':
                max_range = min_range

            # negative and positive values for shape keys alloud.
            if range == 'all':
                if main_dir == -1:
                    max_range = min_range

            if is_scale:
                min_range = 1
            else:
                min_range = 0

            # bring the keframe values from the max/min shape key values into the max/min bone range
            scaled_data = ((max_range - min_range) * ((data - sk_min)) / (sk_max - sk_min)) + min_range

            recombined_data = np.vstack((frames, scaled_data)).T
            return recombined_data

        def populate_motion_data_dict(dp, array_index, new_kf_data, is_scale=False):

            # When the target bone uses scale then it needs to receive 3 FCurves (1 for each channel)
            if is_scale:
                array_index = range(3)

            if not isinstance(array_index, Iterable):
                array_index = [array_index]

            for i in array_index:

                # Used to find the fcurve
                fcurve_identifier = '{}_{}'.format(dp, i)

                # Store the motion data for every fcurve in bone_motion_data:
                motion_data = bone_motion_data.get(fcurve_identifier)
                # If there is an entry in the list, then the fcurve controls multiple shapes (e.g pos and neg range)
                if motion_data and not 'scale' in dp:
                    # add the keyframe data to the existing motion
                    try:
                        motion_data['kf_data'][:, 1] += new_kf_data[:, 1]
                    except ValueError:
                        print('motion data on dp {} cant get added...'.format(dp))
                else:
                    # create a new entry
                    bone_motion_data[fcurve_identifier] = {
                        'data_path': dp,
                        'array_index': i,
                        'kf_data': new_kf_data,
                    }

        bone_motion_data = {}

        # Create the new fcurves for the control rig action
        for sk_name, curve_values in arkit_curves_values.items():

            fc = curve_values['fcurve']

            # Get keyframe_data from the shape key fcurve
            kf_data = fc_dr_utils.kf_data_to_numpy_array(fc)
            # Get the bone data for the new fcurve
            dp, array_index, max_range, min_range, value_range, main_dir, _bone_name = ctrl_data.get_bone_animation_data(
                sk_name, c_rig)

            # The shape key min and max slider value
            sk_max = 1
            sk_min = 0

            is_scale = False
            if 'scale' in dp:
                # min_range = 1
                is_scale = True

            # Scale by Amp factor
            if self.compensate_amplify_values:
                amp_factor = getattr(crig_targets.get(sk_name, None), 'amplify')
            else:
                amp_factor = 1.0

            # Scale the range of motion of the values to the range of motion of the bone
            scaled_kf_data = scale_to_new_range(
                kf_data, min_range, max_range, sk_max, sk_min, value_range, main_dir, is_scale=is_scale,
                amplify_compensation=amp_factor)

            populate_motion_data_dict(dp, array_index, scaled_kf_data, is_scale=is_scale)

        for _bone_name, motion_data in bone_motion_data.items():
            data = motion_data['kf_data']
            # Add offset to the motion data
            data_copy = np.copy(data)
            data_copy[:, 0] += self.frame_start
            dp = motion_data['data_path']
            array_index = motion_data['array_index']

            fc = fc_dr_utils.get_fcurve(dp=dp, array_index=array_index, action=c_rig_action)
            fc_dr_utils.populate_keyframe_points_from_np_array(fc, data_copy, add=True)

        # Remove duplicated action (sampled)
        if self.resample_fcurves or self.remove_sk_action:
            bpy.data.actions.remove(sk_action)

        scene.frame_start, scene.frame_end = c_rig_action.frame_range

        return{'FINISHED'}


class FACEIT_OT_BakeControlRigToShapeKeysFromDriver(bpy.types.Operator):
    '''Bake a Control Rig Action into a Shape Key Action. Slow method sets keyframe for each frame. It can also bake multiple animation layers into a new action.'''
    bl_idname = 'faceit.bake_control_rig_to_shape_keys_from_drivers'
    bl_label = 'Bake Control Rig Action to Shape Keys'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    c_rig_operation: EnumProperty(
        name='Operation after Baking',
        items=(
            ('REMOVE', 'Remove Control Rig', 'Remove the Control Rig from the Scene. Can result in data loss'),
            ('HIDE', 'Hide Control Rig', 'Hide the Control Rig in the Scene. Unhide through the Outliner'),
            ('DISCONNECT', 'Disconnect Drivers', 'Only disconnect the drivers. Keep the rig visible.'),
        )
    )

    target_action_name: StringProperty()
    source_action_name: StringProperty()

    @classmethod
    def poll(self, context):
        if context.mode in ('OBJECT', 'POSE'):
            return futils.get_faceit_control_armature()

    def bake_driver_anim_to_shape_key_anim(self, scene, shape_keys):
        ''' tr
        @anim_data [animation_data]: holds all animation/drivers etc.'''
        anim_data = shape_keys.animation_data
        if anim_data is None:
            return
        frame = scene.frame_start

        while frame <= scene.frame_end:
            scene.frame_set(frame)
            for fc in anim_data.drivers.values():
                shape_keys.keyframe_insert(fc.data_path)
            frame = frame + 1

    def execute(self, context):

        c_rig = futils.get_faceit_control_armature()
        futils.set_hide_obj(c_rig, False)

        main_obj = futils.get_main_faceit_object()

        if not shape_key_utils.has_shape_keys(main_obj):
            self.report({'ERROR'}, 'The registered main object has no shape keys. Did you register the correct object(s)?')
            return{'CANCELLED'}

        if not c_rig.animation_data:
            self.report({'WARNING'}, 'The Control Rig has no Action activated. Cancelled operation.')
            return{'CANCELLED'}

        source_action = bpy.data.actions.get(self.source_action_name)
        if not source_action:
            self.report(
                {'WARNING'},
                'Cannot find the Control Rig Action {}.'.format(self.source_action_name))

        c_rig.animation_data.action = source_action

        time_start = time.time()

        shapekeys = main_obj.data.shape_keys

        if not shapekeys.animation_data:
            shapekeys.animation_data_create()

        target_action = bpy.data.actions.get(self.target_action_name)
        if not target_action:
            target_action = bpy.data.actions.new(self.target_action_name)

        shapekeys.animation_data.action = target_action

        self.bake_driver_anim_to_shape_key_anim(context.scene, shapekeys)

        for dr in shapekeys.animation_data.drivers:
            shapekeys.animation_data.drivers.remove(dr)

        bpy.ops.faceit.populate_action(action_name=target_action.name)

        bpy.ops.faceit.remove_control_drivers()
        after_bake_crig_operation(self.c_rig_operation, c_rig)

        self.report({'INFO'}, 'Motion baked to Shape Keys in {} seconds'.format(round(time.time() - time_start, 2)))

        return{'FINISHED'}


def get_enum_non_sk_actions(self, context):
    global actions
    actions = []
    for a in bpy.data.actions:
        if any(['bone' in fc.data_path for fc in a.fcurves]):
            # if not any(['key_block' in fc.data_path for fc in a.fcurves]):
            actions.append((a.name,)*3)

    return actions


def update_enum_non_sk(self, context):
    if self.action_source:
        new_action_name = self.action_source
        if new_action_name.endswith(CRIG_ACTION_SUFFIX):
            # new_action_name = new_action_name.strip(CRIG_ACTION_SUFFIX)
            new_action_name = new_action_name[:-len(CRIG_ACTION_SUFFIX)]

        self.new_action_name = new_action_name


def after_bake_crig_operation(op, c_rig):
    if op == 'REMOVE':
        bpy.data.objects.remove(c_rig)
    elif op == 'HIDE':
        c_rig.hide_set(state=True)
    else:
        pass


class FACEIT_OT_BakeControlRigToShapeKeys(bpy.types.Operator):
    '''Bake the animation from the control rig to the target shapes'''
    bl_idname = 'faceit.bake_control_rig_to_shape_keys'
    bl_label = 'Bake Control Rig Action to Shape Keys'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    c_rig_operation: EnumProperty(
        name='Operation after Baking',
        items=(
            ('REMOVE', 'Remove Control Rig', 'Remove the Control Rig from the Scene. Can result in data loss'),
            ('HIDE', 'Hide Control Rig', 'Hide the Control Rig in the Scene. Unhide through the Outliner'),
            ('DISCONNECT', 'Disconnect Drivers', 'Only disconnect the drivers. Keep the rig visible.'),
        ),
        default='DISCONNECT'
    )

    bake_method: EnumProperty(
        name='Bake Method',
        items=[('FAST', 'Fast Method',
                'This method is very fast. It normalizes the existing fcurves into the shape key ranges. Does not work for animation layers.'),
               ('SLOW', 'Slow Method',
                'This method is very slow. Evaluates the values directly from the drivers. Works for animation layers too.')],
        default='FAST',)

    action_source: EnumProperty(
        name='Action',
        items=get_enum_non_sk_actions,
        update=update_enum_non_sk,
    )

    action_target: EnumProperty(
        name='Action',
        items=(
            ('NEW', 'Create New Action', 'Create a new action on the control rig'),
            ('ACTIVE', 'Active Action', 'Use the current action from the control rig'),
        )
    )

    new_action_name: StringProperty(
        name='Action',
        default='controls_action',
        update=update_new_action_name,
    )

    new_action_exists: BoolProperty(
        name='Action Exists',
        default=False,
    )

    active_action_name: StringProperty(
        name='Action',
        default=''
    )

    overwrite_action: EnumProperty(
        name='Overwrite Action',
        items=(
            ('OVERWRITE', 'Overwrite', 'Overwrite the entire Action. All existing keyframes will be removed.'),
            ('APPEND', 'Append', 'Append the new keyframes. All existing keyframes will be preserved.'),
        ),
    )

    resample_fcurves: BoolProperty(
        name='Resample Keyframes',
        default=False,
        description='Resampling the keyframes will result in better results for some sparse fcurves.'
    )

    copy_fcurve_properties: BoolProperty(
        name='Copy Fcurve Data',
        default=False,
        description='Try to copy all fcurve properties, including keyframe handles and modifiers.'
    )
    copy_fcurve_modifiers: BoolProperty(
        name='Copy Modifiers',
        default=False,
        description='Try to copy all fcurve properties, including keyframe handles and modifiers.'
    )

    copy_fcurve_handles: BoolProperty(
        name='Copy Handles',
        default=False,
        description='Try to copy all fcurve properties, including keyframe handles and modifiers.'
    )

    compensate_amplify_values: BoolProperty(
        name='Bake Amplify Values',
        default=True,
        description='Disabling this can disturb the baked motion.'
    )

    ignore_use_animation: BoolProperty(
        name='Ignore Mute Property',
        description='Bake all Animation, regardless of the use_animation property in the arkit expressions list',
        default=False,
    )

    show_advanced_settings: BoolProperty(
        name='Show Advanced Settings',
        description='Blend in the advanced settings for this operator',
        default=False,
    )

    frame_start: IntProperty(
        name='Start Frame',
        default=0,
        options={'SKIP_SAVE', }
    )

    @classmethod
    def poll(self, context):
        if context.mode in ('OBJECT', 'POSE'):
            c_rig = futils.get_faceit_control_armature()
            if c_rig:
                return c_rig.faceit_crig_objects
                # or context.scene.faceit_face_objects

    def invoke(self, context, event):

        # Get current Control Rig action
        rig = futils.get_faceit_control_armature()
        if rig.animation_data:
            a = rig.animation_data.action
            if a:
                self.action_source = a.name

        # Check if the main object has a Shape Key Action applied
        main_obj = futils.get_main_faceit_object()
        sk_action = None
        if shape_key_utils.has_shape_keys(main_obj):
            if main_obj.data.shape_keys.animation_data:
                sk_action = main_obj.data.shape_keys.animation_data.action

        if not sk_action:
            sk_action = context.scene.faceit_mocap_action
        if sk_action:
            self.active_action_name = sk_action.name

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, 'bake_method', expand=True)
        row = layout.row()

        if self.bake_method == 'SLOW':
            row = layout.row()
            row.label(text='This Operation can take several Minutes. Continue?')

        row = layout.row(align=True)
        row.label(text='Source Action (Pose Bones)')

        # if self.action_source == '-':
        if not self.action_source:
            row = layout.row(align=True)
            row.label(text='No suitable Shape Key Action found. Load Mocap first!')
        else:
            row = layout.row(align=True)
            row.prop(self, 'action_source', text='', icon='ACTION')
            row = layout.row(align=True)
            row.label(text='Target Action (Shape Keys)')

            row = layout.row(align=True)
            row.prop(self, 'action_target', icon='ACTION_TWEAK', expand=True)

            row = layout.row(align=True)
            if self.action_target == 'NEW':
                row.label(text='New Name:')
                row = layout.row(align=True)
                row.prop(self, 'new_action_name', text='', icon='ACTION')
                if self.new_action_exists:
                    row = layout.row(align=True)
                    row.label(text='WARNING! The Action exists already.')
                    if self.bake_method == 'SLOW':
                        row = layout.row(align=True)
                        row.label(text='Animation Data will be overwritten!')
                    else:
                        row = layout.row(align=True)
                        row.prop(self, 'overwrite_action', expand=True)

            elif self.action_target == 'ACTIVE':
                if self.active_action_name:
                    row.prop(self, 'active_action_name', text='', emboss=False, icon='ACTION')
                    if self.bake_method == 'SLOW':
                        row = layout.row(align=True)
                        row.label(text='Animation Data will be overwritten!')
                    else:
                        row = layout.row(align=True)
                        row.prop(self, 'overwrite_action', expand=True)
                else:
                    row.label(text='No Active Action on Control Rig')

        if self.bake_method != 'SLOW':

            if self.overwrite_action == 'OVERWRITE':
                frame_start_txt = 'Frame Start'
            else:
                frame_start_txt = 'Frame Offset'

            row = layout.row()
            row.prop(self, 'frame_start', text=frame_start_txt, icon='CON_TRANSFORM')

            row = layout.row(align=True)
            row.prop(self, 'show_advanced_settings', icon='COLLAPSEMENU')
            if self.show_advanced_settings:
                row = layout.row(align=True)
                row.label(text='Options')
                row = layout.row(align=True)
                row.prop(self, 'resample_fcurves')
                row = layout.row(align=True)
                row.prop(self, 'compensate_amplify_values')
                # row = layout.row(align=True)
                # row.prop(self, 'ignore_use_animation')
                row = layout.row(align=True)
                row.label(text='(EXPERIMENTAL)')
                row = layout.row(align=True)
                row.prop(self, 'copy_fcurve_properties')
                if self.copy_fcurve_properties:
                    row = layout.row(align=True)
                    row.prop(self, 'copy_fcurve_handles')
                    row.prop(self, 'copy_fcurve_modifiers')
                row = layout.row()
                row.label(text='After Baking:')
                row = layout.row()
                # row.prop(self, 'remove_c_rig', icon='TRASH')
                row.prop(self, 'c_rig_operation', expand=True, icon='TRASH')

    def scale_to_new_range(self, kf_data, sk_min, sk_max, bone_min, bone_max, range, main_dir=1, is_scale=False,
                           compensate_amplify=1.0):
        '''Scale the keyframe values from shapekeys min/max to the bone range min/max
        @kf_data: the keyframes on shapekey fcurve
        @sk_max: default shape key max
        @sk_min: shape key min
        @bone_min: new minimum - the minimum range of motion for the bone
        @bone_max: new maximum - the max range of motion for the bone
        @range: (string) in [pos, neg, all] 
        @main_dir: the direction of movement for the target bone. Needed to negate the values
        '''
        # Split the frames from animation values
        # col 0 holds the frames
        frames = kf_data[:, 0]
        # col 1 holds the values
        data = kf_data[:, 1]

        if range == 'pos':
            data = np.clip(data, 0, bone_max)

        elif range == 'neg':
            bone_max = bone_min
            data = np.clip(data, bone_max, 0)

        # negative and positive values for shape keys alloud.
        elif range == 'all':
            if main_dir == -1:
                bone_max = bone_min

        if is_scale:
            bone_min = 1
        else:
            bone_min = 0

        sk_min = 0

        data *= compensate_amplify

        # bring the keframe values from the max/min shape key values into the max/min bone range
        scaled_data = ((sk_max - sk_min) * ((data - bone_min)) / (bone_max - bone_min)) + sk_min

        recombined_data = np.vstack((frames, scaled_data)).T
        return recombined_data

    def execute(self, context):

        scene = context.scene

        c_rig = futils.get_faceit_control_armature()

        target_objects = control_rig_utils.get_crig_objects_list(c_rig)
        if not target_objects:
            target_objects = futils.get_faceit_objects_list()

        crig_targets = c_rig.faceit_crig_targets
        if not crig_targets:
            crig_targets = scene.faceit_retarget_shapes

        all_shapes_on_target_objects = shape_key_utils.get_shape_key_names_from_objects(target_objects)
        if not all_shapes_on_target_objects:
            self.report({'ERROR'}, 'The target objects have no shape keys. Did you register the correct object(s)?')
            return{'CANCELLED'}

        # The rig action
        rig_action = None

        if self.action_source:
            rig_action = bpy.data.actions.get(self.action_source)

        if not rig_action:
            self.report({'ERROR'}, 'Couldn\'t find a suitable action.')
            return{'CANCELLED'}

        if not rig_action.fcurves:
            self.report({'ERROR'}, 'There is no animation data in the active Action. Cancelled')
            return{'CANCELLED'}

        if self.resample_fcurves:

            rig_action = rig_action.copy()

        sk_action = None

        # Create a new action on the crig object or get active action
        if self.action_target == 'NEW':
            sk_action = bpy.data.actions.get(self.new_action_name)
            # if c_rig_action:
            #     self.report({'WARNING'}, ' The new Action exists already. Overwriting.')
            if not sk_action:
                sk_action = bpy.data.actions.new(self.new_action_name)
        else:
            sk_action = bpy.data.actions.get(self.active_action_name)
            if not sk_action:
                self.report({'ERROR'}, 'No Active Shape Key Action found.')
                # self.report({'ERROR'}, 'The Target Actions name doesn\'t match the active action on Control rig.')
                return{'CANCELLED'}

        if self.overwrite_action == 'OVERWRITE' or self.bake_method == 'SLOW':
            action_name = sk_action.name
            bpy.data.actions.remove(sk_action)
            sk_action = bpy.data.actions.new(action_name)
        if self.overwrite_action == 'APPEND':
            # Add offset to framestart
            kf_end = sk_action.frame_range[1]
            self.frame_start = self.frame_start + kf_end

        def resample_fcurves(fc, start, end):
            fc.convert_to_samples(start, end)
            fc.convert_to_keyframes(start, end)

        target_shapes_dict = retarget_list_utils.get_target_shapes_dict(crig_targets)
        if not target_shapes_dict:
            self.report({'ERROR'}, 'No retarget shapes found. Initialize in Shapes panel.')
            return{'CANCELLED'}

        if self.bake_method == 'SLOW':
            bpy.ops.faceit.bake_control_rig_to_shape_keys_from_drivers(
                'EXEC_DEFAULT',
                c_rig_operation=self.c_rig_operation,
                source_action_name=rig_action.name,
                target_action_name=sk_action.name
            )
            return{'FINISHED'}

        # def get_bone_fcurve():

        for obj in target_objects:
            shape_keys = obj.data.shape_keys
            # Create a new action on the crig object or get active action
            if not shape_keys.animation_data:
                shape_keys.animation_data_create()

            shape_keys.animation_data.action = sk_action

        missing_animation = []
        baked_any = False

        for arkit_name, target_shapes_list in target_shapes_dict.items():

            populated_any = False
            skipped = False
            # Ignore deactivated Shapes
            shape_item = crig_targets[arkit_name]
            if not self.ignore_use_animation:
                if getattr(shape_item, 'use_animation', True) == False:
                    skipped = True
                    continue

            # Compensate for the amplification happening on the control rig drivers
            if self.compensate_amplify_values:
                amp_factor = shape_item.amplify
            else:
                amp_factor = 1.0

            # ctrl_data.get_bone_animation_data(arkit_shape, c_rig)
            bone_dp, array_index, max_range, min_range, value_range, main_dir, _bone_name = ctrl_data.get_bone_animation_data(
                arkit_name, c_rig)

            is_scale = False
            if 'scale' in bone_dp:
                is_scale = True

            bone_fcurve = rig_action.fcurves.find(bone_dp, index=array_index)

            sk_min = 0
            sk_max = 1

            if bone_fcurve:

                if not bone_fcurve.is_empty:

                    if self.resample_fcurves:
                        frame_range = rig_action.frame_range
                        resample_fcurves(bone_fcurve, frame_range[0], frame_range[1])

                    #
                    bone_fc_data_dict = None
                    # copy_fcurve_properties = self.copy_fcurve_modifiers or self.copy

                    if self.copy_fcurve_properties and not self.resample_fcurves:
                        bone_fc_data_dict = fc_dr_utils.copy_fcurve_data(bone_fcurve)

                        # kf_data = fc_dr_utils.kf_data_to_numpy_array(bone_fcurve)
                        kf_data = bone_fc_data_dict['kf_coordinates']
                        kf_hl = bone_fc_data_dict['kf_hl_coordinates']
                        kf_hr = bone_fc_data_dict['kf_hr_coordinates']

                        # Scale the range of motion of the values to the range of motion of the bone
                        kf_data = self.scale_to_new_range(
                            kf_data, sk_min, sk_max, min_range, max_range, value_range, main_dir,
                            is_scale=is_scale, compensate_amplify=amp_factor)

                        kf_hl = self.scale_to_new_range(
                            kf_hl, sk_min, sk_max, min_range, max_range, value_range, main_dir,
                            is_scale=is_scale, compensate_amplify=amp_factor)

                        kf_hr = self.scale_to_new_range(
                            kf_hr, sk_min, sk_max, min_range, max_range, value_range, main_dir,
                            is_scale=is_scale, compensate_amplify=amp_factor)

                        # Add frame offset
                        kf_data[:, 0] += self.frame_start
                        kf_hl[:, 0] += self.frame_start
                        kf_hr[:, 0] += self.frame_start

                        # Overwrite the stored fcurve data with new scaled values!
                        bone_fc_data_dict['kf_coordinates'] = kf_data
                        bone_fc_data_dict['kf_hl_coordinates'] = kf_hl
                        bone_fc_data_dict['kf_hr_coordinates'] = kf_hr

                    else:

                        kf_data = fc_dr_utils.kf_data_to_numpy_array(bone_fcurve)

                        kf_data[:, 0] += self.frame_start
                        # Scale the range of motion of the values to the range of motion of the bone
                        kf_data = self.scale_to_new_range(
                            kf_data, sk_min, sk_max, min_range, max_range, value_range, main_dir,
                            is_scale=is_scale, compensate_amplify=amp_factor)

                    for target_shape in target_shapes_list:

                        # if target_shape not in shape_keys.key_blocks:
                        #     self.report(
                        #         {'WARNING'},
                        #         'The shape key {} has not been found in main object. The motion will be baked anyways'.format(target_shape))
                        # continue
                        # Populate the retargeted/baked/scaled keyframe data into the shape key action
                        dp = 'key_blocks["{}"].value'.format(target_shape)

                        if self.copy_fcurve_properties and bone_fc_data_dict:
                            fc_dr_utils.populate_stored_fcurve_data(
                                bone_fc_data_dict, fc=None, dp=dp, action=sk_action,
                                apply_handles=self.copy_fcurve_handles, apply_modifiers=self.copy_fcurve_modifiers)
                        else:
                            fc = fc_dr_utils.get_fcurve(dp=dp, action=sk_action)
                            fc_dr_utils.populate_keyframe_points_from_np_array(fc, kf_data, add=True)
                            # populate_data_to_fcurve(kf_data, dp, action=sk_action)

                        populated_any = True
                        baked_any = True

            if not populated_any and not skipped:
                missing_animation.append(arkit_name)

        if baked_any:
            self.report(
                {'INFO'},
                'Successfully baked Control Rig Action {} to Shape Key Action {}'.format(
                    rig_action.name, sk_action.name))

        bpy.ops.faceit.remove_control_drivers()

        after_bake_crig_operation(self.c_rig_operation, c_rig)
        # Remove duplicated action (sampled)
        if self.resample_fcurves:
            bpy.data.actions.remove(rig_action)

        scene.frame_start, scene.frame_end = sk_action.frame_range

        return{'FINISHED'}
