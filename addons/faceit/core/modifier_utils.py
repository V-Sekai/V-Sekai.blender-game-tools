
import bpy

from .faceit_utils import get_faceit_armature
from .faceit_data import BAKE_MOD_TYPES, MOD_TYPE_ICON_DICT, GENERATORS


def add_faceit_armature_modifier(obj, rig, force=False, force_original=True):
    '''add faceit_ARMATURE modifier. Set the rig object as target. reorder and setup. return mod'''
    if rig is None:
        rig = get_faceit_armature(force_original=force_original)
        if rig is None and not force:
            return
    if obj is None:
        return
    mod = get_faceit_armature_modifier(obj, force_original=force_original)
    if mod:
        obj.modifiers.remove(mod)
    mod = obj.modifiers.new(name='Faceit_Armature', type='ARMATURE')
    mod.object = rig
    reorder_armature_in_modifier_stack(obj, mod)
    mod.show_on_cage = True
    mod.show_in_editmode = True
    mod.show_viewport = True
    mod.show_render = True
    set_bake_modifier_item(mod, set_bake=True, is_faceit_mod=True)
    return mod


def get_faceit_armature_modifier(obj, force_original=True):
    '''Get the faceit armature modifier for a specific object.'''
    rig = get_faceit_armature(force_original=force_original)
    if rig is None:
        print("No FaceitRig found")
        return
    for mod in obj.modifiers:
        if mod.type == 'ARMATURE':
            if mod.object == rig:
                return mod


def restore_modifier_order(obj):
    obj_item = bpy.context.scene.faceit_face_objects[obj.name]
    for mod_item in obj_item.modifiers:
        mod = obj.modifiers.get(mod_item.name)
        if mod:
            if bpy.app.version < (3, 6, 0):
                override = {'object': obj, 'active_object': obj}
                bpy.ops.object.modifier_move_to_index(
                    override,
                    modifier=mod.name,
                    index=mod_item.index
                )
            else:
                index = obj.modifiers.find(mod.name)
                try:
                    obj.modifiers.move(index, mod_item.index)
                except RuntimeError:
                    pass


def set_mod_bake(obj, mod, bake=True):
    obj_item = bpy.context.scene.faceit_face_objects.get(obj.name)
    if obj_item is not None:
        mod_item = obj_item.modifiers.get(mod.name)
        if mod_item is not None:
            mod_item.bake = bake


def set_bake_modifier_properties(mod, mod_item):
    mod_item.show_viewport = mod.show_viewport
    mod_item.show_render = mod.show_render
    mod_item.show_in_editmode = mod.show_in_editmode
    mod_item.show_on_cage = mod.show_on_cage
    mod_item.show_expanded = mod.show_expanded
    mod_item.show_in_editmode = mod.show_in_editmode
    mod_item.show_in_editmode = mod.show_in_editmode
    if mod.type == 'SURFACE_DEFORM':
        mod_item.strength = mod.strength
        mod_item.target = mod.target
        mod_item.use_sparse_bind = mod.use_sparse_bind
        mod_item.vertex_group = mod.vertex_group
        mod_item.invert_vertex_group = mod.invert_vertex_group
        mod_item.is_bound = mod.is_bound
        mod_item.falloff = mod.falloff
    elif mod.type == 'SHRINKWRAP':
        mod_item.target = mod.target
        mod_item.offset = mod.offset
        mod_item.project_limit = mod.project_limit
        mod_item.subsurf_levels = mod.subsurf_levels
        mod_item.use_invert_cull = mod.use_invert_cull
        mod_item.use_negative_direction = mod.use_negative_direction
        mod_item.use_positive_direction = mod.use_positive_direction
        mod_item.use_project_x = mod.use_project_x
        mod_item.use_project_y = mod.use_project_y
        mod_item.use_project_z = mod.use_project_z
        mod_item.wrap_method = mod.wrap_method
        mod_item.wrap_mode = mod.wrap_mode
        mod_item.vertex_group = mod.vertex_group
        mod_item.invert_vertex_group = mod.invert_vertex_group
    elif mod.type == 'ARMATURE':
        mod_item.object = mod.object
        mod_item.use_bone_envelopes = mod.use_bone_envelopes
        mod_item.use_deform_preserve_volume = mod.use_deform_preserve_volume
        mod_item.use_multi_modifier = mod.use_multi_modifier
        mod_item.use_vertex_groups = mod.use_vertex_groups
        mod_item.vertex_group = mod.vertex_group
        mod_item.invert_vertex_group = mod.invert_vertex_group
    elif mod.type == 'CORRECTIVE_SMOOTH':
        mod_item.factor = mod.factor
        mod_item.is_bind = mod.is_bind
        mod_item.iterations = mod.iterations
        mod_item.smooth_type = mod.smooth_type
        mod_item.scale = mod.scale
        mod_item.smooth_type = mod.smooth_type
        mod_item.use_only_smooth = mod.use_only_smooth
        mod_item.use_pin_boundary = mod.use_pin_boundary
    elif mod.type == 'LATTICE':
        mod_item.object = mod.object
        mod_item.vertex_group = mod.vertex_group
        mod_item.invert_vertex_group = mod.invert_vertex_group
        mod_item.strength = mod.strength
    elif mod.type == 'SMOOTH':
        mod_item.factor = mod.factor
        mod_item.iterations = mod.iterations
        mod_item.use_x = mod.use_x
        mod_item.use_y = mod.use_y
        mod_item.use_z = mod.use_z
        mod_item.vertex_group = mod.vertex_group
        mod_item.invert_vertex_group = mod.invert_vertex_group
    elif mod.type == 'LAPLACIANSMOOTH':
        mod_item.lambda_factor = mod.lambda_factor
        mod_item.lambda_border = mod.lambda_border
        mod_item.iterations = mod.iterations
        mod_item.use_volume_preserve = mod.use_volume_preserve
        mod_item.use_normalized = mod.use_normalized
        mod_item.use_x = mod.use_x
        mod_item.use_y = mod.use_y
        mod_item.use_z = mod.use_z
        mod_item.vertex_group = mod.vertex_group
        mod_item.invert_vertex_group = mod.invert_vertex_group
    if mod.type == 'MESH_DEFORM':
        mod_item.precision = mod.precision
        mod_item.object = mod.object
        mod_item.is_bound = mod.is_bound
        mod_item.use_dynamic_bind = mod.use_dynamic_bind
        mod_item.vertex_group = mod.vertex_group
        mod_item.invert_vertex_group = mod.invert_vertex_group


