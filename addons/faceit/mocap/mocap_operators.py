import os
import bpy
import csv
import numpy as np
from bpy.props import IntProperty, BoolProperty, StringProperty, EnumProperty

from ..core import fc_dr_utils
from ..core import shape_key_utils
from ..core import faceit_utils as futils
from ..core import faceit_data as fdata
from ..retargeting import retarget_list_utils as rutils

from ..ctrl_rig.control_rig_animation_operators import CRIG_ACTION_SUFFIX, get_enum_shape_key_actions, update_new_action_name
from ..ctrl_rig import control_rig_utils as ctrl_utils
from ..ctrl_rig import custom_slider_utils


class FACEIT_OT_NewAction(bpy.types.Operator):
    '''Creates a new Action and OPTIONALLY activates it for all Objects registered in Faceit'''
    bl_idname = 'faceit.new_action'
    bl_label = 'Create New Action'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    action_name: bpy.props.StringProperty(
        name='Action Name',
        default='FaceCapAction',
    )

    populate_animation_data: bpy.props.BoolProperty(
        name='Activate Action',
        description='Populate the new Action to all Objects registered in Faceit',
        default=True,
    )

    head_action: bpy.props.BoolProperty(
        name='Create Head Action',
        description='Creates an action "_head" suffix and populates it to Head Target',
        default=False,
    )

    eye_action: bpy.props.BoolProperty(
        name='Create Eye Action',
        description='Creates an action "_eye" suffix and populates it to Eye Targets',
        default=False,
    )

    @classmethod
    def poll(cls, context):
        # if context.mode == 'OBJECT':
        return True

    def invoke(self, context, event):

        scene = context.scene
        _read_shape_keys, read_head_rotation, read_eye_rotation = \
            scene.faceit_mocap_motion_types.read_settings()

        self.head_action = read_head_rotation
        self.eye_action = read_eye_rotation

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):

        actions = bpy.data.actions
        new_action = actions.new(name=self.action_name)
        # if self.head_action:
        #     actions.new(name=self.action_name + '_head')
        # if self.eye_action:
        #     actions.new(self.action_name + '_eye_L')
        #     actions.new(self.action_name + '_eye_R')

        bpy.ops.faceit.populate_action(action_name=new_action.name)

        return {'FINISHED'}


class FACEIT_OT_PopulateAction(bpy.types.Operator):
    '''Populates the selected Action to all Objects registered with Faceit'''
    bl_idname = 'faceit.populate_action'
    bl_label = 'Activate Action'
    bl_options = {'UNDO', 'INTERNAL'}

    action_name: bpy.props.StringProperty(
        name='New Action',
        default='',
    )

    def execute(self, context):

        # Create a Test Action!
        scene = context.scene
        face_objects = futils.get_faceit_objects_list()

        # if not face_objects:
        #     self.report({'INFO'}, 'You did not register any Objects with Faceit')
        #     return{'FINISHED'}

        if self.action_name:
            new_action = bpy.data.actions.get(self.action_name)
        else:
            new_action = scene.faceit_mocap_action

        if not new_action:
            self.report({'WARNING'}, 'It seems the Action you want to pass does not exist')
            return{'CANCELLED'}

        eye_L_action = bpy.data.actions.get(self.action_name + '_eye_L')
        eye_R_action = bpy.data.actions.get(self.action_name + '_eye_R')
        head_action = bpy.data.actions.get(self.action_name + '_head')

        populate_any = False

        if scene.faceit_mocap_motion_types.blendshapes_target:
            for obj in face_objects:
                shape_keys = obj.data.shape_keys
                if not shape_keys:
                    continue
                if not shape_keys.animation_data:
                    shape_keys.animation_data_create()
                else:
                    # Reset Animation values
                    for sk in shape_keys.key_blocks:
                        sk.value = 0
                populate_any = True
                shape_keys.animation_data.action = new_action

        if head_action:
            head_target = futils.get_object(scene.faceit_mocap_target_head)
            if head_target:
                head_target.animation_data.action = head_action
            else:
                self.report({'WARNING'}, 'You need to specify a Target for Head motion to load an action')

        if eye_L_action or eye_R_action:
            eye_L_empty = futils.get_object(scene.faceit_mocap_target_eye_l)
            eye_R_empty = futils.get_object(scene.faceit_mocap_target_eye_r)
            if eye_L_empty:
                eye_L_empty.animation_data.action = eye_L_action
            else:
                self.report({'WARNING'}, 'You need to specify Targets for Eye motion to load an action')
            if eye_R_empty:
                eye_R_empty.animation_data.action = eye_R_action
            else:
                self.report({'WARNING'}, 'You need to specify Targets for Eye motion to load an action')

        scene.faceit_mocap_action = new_action
        if new_action.frame_range[1] - new_action.frame_range[0] > 1:
            scene.frame_start = scene.frame_current = new_action.frame_range[0]
            scene.frame_end = new_action.frame_range[1]
        # else:
        #     scene.frame_start = scene.frame_current = 0
        #     scene.frame_end = 250

        return{'FINISHED'}


