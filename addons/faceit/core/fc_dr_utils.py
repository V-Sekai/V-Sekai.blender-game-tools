import bpy
import numpy as np

'''
-------------------------------------

Copy Fcurves with all keyframe_points | handles and slopes | properties | modifiers

Copy Drivers with all variables | targets | fcurves

-------------------------------------
'''


MODIFIER_TYPES = [
    'GENERATOR',
    'FNGENERATOR',
    'ENVELOPE',
    'CYCLES',
    'NOISE',
    'LIMITS',
    'STEPPED',
]


def get_fcurve_from_bpy_struct(fcurves_struct, dp='', array_index=-1, replace_fcurve=False):
    ''' Find the fcurve with specified datapath
    @fcurves_struct fcurves: AnimDataDrivers, Action.fcurves, ...
    @dp (string): the data_path
    @array_index (int): the fcurve index in array properties
    '''

    fc = fcurves_struct.find(dp, index=array_index)

    # New Fcurve either becuase
    # the fc does not exist or overwrite_action is true
    if fc:
        if replace_fcurve:
            fcurves_struct.remove(fc)
            fc = fcurves_struct.new(dp, index=array_index)
    else:
        fc = fcurves_struct.new(dp, index=array_index)

    return fc


# | ----------------- MODIFIERS -----------------------


def get_fcurve_modifiers(fc):
    ''' Return the Fcurve Modifiers in dict '''
    mod_dict = {}
    for i, mod in enumerate(fc.modifiers):
        mod_dict[i] = {
            'type': mod.type,
            'active': mod.active,
            'blend_in': mod.blend_in,
            'blend_out': mod.blend_out,
            'frame_end': mod.frame_end,
            'frame_start': mod.frame_start,
            'mute': mod.mute,
            'influence': mod.influence,
            'show_expanded': mod.show_expanded,
            'use_influence': mod.use_influence,
            'use_restricted_range': mod.use_restricted_range,
        }
        if mod.type == 'GENERATOR':
            mod_dict[i].update(
                {
                    'coefficients': mod.coefficients[:],
                    'mode': mod.mode,
                    'poly_order': mod.poly_order,
                    'use_additive': mod.use_additive,
                }
            )
        if mod.type == 'CYCLES':
            mod_dict[i].update(
                {
                    'cycles_after': mod.cycles_after,
                    'cycles_before': mod.cycles_before,
                    'mode_after': mod.mode_after,
                    'mode_before': mod.mode_before,
                }
            )
        if mod.type == 'ENVELOPE':
            control_points = {}
            for point in mod.control_points:
                control_points[point.frame] = {
                    'max': point.max,
                    'min': point.min,
                }
            mod_dict[i].update(
                {
                    # Control Points are read-only.
                    # Remove(point). add(frame). each point has: frame, max, min
                    'control_points': control_points,
                    # 'control_points': mod.control_points,
                    'default_max': mod.default_max,
                    'default_min': mod.default_min,
                    'reference_value': mod.reference_value,
                }
            )
        if mod.type == 'FNGENERATOR':
            mod_dict[i].update(
                {
                    'amplitude': mod.amplitude,
                    'function_type': mod.function_type,
                    'phase_multiplier': mod.phase_multiplier,
                    'phase_offset': mod.phase_offset,
                    'use_additive': mod.use_additive,
                    'value_offset': mod.value_offset,
                }
            )
        if mod.type == 'LIMITS':
            mod_dict[i].update(
                {
                    'max_x': mod.max_x,
                    'max_y': mod.max_y,
                    'min_x': mod.min_x,
                    'min_y': mod.min_y,
                    'use_max_x': mod.use_max_x,
                    'use_max_y': mod.use_max_y,
                    'use_min_x': mod.use_min_x,
                    'use_min_y': mod.use_min_y,
                }
            )
        if mod.type == 'NOISE':
            mod_dict[i].update(
                {
                    'blend_type': mod.blend_type,
                    'depth': mod.depth,
                    'offset': mod.offset,
                    'phase': mod.phase,
                    'scale': mod.scale,
                    'strength': mod.strength,
                }
            )
        if mod.type == 'STEPPED':
            mod_dict[i].update(
                {
                    'frame_end': mod.frame_end,
                    'frame_offset': mod.frame_offset,
                    'frame_start': mod.frame_start,
                    'frame_step': mod.frame_step,
                    'use_frame_end': mod.use_frame_end,
                    'use_frame_start': mod.use_frame_start,
                }
            )

            # 'id_data': mod.id_data,
    return mod_dict


