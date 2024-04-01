
import bpy

from ..core.shape_key_utils import has_shape_keys
from ..core.faceit_utils import get_faceit_objects_list

CORRECTIVE_SK_ACTION_NAME = 'faceit_corrective_shape_keys'


def reevaluate_corrective_shape_keys(expression_list=None, objects=None):
    ''' Re-evaluate the keyframes and properties (in @expression_list) in correspondence to the found corrective shape keys (on @objects). '''
    if not expression_list:
        expression_list = bpy.context.scene.faceit_expression_list
    if not objects:
        objects = get_faceit_objects_list()

    for obj in objects:
        if has_shape_keys(obj):
            found_corrective_shapes = False
            for exp_item in expression_list:
                corr_sk = obj.data.shape_keys.key_blocks.get('faceit_cc_' + exp_item.name)
                if corr_sk:
                    corr_sk.mute = False
                    exp_item.corr_shape_key = True
                    keyframe_corrective_sk_action(exp_item)
                    found_corrective_shapes = True
            if found_corrective_shapes:
                a = get_corrective_sk_action()
                if not getattr(obj.data.shape_keys, 'animation_data'):
                    obj.data.shape_keys.animation_data_create()
                obj.data.shape_keys.animation_data.action = a


def mute_corrective_shape_keys(expression_list=None, objects=None):
    '''Mute all corrective shape keys'''
    if not expression_list:
        expression_list = bpy.context.scene.faceit_expression_list
    if not objects:
        objects = get_faceit_objects_list()

    for obj in objects:
        if has_shape_keys(obj):
            found_corrective_shapes = False
            for exp_item in expression_list:
                corr_sk = obj.data.shape_keys.key_blocks.get('faceit_cc_' + exp_item.name)
                if corr_sk:
                    corr_sk.mute = True
                    found_corrective_shapes = True
            if found_corrective_shapes:
                if obj.data.shape_keys.animation_data:
                    if obj.data.shape_keys.animation_data.action == get_corrective_sk_action():
                        obj.data.shape_keys.animation_data.action = None


def get_corrective_sk_action(clear_invalid_fcurves=True, create=True):
    '''Return the corrective shape key action. 
        @clear_invalid_fcurves: If True, remove all fcurves that are not corrective shape keys.
        @create: create the action if it doesn't exist.
    '''
    action = bpy.data.actions.get(CORRECTIVE_SK_ACTION_NAME)
    if not action:
        if create:
            action = bpy.data.actions.new(CORRECTIVE_SK_ACTION_NAME)
            action.use_fake_user = True
    elif clear_invalid_fcurves:
        # Purge old data-paths not valid
        for fc in action.fcurves:
            if not fc.data_path.startswith('key_blocks["faceit_cc_') or not fc.is_valid:
                action.fcurves.remove(fc)
    return action


def assign_corrective_sk_action(obj):

    action = get_corrective_sk_action()

    if has_shape_keys(obj):
        if not getattr(obj.data.shape_keys, 'animation_data'):
            obj.data.shape_keys.animation_data_create()

        obj.data.shape_keys.animation_data.action = action


def keyframe_corrective_sk_action(expression_item):
    ''' Add the keyframes (0,1,0) for the corrective shape key corresponding to @expression_item. '''

    action = get_corrective_sk_action()

    frame = expression_item.frame

    data_path = 'key_blocks["faceit_cc_{}"].value'.format(expression_item.name)

    fc = action.fcurves.find(data_path)
    if fc:
        action.fcurves.remove(fc)

    fc = action.fcurves.new(data_path=data_path)

    fc.keyframe_points.insert(frame=frame - 9, value=0, options={'FAST'})
    fc.keyframe_points.insert(frame=frame, value=1, options={'FAST'})
    fc.keyframe_points.insert(frame=frame + 1, value=0, options={'FAST'})


def clear_all_corrective_shape_keys(objects, expression_list=None):

    for obj in objects:
        if has_shape_keys(obj):
            for sk in obj.data.shape_keys.key_blocks:
                if not sk.name.startswith('faceit_cc_'):
                    continue
            obj.shape_key_remove(sk)
        else:
            continue

        if has_shape_keys(obj):
            if len(obj.data.shape_keys.key_blocks) == 1:
                obj.shape_key_clear()

    if expression_list:
        for exp_item in expression_list:
            exp_item.corr_shape_key = False

    a = get_corrective_sk_action(clear_invalid_fcurves=False, create=False)
    if a:
        bpy.data.actions.remove(a)


def remove_corrective_shape_key(expression_list, objects, expression_name=''):
    '''Removes a corrective shape key for a given @expression_name from all @objects'''

    expression_item = expression_list.get(expression_name)
    if not expression_item:
        print(f'couldnt find the expression {expression_name}')
        return

    corr_sk_name = 'faceit_cc_' + expression_name
    sk_found = False
    for obj in objects:
        print(obj.name)
        if has_shape_keys(obj):
            corr_sk = obj.data.shape_keys.key_blocks.get(corr_sk_name)
            if corr_sk:
                sk_found = True
                obj.shape_key_remove(corr_sk)
                if len(obj.data.shape_keys.key_blocks) == 1:
                    obj.shape_key_clear()
    if not sk_found:
        return False

    # check if a corrective shape key is still found on any of the other faceit objects
    corrective_sk_cleared = True
    for obj in get_faceit_objects_list():
        if has_shape_keys(obj):
            corr_sk = obj.data.shape_keys.key_blocks.get(corr_sk_name)
            if corr_sk:
                corrective_sk_cleared = False
                break

    if corrective_sk_cleared:
        expression_item.corr_shape_key = False
        a = bpy.data.actions.get(CORRECTIVE_SK_ACTION_NAME)
        if a:
            fc = a.fcurves.find(f'key_blocks["faceit_cc_{expression_name}"].value')
            if fc:
                a.fcurves.remove(fc)
    return True


def get_objects_with_corrective_shape_key_for_expression(expression_name=''):
    '''Return list of objects that hold a corrective sk for the given expression.'''
    found_sk_objects = []
    objects = get_faceit_objects_list()
    for obj in objects:
        if has_shape_keys(obj):
            if 'faceit_cc_' + expression_name in obj.data.shape_keys.key_blocks:
                found_sk_objects.append(obj)
    return found_sk_objects