class MocapLoadFromText():
    '''This class bundles utility functions to read and populate Text or CSV mocap data to the registered objects.'''

    shape_key_animation_values = []
    head_rotation_animation_values = []
    eye_L_rotation_animation_values = []
    eye_R_rotation_animation_values = []
    frames = []
    frame_count = 0

    def __init__(
            self, filename, mocap_engine, fps, frame_start, laod_sk, load_head_rot, load_eye_rot):
        self.filename = filename
        self.framerate = fps
        self.mocap_engine = mocap_engine
        self.frame_start = frame_start
        self.read_shapekeys = laod_sk
        self.read_head_rotation = load_head_rot
        self.read_eye_rotation = load_eye_rot
        self.read_mocap()

    def get_frame_count(self):
        return len(self.frames)

    def convert_timecode_to_frames(self, timecode, start=None):
        '''This function converts an SMPTE timecode into frames
        @timecode [str]: format hh:mm:ss:ff
        @start [str]: optional timecode to start at
        '''
        # recording fps
        recorded_framerate = 1/60

        def _seconds(value):
            '''convert value to seconds
            @value [str, int, float]: either timecode or frames
            '''
            if isinstance(value, str):  # value seems to be a timestamp
                _zip_ft = zip((3600, 60, 1, recorded_framerate), value.split(':'))
                return sum(f * float(t) for f, t in _zip_ft)
            elif isinstance(value, (int, float)):  # frames
                return value / self.framerate
            else:
                return 0

        def _frames(seconds):
            '''convert seconds to frames
            @seconds [int]: the number of seconds
            '''
            return seconds * self.framerate

        return _frames(_seconds(timecode) - _seconds(start))

    def read_mocap(self):
        '''returns all animation values set by user in individual lists'''
        # frames = timecodes
        frames = []
        # values ordered as shapekey indices as lists i.g. [0.00, 0.00, 0.01, 0.02...]
        shape_key_animation_values = []
        head_rotation = []
        eye_L = []
        eye_R = []
        first_frame = 0
        with open(self.filename) as csvfile:
            reader = csv.reader(csvfile)
            if self.mocap_engine == 'EPIC':
                for i, row in enumerate(reader):
                    if not row:
                        continue
                    if i == 0:
                        continue
                    if i == 1:
                        first_frame = self.convert_timecode_to_frames(row[0]) - self.frame_start

                    frames.append(self.convert_timecode_to_frames(row[0]) - first_frame)
                    # Head Motion
                    if self.read_head_rotation:
                        head_rotation.append([float(v) for v in row[54:57]])
                    # Eyes Motion
                    if self.read_eye_rotation:
                        eye_L.append([float(v) for v in row[58:60]])
                        eye_R.append([float(v) for v in row[60:62]])
                    # Blendshapes Motion
                    if self.read_shapekeys:
                        shape_key_animation_values.append([float(v) for v in row[2:54]])

            elif self.mocap_engine == 'FACECAP':
                for row in reader:
                    if not row:
                        continue
                    if row[0] != 'k':
                        continue
                    # Nano seconds since last frame
                    current_frame = self.frame_start + (float(row[1])/1000) * self.framerate
                    frames.append(current_frame)
                    # Head Motion
                    if self.read_head_rotation:
                        head_rotation.append(np.radians([float(v) for v in row[5:8]]))
                    # Eyes Motion
                    if self.read_eye_rotation:
                        eye_L.append(np.radians([float(v) for v in row[8:10]]))
                        eye_R.append(np.radians([float(v) for v in row[10:12]]))
                    # Blendshapes Motion
                    if self.read_shapekeys:
                        shape_key_animation_values.append([float(v) for v in row[12:]])

        self.frames = frames
        self.frame_count = len(frames)
        self.shape_key_animation_values = shape_key_animation_values
        self.head_rotation_animation_values = head_rotation
        self.eye_L_rotation_animation_values = eye_L
        self.eye_R_rotation_animation_values = eye_R

    def get_values_for_animation(self, animation_values, index):
        '''Returns list with the respective captured values per frame'''
        values = []
        if animation_values:
            for j in range(self.frame_count):
                if len(animation_values[j]) > 1:
                    values.append(animation_values[j][index])
                else:
                    values.append(0)
        return values

    def populate_shape_key_motion_data_to_fcurve(self, fc, sk_index=0, scale_value=1.0):  # sk_name, sk_index):
        '''populate the shape key motion data into fcurves
        @sk_name [string]: the name of the shapekey
        @sk_index [int]: the index of the shapekey
        '''

        values = self.get_values_for_animation(self.shape_key_animation_values, sk_index)

        mocap_keyframe_points = fc_dr_utils.frame_value_pairs_to_numpy_array(self.frames, values)
        if scale_value != 1:
            mocap_keyframe_points[:, 1] *= scale_value

        fc_dr_utils.populate_keyframe_points_from_np_array(
            fc,
            mocap_keyframe_points,
            add=True,
            join_with_existing=True  # (not self.overwrite_action)
        )

    def populate_object_transform_motion_data_to_fcurve(
            self, action, dp, motion_type, channels_count, reroute_channels_matrix={}, scale_channels_vector=None,
            invert_values=False):
        '''Populate the motion data into fcurves for each channel of a transform object.
        @part [string]: the part to animate - either eye L, R or head loc, rot
        @action [action id]: the action that should hold or holds the fcurves
        @dp [string]: the data_path of the fcurve (e.g. rotation_euler)
        @channels_count [int]: the number of channels that should be retargeted (e.g. 2 for x/y rotation)
        @reroute_channels_matrix [dict]: A ditionary that maps indices (e.g. to change rotation order)
        @scale_channels_vector [list]: A vector that holds multipliers for each channel (e.g. to negate a value)
        '''
        animation_values = None
        if motion_type == 'head_rot':
            animation_values = self.head_rotation_animation_values
        if motion_type == 'eye_L':
            animation_values = self.eye_L_rotation_animation_values
        if motion_type == 'eye_R':
            animation_values = self.eye_R_rotation_animation_values

        if animation_values:

            for i in range(channels_count):

                values = self.get_values_for_animation(animation_values, index=i)

                if scale_channels_vector:
                    # Scale compensation for unit differences
                    values = np.array(values) * scale_channels_vector[i]

                # indices for XYZ location - reroute to match other coordinate systems
                array_index = reroute_channels_matrix.get(i, i)
                fc = fc_dr_utils.get_fcurve(dp=dp, array_index=array_index, action=action)

                mocap_keyframe_points = fc_dr_utils.frame_value_pairs_to_numpy_array(self.frames, values)

                fc_dr_utils.populate_keyframe_points_from_np_array(
                    fc,
                    mocap_keyframe_points,
                    add=True,
                    join_with_existing=True  # (not self.overwrite_action)
                )


