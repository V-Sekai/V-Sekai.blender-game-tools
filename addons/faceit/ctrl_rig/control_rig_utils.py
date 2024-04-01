import bpy

from ..core import faceit_utils as futils
from ..core.shape_key_utils import get_shape_keys_from_objects, has_shape_keys, get_shape_key_names_from_objects
from ..core.retarget_list_utils import (get_target_shapes_dict,
                                        set_base_regions_from_dict)
from . import control_rig_data as ctrl_data
from . import custom_slider_utils


def populate_control_rig_target_objects_from_scene(c_rig):
    ''' Populates the target objects property on the control rig object from the current faceit_objects '''

    faceit_objects = futils.get_faceit_objects_list()

    crig_objects = c_rig.faceit_crig_objects
    crig_objects.clear()

    for obj in faceit_objects:
        item = crig_objects.add()
        item.name = obj.name
        item.obj_pointer = obj


def get_crig_objects_list(c_rig):
    ''' Returns a list of all target objects found in the scene '''
    crig_objects = []
    for item in c_rig.faceit_crig_objects:
        obj = futils.get_object(item.name)
        if obj is not None:
            crig_objects.append(obj)
    return crig_objects


def is_control_rig_connected(ctrl_rig):
    '''Returns true if the control rig is connected to the target objects.'''
    target_objects = get_crig_objects_list(ctrl_rig)
    if target_objects:
        # Search drivers
        for obj in target_objects:
            if has_shape_keys(obj):
                if obj.data.shape_keys.animation_data:
                    for dr in obj.data.shape_keys.animation_data.drivers:
                        driver = dr.driver
                        targets = []
                        for var in driver.variables:
                            for t in var.targets:
                                targets.append(t.id)
                        if ctrl_rig in targets:
                            return True


def get_slider_bone_name_from_arkit_driver_dict(c_rig, shape_name):
    driver_dict = ctrl_data.get_control_rig_driver_dict(c_rig)
    driver_dict = ctrl_data.control_rig_drivers_dict.get(shape_name)
    if driver_dict:
        return driver_dict['variables']['var']['bone_name']


def populate_control_rig_target_shapes_from_scene(c_rig, update=False, populate_amplify_values=False, range='FULL'):
    ''' Populates the crig_targets on the control rig object from the arkit target shapes 
    @c_rig: the control rig object.
    @update: if this is true, try to find existing amplify values based on version number + find custom controllers.
    '''
    crig_targets = c_rig.faceit_crig_targets
    # Get existing amplify values for conversion
    amplify_value_dict = {}
    region_dict = {}
    if update:
        if crig_targets:
            for ct in crig_targets:
                amplify_value_dict[ct.name] = ct.amplify
                region_dict[ct.name] = ct.region
        else:
            # Get the scene target shapes
            crig_scene_targets = bpy.context.scene.faceit_crig_targets
            for ct in crig_scene_targets:
                amplify_value_dict[ct.name] = ct.amplify
                region_dict[ct.name] = ct.region
    crig_targets.clear()

    target_shapes_dict = get_target_shapes_dict(bpy.context.scene.faceit_arkit_retarget_shapes)
    if populate_amplify_values:
        for item in bpy.context.scene.faceit_arkit_retarget_shapes:
            if item.name in target_shapes_dict:
                amplify_value_dict[item.name] = item.amplify
    custom_sliders = []

    all_shapes = get_shape_keys_from_objects(get_crig_objects_list(c_rig))
    for sk in all_shapes:
        shape_name = sk.name
        # If the shape is already added continue
        if shape_name in target_shapes_dict.values():
            if range == 'FULL':
                sk.slider_min = min(sk.slider_min, -1)
            continue
        # check for a respective slider
        if custom_slider_utils.get_slider_from_shape(c_rig, shape_name):
            if range == 'FULL':
                sk.slider_min = min(sk.slider_min, -1)
            target_shapes_dict[shape_name] = [shape_name, ]
            custom_sliders.append(shape_name)
        # Set the range for this shape key

    for name, target_shapes in target_shapes_dict.items():
        item = crig_targets.add()
        item.name = name
        if name in custom_sliders:
            item.custom_slider = True
            slider = custom_slider_utils.get_slider_from_shape(c_rig, shape_name)
            if slider:
                item.slider_name = slider.name
        else:
            slider_name = get_slider_bone_name_from_arkit_driver_dict(c_rig, name)
            if slider_name:
                item.slider_name = slider_name
        item.amplify = amplify_value_dict.get(name, 1.0)
        for target_name in target_shapes:
            new_target_shape = item.target_shapes.add()
            new_target_shape.name = target_name
    # Try Set the regions for all shapes
    set_base_regions_from_dict(crig_targets)