def set_bake_modifier_item(mod, obj_item=None, set_bake=False, is_faceit_mod=False, index=-1):
    '''Set properties of a modifier to a modifier item. Create a new modifier item if it doesn't exist.'''
    if obj_item is None:
        obj_item = bpy.context.scene.faceit_face_objects.get(mod.id_data.name)
        if obj_item is None:
            return None
    mod_item = obj_item.modifiers.get(mod.name)
    if mod_item is None:
        mod_item = obj_item.modifiers.add()
    mod_item.name = mod.name
    mod_item.type = mod.type
    mod_item.mod_icon = MOD_TYPE_ICON_DICT.get(mod.type, 'MODIFIER')
    mod_item.bake = set_bake
    if index != -1:
        mod_item.index = index
    mod_item.is_faceit_modifier = is_faceit_mod
    if mod.type in BAKE_MOD_TYPES:
        mod_item.can_bake = True
        if mod_item.bake:
            set_bake_modifier_properties(mod, mod_item)


def populate_bake_modifier_items(objects):
    '''Populates the bake modifier list for all passed objects.
    @objects: Should be a list of objects in faceit_face_objects.
    '''
    for obj in objects:
        obj_item = bpy.context.scene.faceit_face_objects.get(obj.name)
        if obj_item is None:
            continue
        bake_mods = []
        faceit_mods = []
        if not obj_item.modifiers:
            arma_mod = get_faceit_armature_modifier(obj, force_original=False)
            if arma_mod:
                bake_mods = faceit_mods = [arma_mod.name, ]
        else:
            bake_mods = [mod_item.name for mod_item in obj_item.modifiers if mod_item.bake]
            faceit_mods = [mod_item.name for mod_item in obj_item.modifiers if mod_item.is_faceit_modifier]
        obj_item.modifiers.clear()
        for i, mod in enumerate(obj.modifiers):
            set_bake_modifier_item(mod, obj_item=obj_item, set_bake=mod.name in bake_mods,
                                   is_faceit_mod=mod.name in faceit_mods, index=i)


