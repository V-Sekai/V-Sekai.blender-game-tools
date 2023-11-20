from math import floor
from typing import Iterable, Tuple

import bpy
from mathutils import Matrix, Vector, Euler, Quaternion


from ..core.fc_dr_utils import get_fcurve_from_bpy_struct


def get_rotation_mode(target) -> str:
    '''Get the rotation mode from the target (object or bone)'''
    rot_mode = target.rotation_mode
    if len(rot_mode) <= 3:
        # EULER if rotation mode in ('XYZ','ZXY',...)
        rot_mode = 'EULER'
    return rot_mode


def get_data_path_from_rotation_mode(rot_mode):
    '''returns the data path value for the rotation mode (rotation_euler, rotation_quaternion, rotation_axis_angle)'''
    if rot_mode == 'EULER':
        return 'rotation_euler'
    return f'rotation_{rot_mode.lower()}'


def get_rotation_mode_from_data_path_val(dp):
    '''returns the rotation mode of the data path (EULER, QUATERNION, AXIS_ANGLE)'''
    return dp[dp.find("rotation_") + 9:].upper()


def get_data_path_value(full_data_path):
    '''returns the transform part of the data path (location, rotation_euler, rotation_quaternion, rotation_axis_angle, scale)'''
    return full_data_path.split('.')[-1]


def get_bone_name_from_data_path(dp):
    '''returns the bone name of the data path'''
    return dp[dp.find("bones[\"") + 7: dp.find("\"]")]


def get_value_as_rotation(rot_mode, rotation_value):
    '''Returns the rotation value as a rotation
        @param rot_mode: value in ('EULER', 'QUATERNION', 'AXIS_ANGLE')
        @param rotation_value (list): rotation value to convert
    '''
    if rot_mode == 'EULER':
        rot = Euler(rotation_value)
    elif rot_mode == 'QUATERNION':
        rot = Quaternion(rotation_value)
    else:
        angle = rotation_value.pop(0)
        axis = Vector(rotation_value)
        rot = Matrix.Rotation(angle, 4, axis)
    return rot


def convert_rotation_values(rot, rot_mode_from, rot_mode_to):
    """
    converts rotation values to the expected rotation mode of the bone
        @param rot: rotation values to convert (either euler, quaternion or axis angle)
        @param rot_mode_from: rotation mode to convert from
        @param rot_mode_to: rotation mode to convert to
    """
    if rot_mode_from == 'EULER':
        rot = rot.to_quaternion()
        if rot_mode_to == 'AXIS_ANGLE':
            vec, angle = rot.to_axis_angle()
            rot = [angle]
            rot.extend([i for i in vec])
        return rot
    if rot_mode_from == 'QUATERNION':
        if rot_mode_to == 'EULER':
            rot = rot.to_euler()
        else:
            vec, angle = rot.to_axis_angle()
            rot = [angle]
            rot.extend([i for i in vec])
        return rot
    if rot_mode_to == 'EULER':
        rot = rot.to_euler()
    else:
        rot = rot.to_quaternion()
    return rot


def ensure_mouth_lock_rig_drivers(rig):
    driver_dps = {
        'pose.bones["MCH-jaw_master"].constraints["Copy Transforms.001"].influence',
        'pose.bones["MCH-jaw_master.001"].constraints["Copy Transforms.001"].influence',
        'pose.bones["MCH-jaw_master.002"].constraints["Copy Transforms.001"].influence',
        'pose.bones["MCH-jaw_master.003"].constraints["Copy Transforms.001"].influence',
        'pose.bones["MCH-jaw_master"].constraints["Copy Transforms.001"].influence',
        'pose.bones["MCH-jaw_master.001"].constraints["Copy Transforms.001"].influence',
        'pose.bones["MCH-jaw_master.002"].constraints["Copy Transforms.001"].influence',
        'pose.bones["MCH-jaw_master.003"].constraints["Copy Transforms.001"].influence',
    }
    for dp in driver_dps:
        dr = rig.animation_data.drivers.find(dp)
        if dr:
            pass
        else:
            dr = rig.animation_data.drivers.new(dp)
            driver = dr.driver
            var = driver.variables.new()
            var.name = 'mouth_lock'
            var.type = 'SINGLE_PROP'
            t = var.targets[0]
            t.id_type = 'OBJECT'
            t.id = rig
            t.data_path = 'pose.bones["jaw_master"]["mouth_lock"]'


