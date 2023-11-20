import bpy
import numpy as np
from mathutils import Vector

from .faceit_data import FACEIT_BONES


def get_action_frame_range(action):
    if bpy.app.version <= (3, 1, 0):
        frame_range = action.frame_range
    else:
        frame_range = action.curve_frame_range
    return frame_range


def get_object(name):
    '''
    returns an object or none
    @name: the name of the obj
    '''
    if isinstance(name, str):
        obj = bpy.context.scene.objects.get(name)
        if obj:
            return obj
        else:
            pass
    return None


def clear_active_object():
    '''Clears the active object'''
    if bpy.context.active_object:
        bpy.context.active_object.select_set(False)
        bpy.context.view_layer.objects.active = None


def set_active_object(obj, select=True):
    '''
    select the object
    @object_name: String or id
    '''
    if isinstance(obj, str):
        obj = bpy.data.objects.get(obj)
    if obj:
        if select:
            obj.select_set(state=True)
        bpy.context.view_layer.objects.active = obj
    else:
        print('WARNING! Object {} does not exist'.format(obj.name))
        return {'CANCELLED'}


def clear_object_selection():
    bpy.ops.object.select_all(action='DESELECT')


CONTEXT_TO_OBJECT_MODE = {
    'EDIT_MESH': 'EDIT',
    'EDIT_CURVE': 'EDIT',
    'EDIT_SURFACE': 'EDIT',
    'EDIT_TEXT': 'EDIT',
    'EDIT_ARMATURE': 'EDIT',
    'EDIT_METABALL': 'EDIT',
    'EDIT_LATTICE': 'EDIT',
    'POSE': 'POSE',
    'SCULPT': 'SCULPT',
    'PAINT_WEIGHT': 'WEIGHT_PAINT',
    'PAINT_VERTEX': 'VERTEX_PAINT',
    'PAINT_TEXTURE': 'TEXTURE_PAINT',
    'PARTICLE': 'PARTICLE_EDIT',
    'OBJECT': 'OBJECT',
    'PAINT_GPENCIL': 'PAINT_GPENCIL',
    'EDIT_GPENCIL': 'EDIT_GPENCIL',
    'SCULPT_GPENCIL': 'SCULPT_GPENCIL',
    'WEIGHT_GPENCIL': 'WEIGHT_GPENCIL',
    'VERTEX_GPENCIL': 'VERTEX_GPENCIL',
}


def get_object_mode_from_context_mode(context_mode):
    '''Return the object mode for operator mode_set from the current context.mode'''
    return CONTEXT_TO_OBJECT_MODE.get(context_mode, 'OBJECT')


def duplicate_obj(obj, link=None):
    '''
    Duplicate an object withouth using modifiers
    @scene : needed to link new obj
    @obj : object
    Returns : the duplicate
    '''
    new_obj = obj.copy()
    new_obj.data = obj.data.copy()
    if link:
        bpy.context.scene.collection.objects.link(new_obj)
    return new_obj


def get_main_faceit_object():
    '''Returns the main object (head or face)'''
    faceit_objects = get_faceit_objects_list()
    for obj in faceit_objects:
        if "faceit_main" in obj.vertex_groups:
            return obj
    return None


def get_faceit_objects_list(clear_invalid_objects=True):
    '''Returns the registered faceit objects in a list.
    Removes items that can't be found in the scene from the propertycollection
    @clear_invalid_objects: when True, this will remove unfound items from the collection
    '''

    faceit_objects_property_collection = bpy.context.scene.faceit_face_objects

    faceit_objects = []

    for obj_item in faceit_objects_property_collection:
        # try to find by obj_pointer
        obj = get_object(obj_item.name)
        if obj is not None:
            faceit_objects.append(obj)
            continue
        elif clear_invalid_objects:
            print('removing item {} from faceit objects, because it does not exist in scene.'.format(obj_item.name))
            remove_item_from_collection_prop(faceit_objects_property_collection, obj_item)

    return faceit_objects


def set_lock_3d_view_rotations(value):
    '''Locks the viewport rotation from user input'''
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                space.region_3d.lock_rotation = value


def get_region_3d_space(context):
    '''Returns the region 3d of the current view'''
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    return space.region_3d


def get_any_view_locked():
    '''Returns True if any view is locked'''
    locked = False
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    locked = locked or space.region_3d.lock_rotation
    return locked


def ui_refresh_properties():
    '''Refreshes the properties panel'''
    for windowManager in bpy.data.window_managers:
        for window in windowManager.windows:
            for area in window.screen.areas:
                if area.type == 'PROPERTIES':
                    area.tag_redraw()