def clear_all_fc_modifiers(fc):
    if fc.modifiers.values():
        for _ in range(len(fc.modifiers)):
            mod = fc.modifiers[-1]
            fc.modifiers.remove(mod)


def populate_modifiers(fc, mod_dict):
    ''' Create the modifiers for a new fcurve '''

    for i, mod_dict in mod_dict.items():

        m_type = mod_dict.get('type')
        if m_type not in MODIFIER_TYPES:
            continue

        mod = fc.modifiers.new(m_type)
        mod.active = mod_dict.get('active', mod.active)
        mod.blend_in = mod_dict.get('blend_in', mod.blend_in)
        mod.blend_out = mod_dict.get('blend_out', mod.blend_out)
        mod.frame_end = mod_dict.get('frame_end', mod.frame_end)
        mod.frame_start = mod_dict.get('frame_start', mod.frame_start)
        mod.mute = mod_dict.get('mute', mod.mute)
        mod.influence = mod_dict.get('influence', mod.influence)
        mod.show_expanded = mod_dict.get('show_expanded', mod.show_expanded)
        mod.use_influence = mod_dict.get('use_influence', mod.use_influence)
        mod.use_restricted_range = mod_dict.get('use_restricted_range', mod.use_restricted_range)

        if mod.type == 'GENERATOR':

            mod.coefficients = mod_dict.get('coefficients', [])[:]
            mod.mode = mod_dict.get('mode', mod.mode)
            mod.poly_order = mod_dict.get('poly_order', mod.poly_order)
            mod.use_additive = mod_dict.get('use_additive', mod.use_additive)

        if mod.type == 'CYCLES':
            mod.cycles_after = mod_dict.get('cycles_after', mod.cycles_after)
            mod.cycles_before = mod_dict.get('cycles_before', mod.cycles_before)
            mod.mode_after = mod_dict.get('mode_after', mod.mode_after)
            mod.mode_before = mod_dict.get('mode_before', mod.mode_before)

        if mod.type == 'ENVELOPE':
            # mod.control_points = mod_dict.get('control_points', mod.control_points)
            for frame, min_max_dict in mod_dict.get('control_points', {}).items():
                point = mod.control_points.add(frame)
                point.min = min_max_dict['min']
                point.max = min_max_dict['max']

            mod.default_max = mod_dict.get('default_max', mod.default_max)
            mod.default_min = mod_dict.get('default_min', mod.default_min)
            mod.reference_value = mod_dict.get('reference_value', mod.reference_value)

        if mod.type == 'FNGENERATOR':
            mod.amplitude = mod_dict.get('amplitude', mod.amplitude)
            mod.function_type = mod_dict.get('function_type', mod.function_type)
            mod.phase_multiplier = mod_dict.get('phase_multiplier', mod.phase_multiplier)
            mod.phase_offset = mod_dict.get('phase_offset', mod.phase_offset)
            mod.use_additive = mod_dict.get('use_additive', mod.use_additive)
            mod.value_offset = mod_dict.get('value_offset', mod.value_offset)

        if mod.type == 'LIMITS':
            mod.max_x = mod_dict.get('max_x', mod.max_x)
            mod.max_y = mod_dict.get('max_y', mod.max_y)
            mod.min_x = mod_dict.get('min_x', mod.min_x)
            mod.min_y = mod_dict.get('min_y', mod.min_y)
            mod.use_max_x = mod_dict.get('use_max_x', mod.use_max_x)
            mod.use_max_y = mod_dict.get('use_max_y', mod.use_max_y)
            mod.use_min_x = mod_dict.get('use_min_x', mod.use_min_x)
            mod.use_min_y = mod_dict.get('use_min_y', mod.use_min_y)

        if mod.type == 'NOISE':
            mod.blend_type = mod_dict.get('blend_type', mod.blend_type)
            mod.depth = mod_dict.get('depth', mod.depth)
            mod.offset = mod_dict.get('offset', mod.offset)
            mod.phase = mod_dict.get('phase', mod.phase)
            mod.scale = mod_dict.get('scale', mod.scale)
            mod.strength = mod_dict.get('strength', mod.strength)

        if mod.type == 'STEPPED':
            mod.frame_end = mod_dict.get('frame_end', mod.frame_end)
            mod.frame_offset = mod_dict.get('frame_offset', mod.frame_offset)
            mod.frame_start = mod_dict.get('frame_start', mod.frame_start)
            mod.frame_step = mod_dict.get('frame_step', mod.frame_step)
            mod.use_frame_end = mod_dict.get('use_frame_end', mod.use_frame_end)
            mod.use_frame_start = mod_dict.get('use_frame_start', mod.use_frame_start)