def scale_action_to_rig(action, scale, invert=False, filter_skip: list = None, frames: list = None) -> None:
    '''Scale an action to the face rigs dimensions
    @action [bpy.types.Action]: the action to scale
    @scale [Vector3]: the scale factor
    @invert [bool]: invert the scale
    @filter_skip [list - str]: bone names to skip
    @frames [list - int]: frames to scale
    '''

    if scale is None:
        return

    # scale = (min(scale),)*3
    if isinstance(scale, Iterable):
        pass
    else:
        scale = (sum(scale) / len(scale),) * 3

    fcurves_skip = []
    if filter_skip:
        for b in filter_skip:
            base_dp = f'pose.bones["{b}"].'
            data_paths = [base_dp + 'location', base_dp + 'rotation_euler']
            for dp in data_paths:
                for i in range(3):
                    fc = action.fcurves.find(dp, index=i)
                    if fc:
                        fcurves_skip.append(dp)

    for fcurve in action.fcurves:
        # get the location curves
        if fcurve.data_path in fcurves_skip:
            continue
        if fcurve.data_path.split('].')[-1] == 'location':
            # fcurves array index represents location[x,y,z]
            i = fcurve.array_index
            # scale the animation
            for key in fcurve.keyframe_points:
                if key.co[0] in frames:
                    key.co[1] *= scale[i] if invert is False else 1 / scale[i]


def matrix_world(armature_ob, bone_name):
    '''Recursive function to find the true world matrix for a given bone (without parent transforms).'''
    local = armature_ob.data.bones[bone_name].matrix_local
    basis = armature_ob.pose.bones[bone_name].matrix_basis

    parent = armature_ob.pose.bones[bone_name].parent

    if parent is None:
        return local @ basis

    parent_local = armature_ob.data.bones[parent.name].matrix_local
    return matrix_world(armature_ob, parent.name) @ (parent_local.inverted() @ local) @ basis


def scale_poses_to_new_dimensions_slow(
        rig,
        pose_bones: Iterable[bpy.types.PoseBone],
        scale=(1, 1, 1),
        active_action=None,
        frames: list = None) -> None:
    """
    Bring a loaded .face pose file to the dimensions of the current character. Scale the world location delta for each pose.
        @rig [bpy.types.Object]: the rig to scale
        @scale [Vector3]: the scale factor in world space
        @active_action [bpy.types.Action]: the action to scale
        @frames [list - int]: frames to scale
    """
    if frames is None:
        return
    # Get only the animated bones if possible.
    if active_action:
        for pb in pose_bones:
            dp = f'pose.bones["{pb.name}"].location'
            if not any(fc.data_path == dp for fc in active_action.fcurves):
                pose_bones.remove(pb)
    # Mute all constraints
    for pb in pose_bones:
        for c in pb.constraints:
            c.mute = True
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        for pb in pose_bones:
            if pb.matrix_basis == Matrix.Identity(4):
                continue
            # Get the pose bone rest position relative to the parent bones pose!
            w_rest = rig.matrix_world @ pb.parent.matrix @ pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local
            # Get the pose bones pose relative to relative rest
            w_pose = w_rest @ pb.matrix_basis
            # Get the world translation vector
            w_delta = w_pose.translation - w_rest.translation
            # Scale the translation vector
            if bpy.app.version >= (2, 90, 0):
                w_delta_scaled = w_delta * Vector(scale)
            else:
                w_delta_scaled = Vector([w_delta[i] * scale[i] for i in range(3)])
            # Reconstruction of the pose matrix
            w_pose_scaled = Matrix.Translation(w_delta_scaled) @ w_rest
            l_pose_scaled = rig.matrix_world.inverted() @ w_pose_scaled
            pb.matrix = l_pose_scaled

            pb.keyframe_insert('location', frame=frame)

    for pb in pose_bones:
        for c in pb.constraints:
            c.mute = False