def ui_refresh_view_3d():
    '''Refreshes the view 3D panel'''
    for windowManager in bpy.data.window_managers:
        for window in windowManager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()


def ui_refresh_all():
    '''Refreshes all panels'''
    if not hasattr(bpy.data, "window_managers"):
        return
    for windowManager in bpy.data.window_managers:
        for window in windowManager.windows:
            for area in window.screen.areas:
                area.tag_redraw()


def remove_item_from_collection_prop(collection, item):
    '''Removes an @item from a given @collection'''
    item = collection.find(item.name)
    if item != -1:
        collection.remove(item)


def find_collection_in_children(collection, name):
    ''' Recursively searches for a collection in the children of a collection'''
    if collection.name == name:
        return collection
    for child in collection.children:
        found = find_collection_in_children(child, name)
        if found:
            return found


# def traverse_tree(t):
#     yield t
#     for child in t.children:
#         yield from traverse_tree(child)


# def parent_lookup():
#     parent_lookup_dict = {}
#     coll = bpy.context.view_layer.layer_collection
#     for coll in traverse_tree(coll):
#         for c in coll.children.keys():
#             parent_lookup_dict.setdefault(c, coll.name)
#     return parent_lookup_dict


def get_layer_collection(collection_name):
    master_collection = bpy.context.view_layer.layer_collection
    return find_collection_in_children(master_collection, collection_name)


def get_faceit_collection(force_access=True, create=True):
    '''Returns the faceit collection, if it does not exist, it creates it'''
    collection_name = 'Faceit_Collection'
    faceit_collection = bpy.data.collections.get(collection_name)
    if faceit_collection is None:
        if create:
            faceit_collection = bpy.data.collections.new(name=collection_name)
        else:
            return None
    faceit_layer_collection = get_layer_collection(collection_name)
    if faceit_layer_collection is None:
        bpy.context.scene.collection.children.link(faceit_collection)
        faceit_layer_collection = get_layer_collection(collection_name)
    if force_access:
        faceit_collection.hide_viewport = False
        faceit_layer_collection.exclude = False
        faceit_layer_collection.hide_viewport = False
    # Print parent of active collection
    # coll_parents = parent_lookup()
    # print("Parent of {} is {}".format(
    #     collection_name,
    #     coll_parents.get(collection_name))
    # )
    return faceit_collection


def is_collection_visible(context, collection):
    '''Returns True if the collection is visible'''
    if collection.hide_viewport:
        return False
    collection_name = collection.name
    master_collection = context.view_layer.layer_collection
    view_layer_collection = find_collection_in_children(master_collection, collection_name)
    if not view_layer_collection:
        return False
    return not (view_layer_collection.exclude and view_layer_collection.hide_viewport)


def set_hide_obj(obj, hide):
    '''
    un/hides the object
    @obj : the object
    @hide (bool): True = hide
    '''
    # hide the objectBase in renderlayer
    obj.hide_set(hide)
    # hide the object itself
    obj.hide_viewport = hide


def get_hide_obj(obj):
    return (obj.hide_get() or obj.hide_viewport)


def set_hidden_state_object(object_to_hide, hide_viewport, hide_render):
    '''
    object_to_hide : object to hide
    hide_viewport : hide the object itself
    hide_render : hide the objectBase in renderlayer
    '''
    object_to_hide.hide_viewport = hide_viewport
    object_to_hide.hide_set(hide_render)


def set_hidden_states(objects_hidden_states={}, overwrite=False, objects=[], hide_value=False):
    '''
    Set the state of hidden objects
    @objects_hidden_states : dictionary from get_hidden_states
    @overwrite : overwrite all values
    @objects : objects to hide/unhide
    @hide_value : value if overwrite
    '''
    if overwrite and objects:
        for obj in objects:
            if not obj:
                continue
            set_hidden_state_object(obj, hide_value, hide_value)
    for obj, states in objects_hidden_states.items():
        obj = get_object(obj)
        if not obj:
            continue
        hide_viewport = states[0]
        hide_render = states[1]
        set_hidden_state_object(obj, hide_viewport, hide_render)


def get_hidden_states(objects_to_hide):
    '''returns hidden state of objects in dictioray'''
    objects_hidden = {}
    for obj in objects_to_hide:
        objects_hidden[obj.name] = [obj.hide_viewport, obj.hide_get()]
    return objects_hidden