def save_control_rig_template(c_rig, save_amplify_values=True, save_regions=True, save_target_objects=False):
    retarget_list = c_rig.faceit_crig_targets
    # custom_slider_names = custom_slider_utils.get_custom_sliders_in_crig(c_rig)
    data = {}
    # Store the target objects
    if save_target_objects:
        data['target_objects'] = [obj.name for obj in get_crig_objects_list(c_rig)]
    shape_dict = get_target_shapes_dict(retarget_list, force_empty_strings=True)
    target_shapes_dict = {}
    for shape_name, target_shape_list in shape_dict.items():
        shape_item = retarget_list[shape_name]
        _dict = {
            'target_shapes': target_shape_list,
        }
        if save_amplify_values:
            _dict['amplify'] = getattr(shape_item, 'amplify', 1.0)
        if save_regions:
            _dict['region'] = getattr(shape_item, 'region', 'OTHER')
        slider_name = shape_item.slider_name
        _dict['custom_slider'] = shape_item.custom_slider
        if shape_item.custom_slider:
            custom_slider = custom_slider_utils.get_slider_from_shape(c_rig, shape_name)
            if not slider_name:
                slider_name = custom_slider.name
            # print('custom slider: ', shape_item.custom_slider, shape_item.slider_name)
            # slider_name = shape_item.slider_name
            slider_range = shape_item.slider_range
            if slider_range == 'NONE':
                if custom_slider:
                    _max, min = ctrl_data.get_pose_bone_range_from_limit_constraint(custom_slider)
                    _dict['custom_slider_range'] = 'FULL' if min[1] < 0 else 'POS'
                    shape_item.slider_range = 'FULL' if min[1] < 0 else 'POS'

            else:
                _dict['custom_slider_range'] = slider_range
        target_shapes_dict[shape_name] = _dict
    data['target_shapes'] = target_shapes_dict
    return data


def load_control_rig_template(context, c_rig, data, overwrite_existing_controllers=True,
                              load_target_objects=False):
    created_any_custom_controllers = False
    print('INFO', 'Loading control rig template...')
    crig_targets = c_rig.faceit_crig_targets
    if load_target_objects:
        target_objects = data.get('target_objects', [])
        if target_objects:
            for obj in target_objects:
                if obj not in c_rig.faceit_crig_objects:
                    c_rig.faceit_crig_objects.add().name = obj
    target_shapes_dict = data.get('target_shapes', {})
    for expression_name, target_dict in target_shapes_dict.items():
        target_shapes_list = target_dict['target_shapes']
        region = target_dict.get('region', 'OTHER')
        custom_slider = target_dict.get('custom_slider', False)
        if expression_name in crig_targets:
            if not custom_slider:
                crig_targets.remove(crig_targets.find(expression_name))
            else:
                if overwrite_existing_controllers:
                    # Remove the existing controller
                    # try:
                    #     bpy.ops.faceit.remove_custom_controller(
                    #         'EXEC_DEFAULT', custom_slider=expression_name)
                    # except (RuntimeError, TypeError):
                    #     print('WARNING', f'Attempted to remove {expression_name} from the rig.')
                    found_index = crig_targets.find(expression_name)
                    if c_rig.faceit_crig_targets_index >= found_index:
                        c_rig.faceit_crig_targets_index -= 1
                    crig_targets.remove(found_index)
                else:
                    print('INFO', f'Skipping {expression_name} because it already exists in the rig.')
                    continue
        item = crig_targets.add()
        item.name = expression_name
        item.amplify = 1.0
        item.region = region
        for shape_name in target_shapes_list:
            target_item = item.target_shapes.add()
            target_item.name = shape_name
        if custom_slider:
            item.custom_slider = True
            slider_range = target_dict.get('custom_slider_range', 'FULL')
            item.slider_range = slider_range
            # Create the custom slider
            item.slider_name = custom_slider_utils.generate_extra_sliders(
                context,
                expression_name,
                'full_range' if slider_range == 'FULL' else 'pos_range',
                rig_obj=c_rig,
                overwrite=True
            )
            created_any_custom_controllers = True
    return created_any_custom_controllers


def load_amplify_values_as_custom_id_props(ctrl_rig):
    '''Transfers the amplify values of the give control rig to custom id properties.'''
    for target in ctrl_rig.faceit_crig_targets:
        ctrl_rig[target.name] = target.amplify


