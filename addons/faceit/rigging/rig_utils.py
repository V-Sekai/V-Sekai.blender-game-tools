import bpy
from mathutils import Vector
from operator import attrgetter
from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils


def get_median_position_from_vert_grp(vgroup_name):
    '''
    returns a median point of the vertices assossiated with:
    @vgroup_name [String] = the user defined vertex groups, for facial parts.
    '''
    position = Vector((0, 0, 0))

    obj = vg_utils.get_objects_with_vertex_group(vgroup_name)
    if not obj:
        return

    vs = vg_utils.get_verts_in_vgroup(obj, vgroup_name)

    # Remve group if it's empty
    if not vs:
        grp = obj.vertex_groups.get(vgroup_name)
        if grp:
            obj.vertex_groups.remove(grp)
        return None  # position

    mw = obj.matrix_world
    # get the global coordinates of group vertices
    global_v_co = [mw @ v.co for v in vs]

    if vgroup_name == 'faceit_tongue':
        position = min(global_v_co, key=attrgetter('y'))
        position.x = 0
    # teeth or eyes
    else:
        # get bounds (highest and lowest vertex)
        # bounds = [(max(global_v_co, key=attrgetter('z'))), (min(global_v_co, key=attrgetter('z')))]
        bounds = get_bounds_from_locations(global_v_co, 'z')
        position = futils.get_median_pos(bounds)
        # for teeth only - set y as well
        if vgroup_name == 'faceit_teeth':
            # bounds = [(max(global_v_co, key=attrgetter('y'))), (min(global_v_co, key=attrgetter('y')))]
            bounds = get_bounds_from_locations(global_v_co, 'y')
            position.y = futils.get_median_pos(bounds).y
            position.x = 0

    return position


def get_bounds_from_locations(locations, axis):
    '''Returns the bounds (max, min) for the specified locations
    @locations: list of vector3 elements,
    @axis: string in x, y, z
    '''

    if not locations:
        return

    axis = str(axis).lower()
    if not axis in ('x', 'y', 'z'):
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

    for pb in rig.pose.bones:
        bg = pb.bone_group
        if bg:
            if bg.name in bone_groups_dict.keys():
                bone_groups_dict[bg.name]['bones'].append(pb.name)
            else:
                bone_groups_dict[bg.name] = {
                    'bones': [pb.name],
                    'color_set': bg.color_set,
                    'colors': {
                        'active': bg.colors.active,
                        'normal': bg.colors.normal,
                        'select': bg.colors.select,
                        'show_colored_constraints': bg.colors.show_colored_constraints,
                    }
                }
    return bone_groups_dict


def set_bone_groups_from_dict(rig, bone_groups_dict):
    ''' Creates and/or sets the pose bone groups based on a dictionary. @Rig needs to be the active object + Pose mode '''

    for bg_name, values in bone_groups_dict.items():
        bg = rig.pose.bone_groups.get(bg_name)
        if bg:
            # The bg already exists
            pass
        else:
            bpy.ops.pose.group_add()
            bg = rig.pose.bone_groups[-1]
            bg.name = bg_name
            color_set = values['color_set']
            bg.color_set = color_set
            if color_set == 'CUSTOM':
                bg.colors.active = values['colors']['active']
                bg.colors.normal = values['colors']['normal']
                bg.colors.select = values['colors']['select']
                bg.colors.show_colored_constraints = values['colors']['show_colored_constraints']

        for pb_name in values['bones']:
            pb = rig.pose.bones.get(pb_name)
            pb.bone_group = bg