# | ----------------- KEYFRAMES -----------------------


def get_keyframe_meta_data(fc):
    ''' Returns a dict of frame (time), keyframe data'''
    meta_data = {}

    for i, kf in enumerate(fc.keyframe_points):
        meta_data[i] = {
            'easing': kf.easing,
            'interpolation': kf.interpolation,
            'amplitude': kf.amplitude,
            'period': kf.period,
            'type': kf.type,
            'back': kf.back,
            'handle_left_type': kf.handle_left_type,
            'handle_right_type': kf.handle_right_type,
        }

    return meta_data


def populate_kf_meta_data(fc, kf_data_dict=None):
    ''' Get keyframe_point by frame and find matching key, value pair in the keyframe_data dict '''

    for i, kf_meta_data in kf_data_dict.items():
        kf = fc.keyframe_points[i]
        kf.easing = kf_meta_data.get('easing', kf.easing)
        kf.interpolation = kf_meta_data.get('interpolation', kf.interpolation)
        kf.amplitude = kf_meta_data.get('amplitude', kf.amplitude)
        kf.period = kf_meta_data.get('period', kf.period)
        kf.type = kf_meta_data.get('type', kf.type)
        kf.back = kf_meta_data.get('back', kf.back)
        kf.handle_left_type = kf_meta_data.get('handle_left_type', kf.handle_left_type)
        kf.handle_right_type = kf_meta_data.get('handle_right_type', kf.handle_right_type)


def clear_invalid_drivers():
    prop_collections = [
        p for p in dir(bpy.data)
        if isinstance(getattr(bpy.data, p), bpy.types.bpy_prop_collection)
    ]

    for p in prop_collections:
        for ob in getattr(bpy.data, p, []):
            anim_data = getattr(ob, 'animation_data', None)
            if not anim_data:
                continue
            invalid_drivers = []
            # find bung drivers
            for d in anim_data.drivers:
                try:
                    ob.path_resolve(d.data_path)
                except ValueError:
                    invalid_drivers.append(d)
            # remove bung drivers
            while invalid_drivers:
                anim_data.drivers.remove(
                    invalid_drivers.pop()
                )


def kf_data_to_numpy_array(fc, attr='co'):
    '''Get Keyframe Data from an Fcurve.
    @fc: the fcurve
    @attr: string in (co, handle_left, handle_right)
    '''
    kf_count = len(fc.keyframe_points)

    kf_data = np.zeros(kf_count*2, dtype=np.float32)
    fc.keyframe_points.foreach_get(attr, kf_data)
    kf_data = np.reshape(kf_data, (-1, 2))
    return kf_data


def frame_value_pairs_to_numpy_array(frames, values):
    # kf_data = [x for co in zip(frames, values) for x in co]
    return np.array(list(zip(frames, values)))


def populate_keyframe_points_from_np_array(fc, data, attr='co', add=False, join_with_existing=True):

    result = False
    if not fc:
        print('ERROR: Can not find fcurve')
        return False

    if add:

        if len(fc.keyframe_points) > 0 and join_with_existing:
            existing_kf_data = kf_data_to_numpy_array(fc, attr=attr)
            data = join_np_array_kf_data(existing_kf_data, data)

        clear_fcurve_kf_points(fc)
        count = data.shape[0]
        fc.keyframe_points.add(count=count)

    # try:
    if data.shape[0] == len(fc.keyframe_points):
        fc.keyframe_points.foreach_set(attr, np.reshape(data, (-1, 1)))
        result = True
    else:
        print('[fc_dr_utils/populate_keyframe_points_from_np_array] Keyframe_Points don\'t match array. Add Keyframes first')

    fc.update()

    return result


def clear_fcurve_kf_points(fc):
    ''' Clear all keyframe points from fcurve '''

    kf_count = len(fc.keyframe_points)
    for _ in range(kf_count):
        kf = fc.keyframe_points[-1]
        fc.keyframe_points.remove(kf, fast=True)


def join_np_array_kf_data(kf_data_old, kf_data_new):
    '''Joins two numpy arrays containing keyframe data. The intersection of both will be overwritten by kf_data_new'''
    # Get all rows in first column --> frame values
    new_frames = kf_data_new[:, 0]
    # Create a mask to remove new_frames range from the old data
    mask = ((kf_data_old < min(new_frames)) | (kf_data_old > max(new_frames))).all(axis=1)

    kf_data_old = kf_data_old[mask, :]

    final_kf_data = np.append(kf_data_old, kf_data_new, 0)

    return final_kf_data