def create_eye_lookat_driver_mechanics(rig):
    lookat_targets = ['c_eye_lookat', 'c_eye_lookat.L', 'c_eye_lookat.R']
    switch_bone = rig.pose.bones['c_SwitchLookAt_slider']
    switch_max, _switch_min = ctrl_data.get_pose_bone_range_from_limit_constraint(
        switch_bone)

    # lookat_target.driver_add('["hide"]')
    for target in lookat_targets:
        path = f'bones["{target}"].hide'
        driver = rig.data.driver_add(path)
        dr = driver.driver
        var = dr.variables.new()
        var.type = 'TRANSFORMS'
        t = var.targets[0]
        t.id = rig
        t.bone_target = 'c_SwitchLookAt_slider'
        t.transform_space = 'LOCAL_SPACE'
        t.transform_type = 'LOC_Y'
        dr.expression = f'round(1-var/{switch_max.y})'

    slider_lookat_2D = rig.pose.bones['c_LookAt2D_slider2d']
    mcp_max, mcp_min = ctrl_data.get_pose_bone_range_from_limit_constraint(
        slider_lookat_2D)
    mocap2d_L = rig.pose.bones.get('c_EyeLeft_slider2d')
    mcp_L_max, mcp_L_min = ctrl_data.get_pose_bone_range_from_limit_constraint(
        mocap2d_L)
    # Add drivers to the eye mch bones
    # Drive eye movement with those mch bones.
    mch_bone_L = rig.pose.bones['c_lookat_mch.L']
    mch_bone_R = rig.pose.bones['c_lookat_mch.R']
    # Add driver to the eye mch bones.
    for mch_bone in [mch_bone_L, mch_bone_R]:
        # Add a driver to the rotation constraint on the mch bones.
        # Important for switching between 2d and world target.
        constraint_path = f'pose.bones["{mch_bone.name}"].constraints["Damped Track"].influence'
        driver = rig.driver_add(constraint_path)
        dr = driver.driver
        var = dr.variables.new()
        var.type = 'TRANSFORMS'
        t = var.targets[0]
        t.id = rig
        t.bone_target = 'c_SwitchLookAt_slider'
        t.transform_space = 'LOCAL_SPACE'
        t.transform_type = 'LOC_Y'
        dr.expression = f'1-(1-var/{switch_max.y})**2'
        # Add X rotation driver for the 2d target
        mch_bone.rotation_mode = 'XYZ'
        path = f'pose.bones["{mch_bone.name}"].rotation_euler'
        driver = rig.driver_add(path, 0)
        dr = driver.driver
        var = dr.variables.new()
        # lookat main
        var.type = 'TRANSFORMS'
        t = var.targets[0]
        t.id = rig
        t.bone_target = 'c_LookAt2D_slider2d'
        t.transform_space = 'LOCAL_SPACE'
        t.transform_type = 'LOC_X'
        # lookat left isolated
        var = dr.variables.new()
        var.type = 'TRANSFORMS'
        var.name = 'var_1'
        t = var.targets[0]
        t.id = rig
        t.bone_target = 'c_EyeLeft_slider2d' if '.L' in mch_bone.name else 'c_EyeRight_slider2d'
        t.transform_space = 'LOCAL_SPACE'
        t.transform_type = 'LOC_X'

        # add another variable to remove the influence depending on the influence value..
        var = dr.variables.new()
        var.type = 'TRANSFORMS'
        var.name = 'switch'
        t = var.targets[0]
        t.id = rig
        t.bone_target = 'c_SwitchLookAt_slider'
        t.transform_space = 'LOCAL_SPACE'
        t.transform_type = 'LOC_Y'
        dr.expression = f'(var/{mcp_max.x} + var_1/{mcp_L_max.x}) * (1-(switch/{switch_max.y}))'
        # Add Z rotation driver
        driver = rig.driver_add(path, 2)
        dr = driver.driver
        # lookat main
        var = dr.variables.new()
        var.type = 'TRANSFORMS'
        t = var.targets[0]
        t.id = rig
        t.bone_target = 'c_LookAt2D_slider2d'
        t.transform_space = 'LOCAL_SPACE'
        t.transform_type = 'LOC_Y'
        # lookat right isolated
        var = dr.variables.new()
        var.type = 'TRANSFORMS'
        var.name = 'var_1'
        t = var.targets[0]
        t.id = rig
        t.bone_target = 'c_EyeLeft_slider2d' if '.L' in mch_bone.name else 'c_EyeRight_slider2d'
        t.transform_space = 'LOCAL_SPACE'
        t.transform_type = 'LOC_Y'
        # switch
        var = dr.variables.new()
        var.type = 'TRANSFORMS'
        var.name = 'switch'
        t = var.targets[0]
        t.id = rig
        t.bone_target = 'c_SwitchLookAt_slider'
        t.transform_space = 'LOCAL_SPACE'
        t.transform_type = 'LOC_Y'
        dr.expression = f'(var/{mcp_max.y} + var_1/{mcp_L_max.y}) * (1-(switch/{switch_max.y}))'
        # TODO: The ranges are still wrong.
        # Nach oben: etwa 25 bis 35 Grad
        # Nach unten: etwa 30 bis 45 Grad
        # Nach rechts und links: horizontale Bewegungen können bis zu 45 Grad in Richtung der Nase (medial) und bis zu 100 bis 110 Grad weg von der Nase (lateral) betragen
        # In radiants:
        # Nach oben: etwa 0,44 bis 0,61 Radianten
        # Nach unten: etwa 0,52 bis 0,79 Radianten
        # Nach rechts: etwa 0,79 bis 1,75 Radianten
        # Nach links: etwa 0,79 bis 1,75 Radianten
