from random import randint

import bpy
from mathutils import Vector

CNTRL_RIG_VERSION = 1.7


def get_random_rig_id():
    range_start = 10**4
    range_end = (10**5) - 1
    return randint(range_start, range_end)


def get_pose_bone_range_from_limit_constraint(pose_bone):
    '''Returns the limit location constraint limits for the passed pose bone'''
    max = min = None
    for c in pose_bone.constraints:
        if c.type in ('LIMIT_LOCATION', 'LIMIT_ROTATION', 'LIMIT_SCALE'):
            max = Vector((c.max_x, c.max_y, c.max_z))
            min = Vector((c.min_x, c.min_y, c.min_z))
    return max, min


def get_default_driver_info_dict(expression_name, range='all'):
    dr_info = {
        'variables': {
            'var': {
                'bone_name': 'c_{}_slider'.format(expression_name),
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': range,
        'main_dir': 1,
    }
    return dr_info


def get_driver_from_retarget_dictionary_fixed_slider_range(
        expression_name, target_shape_key_name, control_rig_id, shape_key_data=None, custom_slider=False,
        current_range='all', jaw_open_shape='jawOpen'):
    '''Creates a driver from the data in the retargeting dict, for the given shape_key_data'''
    if not expression_name:
        return False, None
    if not shape_key_data:
        return False, None
    if not target_shape_key_name:
        print(f'Can\'t find the driver info for shape {expression_name}')
        # target_shape_key_name = arkit_expression_name
        return False, None
    if not shape_key_data.animation_data:
        shape_key_data.animation_data_create()
    driver_dict = get_control_rig_driver_dict(control_rig_id)
    if custom_slider:
        dr_info = get_default_driver_info_dict(expression_name, range=current_range)
    else:
        dr_info = driver_dict[expression_name]
    if dr_info:
        dp = dr_info.get('data_path', f'key_blocks["{target_shape_key_name}"].value')
        shape_key_data.driver_remove(dp, -1)
        target_shape_key = shape_key_data.key_blocks.get(target_shape_key_name)
        if target_shape_key:
            driver = target_shape_key.driver_add('value', -1)
        else:
            return False, None
        dr = driver.driver
        # default type is scripted expression
        dr.type = dr_info.get('type', 'SCRIPTED')
        transform_type = ''
        bone_name = ''
        bone_name, transform_type, transform_space = get_bone_settings_from_driver_dict(dr_info)

        # setup the variables contributing
        variables = dr_info.get('variables', None)
        if variables:
            for v_name, v_data in variables.items():
                var = dr.variables.new()
                var.name = v_name
                type = v_data.get('type', 'TRANSFORMS')
                var.type = type
                t = var.targets[0]
                # standart var for bone transforms
                if type == 'TRANSFORMS':
                    t.id = v_data.get('id', control_rig_id)
                    t.bone_target = v_data.get('bone_name')
                    t.transform_space = v_data.get('transform_space')
                    t.transform_type = v_data.get('transform_type')
                    t.rotation_mode = v_data.get('rotation_mode', 'AUTO')
                # single prob for other properties
                elif type == 'SINGLE_PROP':
                    data_path = v_data.get('data_path', '')
                    if v_name == 'jaw_value':
                        data_path = data_path.replace('{jawOpen}', jaw_open_shape)
                    t.id_type = v_data.get('id_type')
                    _id = v_data.get('id')
                    if _id == '{ARMA}':
                        t.id = control_rig_id.data
                    elif _id == '{SHAPEKEYS}':
                        t.id = shape_key_data
                    else:
                        t.id = _id
                    t.data_path = data_path
        # Set the expression
        expression = dr_info.get('expression', '')
        overwrite_expression = dr_info.get('overwrite_expression', True)
        if '{auto_close_slider_max}' in expression:
            auto_close_bone = control_rig_id.pose.bones.get('c_forceMouthClose_slider')
            max, _min = get_pose_bone_range_from_limit_constraint(auto_close_bone)
            expression = expression.replace('{auto_close_slider_max}', str(max.y))
        # Get the axis in X,Y,Z
        if bone_name:  # and not expression or any([t in expression for t in ('{max_range}', '{min_range}')]):
            bone = control_rig_id.pose.bones.get(bone_name)
            _transform, axis = transform_type.split('_')
            array_index = get_array_index_from_driver[axis]
            max, min = get_pose_bone_range_from_limit_constraint(bone)
            if min or max:
                replace_range_max = max[array_index]
                replace_range_min = min[array_index]
                sk_range = dr_info.get('range')
                main_dir = dr_info.get('main_dir')
                if overwrite_expression:
                    if sk_range == 'pos':
                        expression = 'max( 0, var / {max_range})'
                    elif sk_range == 'neg':
                        expression = 'max( 0, var / {min_range})'
                    elif sk_range == 'all':
                        if main_dir == 1:
                            expression = 'var/{max_range}'
                        elif main_dir == -1:
                            expression = 'var/{min_range}'
                expression = expression.replace(
                    '{max_range}', str(replace_range_max)).replace('{min_range}', str(replace_range_min))

        # add the amplify value
        var = dr.variables.new()
        var.name = 'amp'
        var.type = 'SINGLE_PROP'
        t = var.targets[0]
        t.id_type = 'OBJECT'
        t.id = control_rig_id
        t.data_path = f'["{expression_name}"]'
        # t.data_path = f'faceit_crig_targets["{expression_name}"].amplify'
        dr.expression = '(' + expression + ') * amp'
        return True, bone_name
    else:
        print('Can\'t find the driver info for shape {}'.format(expression_name))
        return False, None


def get_bone_settings_from_driver_dict(dr_info):
    '''Get the bone transform settings from driver_info dictionary (only variable named var)'''
    bone_name = transform_type = transform_space = None
    vars = dr_info.get('variables')
    if vars:
        var = vars.get('var')
        if var:
            bone_name = var.get('bone_name')
            transform_type = var.get('transform_type')
            transform_space = var.get('transform_space')
    return bone_name, transform_type, transform_space


def get_pose_bone_from_driver_dict(rig, arkit_shape_name):
    ''' Returns the pose bone specified in target variable of shape key driver '''
    driver_dict = get_control_rig_driver_dict(rig)
    dr_info = driver_dict[arkit_shape_name]
    bone_name, _, _ = get_bone_settings_from_driver_dict(dr_info)
    return rig.pose.bones.get(bone_name, None)


def get_bone_animation_data(shape_key_name, c_rig):
    '''Returns the values that are needed to retarget animation from shape keys to bones, including:
    data_path: used to create the new fcurve
    array_index: needed for transform channels
    minimum range of the bone for the given expression
    maximum range of the bone for the given expression
    '''
    driver_dict = get_control_rig_driver_dict(c_rig)
    dr_info = driver_dict.get(shape_key_name)
    if not dr_info:
        # Get default dict
        dr_info = get_default_driver_info_dict(shape_key_name)
    bone_name, transform_type, _transform_space = get_bone_settings_from_driver_dict(dr_info)
    # Get the pose bone
    pose_bone = c_rig.pose.bones.get(bone_name)
    if not pose_bone:
        # Create an fcurve that can potentially be used by sliders later.
        pose_bone = c_rig.pose.bones.get('c_slider_ref')
    # get data path and array index
    transform, axis = transform_type.split('_')
    array_index = get_array_index_from_driver[axis]
    # location, rotation_euler, scale
    driver_data_path = get_data_path_from_driver_transform[transform]
    dp = 'pose.bones["{}"].{}'.format(bone_name, driver_data_path)
    max_range, min_range = get_pose_bone_range_from_limit_constraint(pose_bone)
    if not min_range and max_range:
        print('cant find the bone max/min range')
    max_range, min_range = max_range[array_index], min_range[array_index]
    bone_range = dr_info.get('range')
    main_dir = dr_info.get('main_dir', -1)
    # print(shape_key_name)
    # print(max_range, min_range, bone_range, main_dir)
    return dp, array_index, max_range, min_range, bone_range, main_dir, bone_name


def get_control_rig_driver_dict(control_rig):
    '''Get the drivers dict based on the control rig version'''
    ctrl_rig_version = control_rig.get('ctrl_rig_version', 1.0)
    driver_dict = control_rig_drivers_dict
    if ctrl_rig_version > 1.3:
        driver_dict.update(get_eye_2d_driver_dict(control_rig))
    if ctrl_rig_version > 1.5:
        driver_dict.update(update_drivers_1_6())
    return driver_dict


get_data_path_from_driver_transform = {
    # ['location','rotation_euler','scale']
    'LOC': 'location',
    'ROT': 'rotation_euler',
    'SCALE': 'scale',
}
get_array_index_from_driver = {
    'X': 0,
    'Y': 1,
    'Z': 2,
    'AVG': 0,
}


def update_drivers_1_6():
    driver_dict = {
        'noseSneerLeft': {
            'variables': {
                'var': {
                    'bone_name': 'c_nose_sneer.L',
                    'transform_type': 'LOC_Y',
                    'transform_space': 'LOCAL_SPACE',
                },
            },
            'range': 'pos',
        },
        'noseSneerRight': {
            'variables': {
                'var': {
                    'bone_name': 'c_nose_sneer.R',
                    'transform_type': 'LOC_Y',
                    'transform_space': 'LOCAL_SPACE',
                },
            },
            'range': 'pos',
        },
    }
    return driver_dict


def get_eye_2d_driver_dict(control_rig):
    '''Get the driver dict and fill in the missing properties'''
    driver_dict = {}
    mocap2dtarget = control_rig.pose.bones.get('c_LookAt2D_slider2d')
    driver_dict['eyeLookUpLeft'] = {
        'expression': 'max(0, min(amp, wrld))',
        'variables': {
            'var': {
                'bone_name': f'{mocap2dtarget.name}',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
            'wrld': {
                'id': control_rig,
                'bone_name': 'c_lookat_mch.L',
                'transform_type': 'ROT_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
        'overwrite_expression': False,
    }
    driver_dict['eyeLookDownLeft'] = {
        'expression': '-min(0,max(-amp,wrld))',
        'variables': {
            'var': {
                'bone_name': f'{mocap2dtarget.name}',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
            'wrld': {
                'id': control_rig,
                'bone_name': 'c_lookat_mch.L',
                'transform_type': 'ROT_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
        'overwrite_expression': False,
    }
    driver_dict['eyeLookInLeft'] = {
        'expression': '-min(0,max(-amp,wrld))',
        'variables': {
            'var': {
                'bone_name': f'{mocap2dtarget.name}',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
            'wrld': {
                'id': control_rig,
                'bone_name': 'c_lookat_mch.L',
                'transform_type': 'ROT_Z',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'overwrite_expression': False,
        'range': 'neg',
    }
    driver_dict['eyeLookOutLeft'] = {
        'expression': 'max(0,min(amp,wrld))',
        'variables': {
            'var': {
                'bone_name': f'{mocap2dtarget.name}',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
            'wrld': {
                'id': control_rig,
                'bone_name': 'c_lookat_mch.L',
                'transform_type': 'ROT_Z',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
        'overwrite_expression': False,
    }
    driver_dict['eyeLookUpRight'] = {
        'expression': 'max(0, min(amp, wrld))',
        'variables': {
            'var': {
                'bone_name': f'{mocap2dtarget.name}',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
            'wrld': {
                'id': control_rig,
                'bone_name': 'c_lookat_mch.R',
                'transform_type': 'ROT_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
        'overwrite_expression': False,
    }
    driver_dict['eyeLookDownRight'] = {
        'expression': '-min(0,max(-amp,wrld))',
        'variables': {
            'var': {
                'bone_name': f'{mocap2dtarget.name}',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
            'wrld': {
                'id': control_rig,
                'bone_name': 'c_lookat_mch.R',
                'transform_type': 'ROT_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
        'overwrite_expression': False,
    }
    driver_dict['eyeLookInRight'] = {
        'expression': 'max(0,min(amp,wrld))',
        'variables': {
            'var': {
                'bone_name': f'{mocap2dtarget.name}',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
            'wrld': {
                'id': control_rig,
                'bone_name': 'c_lookat_mch.R',
                'transform_type': 'ROT_Z',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
        'overwrite_expression': False,
    }
    driver_dict['eyeLookOutRight'] = {
        'expression': '-min(0,max(-amp,wrld))',
        'variables': {
            'var': {
                'bone_name': f'{mocap2dtarget.name}',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
            'wrld': {
                'id': control_rig,
                'bone_name': 'c_lookat_mch.R',
                'transform_type': 'ROT_Z',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
        'overwrite_expression': False,
    }
    return driver_dict


control_rig_drivers_dict = {
    'eyeBlinkLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eyelid_upper.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        # value in [pos, neg, all] --> positive, negative: only pos, neg direction shape key, all: both directtions
        'range': 'pos',
    },
    'eyeLookDownLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'eyeLookInLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.L',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'eyeLookOutLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.L',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'eyeLookUpLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'eyeSquintLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eyelid_lower.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'eyeWideLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eyelid_upper.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'eyeBlinkRight': {
        'variables': {
            'var': {
                'bone_name': 'c_eyelid_upper.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'eyeLookDownRight': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'eyeLookInRight': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.R',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'eyeLookOutRight': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.R',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'eyeLookUpRight': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'eyeSquintRight': {
        'variables': {
            'var': {
                'bone_name': 'c_eyelid_lower.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'eyeWideRight': {
        # 'expression': 'var/0.02 * s_max',
        'variables': {
            'var': {
                'bone_name': 'c_eyelid_upper.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'jawForward': {
        'variables': {
            'var': {
                'bone_name': 'c_jaw_target',
                'transform_type': 'LOC_Z',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'jawLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_jaw_target',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'jawRight': {
        'variables': {
            'var': {
                'bone_name': 'c_jaw_target',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'jawOpen': {
        'variables': {
            'var': {
                'bone_name': 'c_jaw_target',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': -1,
    },
    'mouthClose': {
        # linear interpolation between the jaw open value and the mouthclose value, controlled by auto_close slider.
        'expression': 'lerp( max ( 0, var / {max_range}), jaw_value * auto_close / {auto_close_slider_max}, auto_close / {auto_close_slider_max})',
        'variables': {
            'var': {
                'bone_name': 'c_lips_closed',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
            'jaw_value': {
                'name': 'jaw_value',
                'id_type': 'KEY',
                'type': 'SINGLE_PROP',
                'id': '{SHAPEKEYS}',
                'data_path': 'key_blocks["{jawOpen}"].value',
            },
            'auto_close': {
                'bone_name': 'c_forceMouthClose_slider',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'overwrite_expression': False,
        'range': 'pos',
        'main_dir': 1,
    } if bpy.app.version >= (2, 90, 0) else {
        'variables': {
            'var': {
                'bone_name': 'c_lips_closed',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
        'main_dir': 1,
    },
    'mouthFunnel': {
        'variables': {
            'var': {
                'bone_name': 'c_mouthFunnel_slider',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthPucker': {
        'variables': {
            'var': {
                'bone_name': 'c_mouthPucker_slider',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthRight': {
        'variables': {
            'var': {
                'bone_name': 'c_mouth_controller',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'mouthLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_mouth_controller',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    # Smile ---- The coefficient describing upward movement of the left corner of the mouth.
    'mouthSmileLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'mouthSmileRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    # Frown ---- The coefficient describing downward movement of the left corner of the mouth.
    'mouthFrownRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'mouthFrownLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    # Dimple ---- The coefficient describing backward movement of the left corner of the mouth.
    'mouthDimpleLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner_adjust.L',
                'transform_type': 'LOC_Z',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': -1,
    },
    'mouthDimpleRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner_adjust.R',
                'transform_type': 'LOC_Z',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': -1,
    },
    # Stretch ---- The coefficient describing leftward movement of the left corner of the mouth.
    'mouthStretchLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner_adjust.L',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthStretchRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner_adjust.R',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': -1,
    },
    'mouthRollLower': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_lower_roll',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthRollUpper': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_upper_roll',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthShrugLower': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_lower',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthShrugUpper': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_upper',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    # Press ---- The coefficient describing upward compression of the lower lip on the left side.
    'mouthPressLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner_adjust.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthPressRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner_adjust.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthLowerDownLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_outer_lower.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': -1,
    },
    'mouthLowerDownRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_outer_lower.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': -1,
    },
    'mouthUpperUpLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_outer_upper.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthUpperUpRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_outer_upper.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'browDownLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_brow_inner.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'browDownRight': {
        'variables': {
            'var': {
                'bone_name': 'c_brow_inner.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'browInnerUp': {
        'variables': {
            'var': {
                'bone_name': 'c_eyebrow_mid',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'browOuterUpLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_brow_outer.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'browOuterUpRight': {
        'variables': {
            'var': {
                'bone_name': 'c_brow_outer.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'cheekPuff': {
        'variables': {
            'var': {
                'bone_name': 'c_cheekPuff_slider',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'cheekSquintLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_cheek_upper.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'cheekSquintRight': {
        'variables': {
            'var': {
                'bone_name': 'c_cheek_upper.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'noseSneerLeft': {
        'expression': '( ( var - 1 ) / 0.5) if var >= 1 else ((- var + 1) / 0.5)',
        # 'expression': '( ( var - 1 ) / 0.5 * {slider_min} ) if var >= 1 else ((- var + 1) / 0.5 * {slider_max} )',
        'variables': {
            'var': {
                'bone_name': 'c_nose_sneer.L',
                'transform_type': 'SCALE_AVG',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'overwrite_expression': False,
        'range': 'all',
        'main_dir': -1,
    },
    'noseSneerRight': {
        # 'expression': 'var / 1.5',
        'expression': '( ( var - 1 ) / 0.5) if abs(var) >= 1 else (((- var + 1) / 0.5))',
        # 'expression': '( ( var - 1 ) / 0.5 * {slider_min} ) if abs(var) >= 1 else (((- var + 1) / 0.5) * {slider_max} )',
        'variables': {
            'var': {
                'bone_name': 'c_nose_sneer.R',
                'transform_type': 'SCALE_AVG',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'overwrite_expression': False,
        'range': 'all',
        'main_dir': -1,
    },
    'tongueOut': {
        'variables': {
            'var': {
                'bone_name': 'c_tongueOut_slider',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
}

match_bones_asymmetry_dict = {
    0: {
        'head': [],
        'tail': [],
        'all': ['c_jaw_target'],
    },
    1: {
        'head': [],
        'tail': [],
        'all': [],
    },
    2: {
        'head': [],
        'tail': [],
        'all': [],
    },
    3: {
        'head': [],
        'tail': [],
        'all': ['c_lips_lower_roll'],
    },
    4: {
        'head': [],
        'tail': [],
        'all': [],
    },
    5: {
        'head': [],
        'tail': [],
        'all': [],
    },
    6: {
        'head': [],
        'tail': [],
        'all': ['c_lips_lower', 'c_mouth_controller']
    },
    7: {
        'head': [],
        'tail': [],
        'all': ['c_lips_outer_lower.R'],
    },
    8: {
        'head': [],
        'tail': [],
        'all': ['c_lips_outer_lower.L'],
    },
    9: {
        'head': [],
        'tail': [],
        'all': ['c_lips_upper'],
    },
    10: {
        'head': [],
        'tail': [],
        'all': ['c_lips_outer_upper.R'],
    },
    11: {
        'head': [],
        'tail': [],
        'all': ['c_lips_outer_upper.L'],
    },
    12: {
        'head': [],
        'tail': [],
        'all': ['c_lips_corner.L', 'c_lips_corner_adjust.L'],
    },
    13: {
        'head': [],
        'tail': [],
        'all': ['c_lips_corner.R', 'c_lips_corner_adjust.R'],
    },
    14: {
        'head': [],
        'tail': [],
        'all': ['c_lips_upper_roll'],
    },
    # cheeck low
    15: {
        'head': [],
        'tail': [],
        'all': [],
    },
    16: {
        'head': [],
        'tail': [],
        'all': [],
    },
    17: {
        'head': [],
        'tail': [],
        'all': [],
    },
    18: {
        'head': [],
        'tail': [],
        'all': [],
    },
    19: {
        'head': [],
        'tail': [],
        'all': [],
    },
    20: {
        'head': [],
        'tail': [],
        'all': [],
    },
    21: {
        'head': [],
        'tail': [],
        'all': [],
    },
    22: {
        'head': [],
        'tail': [],
        'all': ['c_cheek_upper.R'],
    },
    23: {
        'head': [],
        'tail': [],
        'all': ['c_cheek_upper.L']
    },

    24: {
        'head': [],
        'tail': [],
        'all': [],
    },
    25: {
        'head': [],
        'tail': [],
        'all': [],
    },
    26: {
        'head': [],
        'tail': [],
        'all': ['c_nose_sneer.L'],
    },
    27: {
        'head': [],
        'tail': [],
        'all': ['c_nose_sneer.R'],
    },
    28: {
        'head': [],
        'tail': [],
        'all': []
    },
    29: {
        'head': [],
        'tail': [],
        'all': [],
    },
    30: {
        'head': [],
        'tail': [],
        'all': ['c_eyelid_lower.L'],
    },
    31: {
        'head': [],
        'tail': [],
        'all': ['c_eyelid_lower.R'],
    },
    32: {
        'head': [],
        'tail': [],
        'all': [],
    },
    33: {
        'head': [],
        'tail': [],
        'all': [],
    },
    34: {
        'head': [],
        'tail': [],
        'all': [],
    },
    35: {
        'head': [],
        'tail': [],
        'all': [],
    },
    36: {
        'head': [],
        'tail': [],
        'all': [],
    },
    37: {
        'head': [],
        'tail': [],
        'all': [],
    },
    38: {
        'head': [],
        'tail': [],
        'all': [],
    },
    39: {
        'head': [],
        'tail': [],
        'all': [],
    },
    40: {
        'head': [],
        'tail': [],
        'all': [],
    },
    41: {
        'head': [],
        'tail': [],
        'all': [],
    },
    42: {
        'head': [],
        'tail': [],
        'all': [],
    },
    43: {
        'head': [],
        'tail': [],
        'all': ['c_eyelid_upper.R'],
    },
    44: {
        'head': [],
        'tail': [],
        'all': ['c_eyelid_upper.L'],
    },
    45: {
        'head': [],
        'tail': [],
        'all': [],
    },
    46: {
        'head': [],
        'tail': [],
        'all': [],
    },
    47: {
        'head': [],
        'tail': [],
        'all': [],
    },
    48: {
        'head': [],
        'tail': [],
        'all': [],
    },
    49: {
        'head': [],
        'tail': [],
        'all': [],
    },
    50: {
        'head': [],
        'tail': [],
        'all': [],
    },
    51: {
        'head': [],
        'tail': [],
        'all': [],
    },
    52: {
        'head': [],
        'tail': [],
        'all': [],
    },
    53: {
        'head': [],
        'tail': [],
        'all': [],
    },
    54: {
        'head': [],
        'tail': [],
        'all': [],
    },
    55: {
        'head': [],
        'tail': [],
        'all': [],
    },
    56: {
        'head': [],
        'tail': [],
        'all': [],
    },
    57: {
        'head': [],
        'tail': [],
        'all': ['c_brow_inner.L'],
    },
    58: {
        'head': [],
        'tail': [],
        'all': ['c_brow_inner.R'],
    },
    59: {
        'head': [],
        'tail': [],
        'all': [],
    },
    60: {
        'head': [],
        'tail': [],
        'all': [],
    },
    61: {
        'head': [],
        'tail': [],
        'all': ['c_brow_outer.R'],
    },
    62: {
        'head': [],
        'tail': [],
        'all': ['c_brow_outer.L'],
    },
    63: {
        'head': [],
        'tail': [],
        'all': ['c_brow_master.L'],
    },
    64: {
        'head': [],
        'tail': [],
        'all': ['c_brow_master.R'],
    },
    65: {
        'head': [],
        'tail': [],
        'all': [],
    },
    66: {
        'head': [],
        'tail': [],
        'all': [],
    },
    67: {
        'head': [],
        'tail': [],
        'all': [],
    },
    68: {
        'head': [],
        'tail': [],
        'all': [],
    },
    69: {
        'head': [],
        'tail': [],
        'all': [],
    },
    70: {
        'head': [],
        'tail': [],
        'all': [],
    },
    71: {
        'head': [],
        'tail': [],
        'all': [],
    },

    101: {
        'head': [],
        'tail': [],
        'all': ['c_eyebrow_mid'],
    },
    102: {
        'head': [],
        'tail': [],
        'all': ['c_lower_lips', 'c_lips_parent', 'c_jaw_target_master', 'c_face_main'],
    },
    103: {
        'head': [],
        'tail': [],
        'all': ['c_lookat_mch.L'],
    },
    104: {
        'head': [],
        'tail': [],
        'all': ['c_lookat_mch.R'],
    },
    105: {
        'head': [],
        'tail': [],
        'all': ['c_eye_lookat', 'c_eye_lookat.R', 'c_eye_lookat.L']
    }
}

match_bones_symmetry_dict = {
    # chin 0,1,2,3
    0: {
        'head': [],
        'tail': [],
        'all': [],
    },
    1: {
        'head': [],
        'tail': [],
        'all': ['c_jaw_target'],
    },
    2: {
        'head': [],
        'tail': [],
        'all': [],
    },
    3: {
        'head': [],
        'tail': [],
        'all': ['c_lips_lower_roll'],
    },
    # chin side
    4: {
        'head': [],
        'tail': [],
        'all': [],
    },
    # lowerlip mid
    5: {
        'head': [],
        'tail': [],
        'all': ['c_lips_lower', 'c_mouth_controller'],
    },
    # lower lip side
    6: {
        'head': [],
        'tail': [],
        'all': ['c_lips_outer_lower.L'],
    },
    # lip corner
    7: {
        'head': [],
        'tail': [],
        'all': ['c_lips_corner.L', 'c_lips_corner_adjust.L'],
    },
    # upper lip mid
    8: {
        'head': [],
        'tail': [],
        'all': ['c_lips_upper'],
    },
    # upper lip side
    9: {
        'head': [],
        'tail': [],
        'all': ['c_lips_outer_upper.L'],
    },
    # nose low
    10: {
        'head': [],
        'tail': [],
        'all': ['c_lips_upper_roll'],
    },
    # nose tip
    11: {
        'head': [],
        'tail': [],
        'all': [],
    },
    # jaw mid
    12: {
        'head': [],
        'tail': [],
        'all': [],
    },
    # nose wing
    13: {
        'head': [],
        'tail': [],
        'all': [],
    },
    # cheeck low
    14: {
        'head': [],
        'tail': [],
        'all': [],
    },
    # cheeck high
    15: {
        'head': [],
        'tail': [],
        'all': ['c_cheek_upper.L'],
    },
    # nose side
    16: {
        'head': [],
        'tail': [],
        'all': ['c_nose_sneer.L'],
    },
    # EL_lower_1
    17: {
        'head': [],
        'tail': [],
        'all': [],
    },
    # EL_corner
    18: {
        'head': [],
        'tail': [],
        'all': [],
    },
    # nose side
    19: {
        'head': [],
        'tail': [],
        'all': ['c_eyelid_lower.L'],
    },
    # nose side
    20: {
        'head': [],
        'tail': [],
        'all': [],
    },
    21: {
        'head': [],
        'tail': [],
        'all': [],
    },
    22: {
        'head': [],
        'tail': [],
        'all': [],
    },
    23: {
        'head': [],
        'tail': [],
        'all': [],
    },
    24: {
        'head': [],
        'tail': [],
        'all': [],
    },
    25: {
        'head': [],
        'tail': [],
        'all': [],
    },
    26: {
        'head': [],
        'tail': [],
        'all': [],
    },
    27: {
        'head': [],
        'tail': [],
        'all': ['c_eyelid_upper.L'],
    },
    28: {
        'head': [],
        'tail': [],
        'all': [],
    },
    29: {
        'head': [],
        'tail': [],
        'all': [],
    },
    30: {
        'head': [],
        'tail': [],
        'all': ['c_brow_inner.L'],
    },
    31: {
        'head': [],
        'tail': [],
        'all': [],
    },
    32: {
        'head': [],
        'tail': [],
        'all': [],
    },
    33: {
        'head': [],
        'tail': [],
        'all': [],
    },
    34: {
        'head': [],
        'tail': [],
        'all': ['c_brow_master.L'],
    },
    35: {
        'head': [],
        'tail': [],
        'all': ['c_brow_outer.L'],
    },
    36: {
        'head': [],
        'tail': [],
        'all': [],
    },
    37: {
        'head': [],
        'tail': [],
        'all': [],
    },
    38: {
        'head': [],
        'tail': [],
        'all': [],
    },
    39: {
        'head': [],
        'tail': [],
        'all': [],
    },
    40: {
        'head': [],
        'tail': [],
        'all': [],
    },
    # mid brow - between inner brows
    101: {
        'head': [],
        'tail': [],
        'all': ['c_eyebrow_mid'],
    },
    # innerbones all on ZY (X=0) plane at landmarks pos 22
    102: {
        'head': [],
        'tail': [],
        'all': ['c_lower_lips', 'c_lips_parent', 'c_jaw_target_master', 'c_face_main'],
    },
    103: {
        'head': [],
        'tail': [],
        'all': ['c_lookat_mch.L'],
    },
    104: {
        'head': [],
        'tail': [],
        'all': ['c_lookat_mch.R'],
    },
    105: {
        'head': [],
        'tail': [],
        'all': ['c_eye_lookat', 'c_eye_lookat.R', 'c_eye_lookat.L']
    }
}