def get_eye_dimensions(rig) -> Tuple:
    '''Get the dimensions/height for left and right eye'''

    ######################## EYE -- LEFT #########################

    top_lid_bone = rig.pose.bones.get('lid.T.L.002')
    bot_lid_bone = rig.pose.bones.get('lid.B.L.002')

    # top_bot_vec = (rig.matrix_world @ top_lid_bone.bone.matrix_local).translation
    bot_pos_world = (rig.matrix_world @ bot_lid_bone.bone.matrix_local).translation
    top_pos_world = (rig.matrix_world @ top_lid_bone.bone.matrix_local).translation
    top_bot_vec = bot_pos_world - top_pos_world
    distance_L = top_bot_vec.length

    top_lid_bone = rig.pose.bones.get('lid.T.R.002')
    bot_lid_bone = rig.pose.bones.get('lid.B.R.002')

    bot_pos_world = (rig.matrix_world @ bot_lid_bone.bone.matrix_local).translation
    top_pos_world = (rig.matrix_world @ top_lid_bone.bone.matrix_local).translation
    top_bot_vec = bot_pos_world - top_pos_world
    # top_bot_vec = (rig.matrix_world @ top_lid_bone.bone.matrix_local).translation - (rig.matrix_world @
    #                                                                                  bot_lid_bone.bone.matrix_local).translation
    distance_R = top_bot_vec.length

    return distance_L, distance_R


def scale_eye_animation(rig, eye_dim_L_old, eye_dim_R_old, action=None) -> None:
    '''Scale the eye animation (all keyframes)'''

    if not action:
        action = rig.animation_data.action
    if not action:
        return

    eye_dim_L_new, eye_dim_R_new = get_eye_dimensions(rig)

    scale_factor_L = eye_dim_L_new / eye_dim_L_old

    top_lid_pose_bones = ['lid.T.L.003', 'lid.T.L.002', 'lid.T.L.001', ]
    bot_lid_pose_bones = ['lid.B.L.001', 'lid.B.L.002', 'lid.B.L.003', ]

    amplify_pose(
        action,
        filter_pose_bone_names=(top_lid_pose_bones + bot_lid_pose_bones),
        scale_factor=scale_factor_L
    )

    top_lid_pose_bones = ['lid.T.R.003', 'lid.T.R.002', 'lid.T.R.001', ]
    bot_lid_pose_bones = ['lid.B.R.001', 'lid.B.R.002', 'lid.B.R.003', ]

    scale_factor_R = eye_dim_R_new / eye_dim_R_old  # / rig_scale_proportions_Z

    amplify_pose(
        action,
        filter_pose_bone_names=(top_lid_pose_bones + bot_lid_pose_bones),
        scale_factor=scale_factor_R
    )


def scale_eye_look_animation(rig, scale_factor=0.25, action=None,) -> None:
    '''Scale the anime eye animation (all keyframes)'''

    if not action:
        action = rig.animation_data.action
    if not action:
        return

    eye_bones = ["eye.R", "eye.L", "eyes", "eye_common"]

    amplify_pose(
        action,
        filter_pose_bone_names=(eye_bones),
        scale_factor=scale_factor
    )


