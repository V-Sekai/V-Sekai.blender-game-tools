
import re
import numpy as np
from . import fc_dr_utils
from . import faceit_utils as futils


def has_shape_keys(obj):
    '''Returns True when the object data holds Shape Keys'''
    if hasattr(obj.data, 'shape_keys'):
        return hasattr(obj.data.shape_keys, 'key_blocks')
    else:
        return False


def get_shape_key_names_from_objects(objects=[]):
    shape_key_names = []
    if not objects:
        objects = futils.get_faceit_objects_list()

    for obj in objects:
        if has_shape_keys(obj):
            shape_key_names.extend([sk.name for sk in obj.data.shape_keys.key_blocks if sk.name != 'Basis'])
    return list(set(shape_key_names))


def get_shape_key_names_from_action(action):
    shape_key_names = []
    for fc in action.fcurves:
        if fc.is_empty:
            continue
        dp = str(fc.data_path)
        if 'key_blocks' in dp:

            found_shapes = re.findall(r"['\"](.*?)['\"]", dp)

            if found_shapes:
                for shape in found_shapes:
                    shape_key_names.append(shape)

    return shape_key_names


def get_shape_keys_from_faceit_objects_enum(self, context):
    '''Returns a items list to be used in EnumProperties'''
    # blender is prone to crash without making shapes global
    global shapes
    shapes = []

    if context is None:
        print('get_shape_keys_from_main_object --> Context is None')
        return shapes
    faceit_objects = futils.get_faceit_objects_list()

    if faceit_objects:
        shape_key_names = get_shape_key_names_from_objects(faceit_objects)

        for i, name in enumerate(shape_key_names):

            shapes.append((name, name, name, i))
    else:
        shapes.append(("None", "None", "None"))

    return shapes


def store_shape_keys(obj, store_drivers=True):
    '''
    Store all shapekeys data in numpy arrays
    Returns a dict that holds (data as np array and meta properties (value, relative_key etc.))
    '''
    sk_dict = {}

    if not has_shape_keys(obj):
        return sk_dict

    vert_count = len(obj.data.vertices)

    src_shape_keys = obj.data.shape_keys
    i = 0
    for sk in src_shape_keys.key_blocks[1:]:

        # numpy array with shapekey data
        sk_shape_data = np.zeros(vert_count*3, dtype=np.float32)
        sk.data.foreach_get('co', sk_shape_data.ravel())

        # Get driver
        stored_drivers = []
        if src_shape_keys.animation_data:
            for dr in src_shape_keys.animation_data.drivers:
                if 'key_blocks["{}"].'.format(sk.name) in dr.data_path:
                    stored_drivers.append(fc_dr_utils.copy_driver_data(dr))

        sk_dict[sk.name] = {
            'data': sk_shape_data,
            'drivers': stored_drivers,
            'value': sk.value,
            'mute': sk.mute,
            'relative_key': sk.relative_key,
            'slider_min': sk.slider_min,
            'slider_max': sk.slider_max,
            'vertex_group': sk.vertex_group,
            'interpolation': sk.interpolation,
            'index': i,
        }
        i += 1

    return sk_dict


def apply_stored_shape_keys(obj, sk_dict, new_order_list=None, apply_drivers=True):
    ''' Apply the saved shapekey data from @sk_dict to objects shapekeys in new order from @export_order_dict '''
    # The new index for the shapekey with name shapekey_name

    relative_key = None
    if not has_shape_keys(obj):
        relative_key = obj.shape_key_add(name='Basis')

    # Apply all shape keys in reorder list first. Then others
    reordered_shapes = []

    # New order dict: {sk_name, index}
    if new_order_list:
        for shapekey_name in new_order_list:
            sk_data = sk_dict.get(shapekey_name)
            if sk_data:
                reordered_shapes.append(shapekey_name)
                apply_shape_key_from_data(obj, shapekey_name, sk_data, relative_key, apply_drivers=apply_drivers)
            else:
                print('cannot apply the order becuase the shape key {} has not been found.'.format(shapekey_name))

    for shapekey_name, sk_data in sk_dict.items():
        if not shapekey_name in reordered_shapes:
            apply_shape_key_from_data(obj, shapekey_name, sk_data, relative_key, apply_drivers=apply_drivers)


def apply_shape_key_from_data(obj, shapekey_name, sk_data, relative_key, apply_drivers=True):
    ''' Create a new Shape Key and populate the stored data/properties/drivers '''
    if shapekey_name in obj.data.shape_keys:
        print('The Shape Key {} already exists.'.format(shapekey_name))
        return
    new_sk = obj.shape_key_add(name=shapekey_name)
    # Load the Shape Datask_shape_data = sk_data['data']
    sk_shape_data = sk_data['data']
    new_sk.data.foreach_set('co', sk_shape_data.ravel())
    # Load the Meta Datanew_sk.value = sk_data.get('value', new_sk.value)
    new_sk.mute = sk_data.get('mute', new_sk.mute)
    new_sk.relative_key = relative_key or sk_data.get('relative_key', new_sk.relative_key)
    new_sk.slider_min = sk_data.get('slider_min', new_sk.slider_min)
    new_sk.slider_max = sk_data.get('slider_max', new_sk.slider_max)
    new_sk.vertex_group = sk_data.get('vertex_group', new_sk.vertex_group)
    new_sk.interpolation = sk_data.get('interpolation', new_sk.interpolation)

    if apply_drivers:
        stored_drivers = sk_data.get('drivers')
        if stored_drivers:

            for sk_driver_dict in stored_drivers:

                # Value will be replaced in populate_driver_data/populate_fcurve
                dr = new_sk.driver_add('value', -1)
                fc_dr_utils.populate_driver_data(sk_driver_dict, dr)


def apply_all_shape_keys(obj):
    apply_shape_sk = obj.shape_key_add(name='temp_sk', from_mix=True)
    shape_keys = obj.data.shape_keys.key_blocks

    for _ in range(len(shape_keys)):
        if shape_keys[0].name != apply_shape_sk.name:
            obj.shape_key_remove(shape_keys[0])
    obj.shape_key_clear()


def remove_all_sk_apply_basis(obj, apply_basis=True):
    key_blocks = obj.data.shape_keys.key_blocks

    for sk in range(len(key_blocks))[::-1]:
        if len(key_blocks) > (1 if apply_basis else 0):
            last_sk = obj.data.shape_keys.key_blocks[-1]
            obj.shape_key_remove(last_sk)
    if apply_basis:
        apply_all_shape_keys(obj)