def sampled_points_to_numpy_array(fc, attr='sampled_points'):
    '''Get Keyframe Data from an Fcurve.
    @fc: the fcurve
    @attr: string in (co, handle_left, handle_right)
    '''
    kf_points = fc.sampled_points
    kf_count = len(kf_points)

    kf_data = np.zeros(kf_count*2, dtype=np.float32)
    fc.sampled_points.foreach_get(attr, kf_data)
    kf_data = np.reshape(kf_data, (-1, 2))
    return kf_data


# | ----------------- FCURVE -----------------------


def get_fcurve_properties(fc):
    ''' Fcurve Properties in a Dictionary format '''
    fc_data_dict = {}

    fc_data_dict = {
        'dp': fc.data_path,
        'select': fc.select,
        'extrapolation': fc.extrapolation,
        'lock': fc.lock,
        'mute': fc.mute,
        'array_index': fc.array_index,
        'auto_smoothing': fc.auto_smoothing,
        'hide': fc.hide,
        'color': fc.color,
        'color_mode': fc.color_mode,
        'group': fc.group,
    }

    return fc_data_dict


def populate_fcurve_properties(fc, fc_data_dict):

    fc.auto_smoothing = fc_data_dict.get('auto_smoothing', fc.auto_smoothing)
    fc.color = fc_data_dict.get('color', fc.color)
    fc.color_mode = fc_data_dict.get('color_mode', fc.color_mode)
    fc.select = fc_data_dict.get('select', fc.select)
    fc.hide = fc_data_dict.get('hide', fc.hide)
    fc.extrapolation = fc_data_dict.get('extrapolation', fc.extrapolation)
    fc.lock = fc_data_dict.get('lock', fc.lock)
    fc.mute = fc_data_dict.get('mute', fc.mute)
    grp = fc_data_dict.get('group')
    if grp:
        fc.group = grp

    fc.update()


def copy_fcurve_data(
        fc, apply_keyframes=True, apply_kf_props=True, apply_handles=True, apply_samples=True, apply_properties=True,
        apply_modifiers=True):
    '''
    Returns from an fcurve (@fc): keyframe_points | handles and slopes | properties | modifiers
    '''

    fcurve_data = {}

    # ------ Keyframe Coordinates
    if apply_keyframes:
        kf_data = kf_data_to_numpy_array(fc, attr='co')

    # # ------ Hadle Coordinates
    if apply_handles:
        hl_data = kf_data_to_numpy_array(fc, attr='handle_left')
        hr_data = kf_data_to_numpy_array(fc, attr='handle_right')

    # # ------ SamplePoints Coordinates
    if apply_samples:
        sampled_points = sampled_points_to_numpy_array(fc, attr='sampled_points')

    # Foreachget doesnt work for strings... Only bool int float
    if apply_kf_props:
        kf_properties = get_keyframe_meta_data(fc)

    if apply_properties:
        fc_properties = get_fcurve_properties(fc)

    if apply_modifiers:
        fc_modifiers = get_fcurve_modifiers(fc)

    fcurve_data = {
        'properties': fc_properties,
        'kf_properties': kf_properties,
        'kf_coordinates': kf_data,
        'kf_hl_coordinates': hl_data,
        'kf_hr_coordinates': hr_data,
        'sampled_points': sampled_points,
        'modifiers': fc_modifiers,
    }

    return fcurve_data

# def create_empty_fcurve_data()


def get_fcurve(fc=None, dp='', array_index=-1, action=None, replace=False):

    if fc and replace:
        action.fcurves.remove(fc)
        fc = None

    if not fc:
        if action and dp:
            # Search for existing fcurves, remove them.
            fc = action.fcurves.find(dp, index=array_index)
            # fc = action.fcurves.new(dp, index=array_index)
            # Create new fcurve
            if not fc:
                fc = action.fcurves.new(dp, index=array_index)
        else:
            return
    return fc