def amplify_pose(action, filter_pose_bone_names: list = None, frame=-1, scale_factor=1.0) -> None:
    '''
    Scale/Amplify the given action.
    @filter_pose_bone_names [list]: if specified, scale only the fcurves for the bones in.
    @frame [int]: specify a single frame. -1 scales all.
    @scale_factor [float]: the factor.
    '''
    for fc in action.fcurves:
        dp = fc.data_path
        bone_name = dp.split('["')[1].split('"]')[0]
        if filter_pose_bone_names:
            if bone_name not in filter_pose_bone_names:
                continue
        if any([s in dp for s in ['location', 'rotation_euler', 'rotation_quaternion']]):
            if 'rotation_quaternion' in dp:
                if fc.array_index == 0:
                    continue
            for kf in fc.keyframe_points:
                if kf.co[1] == 0:
                    continue
                if frame != -1:
                    if kf.co[0] != frame:
                        continue
                kf.co[1] *= scale_factor
        elif 'scale' in dp:
            for kf in fc.keyframe_points:
                if kf.co[1] == 1:
                    continue
                if frame != -1:
                    if kf.co[0] != frame:
                        continue
                # Subtract 1.0 from value and scale it. Then add 1.0 to the result.
                kf.co[1] = ((kf.co[1] - 1.0) * scale_factor) + 1.0


def set_pose_from_timeline(context):
    '''Set the timeline cursor to the closes expression frame.'''
    scene = context.scene
    shape_index = scene.faceit_expression_list_index
    if scene.faceit_expression_list[shape_index].frame != scene.frame_current:
        frame = scene.frame_current
        new_index = floor(frame / 10)  # shapes animation every 10 frames
        if frame % 10 == 0:
            new_index = new_index - 1
        scene.faceit_expression_list_index = new_index


BONE_CONSTRAINT_DP_VALUE_DICT = {
    'lip.T.L.001': {"Copy Location": 0.25,
                    "Copy Location.001": 0.5,
                    "Copy Rotation": 1.0,
                    "Copy Scale": 1.0, },
    'lip.T.R.001': {"Copy Location": 0.25,
                    "Copy Location.001": 0.5,
                    "Copy Rotation": 1.0,
                    "Copy Scale": 1.0, },
    'lip.B.L.001': {"Copy Location": 0.25,
                    "Copy Location.001": 0.5,
                    "Copy Rotation": 1.0,
                    "Copy Scale": 1.0, },
    'lip.B.R.001': {"Copy Location": 0.25,
                    "Copy Location.001": 0.5,
                    "Copy Rotation": 1.0,
                    "Copy Scale": 1.0, },
    'lid.T.L.003': {"Copy Location": 0.6,
                    "Copy Rotation": 1.0, },
    'lid.T.L.002': {"Copy Location": 0.5},
    'lid.T.L.001': {"Copy Location": 0.6,
                    "Copy Rotation": 1.0, },
    'lid.B.L.001': {"Copy Rotation": 1.0,
                    "Copy Location": 0.6, },
    'lid.B.L.002': {"Copy Location": 0.5,
                    "Copy Location.001": 0.1, },
    'lid.B.L.003': {"Copy Rotation": 1.0,
                    "Copy Location": 0.6, },
    'brow.B.L.003': {"Copy Location": 0.6},
    'brow.B.L.002': {"Copy Location": 0.25},
    'brow.B.L.001': {"Copy Location": 0.6},
    'lid.T.R.003': {"Copy Location": 0.6, },
    'lid.T.R.002': {"Copy Location": 0.5, },
    'lid.T.R.001': {"Copy Location": 0.6, },
    'lid.B.R.001': {"Copy Location": 0.6, },
    'lid.B.R.002': {"Copy Location": 0.5,
                    "Copy Location.001": 0.1, },
    'lid.B.R.003': {"Copy Location": 0.6, },
    'brow.B.R.003': {"Copy Location": 0.6, },
    'brow.B.R.002': {"Copy Location": 0.25, },
    'brow.B.R.001': {"Copy Location": 0.6, },
    'nose.005': {'Copy Location': 0.5},
    'nose.003': {'Copy Location': 0.5},
    'nose.L.001': {'Copy Location': 0.2},
    'nose.R.001': {'Copy Location': 0.2},
    'cheek.T.L.001': {'Copy Location': 0.0},
    'cheek.T.R.001': {'Copy Location': 0.0},
    'nose.L': {'Copy Location': 0.25},
    'nose.R': {'Copy Location': 0.25},
    'chin.002': {'Copy Location': 0.5},
    'cheek.B.L.001': {'Copy Location': 0.5},
    'cheek.B.R.001': {'Copy Location': 0.5},
    'brow.T.L.002': {'Copy Location': 0.5, 'Copy Location.001': 0.5},
    'brow.T.R.002': {'Copy Location': 0.5, 'Copy Location.001': 0.5},
}


