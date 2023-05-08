from operator import attrgetter

import bpy
from mathutils import Vector, Quaternion

from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils


def get_evaluated_vertex_group_positions(obj, vgroup_name) -> list:
    '''Returns a list world location vectors for each vertex in vertex group'''
    dg = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(dg)
    vs = vg_utils.get_verts_in_vgroup(obj_eval, vgroup_name)
    # Remve group if it's empty
    if not vs:
        grp = obj_eval.vertex_groups.get(vgroup_name)
        if grp:
            obj_eval.vertex_groups.remove(grp)
        return None  # position
    mw = obj_eval.matrix_world
    return [mw @ v.co for v in vs]


def get_bounds_from_locations(locations, axis):
    '''Returns the bounds (max, min) for the specified locations
    @locations: list of vector3 elements,
    @axis: string in x, y, z
    '''
    if not locations:
        return
    axis = str(axis).lower()
    if axis not in ('x', 'y', 'z'):
        return
    bounds = [(max(locations, key=attrgetter(axis))), (min(locations, key=attrgetter(axis)))]
    return bounds


def reset_stretch(rig_obj=None, bone=None):
    ''' reset stretch constraints '''
    # it is important to frame_set before resetting!
    bpy.context.scene.frame_set(1)

    def reset_bones_contraints(bone):
        for c in b.constraints:
            if c.name == 'Stretch To':
                c.rest_length = 0
    if bone:
        reset_bones_contraints(bone)
    elif rig_obj:
        for b in rig_obj.pose.bones:
            reset_bones_contraints(b)


def get_bone_delta(bone1, bone2) -> Vector:
    '''returns object space vector between two pose bones'''
    pos1 = bone1.matrix.translation
    pos2 = bone2.matrix.translation
    vec = pos1 - pos2
    return vec


def set_lid_follow_constraints(rig, side="L"):
    '''Set best follow location constraint influence on the lid bones.'''
    # All bottom lid bones
    bot_inner_lid = rig.pose.bones.get(f"lid.B.{side}.001")
    bot_mid_lid = rig.pose.bones.get(f"lid.B.{side}.002")
    bot_outer_lid = rig.pose.bones.get(f"lid.B.{side}.003")
    # All upper lid bones
    top_outer_lid = rig.pose.bones.get(f"lid.T.{side}.001")
    top_mid_lid = rig.pose.bones.get(f"lid.T.{side}.002")
    top_inner_lid = rig.pose.bones.get(f"lid.T.{side}.003")
    # Calculate a delta vector for each pair (top to bottom)
    mid_delta = get_bone_delta(top_mid_lid, bot_mid_lid)
    outer_lid_delta = get_bone_delta(top_outer_lid, bot_outer_lid)
    inner_lid_delta = get_bone_delta(top_inner_lid, bot_inner_lid)
    # Set the influence of the copy location constraint
    outer_lid_influence = outer_lid_delta.length / mid_delta.length
    constraint = top_outer_lid.constraints.get("Copy Location")
    if constraint:
        constraint.influence = outer_lid_influence
    constraint = bot_outer_lid.constraints.get("Copy Location")
    if constraint:
        constraint.influence = outer_lid_influence
    inner_lid_influence = inner_lid_delta.length / mid_delta.length
    constraint = top_inner_lid.constraints.get("Copy Location")
    if constraint:
        constraint.influence = inner_lid_influence
    constraint = bot_inner_lid.constraints.get("Copy Location")
    if constraint:
        constraint.influence = inner_lid_influence


def child_of_set_inverse(rig_obj=None, bone=None):
    ''' reset stretch constraints '''
    if bpy.context.mode != 'POSE':
        return

    def set_inverse_on_bone(bone):
        for c in bone.constraints:
            if c.type == 'CHILD_OF':
                c.set_inverse_pending = True
    if bone:
        set_inverse_on_bone(bone)
    elif rig_obj:
        for b in rig_obj.pose.bones:
            set_inverse_on_bone(b)


def get_bone_groups_dict(rig):
    ''' Reads all bone groups for all pose bones and returns them in a dictionary '''
    # bone_group_name: bones, color_set, colors
    bone_groups_dict = {}
    for bg in rig.pose.bone_groups:
        bone_groups_dict[bg.name] = {
            'color_set': bg.color_set,
            'colors': {
                'active': bg.colors.active.copy(),
                'normal': bg.colors.normal.copy(),
                'select': bg.colors.select.copy(),
                'show_colored_constraints': bg.colors.show_colored_constraints,
            },
            'bones': [pb.name for pb in rig.pose.bones if pb.bone_group == bg],
        }
        # bone_groups_dict[bg.name]['bones'] = [pb.name for pb in rig.pose.bones if pb.bone_group == bg]
    return bone_groups_dict


def set_bone_groups_from_dict(rig, bone_groups_dict):
    ''' Creates and/or sets the pose bone groups based on a dictionary. @Rig needs to be the active object + Pose mode '''
    for bg_name, values in bone_groups_dict.items():
        bg = rig.pose.bone_groups.get(bg_name)
        if bg:
            # Create a new group if the name already exists
            bg_name = bg_name + '_Faceit'
        bpy.ops.pose.group_add()
        bg = rig.pose.bone_groups[-1]
        bg.name = bg_name
        rig.pose.bone_groups.active = bg
        # color_set = values['color_set']
        bg.color_set = 'CUSTOM'
        bg.colors.active = values['colors']['active']
        bg.colors.normal = values['colors']['normal']
        bg.colors.select = values['colors']['select']
        bg.colors.show_colored_constraints = values['colors']['show_colored_constraints']

    # bpy.ops.object.mode_set(mode='OBJECT')
    # bpy.ops.object.mode_set(mode='POSE')
        for pb_name in values['bones']:
            pb = rig.pose.bones.get(pb_name)
            if pb:
                pb.bone_group = bg
