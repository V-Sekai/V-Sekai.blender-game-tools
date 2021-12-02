
import bpy
from math import floor
from typing import Iterable
from mathutils import Matrix, Vector


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
    driver_data = {
        'type': 'SINGLE_PROP',
        'id_type': 'OBJECT',
        'id': rig,
        'data_path': 'pose.bones["jaw_master"]["mouth_lock"]',
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


def scale_action_to_rig(action, scale, data_path='', invert=False, filter_skip=[], frames=[]):

    # scale = (min(scale),)*3
    if isinstance(scale, Iterable):
        pass
    else:
        scale = (sum(scale)/len(scale),)*3

    fcurves_skip = []
    if filter_skip:
        for b in filter_skip:
            base_dp = 'pose.bones["{}"].'.format(b)
            data_paths = [base_dp+'location', base_dp+'rotation_euler']
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
                    key.co[1] *= scale[i] if invert == False else 1/scale[i]


# def get_dopesheet_area():
#     override_area = None
#     for screen in bpy.context.workspace.screens:
#         for area in screen.areas:
#             if area.type == "DOPESHEET_EDITOR":
#                 return area
#     return None

# override = bpy.context.copy()
# override["area"] = get_dopesheet_area()

# if override["area"] is not None:
#     bpy.ops.anim.channels_setting_enable(override, type='MUTE')

# def disable_all_anim_channels():
#     current_type = bpy.context.area.type
#     bpy.context.area.type = 'DOPESHEET_EDITOR'
#     bpy.ops.anim.channels_setting_enable(mode='ENABLE', type='MUTE')
#     # bpy.ops.nla.tweakmode_exit()
#     bpy.context.area.type = current_type

def matrix_world(armature_ob, bone_name):
    local = armature_ob.data.bones[bone_name].matrix_local
    basis = armature_ob.pose.bones[bone_name].matrix_basis

    parent = armature_ob.pose.bones[bone_name].parent
    if parent == None:
        return local @ basis
    else:
        parent_local = armature_ob.data.bones[parent.name].matrix_local
        return matrix_world(armature_ob, parent.name) @ (parent_local.inverted() @ local) @ basis


def scale_poses_to_new_dimensions_slow(rig, scale=(1, 1, 1), filter_skip=[], frames=[]):
    '''
    Bring a loaded .face pose file to the dimensions of the current character.
    Scale the world location delta for each pose. 
    '''

    action = rig.animation_data.action
    if not action:
        return

    for pb in rig.pose.bones:
        if pb.name not in filter_skip and not any(x in pb.name for x in ['DEF', 'MCH']):
            for c in pb.constraints:
                c.mute = True

    for frame in frames:
        bpy.context.scene.frame_set(frame)
        # for pb in sorted(rig.pose.bones, key=lambda x: get_parent_count(x), reverse=False):
        for pb in rig.pose.bones:
            if pb.name not in filter_skip and not any(x in pb.name for x in ['DEF', 'MCH']):

                if pb.matrix_basis == Matrix.Identity(4):
                    continue

                # Get the pose bone rest position relative to the parent bones pose!
                w_rest = rig.matrix_world @ pb.parent.matrix @ pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local
                # Get the pose bones pose relative to relative rest
                w_pose = w_rest @ pb.matrix_basis

                w_delta = w_pose.translation - w_rest.translation

                # def get_number_above_tresh(num, threshold=1e-06):
                #     return num if abs(num) > abs(threshold) else 0.0

                # w_delta = Vector([get_number_above_tresh(i) for i in w_delta])

                if bpy.app.version >= (2, 90, 0):
                    w_delta_scaled = w_delta * Vector(scale)
                else:
                    w_delta_scaled = Vector([w_delta[i] * scale[i] for i in range(3)])

                w_pose_scaled = Matrix.Translation(w_delta_scaled) @ w_rest
                l_pose_scaled = rig.matrix_world.inverted() @ w_pose_scaled
                pb.matrix = l_pose_scaled

                pb.keyframe_insert('location')

    for pb in rig.pose.bones:
        if pb.name not in filter_skip and not any(x in pb.name for x in ['DEF', 'MCH']):
            for c in pb.constraints:
                c.mute = False


def get_eye_dimensions(rig):

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


def scale_eye_animation(rig, eye_dim_L_old, eye_dim_R_old):

    action = rig.animation_data.action
    if not action:
        return

    eye_dim_L_new, eye_dim_R_new = get_eye_dimensions(rig)

    scale_factor_L = eye_dim_L_new / eye_dim_L_old

    top_lid_pose_bones = ['lid.T.L.003', 'lid.T.L.002', 'lid.T.L.001', ]
    bot_lid_pose_bones = ['lid.B.L.001', 'lid.B.L.002', 'lid.B.L.003', ]
    brow_bot_pose_bones = ['brow.B.L.004', 'brow.B.L.003', 'brow.B.L.002', 'brow.B.L.001', 'brow.B.L']

    amplify_pose(
        action,
        filter_pose_bone_names=(top_lid_pose_bones + bot_lid_pose_bones),
        scale_factor=scale_factor_L
    )

    top_lid_pose_bones = ['lid.T.R.003', 'lid.T.R.002', 'lid.T.R.001', ]
    bot_lid_pose_bones = ['lid.B.R.001', 'lid.B.R.002', 'lid.B.R.003', ]
    brow_bot_pose_bones = ['brow.B.R.004', 'brow.B.R.003', 'brow.B.R.002', 'brow.B.R.001', 'brow.B.R']

    scale_factor_R = eye_dim_R_new / eye_dim_R_old  # / rig_scale_proportions_Z

    amplify_pose(
        action,
        filter_pose_bone_names=(top_lid_pose_bones + bot_lid_pose_bones),
        scale_factor=scale_factor_R
    )


def amplify_pose(action, filter_pose_bone_names=[], frame=-1, scale_factor=1):

    fcurves = []
    if filter_pose_bone_names:
        for b in filter_pose_bone_names:
            base_dp = 'pose.bones["{}"].'.format(b)
            data_paths = [base_dp+'location', base_dp+'rotation_euler']
            for dp in data_paths:
                for i in range(3):
                    fc = action.fcurves.find(dp, index=i)
                    if fc:
                        fcurves.append(fc)
    else:
        fcurves = action.fcurves
    for fc in fcurves:
        if fc.data_path.split('].')[-1] == 'scale':
            continue
        for kf in fc.keyframe_points:
            if frame != -1:
                if kf.co[0] != frame:
                    continue
            kf.co[1] *= scale_factor


def set_pose_from_timeline(context):
    scene = context.scene
    shape_index = scene.faceit_expression_list_index
    if scene.faceit_expression_list[shape_index].frame != scene.frame_current:
        frame = scene.frame_current
        new_index = floor(frame / 10)  # shapes animation every 10 frames
        if frame % 10 == 0:
            new_index = new_index - 1
        scene.faceit_expression_list_index = new_index


bone_constraint_dp_value_dict = {
    'lip.T.L.001': {"Copy Location": 0.25,
                    "Copy Location.001":  0.5,
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
    'lid.T.L.002': {"Copy Location": 0.5, },
    'lid.T.L.001': {"Copy Location": 0.6,
                    "Copy Rotation": 1.0, },
    'lid.B.L.001': {"Copy Rotation": 1.0,
                    "Copy Location": 0.6, },
    'lid.B.L.002': {"Copy Location": 0.5,
                    "Copy Location.001": 0.1, },
    'lid.B.L.003': {"Copy Rotation": 1.0,
                    "Copy Location": 0.6, },
    'brow.B.L.003': {"Copy Location": 0.6, },
    'brow.B.L.002': {"Copy Location": 0.25, },
    'brow.B.L.001': {"Copy Location": 0.6, },
    'lid.T.R.003': {"Copy Location": 0.6, },
    'lid.T.R.002': {"Copy Location": 0.5, },
    'lid.T.R.001': {"Copy Location": 0.6, },
    'lid.B.R.001': {"Copy Location": 0.6, },
    'lid.B.R.002': {"Copy Location": 0.5, },
    'lid.B.R.002': {"Copy Location.001": 0.1, },
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


def restore_constraints_to_default_values(rig):
    for b_name, constraints_dict in bone_constraint_dp_value_dict.items():
        pbone = rig.pose.bones.get(b_name)
        if pbone:
            for c, influence in constraints_dict.items():
                constraint = pbone.constraints.get(c)
                if constraint:
                    constraint.influence = influence


def _remove_constraint_influence_for_frame(arm_obj, bone, frame, replace=False, action=None, constraint_filter=[]):
    '''
    Removes the influence for the specified frame for the specified bone
    @arm_obj : the object holding the armature data
    @bone : a pose bone (in arm_obj.data)
    @frame : the frame that should be free of constraint influence
    '''
    if (action or arm_obj) and replace:
        action = action or arm_obj.animation_data.action
        for b_name, constraints_dict in bone_constraint_dp_value_dict.items():
            for c, _influence in constraints_dict.items():
                dp = 'pose.bones["{}"].constraints["{}"].influence'.format(b_name, c)
                fc = action.fcurves.find(dp)
                if fc:
                    action.fcurves.remove(fc)

    frames_value_dict = {
        'original': [-10, 1],
        'zero': [-9, 0],
    }

    bone_constraints = bone_constraint_dp_value_dict.get(bone.name)
    if not bone_constraints:
        return

    for c_name, influence_value in bone_constraints.items():
        c = bone.constraints.get(c_name)
        if not c:
            continue

        dp = 'pose.bones["{}"].constraints["{}"].influence'.format(bone.name, c_name)

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


def copy_keyframe(action, frame_from, frame_to, dp_filter=[]):
    for fc in action.fcurves:
        if dp_filter:
            if not any([fd in fc.data_path for fd in dp_filter]):
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


def reset_key_frame(context, rig, frame):
    ''' reset keyframe on overwrite action to original value in shape action (undo edits) '''

    current_type = bpy.context.area.type
    shape_action = bpy.data.actions.get('faceit_shape_action')
    ow_action = bpy.data.actions.get('overwrite_shape_action')
    if not shape_action or not ow_action:
        print('ERROR resetting pose. The shape action could not be found')
        return
    try:
        bpy.context.area.type = 'DOPESHEET_EDITOR'
        bpy.context.space_data.ui_mode = 'ACTION'
        rig.animation_data.action = shape_action
        bpy.context.space_data.dopesheet.show_only_selected = False
        bpy.ops.action.select_all(action='DESELECT')
        context.scene.frame_current = frame
        bpy.ops.action.select_column(mode='CFRA')
        bpy.ops.action.copy()
        rig.animation_data.action = ow_action
        bpy.ops.action.paste()
    except:
        print('ERROR occured while pasting keyframes. Does the pose exist?')
    finally:
        bpy.context.area.type = current_type


def add_expression_keyframes(rig, frame):

    frames = [frame, frame + 1, frame - 9]

    for fc in rig.animation_data.action.fcurves:
        dp = fc.data_path
        ar_index = fc.array_index
        if any(d in dp for d in ['location', 'rotation_euler', 'scale']):
            for fr in frames:
                # ow_action.keyframe_insert(dp, frame=fr)
                try:
                    rig.keyframe_insert(dp, index=ar_index, frame=fr)
                except:
                    rig.keyframe_insert(dp, index=-1, frame=fr)


def remove_all_animation_for_frame(action, frame):
    ''' Removes all keyframes from @action at @frame '''
    for curve in action.fcurves:
        for key in curve.keyframe_points:
            if key.co[0] == frame:
                curve.keyframe_points.remove(key, fast=True)


def remove_fcurve_from_action(action, fcurve_data_path):
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
