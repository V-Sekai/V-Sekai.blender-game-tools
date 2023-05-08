import bpy

from ..core import faceit_utils as futils
from ..core.shape_key_utils import has_shape_keys, get_shape_key_names_from_objects
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


def get_slider_bone_name_from_arkit_driver_dict(shape_name):
    driver_dict = ctrl_data.control_rig_drivers_dict.get(shape_name)
    if driver_dict:
        return driver_dict['variables']['var']['bone_name']


def populate_control_rig_target_shapes_from_scene(c_rig, update=False, populate_amplify_values=False):
    ''' Populates the crig_targets on the control rig object from the arkit target shapes 
    @c_rig: the control rig object.
    @update: if this is true, try to find existing amplify values based on version number + find custom controllers.
    '''
    crig_targets = c_rig.faceit_crig_targets

    # Only used when updating:
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

    # if update:
    # Get custom controllers too...
    all_shapes = get_shape_key_names_from_objects()
    for shape_name in all_shapes:
        # If the shape is already added continue
        if shape_name in target_shapes_dict.values():
            continue
        # check for a respective slider
        if custom_slider_utils.get_custom_slider_from_shape(c_rig, shape_name):
            target_shapes_dict[shape_name] = [shape_name, ]
            custom_sliders.append(shape_name)

    for name, target_shapes in target_shapes_dict.items():

        item = crig_targets.add()
        item.name = name
        if name in custom_sliders:
            item.custom_slider = True
            # slider_name = ''
        else:
            slider_name = get_slider_bone_name_from_arkit_driver_dict(name)
            if slider_name:
                item.slider_name = slider_name
        # Populate existing values or standart:

        # item.region = region_dict.get(name, 'Mouth')
        item.amplify = amplify_value_dict.get(name, 1.0)

        for target_name in target_shapes:
            new_target_shape = item.target_shapes.add()
            new_target_shape.name = target_name

    # Try Set the regions for all shapes
    set_base_regions_from_dict(crig_targets)
