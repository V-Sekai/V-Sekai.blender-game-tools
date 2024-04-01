from math import floor
import re
from typing import Iterable, Tuple

import bpy
from mathutils import Matrix, Vector, Euler, Quaternion
import numpy as np


from ..core.fc_dr_utils import get_fcurve_from_bpy_struct, kf_data_to_numpy_array, populate_keyframe_points_from_np_array


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
    if rot_mode_from == rot_mode_to:
        return rot
    if rot_mode_from == 'EULER':
        rot = rot.to_quaternion()
        if rot_mode_to == 'AXIS_ANGLE':
            vec, angle = rot.to_axis_angle()
            rot = [angle]
            rot.extend([i for i in vec])
        return rot
    elif rot_mode_from == 'QUATERNION':
        if rot_mode_to == 'EULER':
            rot = rot.to_euler()
        else:
            vec, angle = rot.to_axis_angle()
            rot = [angle]
            rot.extend([i for i in vec])
        return rot
    else:
        if rot_mode_to == 'EULER':
            rot = rot.to_euler()
        else:
            rot = rot.to_quaternion()
    return rot


def exit_nla_tweak_mode(context):
    '''exit the nla tweak mode (important for nla editor actions)'''
    current_type = bpy.context.area.type
    bpy.context.area.type = 'NLA_EDITOR'
    bpy.ops.nla.tweakmode_exit()
    bpy.context.area.type = current_type


def create_default_zero_frames(zero_frames, action, rig, bone_filter: list = None):
    '''Create zero keyframes for the given action.'''
    for pb in rig.pose.bones:
        if bone_filter and pb.name not in bone_filter:
            continue
        rot_mode = get_rotation_mode(pb)
        data_paths = [
            "location",
            get_data_path_from_rotation_mode(rot_mode),
            "scale",
        ]

        for prop_dp in data_paths:
            prop = pb.bl_rna.properties.get(prop_dp)
            if prop and getattr(prop, "is_animatable", False):
                # Get the default value
                if not hasattr(prop, "default"):
                    continue
                dp = f'pose.bones["{pb.name}"].{prop.identifier}'
                if getattr(prop, "is_array", False):
                    default_array = [p for p in prop.default_array]
                else:
                    default_array = [prop.default]
                for i, default in enumerate(default_array):
                    fc = action.fcurves.find(dp, index=i)
                    if fc is None:
                        fc = action.fcurves.new(dp, index=i, action_group=pb.name)
                    # Check if the fcurve contains non-default values.
                    # existing_kf_data = kf_data_to_numpy_array(fc)
                    # if np.all(existing_kf_data[:, 1] == default):
                    # Create the keyframe data
                    kf_data = np.array([(f, default) for f in zero_frames], dtype=float)
                    populate_keyframe_points_from_np_array(fc, kf_data, add=True, join_with_existing=True)


# Precompile the regular expressions
bone_name_pattern = re.compile(r'^pose.bones\["([^"]+)"\]')
custom_property_pattern = re.compile(r'^\[["\']([^"^\']+?)["\']\]')
bone_property_pattern = re.compile(r'\A\.(\w+)(?:(?![.\[\]])\b)(?!\["?[^"]+"?\])')
constraint_pattern = re.compile(r'^\.constraints\["([^"]+)"\]\.(\w+)')


def parse_pose_bone_data_path(data_path):
    '''Parses a pose bone data path and returns the property values.'''
    result = {
        "bone_name": "",
        "prop_name": "",
        "custom_prop_name": "",
        # "constraint_name": "",
        # "constraint_prop_name": "",
    }
    bone_match = bone_name_pattern.match(data_path)
    if bone_match:
        result["bone_name"] = bone_match.group(1)
        remaining_path = data_path[bone_match.end():]
        # Check for custom property
        custom_prop_match = custom_property_pattern.search(remaining_path)
        if custom_prop_match:
            result["custom_prop_name"] = custom_prop_match.group(1)
        else:
            constraint_match = constraint_pattern.search(remaining_path)
            if constraint_match:
                pass
                # result["constraint_name"] = constraint_match.group(1)
                # result["constraint_prop_name"] = constraint_match.group(2)
            else:
                # Check for Pose Bone Properties, ensure no trailing dot or square bracket
                bone_prop_match = bone_property_pattern.search(remaining_path)
                if bone_prop_match:
                    result["prop_name"] = bone_prop_match.group(1)
    return result


