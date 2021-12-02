import bpy
import numpy as np
from mathutils import Vector


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


def set_active_object(obj):
    '''
    select the object
    @object_name: String or id
    '''
    if isinstance(obj, str):
        obj = bpy.data.objects.get(obj)
    if obj:
        obj.select_set(state=True)
        bpy.context.view_layer.objects.active = obj
    else:
        print('WARNING! Object {} does not exist'.format(obj.name))
        return{'CANCELLED'}


def clear_object_selection():
    bpy.ops.object.select_all(action='DESELECT')


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
        if obj.vertex_groups.get('faceit_main'):
            return obj

    return faceit_objects[0]


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


def remove_item_from_collection_prop(collection, item):
    '''Removes an @item from a given @collection'''
    item = collection.find(item.name)
    if item != -1:
        collection.remove(item)


def get_faceit_collection(force_access=True, create=True):

    faceit_collection = bpy.data.collections.get('Faceit_Collection')
    context = bpy.context
    if not faceit_collection:
        if create:
            faceit_collection = bpy.data.collections.new(name='Faceit_Collection')
            context.scene.collection.children.link(faceit_collection)
        else:
            return

    if force_access:
        # Get collection in viewlayer to toggle exclude and visibility options
        master_collection = context.view_layer.layer_collection
        view_layer_faceit_collection = master_collection.children.get('Faceit_Collection')

        if view_layer_faceit_collection:
            # make sure the collection is included in viewlayer
            view_layer_faceit_collection.exclude = False
            view_layer_faceit_collection.hide_viewport = False
        faceit_collection.hide_viewport = False

    return faceit_collection


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
    list(objects_to_hide)
    objects_hidden = {}
    for obj in objects_to_hide:
        objects_hidden[obj.name] = [obj.hide_viewport, obj.hide_get()]
    return objects_hidden


def get_modifiers_of_type(obj, type):
    mods = []
    for mod in obj.modifiers:
        if mod.type == type:
            mods.append(mod)
    return mods


def add_faceit_armature_modifier(obj, rig, force=False, force_original=True):
    '''add faceit_ARMATURE modifier. Set the rig object as target. reorder and setup. return mod'''

    if rig is None:
        rig = get_faceit_armature(force_original=force_original)  # bpy.data.objects.get('FaceitRig')
        if rig is None and not force:
            return

    if obj is None:
        return

    mod = get_faceit_armature_modifier(obj, force_original=force_original)
    if not mod:
        mod = obj.modifiers.new(name='Faceit_Armature', type='ARMATURE')

    mod.object = rig

    reorder_armature_in_modifier_stack(obj, mod)

    mod.show_on_cage = True
    mod.show_in_editmode = True
    mod.show_viewport = True
    mod.show_render = True

    return mod


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
    rig = bpy.context.scene.faceit_armature  # bpy.futils.get_faceit_armature()
    if rig != None:
        if rig.name not in bpy.context.scene.objects:
            rig = None
    if rig == None or force_original:
        rig = get_object('FaceitRig')
    return rig


def get_faceit_armature_modifier(obj, force_original=True):
    if obj is None:
        return

    rig = get_faceit_armature(force_original=force_original)

    rig_name = 'FaceitRig'
    if rig:
        rig_name = rig.name
    for mod in obj.modifiers:

        if mod.type == 'ARMATURE':

            match_object = False
            if mod.object:
                match_object = mod.object.name == rig_name
            match_name = mod.name == 'Faceit_Armature' or mod.name == rig_name
            if match_name or match_object:
                return mod


def reorder_armature_in_modifier_stack(obj, arm_mod=None):

    if not arm_mod:
        arm_mod = get_faceit_armature_modifier(obj)
    if arm_mod:
        # for _ in range(0, len(arm_mod.modifiers)):
        safe_count = 100
        while obj.modifiers.find(arm_mod.name) != 0:

            bpy.ops.object.modifier_move_up({'object': obj}, modifier=arm_mod.name)
            if safe_count <= 0:
                break
            safe_count -= 1
        # put mirror at first
        for mod in obj.modifiers:
            if mod.type == 'MIRROR':
                safe_count = 100
                while obj.modifiers.find(mod.name) != 0:
                    bpy.ops.object.modifier_move_up({'object': obj}, modifier=mod.name)
                    if safe_count <= 0:
                        break
                    safe_count -= 1


def apply_modifier(mod_name):
    if bpy.app.version >= (2, 90, 0):
        bpy.ops.object.modifier_apply(modifier=mod_name)
    else:
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier=mod_name)


def get_mouse_select():
    active_kc = bpy.context.preferences.keymap.active_keyconfig
    active_pref = bpy.context.window_manager.keyconfigs[active_kc].preferences
    return getattr(active_pref, 'select_mouse', 'LEFT')


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