class FACEIT_OT_ImportMocap(bpy.types.Operator):
    '''Import raw mocap data from text or csv files'''
    bl_idname = 'faceit.import_mocap'
    bl_label = 'Import'
    bl_options = {'UNDO', 'INTERNAL'}

    engine: bpy.props.EnumProperty(
        name='mocap engine',
        items=(
            ('FACECAP', 'Face Cap', 'Face Cap TXT'),
            ('EPIC', 'Live Link Face', 'Live Link Face CSV'),
        ),
    )
    # new_action: BoolProperty(
    #     name='Create a new Action',
    #     default=True,
    #     options={'SKIP_SAVE', 'HIDDEN'},
    # )
    load_action_type: EnumProperty(
        name='New or Active Action',
        items=(
            ('NEW', 'New Action', 'Create a new Action and load the mocap data.'),
            ('ACTIVE', 'Active Action', 'Load the mocap data into an existing Action.'),
        )
    )
    new_action_name: StringProperty(
        name='New Action Name',
        update=update_new_action_name,
    )
    new_action_exists: BoolProperty(
        name='Action Exists',
        default=False,
    )
    existing_action: EnumProperty(
        name='Action',
        items=get_enum_shape_key_actions,
    )
    overwrite_action: EnumProperty(
        name='Overwrite Action',
        items=(
            ('OVERWRITE', 'Overwrite', 'Overwrite the entire Action. All existing keyframes will be removed.'),
            ('APPEND', 'Append', 'Append the new keyframes. All existing keyframes will be preserved.'),
        ),
    )
    bake_to_control_rig: BoolProperty(
        name='Bake to Control Rig',
        default=False,
        description='Loads the mocap action directly on the control rig. Creates a temp Action with the 52 Shape Keys.',
        options={'SKIP_SAVE', }
    )

    frame_start: IntProperty(
        name='Start Frame',
        default=0,
        options={'SKIP_SAVE', }

    )

    @classmethod
    def poll(self, context):
        return context.scene.faceit_face_objects

    def invoke(self, context, event):

        # Check if the main object has a Shape Key Action applied
        main_obj = futils.get_main_faceit_object()
        sk_action = None
        if shape_key_utils.has_shape_keys(main_obj):
            if main_obj.data.shape_keys.animation_data:
                sk_action = main_obj.data.shape_keys.animation_data.action

        if sk_action:
            self.existing_action = sk_action.name

        engine_settings = fdata.get_engine_settings(self.engine)
        self.new_action_name = self.get_clean_filename(engine_settings.filename)
        if not self.check_file_path(engine_settings.filename):
            self.report({'ERROR'}, 'Mocap File not set or invalid')
            return {'CANCELLED'}

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        if futils.get_faceit_control_armature():
            row.prop(self, 'bake_to_control_rig', icon='CON_ARMATURE')

        if self.bake_to_control_rig:
            row = layout.row()
            row.label(text='New Action Name:')
            row = layout.row()
            row.prop(self, 'new_action_name', text='', icon='ACTION')
            # row.prop()
        else:
            row = layout.row()
            row.prop(self, 'load_action_type', icon='ACTION', expand=True)
            row = layout.row()
            if self.load_action_type == 'NEW':
                row.label(text='New Action Name:')
                row = layout.row()
                row.prop(self, 'new_action_name', text='', icon='ACTION')
            else:

                row = layout.row()
                row.label(text='Choose a Shape Key Action:')
                row = layout.row()
                row.prop(self, 'existing_action', text='', icon='ACTION')

            if self.new_action_exists or self.load_action_type == 'ACTIVE':
                if self.new_action_exists:
                    row = layout.row()
                    row.label(text='This Action already exists.')
                row = layout.row()
                row.prop(self, 'overwrite_action', expand=True)

            if self.overwrite_action == 'OVERWRITE':
                frame_start_txt = 'Frame Start'
            else:
                frame_start_txt = 'Frame Offset'

            row = layout.row()
            row.prop(self, 'frame_start', text=frame_start_txt, icon='CON_TRANSFORM')

    def check_file_path(self, filename):
        '''Returns True when filename is valid'''
        if not filename or not os.path.exists(filename) or not os.path.isfile(filename):
            return False
        return True

    def get_clean_filename(self, filename):
        '''Returns the string filename - strips directories and file extension'''
        return (filename.split('\\')[-1]).split('.')[0]  # .strip('.{}'.format(file_extension))

    def get_action(self, action_name):
        '''
        Get an action by name, create it if it does not exist
        '''
        action = bpy.data.actions.get(action_name)
        if not action:
            self.report({'INFO'}, 'Creating new Action with name {}'.format(action_name))
            action = bpy.data.actions.new(name=action_name)
        return action

    def execute(self, context):

        scene = context.scene
        scene_framerate = scene.render.fps
        new_frame_range = scene.frame_start, scene.frame_end

        engine_settings = fdata.get_engine_settings(self.engine)

        filename = engine_settings.filename  # self.get_mocap_filename()

        if self.bake_to_control_rig:
            c_rig = futils.get_faceit_control_armature()
            if not c_rig:
                self.report(
                    {'ERROR'},
                    'Can\'t find the active control rig. Please create/choose control rig first or import directly to the meshes.')
                return{'CANCELLED'}

            a_remove = bpy.data.actions.get('mocap_import')
            if a_remove:
                bpy.data.actions.remove(a_remove)
            mocap_action = bpy.data.actions.new('mocap_import')
        else:
            if self.load_action_type == 'NEW':
                bpy.ops.faceit.new_action('EXEC_DEFAULT', action_name=self.new_action_name,
                                          populate_animation_data=True)
                engine_settings.load_to_new_action = False
                mocap_action = scene.faceit_mocap_action
            else:
                mocap_action = bpy.data.actions.get(self.existing_action)
                # scene.faceit_mocap_action = scene.faceit_mocap_action
                # mocap_action = self.existing_action
                pass
            if not mocap_action:
                self.report({'WARNING'}, 'The action couldn\'t be loaded.')
                return({'CANCELLED'})

            action_name = mocap_action.name
            if self.overwrite_action == 'OVERWRITE':
                bpy.data.actions.remove(mocap_action)
                mocap_action = bpy.data.actions.new(action_name)
                bpy.ops.faceit.populate_action(action_name=action_name)
            else:
                # Add offset to framestart
                kf_end = mocap_action.frame_range[1]
                self.frame_start = self.frame_start + kf_end
                bpy.ops.faceit.populate_action(action_name=action_name)
                bpy.ops.faceit.populate_action()

        laod_sk, load_head_rot, load_eye_rot = \
            scene.faceit_mocap_motion_types.read_settings()
        if not (laod_sk or load_head_rot or load_eye_rot):
            self.report({'ERROR'}, 'You have to choose wich type of motion you want to import')
            return {'CANCELLED'}

        mocap_loaded = MocapLoadFromText(filename, self.engine, scene_framerate,
                                         self.frame_start, laod_sk, load_head_rot, load_eye_rot)

        if laod_sk:

            target_objects = []
            retarget_list = {}

            if self.bake_to_control_rig:
                target_objects = ctrl_utils.get_crig_objects_list(c_rig)
                retarget_list = c_rig.faceit_crig_targets
                # if not retarget_list:
                #     self.report(
                #         {'WARNING'},
                #         'No Target Shapes found on the control rig. Trying to use scene target shapes. Please update the control rig.')
                # if not target_objects:
                #     self.report(
                #         {'WARNING'},
                #         'No Target Objects found on the control rig. Trying to use registered faceit objects. Please update the control rig.')
            else:
                retarget_list = scene.faceit_retarget_shapes
                target_objects = futils.get_faceit_objects_list()

            if not target_objects:
                self.report(
                    {'WARNING'},
                    'No registered objects found. {}'.format(
                        'Please update the control rig'
                        if self.bake_to_control_rig else 'Please register objects in Setup panel'))
                return{'CANCELLED'}

            if not retarget_list or not rutils.get_all_set_target_shapes(retarget_list):
                self.report({'WARNING'}, 'Target Shapes are not properly configured. {}'.format(
                    'Please update the control rig' if self.bake_to_control_rig else 'Set up target shapes in ARKit Shapes panel.'))
                return{'CANCELLED'}

            if not shape_key_utils.get_shape_key_names_from_objects(objects=target_objects):
                self.report(
                    {'WARNING'},
                    'The registered objects hold no Shape Keys. Please create Shape Keys before loading mocap data.')
                return{'CANCELLED'}

            arkit_reference_data = fdata.get_shape_data_for_mocap_engine(mocap_engine=self.engine)

            for shape_item in retarget_list:

                if getattr(shape_item, 'use_animation', True) == False:
                    print('Skipping Shape {}, because it is disabled in the shapes list.'.format(shape_item.name))
                    continue

                arkit_ref = arkit_reference_data.get(shape_item.name)
                if not arkit_ref:
                    # This is a custom slider
                    continue

                arkit_index = arkit_ref['index']

                for target_shape in shape_item.target_shapes:

                    dp = 'key_blocks["{}"].value'.format(target_shape.name)
                    fc = fc_dr_utils.get_fcurve(dp=dp, action=mocap_action)

                    mocap_loaded.populate_shape_key_motion_data_to_fcurve(
                        fc, sk_index=arkit_index)

            if self.bake_to_control_rig:
                if mocap_action.fcurves:
                    bpy.ops.faceit.bake_shape_keys_to_control_rig(
                        'INVOKE_DEFAULT',
                        action_source=mocap_action.name,
                        action_target='NEW',
                        new_action_name=self.new_action_name+CRIG_ACTION_SUFFIX,
                        compensate_amplify_values=True,
                        remove_sk_action=True,
                    )
                else:
                    self.report({'WARNING'}, 'No target shapes found. Please update control rig first!')
                    bpy.data.actions.remove(mocap_action)
                    return{'CANCELLED'}
            if (mocap_action.frame_range[1] - mocap_action.frame_range[0]) > 1:
                new_frame_range = mocap_action.frame_range

        # Create new Actions for rotation/location targets with suffixes
        action_prefix = mocap_action.name

        if (load_head_rot):
            # the rotation/location objects set by user
            head_empty = futils.get_object(scene.faceit_mocap_target_head)

            if head_empty:
                # Populate the head motion action with mocap values
                head_action = self.get_action(action_prefix + '_head')

                if not head_empty.animation_data:
                    head_empty.animation_data_create()

                head_empty.animation_data.action = head_action

                # Yaw Pitch Roll
                reroute_UE = {
                    0: 2,
                    1: 0,
                    2: 1,
                }

                reroute_FC = {
                    0: 0,
                    1: 2,
                    2: 1,
                }

                scale_rotation_vec_UE = [
                    1,
                    -1,
                    1,
                ]

                if self.engine == 'FACECAP':
                    reroute_matrix = reroute_FC
                    scale_rotation_vec = None
                else:
                    reroute_matrix = reroute_UE
                    scale_rotation_vec = scale_rotation_vec_UE

                # Head Rotation
                if load_head_rot:

                    mocap_loaded.populate_object_transform_motion_data_to_fcurve(
                        head_action,
                        dp='rotation_euler',
                        motion_type='head_rot',
                        channels_count=3,
                        reroute_channels_matrix=reroute_matrix,
                        scale_channels_vector=scale_rotation_vec

                    )

                new_frame_range = head_action.frame_range
            else:
                self.report({'WARNING'}, 'You did not specify a target for head motion')

        if load_eye_rot:

            eye_L_empty = futils.get_object(scene.faceit_mocap_target_eye_l)
            eye_R_empty = futils.get_object(scene.faceit_mocap_target_eye_r)

            reroute_YZ = {
                0: 0,
                1: 2,
            }

            if eye_L_empty:

                eye_L_action = self.get_action(action_prefix + '_eye_L')

                if not eye_L_empty.animation_data:
                    eye_L_empty.animation_data_create()

                eye_L_empty.animation_data.action = eye_L_action

                mocap_loaded.populate_object_transform_motion_data_to_fcurve(
                    eye_L_action,
                    dp='rotation_euler',
                    motion_type='eye_L',
                    channels_count=2,
                    reroute_channels_matrix=reroute_YZ,
                )
                new_frame_range = eye_L_action.frame_range

            else:
                self.report({'WARNING'}, 'You did not specify a target for Left Eye motion')

            if eye_R_empty:

                eye_R_action = self.get_action(action_prefix + '_eye_R')

                if not eye_R_empty.animation_data:
                    eye_R_empty.animation_data_create()

                eye_R_empty.animation_data.action = eye_R_action

                mocap_loaded.populate_object_transform_motion_data_to_fcurve(
                    eye_R_action,
                    dp='rotation_euler',
                    motion_type='eye_R',
                    channels_count=2,
                    reroute_channels_matrix=reroute_YZ,
                )

                new_frame_range = eye_R_action.frame_range

            else:
                self.report({'WARNING'}, 'You did not specify a target for Left Eye motion')

        # if new_frame_range:
        print(new_frame_range)
        scene.frame_start, scene.frame_end = new_frame_range
        # scene.frame_end = new_frame_range[1]
        # engine_settings.load_to_new_action = False
        # scene.frame_current = self.frame_start
        # if self.bake_to_control_rig and self.new_action:
        # bpy.data.actions.remove(mocap_action)

        # else:
        #     self.report({'ERROR'}, 'No motion imported. Did you setup the correct targets?')

        return{'FINISHED'}


class OpenFile(bpy.types.Operator):
    '''Choose a catured file to import as keyframes'''
    bl_idname = 'faceit.custom_path'
    bl_label = 'Load mocap'
    bl_options = {'UNDO', 'INTERNAL'}

    engine: bpy.props.EnumProperty(
        name='mocap engine',
        items=(
            ('FACECAP', 'Face Cap', 'Face Cap TXT'),
            ('EPIC', 'Live Link Face', 'Live Link Face CSV'),
        ),
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

        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}