# if __name__ == "__main__":
#     test_path = 'pose.bones["arm"].constraints["limit_rotation"].enforce'
#     print(parse_pose_bone_data_path(test_path))
#     test_path = 'pose.bones["arm"].rotation_quaternion'
#     print(parse_pose_bone_data_path(test_path))
#     test_path = 'pose.bones["arm"]["mouth_close"]'
#     print(parse_pose_bone_data_path(test_path))
#     test_path = "pose.bones[\"jaw_master\"][\"mouth_lock\"]"
#     print(parse_pose_bone_data_path(test_path))


def get_default_value_from_fcurve(rig, fc):
    '''Gets the property from the data_path and returns a default if it exists.'''
    dp = fc.data_path
    array_index = fc.array_index
    default = None
    if "pose.bones" in dp:
        parsed_data_path = parse_pose_bone_data_path(dp)
        bone_name = parsed_data_path["bone_name"]
        prop_name = parsed_data_path["prop_name"]
        custom_prop_name = parsed_data_path["custom_prop_name"]
        # constraint_name = parsed_data_path["constraint_name"]
        # constraint_prop_name = parsed_data_path["constraint_prop_name"]
        pb = rig.pose.bones.get(bone_name)
        if prop_name:
            prop = pb.bl_rna.properties.get(prop_name)
            if prop:
                if hasattr(prop, "default"):
                    if getattr(prop, "is_array", False):
                        default = prop.default_array[array_index]
                    else:
                        default = prop.default
        elif custom_prop_name:
            prop = pb.id_properties_ui(custom_prop_name)
            default = prop.as_dict().get("default")
            if default is not None:
                if hasattr(default, "__iter__"):
                    default = default[array_index]
        # elif constraint_name:
        #     c = pb.constraints.get(constraint_name)
        #     prop = c.bl_rna.properties.get(constraint_prop_name)
        #     if prop:
        #         if hasattr(prop, "default"):
        #             if getattr(prop, "is_array", False):
        #                 default = prop.default_array[array_index]
        #             else:
        #                 default = prop.default
    # TODO: Find non pose bone animated props.
    return default


def update_zero_frames(zero_frames, action, rig, update_only_non_default_curves=False):
    '''Check the existing fcurves and get the default value for the keyed property.
        If the fcurve contains non-default values, reset the zero frames. Otherwise ignore.
    '''
    # for pb in rig.pose.bones:
    for fc in action.fcurves:
        default = get_default_value_from_fcurve(rig, fc)
        if default is None:
            print(f"Skipping fcurve {fc.data_path} because no default value could be found.")
            return
        if update_only_non_default_curves:
            # Check if the fcurve contains non-default values.
            existing_kf_data = kf_data_to_numpy_array(fc)
            if np.all(existing_kf_data[:, 1] == default):
                # print(f"the fcurve {fc} contains only default values.")
                continue
        # Create the keyframe data
        kf_data = np.array([(f, default) for f in zero_frames], dtype=float)
        populate_keyframe_points_from_np_array(
            fc, kf_data, add=True, join_with_existing=True, overwrite_old_range=False)


def cleanup_unused_fcurves(rig, action):
    '''Removes Fcurves that contain no keyframes or only default values.
        Returns:
            n_removed: number of removed fcurves
    '''
    n_removed = 0
    for fc in action.fcurves:
        if fc.is_empty:
            action.fcurves.remove(fc)
            n_removed += 1
            continue
        default = get_default_value_from_fcurve(rig, fc)
        if default is None:
            print(f"Skipping fcurve {fc.data_path} because no default value could be found.")
            continue
        # Check if the fcurve contains non-default values.
        existing_kf_data = kf_data_to_numpy_array(fc)
        if np.all(existing_kf_data[:, 1] == default):
            n_removed += 1
            action.fcurves.remove(fc)
    return n_removed


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