def get_faceit_control_armatures():
    ctrl_rigs = []
    for obj in bpy.context.scene.objects:
        if 'ctrl_rig_id' in obj:
            ctrl_rigs.append(obj)
            continue
        else:
            if 'FaceitControlRig' in obj.name:
                ctrl_rigs.append(obj)
    return ctrl_rigs


def get_faceit_control_armature():
    return bpy.context.scene.faceit_control_armature


def get_faceit_armature(force_original=False):
    '''Get the faceit armature object.'''
    rig = bpy.context.scene.faceit_armature
    if rig is not None and force_original is True:
        if not is_faceit_original_armature(rig):
            return None
    return rig


def get_rig_type(rig):
    """
    Get the type of this rig.
        @rig: the rig object
        Returns: 'FACEIT', 'RIGIFY', 'RIGIFY_NEW' or None
    """
    rig = get_faceit_armature()
    if rig is None:
        return None
    if is_faceit_original_armature(rig):
        return 'FACEIT'
    # Is this a rigify structure?
    if len(set((b.name for b in rig.data.bones)).intersection(FACEIT_BONES)) > len(FACEIT_BONES) // 4:
        if "lip_end.L.001" in rig.pose.bones:
            return 'RIGIFY_NEW'
        else:
            return 'RIGIFY'
    return None


def is_faceit_original_armature(rig):
    '''Check if the Faceit Armature is created with Faceit.'''
    if rig.name == 'FaceitRig':
        return True
    if all([b.name in FACEIT_BONES for b in rig.data.bones]):
        return True
    return False


def is_rigify_armature(rig):
    '''Check if the Armature is created with Rigify.'''
    # print(len(set((b.name for b in rig.data.bones)).intersection(FACEIT_BONES)))
    if 'rig_id' in rig.data:
        if len(rig.data['rig_id']) == 16:
            return True
    # Check if at least half of the Faceit (Rigify) bones are in the armature.#
    if len(set((b.name for b in rig.data.bones)).intersection(FACEIT_BONES)) > len(FACEIT_BONES) // 4:
        return True
    return False


def using_rigify_armature():
    '''Check if the user wants to use another Rigify face rig for generating the expressions.'''
    scene = bpy.context.scene
    if not scene.faceit_use_rigify_armature:
        return False
    rig = scene.faceit_armature
    if rig:
        if is_rigify_armature(rig):
            return True
    return False


def is_armature_bound_to_registered_objects(rig):
    '''Check whether the rig is bound to the registered objects. -> does an armature modifier exist?'''
    for obj in get_faceit_objects_list():
        if rig.name in [mod.object.name for mod in obj.modifiers if mod.type == 'ARMATURE' and mod.object is not None]:
            return True


def get_median_pos(locations):
    '''
    returns the center of all points in locations
    @locations : list of points (Vector3) in one space
    '''
    return Vector(np.mean(locations, axis=0).tolist())


def exit_nla_tweak_mode(context):
    '''exit the nla tweak mode (important for nla editor actions)'''
    current_type = bpy.context.area.type
    bpy.context.area.type = 'NLA_EDITOR'
    bpy.ops.nla.tweakmode_exit()
    bpy.context.area.type = current_type


def save_scene_state(context):
    '''Stores the current state of all objects'''
    hidden_states = get_hidden_states(context.scene.objects)
    selected_objects = context.selected_objects.copy()
    active_obj = context.object
    mode_save = get_object_mode_from_context_mode(context.mode)
    auto_key = context.scene.tool_settings.use_keyframe_insert_auto
    context.scene.tool_settings.use_keyframe_insert_auto = False
    state_dict = {
        'hidden_states': hidden_states,
        'selected_objects': selected_objects,
        'active_obj': active_obj,
        'mode_save': mode_save,
        'auto_key': auto_key,
    }
    return state_dict


def restore_scene_state(context, state_dict):
    '''Restores the scene state based on the state_dict.'''
    obj = context.object
    if obj:
        if not (obj.hide_get() or obj.hide_viewport):
            bpy.ops.object.mode_set(mode='OBJECT')
    clear_object_selection()
    hidden_states = state_dict['hidden_states']
    selected_objects = state_dict['selected_objects']
    active_obj = state_dict['active_obj']
    mode_save = state_dict['mode_save']
    auto_key = state_dict['auto_key']
    set_hidden_states(hidden_states)
    for obj in selected_objects:
        if obj:
            obj.select_set(True)
    if active_obj:
        try:
            set_active_object(active_obj.name, select=False)
            bpy.ops.object.mode_set(mode=mode_save)
        except RuntimeError:
            pass
    else:
        clear_active_object()
    context.scene.tool_settings.use_keyframe_insert_auto = auto_key
