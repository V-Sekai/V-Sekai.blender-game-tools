import re
import bpy


def get_index_of_parent_collection_from_target_shape(target_shape_item):
    parent_path = target_shape_item.path_from_id().split('.')[0]
    parent_index = parent_path[parent_path.find('[')+1:parent_path.find(']')]
    if parent_index:
        parent_index = int(parent_index)
        return parent_index
    else:
        return -1
    #re.findall(r"['\"](.*?)['\"]", parent_path)


def get_all_set_target_shapes(retarget_shapes):
    ''' Return a list of all target shapes registered to all arkit source shapes.
    @retarget_shapes: the collection property (either scene or fbx)
     '''
    # retarget_shapes = bpy.context.scene.faceit_retarget_shapes
    all_target_shapes = []
    for item in retarget_shapes:
        target_shapes = item.target_shapes
        for target_item in target_shapes:
            all_target_shapes.append(target_item.name)
    return all_target_shapes


def is_target_shape_double(shape_name, retarget_shapes):
    ''' Check if the target shape with @shape_name has been registered to any Arkit shape'''
    all_target_shapes = get_all_set_target_shapes(retarget_shapes)
    return shape_name in all_target_shapes


# def add_target_shape(retarget_list, source_shape_item, target_shape_name):
#     ''' Add a new target shape
#     @retarget_list (prop_collection): the retarget list scene property
#     @source_shape_item: the source shape item in retarget_list (arkit shape)
#     @target_shape_name: the name of the target shape to be added.
#     '''


def eval_target_shapes():
    scene = bpy.context.scene
    target_shapes_initiated = False
    retarget_list = scene.faceit_retarget_shapes
    if retarget_list:
        target_shapes_initiated = any([(len(item.target_shapes) > 0) for item in retarget_list])
    return target_shapes_initiated


def get_target_shapes_dict(retarget_list, force_empty_strings=False):
    '''Returns a dict of arkit shape name and target shape based on retarget_shapes collectionprop'''
    # scene = bpy.context.scene
    # retarget_list = retarget_data  # scene.faceit_retarget_shapes

    target_shapes_dict = {}

    if retarget_list:

        for item in retarget_list:

            arkit_shape = item.name
            target_shapes = item.target_shapes
            target_shapes_list = [t.name for t in target_shapes]

            if target_shapes_list:
                target_shapes_dict[arkit_shape] = target_shapes_list
            else:
                if force_empty_strings:
                    target_shapes_dict[arkit_shape] = ['', ]
                # elif

    return target_shapes_dict


def get_target_shapes_from_source_shape(source_shape_key_name, only_valid=True):
    '''Returns the target shape name from @source shape key name
    Specified in retarget shapes list
    '''
    scene = bpy.context.scene
    retarget_shapes = scene.faceit_retarget_shapes

    target_shapes = []

    if retarget_shapes:
        try:
            target_shapes = retarget_shapes[source_shape_key_name].target_shapes
        except KeyError:
            pass
            # target_shapes = source_shape_key_name
    if target_shapes:
        target_shapes = [t.name for t in target_shapes]

    return target_shapes