def restore_constraints_to_default_values(rig) -> None:
    '''Restore all Constraints to their default values.'''
    for b_name, constraints_dict in BONE_CONSTRAINT_DP_VALUE_DICT.items():
        pbone = rig.pose.bones.get(b_name)
        if pbone:
            for c, influence in constraints_dict.items():
                constraint = pbone.constraints.get(c)
                if constraint:
                    constraint.influence = influence


def remove_constraint_influence_for_frame(
        arm_obj: bpy.types.Object,
        bone: bpy.types.PoseBone,
        frame: int,
        replace_fcurve=False,
        action: bpy.types.Action = None) -> None:
    '''
    Removes the influence for the specified frame for the specified bone
    @arm_obj [bpy.types.Object]: the object holding the armature data
    @bone [bpy.types.PoseBone]: a pose bone (in arm_obj.pose.bones)
    @frame [int]: the frame that should be free of constraint influence
    @replace_fcurve [bool]: if true, removes the existing fcurve and recreates it.
    @action [bpy.types.Action]: Specific action to process.
    '''
    if (action or arm_obj) and replace_fcurve:
        action = action or arm_obj.animation_data.action
        if action:
            for b_name, constraints_dict in BONE_CONSTRAINT_DP_VALUE_DICT.items():
                for c, _influence in constraints_dict.items():
                    dp = f'pose.bones["{b_name}"].constraints["{c}"].influence'
                    fc = action.fcurves.find(dp)
                    if fc:
                        action.fcurves.remove(fc)

    frames_value_dict = {
        'original': [-10, 1],
        'zero': [-9, 0],
    }

    bone_constraints = BONE_CONSTRAINT_DP_VALUE_DICT.get(bone.name)
    if not bone_constraints:
        return

    for c_name, influence_value in bone_constraints.items():
        c = bone.constraints.get(c_name)
        if not c:
            continue

        dp = f'pose.bones["{bone.name}"].constraints["{c_name}"].influence'

        if influence_value:
            for value, frames in frames_value_dict.items():
                # if influence_value:

                if value == 'zero':
                    c.influence = 0
                else:
                    c.influence = influence_value

                for f in frames:
                    arm_obj.keyframe_insert(
                        data_path=dp,
                        frame=frame + f)


def copy_keyframe(action, frame_from, frame_to, dp_filter: list = None):
    '''Copy a keyframe_point from one frame to another'''
    for fc in action.fcurves:
        if dp_filter:
            if not any(fd in fc.data_path for fd in dp_filter):
                continue

        for kf in fc.keyframe_points:
            if kf.co[0] == frame_from:
                fc.keyframe_points.insert(frame_to, kf.co[1])
                fc.update()


def mirror_key_frame(context, frame_from, frame_to):
    '''
    mirror keyframe to the opposite side
    @frame_from : frame mirror from
    @frame_to : frame mirror to
    '''
    context = bpy.context
    current_type = context.area.type
    context.area.type = 'DOPESHEET_EDITOR'

    bpy.ops.action.select_all(action='DESELECT')
    # select channels to effect
    bpy.ops.anim.channels_select_all(action='SELECT')
    context.scene.frame_current = frame_from
    bpy.ops.action.select_column(mode='CFRA')
    bpy.ops.action.copy()
    context.scene.frame_current = frame_to
    bpy.ops.action.paste(flipped=True)
    bpy.context.area.type = current_type