def restore_bake_modifiers(obj, modifier_list):
    '''Restores the bake modifiers for an object.'''
    for mod_item in modifier_list:
        if not mod_item.bake:
            continue
        mod = obj.modifiers.get(mod_item.name)
        if mod:
            mod.show_viewport = True
        elif mod_item.recreate:
            # Create a new modifier with same settings
            mod = obj.modifiers.new(mod_item.name, mod_item.type)
            mod.show_viewport = mod_item.show_viewport
            mod.show_render = mod_item.show_render
            mod.show_in_editmode = mod_item.show_in_editmode
            mod.show_on_cage = mod_item.show_on_cage
            mod.show_expanded = mod_item.show_expanded
            mod.show_in_editmode = mod_item.show_in_editmode
            mod.show_in_editmode = mod_item.show_in_editmode
            if mod_item.type == 'SURFACE_DEFORM':
                mod.show_expanded = mod_item.show_expanded
                mod.strength = mod_item.strength
                mod.target = mod_item.target
                mod.use_sparse_bind = mod_item.use_sparse_bind
                mod.invert_vertex_group = mod_item.invert_vertex_group
                mod.vertex_group = mod_item.vertex_group
            elif mod_item.type == 'SHRINKWRAP':
                mod.target = mod_item.target
                mod.offset = mod_item.offset
                mod.project_limit = mod_item.project_limit
                mod.subsurf_levels = mod_item.subsurf_levels
                mod.use_invert_cull = mod_item.use_invert_cull
                mod.use_negative_direction = mod_item.use_negative_direction
                mod.use_positive_direction = mod_item.use_positive_direction
                mod.use_project_x = mod_item.use_project_x
                mod.use_project_y = mod_item.use_project_y
                mod.use_project_z = mod_item.use_project_z
                mod.wrap_method = mod_item.wrap_method
                mod.wrap_mode = mod_item.wrap_mode
                mod.invert_vertex_group = mod_item.invert_vertex_group
                mod.vertex_group = mod_item.vertex_group
            elif mod.type == 'ARMATURE':
                mod.object = mod_item.object
                mod.use_bone_envelopes = mod_item.use_bone_envelopes
                mod.use_deform_preserve_volume = mod_item.use_deform_preserve_volume
                mod.use_multi_modifier = mod_item.use_multi_modifier
                mod.use_vertex_groups = mod_item.use_vertex_groups
                mod.invert_vertex_group = mod_item.invert_vertex_group
                mod.vertex_group = mod_item.vertex_group
            elif mod.type == 'CORRECTIVE_SMOOTH':
                mod.factor = mod_item.factor
                mod.iterations = mod_item.iterations
                mod.smooth_type = mod_item.smooth_type
                mod.scale = mod_item.scale
                mod.smooth_type = mod_item.smooth_type
                mod.use_only_smooth = mod_item.use_only_smooth
                mod.use_pin_boundary = mod_item.use_pin_boundary
            elif mod.type == 'LATTICE':
                mod.object = mod_item.object
                mod.vertex_group = mod_item.vertex_group
                mod.invert_vertex_group = mod_item.invert_vertex_group
                mod.strength = mod_item.strength
            elif mod.type == 'SMOOTH':
                mod.factor = mod_item.factor
                mod.iterations = mod_item.iterations
                mod.use_x = mod_item.use_x
                mod.use_y = mod_item.use_y
                mod.use_z = mod_item.use_z
                mod.vertex_group = mod_item.vertex_group
                mod.invert_vertex_group = mod_item.invert_vertex_group
            elif mod.type == 'LAPLACIANSMOOTH':
                mod.lambda_factor = mod_item.lambda_factor
                mod.lambda_border = mod_item.lambda_border
                mod.iterations = mod_item.iterations
                mod.use_volume_preserve = mod_item.use_volume_preserve
                mod.use_normalized = mod_item.use_normalized
                mod.use_x = mod_item.use_x
                mod.use_y = mod_item.use_y
                mod.use_z = mod_item.use_z
                mod.vertex_group = mod_item.vertex_group
                mod.invert_vertex_group = mod_item.invert_vertex_group
            if mod.type == 'MESH_DEFORM':
                mod.precision = mod_item.precision
                mod.object = mod_item.object
                mod.is_bound = mod_item.is_bound
                mod.use_dynamic_bind = mod_item.use_dynamic_bind
                mod.vertex_group = mod_item.vertex_group
                mod.invert_vertex_group = mod_item.invert_vertex_group

        if mod is not None and obj.animation_data is not None:
            for dr_item in mod_item.drivers:
                dr = obj.animation_data.drivers.find(dr_item.data_path)
                if dr is not None:
                    dr.mute = False

    # Restore the modifier order
    for mod_item in modifier_list:
        mod = obj.modifiers.get(mod_item.name)
        if mod:
            if bpy.app.version < (3, 6, 0):
                override = {'object': obj, 'active_object': obj}
                bpy.ops.object.modifier_move_to_index(
                    override,
                    modifier=mod.name,
                    index=mod_item.index
                )
            else:
                index = obj.modifiers.find(mod.name)
                try:
                    obj.modifiers.move(index, mod_item.index)
                except RuntimeError:
                    pass
        # Restore modifier drivers
        if obj.animation_data is not None:
            for dr_item in mod_item.drivers:
                dr = obj.animation_data.drivers.find(dr_item.data_path)
                if dr is not None:
                    dr.mute = False
    # Re-bind deform modifiers
    bind_valid_bake_modifiers(obj, modifier_list)