def populate_stored_fcurve_data(
        fc_data, fc=None, dp='', array_index=-1, action=None, join_with_existing_data=True,
        apply_keyframes=True, apply_kf_props=True, apply_handles=True, apply_samples=True, apply_properties=True,
        apply_modifiers=True):
    '''
    Populates the keyframe data into a new fcurve
    @data: the values for that particular fcurve
    @fc: the fcurve
    @dp: the datapath
    @index: (optional) array index of location/rotation values
    @action: the action to hold the new motion
    @join_with_existing_data (bool): If True, Join Keyframes with existing motion, overwrite overlap
    '''

    kf_data = fc_data['kf_coordinates']

    # get all frames from kf data
    # frames = kf_data[:, 0]
    fc = get_fcurve(fc, dp=dp, array_index=array_index, action=action, replace=not join_with_existing_data)

    keyframes_added = False

    if apply_keyframes:
        # Create new keyframe points and populate captured values
        keyframes_added = populate_keyframe_points_from_np_array(
            fc, kf_data, add=True, join_with_existing=join_with_existing_data)

    if keyframes_added:

        if apply_samples:
            sampled_points = fc_data.get('sampled_points')
            fc.sampled_points.foreach_set('sampled_points', np.reshape(sampled_points, (-1, 1)))
            fc.update()

        if not fc.is_empty:

            if apply_kf_props:
                kf_props = fc_data.get('kf_properties', {})
                populate_kf_meta_data(fc, kf_data_dict=kf_props)

            if apply_handles:
                # Handle Data
                hl_data = fc_data.get('kf_hl_coordinates')
                populate_keyframe_points_from_np_array(fc, hl_data, attr='handle_left')

                hr_data = fc_data.get('kf_hr_coordinates')
                populate_keyframe_points_from_np_array(fc, hr_data, attr='handle_right')

            fc.update()
    else:
        print('Error adding keyframes')

    if apply_properties:
        fc_properties = fc_data.get('properties')
        populate_fcurve_properties(fc, fc_properties)

    if apply_modifiers:
        fc_modifiers = fc_data.get('modifiers')
        populate_modifiers(fc, fc_modifiers)

    for region in bpy.context.area.regions:
        region.tag_redraw()


def copy_driver_data(driver_fcurve):

    driver = driver_fcurve.driver

    driver_dict = {}
    # { fcurve_data, variables, modifiers }

    variable_dict = {}
    # variables: { targets: { bone_target.... } }

    for var in driver.variables:

        targets_dict = {}

        for i, t in enumerate(var.targets):
            # Get ID, only if valid
            # In case the data container (KEY) gets recreated or changes
            id_is_self = t.id == driver_fcurve.id_data
            targets_dict[i] = {
                'id_type': t.id_type,
                'id': t.id,
                'id_is_self': id_is_self,
                'bone_target': t.bone_target,
                'transform_type': t.transform_type,
                'transform_space': t.transform_space,
                'rotation_mode': t.rotation_mode,
                'data_path': t.data_path
            }

        variable_dict[var.name] = {
            'type': var.type,
            'targets': targets_dict,
        }

    driver_dict = {
        'expression': driver.expression,
        'type': driver.type,
        'id_data': driver.id_data,
        'use_self': driver.use_self,
        'variables': variable_dict,
    }
    fc_data_dict = copy_fcurve_data(driver_fcurve)
    mod_dict = get_fcurve_modifiers(driver_fcurve)

    driver_dict = {
        'fc': fc_data_dict,
        'driver': driver_dict,
        'modifiers': mod_dict,
    }
    return driver_dict


def populate_driver_data(driver_dict, dr_fcurve):
    ''' Sets up all prperties from stored driver_dict '''

    fc_data_dict = driver_dict.get('fc')
    mod_dict = driver_dict.get('modifiers')
    dr_data_dict = driver_dict.get('driver')

    driver = dr_fcurve.driver

    if dr_data_dict:
        driver.type = dr_data_dict.get('type', driver.type)
        driver.use_self = dr_data_dict.get('use_self', driver.use_self)
        driver.expression = dr_data_dict.get('expression', driver.expression)
        var_dict = dr_data_dict.get('variables')

        if var_dict:
            for v_name, var_data in var_dict.items():
                v = driver.variables.new()
                v.name = v_name
                v.type = var_data.get('type', v.type)

                target_dict = var_data.get('targets')
                if target_dict:
                    for i, t_data in target_dict.items():
                        t = v.targets[i]

                        try:
                            t.id_type = t_data.get('id_type', t.id_type)
                        except:
                            pass

                        if t_data.get('id_is_self') == True:
                            t.id = dr_fcurve.id_data

                        else:
                            try:
                                t.id = t_data['id']
                            except ReferenceError:
                                print('The id {} has been removed'.format(t_data['id']))

                        t.data_path = t_data.get('data_path', t.data_path)
                        t.bone_target = t_data.get('bone_target', t.bone_target)
                        t.transform_type = t_data.get('transform_type', t.transform_type)
                        t.transform_space = t_data.get('transform_space', t.transform_space)
                        t.rotation_mode = t_data.get('rotation_mode', t.rotation_mode)

    clear_all_fc_modifiers(dr_fcurve)
    populate_stored_fcurve_data(fc_data_dict, dr_fcurve)
    dr_fcurve.update()
    if mod_dict:
        populate_modifiers(dr_fcurve, mod_dict=mod_dict)