def get_default_fc_value(data_path, idx=-1):
    '''return the default value for the given transform channel
    @data_path [str]: the data_path string
    @idx [int]: the array_index
    '''
    val = 0.0
    if 'scale' in data_path or ('rotation_quaternion' in data_path and idx == 0):
        val = 1.0
    return val


def reset_key_frame(action, filter_pose_bone_names, backup_action, frame):
    ''' reset keyframe on overwrite action to original value in shape action (undo edits) '''

    fcurves = []
    if filter_pose_bone_names:
        for bone_name in filter_pose_bone_names:
            base_dp = f'pose.bones["{bone_name}"].'
            data_paths = [base_dp + 'location', base_dp + 'rotation_euler']
            for dp in data_paths:
                for i in range(3):
                    fc = action.fcurves.find(dp, index=i)
                    if fc:
                        fcurves.append(fc)
    else:
        fcurves = action.fcurves

    for fc in fcurves:
        if frame in ([kf.co.x for kf in fc.keyframe_points]):
            dp = fc.data_path
            array_idx = fc.array_index
            backup_fc = backup_action.fcurves.find(dp, index=array_idx)
            if backup_fc:
                val = backup_fc.evaluate(frame)
            else:
                val = get_default_fc_value(dp, idx=array_idx)

            fc.keyframe_points.insert(frame=frame, value=val, options={'FAST'})


def backup_expression(action, backup_action, frame):
    '''save keyframes on frame from override action to backup action (shape action)'''
    for fc in action.fcurves:
        if frame in ([kf.co.x for kf in fc.keyframe_points]):
            dp = fc.data_path
            array_idx = fc.array_index
            bckp_fc = get_fcurve_from_bpy_struct(backup_action.fcurves, dp=dp, array_index=array_idx, replace=False)

            val = fc.evaluate(frame)
            bckp_fc.keyframe_points.insert(frame=frame, value=val, options={'FAST'})


def add_expression_keyframes(rig, frame):
    '''Add a keyframe for given frame on all fcurves in active action'''
    frames = [frame, frame + 1, frame - 9]

    for fc in rig.animation_data.action.fcurves:
        if 'influence' in fc.data_path:
            continue
        dp = fc.data_path
        ar_index = fc.array_index
        for fr in frames:
            fc.keyframe_points.insert(frame=fr, value=get_default_fc_value(dp, idx=ar_index))


def remove_all_animation_for_frame(action, frame):
    ''' Removes all keyframes from @action at @frame '''
    for curve in action.fcurves:
        for key in curve.keyframe_points:
            if key.co[0] == frame:
                curve.keyframe_points.remove(key, fast=True)


def remove_fcurve_from_action(action, fcurve_data_path):
    '''Remove an fcurve from action
    @action [bpy.types.Action]: the action
    @fcurve_data_path [str]: the data_path for the fcurve to remove
    '''
    fc = action.fcurves.find(fcurve_data_path)
    if fc:
        action.fcurves.remove(fc)


def get_active_expression():
    ''' returns the active expression from expression_list property'''
    return bpy.context.scene.faceit_expression_list[bpy.context.scene.faceit_expression_list_index]


def create_overwrite_animation(rig_obj):
    '''
    adds an action to the rig objects stack
    @rig_obj : the rig, that holds the shape animations.
    '''
    original_action = bpy.data.actions.get('faceit_shape_action')

    ow_action = bpy.data.actions.get('overwrite_shape_action')
    if ow_action:
        bpy.data.actions.remove(ow_action)

    ow_action = original_action.copy()
    ow_action.use_fake_user = True
    ow_action.name = 'overwrite_shape_action'
    rig_obj.animation_data.action = ow_action

    return ow_action