def bind_valid_bake_modifiers(obj, modifier_list):
    '''Re-bind deform modifiers'''
    # bpy.context.scene.frame_set(0)
    for mod_item in modifier_list:
        if not mod_item.bake:
            continue
        mod = obj.modifiers.get(mod_item.name)
        if mod is not None:
            if mod.show_viewport:
                if mod_item.type == 'SURFACE_DEFORM':
                    if mod_item.is_bound:
                        if bpy.app.version < (4, 0, 0):
                            bpy.ops.object.surfacedeform_bind(
                                {"object": obj},
                                modifier=mod.name
                            )
                            bpy.ops.object.surfacedeform_bind(
                                {"object": obj},
                                modifier=mod.name
                            )
                        else:
                            with bpy.context.temp_override(object=obj, active_object=obj):
                                bpy.ops.object.surfacedeform_bind(
                                    modifier=mod.name,
                                )
                elif mod_item.type == 'CORRECTIVE_SMOOTH':
                    if mod_item.smooth_type == 'BIND':
                        if mod_item.is_bind:
                            if bpy.app.version < (4, 0, 0):
                                bpy.ops.object.correctivesmooth_bind(
                                    {"object": obj},
                                    modifier=mod.name
                                )
                            else:
                                with bpy.context.temp_override(object=obj, active_object=obj):
                                    bpy.ops.object.correctivesmooth_bind(
                                        modifier=mod.name,
                                    )


def reorder_armature_in_modifier_stack(obj, arm_mod=None):
    '''Reorder the armature modifier in the modifier stack.'''
    # deformers = ['SURFACE_DEFORM']
    above_faceit_arma = ['MIRROR', 'SURFACE_DEFORM', 'LATTICE', 'SMOOTH', 'SURFACE_DEFORM',
                         'LAPLACIANSMOOTH', 'SIMPLE_DEFORM', 'BEVEL', 'BOOLEAN', 'BUILD', 'EDGE_SPLIT', 'NODES', 'SKIN',
                         'SOLIDIFY', 'TRIANGULATE', 'VOLUME_TO_MESH', 'WELD', 'SHRINKWRAP', 'WARP'
                         'CURVE', 'CAST']
    if not arm_mod:
        return
    new_idx = -1
    if arm_mod:
        above_mods = [i for i, mod in enumerate(obj.modifiers) if mod.type == 'ARMATURE' and mod != arm_mod]
        if not above_mods:
            above_mods = [i for i, m in enumerate(obj.modifiers) if m.type in above_faceit_arma]
        if above_mods:
            # Move it right below other armature mods
            new_idx = max(above_mods)
            if bpy.app.version < (3, 6, 0):
                override = {'object': obj, 'active_object': obj}
                bpy.ops.object.modifier_move_to_index(
                    override,
                    modifier=arm_mod.name,
                    index=new_idx + 1
                )
            else:
                index = obj.modifiers.find(arm_mod.name)
                obj.modifiers.move(index, new_idx + 1)


def get_modifiers_of_type(obj, type):
    mods = []
    for mod in obj.modifiers:
        if mod.type == type:
            mods.append(mod)
    return mods


def apply_modifier(mod_name):
    if bpy.app.version >= (2, 90, 0):
        bpy.ops.object.modifier_apply(modifier=mod_name)
    else:
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier=mod_name)


def move_above_generators(mod, obj):
    '''Move the modifier above other generator mods'''
    gen_mod_types = GENERATORS.copy()
    gen_mod_types.remove('MULTIRES')  # Can't move above a modifier requiring original data.
    above_mods = [i for i, m in enumerate(obj.modifiers) if m.type in gen_mod_types]
    if above_mods:
        new_idx = min(above_mods)
        if bpy.app.version < (3, 6, 0):
            override = {'object': obj, 'active_object': obj}
            bpy.ops.object.modifier_move_to_index(override, modifier=mod.name, index=new_idx)
        else:
            index = obj.modifiers.find(mod.name)
            obj.modifiers.move(index, new_idx)
