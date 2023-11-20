import bpy
from mathutils import Vector

from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import shape_key_utils


def get_custom_slider_from_shape(c_rig, shape_name):
    ''' Get the control slider by comparing the bone name to shape name. 
    @c_rig: the control rig.
    @shape_name: the target shape.
    '''
    arkit_ref_data = fdata.get_arkit_shape_data().keys()
    if shape_name not in arkit_ref_data:
        return c_rig.pose.bones.get('c_{}_slider'.format(shape_name))


def get_custom_sliders_in_crig(c_rig):

    shape_key_names = []

    if c_rig:

        crig_targets = c_rig.faceit_crig_targets
        if not crig_targets:
            return shape_key_names
        return [n.name for n in crig_targets if get_custom_slider_from_shape(c_rig, n.name)]


def get_custom_sliders_in_crig_targets_enum(self, context):
    '''Returns an enum list of all custom sliders in the active control rig '''
    # blender is prone to crash without making shapes global
    global shapes
    shapes = []

    if context is None:
        return shapes
    # faceit_objects = futils.get_faceit_objects_list()
    c_rig = futils.get_faceit_control_armature()
    if c_rig:

        for i, name in enumerate(get_custom_sliders_in_crig(c_rig)):

            shapes.append((name, name, name, i))
    else:
        print('no shapes found --> add None')
        shapes.append(("None", "None", "None"))

    return shapes


def get_custom_sliders_from_faceit_objects_enum(self, context):
    '''Returns an enum list of all available shape keys that are not already used in custom sliders '''
    # blender is prone to crash without making shapes global
    global shapes
    shapes = []

    if context is None:
        print('get_shape_keys_from_main_object --> Context is None')
        return shapes
    faceit_objects = futils.get_faceit_objects_list()

    if faceit_objects:

        crig = futils.get_faceit_control_armature()
        if crig:
            crig_target_shapes = crig.faceit_crig_targets
        else:
            crig_target_shapes = []

        shape_key_names = [n for n in shape_key_utils.get_shape_key_names_from_objects(
            faceit_objects) if n not in crig_target_shapes]

        for i, name in enumerate(shape_key_names):

            shapes.append((name, name, name, i))
    else:
        print('no shapes found --> add None')
        shapes.append(("None", "None", "None"))

    return shapes


def generate_extra_sliders(context, shape_name, slider_range, rig_obj, max_rows=10, overwrite=False) -> str:
    """Create standart shape key sliders in the control rig armature
    Args:
        @shape: [string] name of new slider.
        @slider_range: [string] value in (pos_range, full range)
        @rig_obj: the obj id of the control rig armature
        @max_rows: When multiple shapes are present, create a new column for every [...] shapes
    Returns:
        the name of the new slider
    """
    mirror_settings = rig_obj.data.use_mirror_x
    rig_obj.data.use_mirror_x = False
    layer_state = rig_obj.data.layers[:]
    for i in range(len(rig_obj.data.layers)):
        rig_obj.data.layers[i] = True
    slider_existing_already = get_all_slider_bones(rig_obj, only_controllers=True)
    bpy.ops.object.mode_set(mode='EDIT')
    ref_slider_parent_bone = rig_obj.data.edit_bones.get('c_slider_small_ref_parent')
    init_pos = ref_slider_parent_bone.head.copy()
    ref_length = ref_slider_parent_bone.length

    def select_ref_bones(slider_range):
        if slider_range == 'full_range':
            ref_bones = ['c_slider_ref', 'c_slider_ref_parent', 'c_slider_ref_txt']
        elif slider_range == 'pos_range':
            ref_bones = ['c_slider_small_ref', 'c_slider_small_ref_parent', 'c_slider_small_ref_txt']
        for b_name in ref_bones:
            b = rig_obj.data.edit_bones.get(b_name)
            if b:
                b.select = True
            else:
                print('bones not found...')
                return

    def new_bone_pair_at_location(name, pos, overwrite=False):
        '''create new slider bones and move them to location'''

        bpy.ops.armature.select_all(action='DESELECT')

        edit_bones = rig_obj.data.edit_bones
        # Try to find the bones:
        b_parent = edit_bones.get('c_{}_slider_parent'.format(name))
        b_txt = edit_bones.get('c_{}_slider_txt'.format(name))
        b_slider = edit_bones.get('c_{}_slider'.format(name))
        slider_bones = [b_parent, b_txt, b_slider]

        if any([b is not None for b in slider_bones]) and overwrite:
            pos = b_slider.head.copy()
            for b in slider_bones:
                edit_bones.remove(b)
            slider_bones = None

        # Create new bones
        if not slider_bones or all([b is None for b in slider_bones]):
            # Create new slider bones:
            select_ref_bones(slider_range)
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.armature.duplicate()
            slider_bones = context.selected_bones

        elif any([b is not None for b in slider_bones]) and not overwrite:
            slider_existing_already.append(b_slider.name)
            return False

        # b_parent, b_txt, b_slider = get_slider_bones(name)
        # renamex
        for b in slider_bones:
            vec = pos - b.head
            if 'txt' in b.name:
                # Move above slider
                vec.z += rig_obj.data.edit_bones.get('c_slider_ref_txt').length

                # Move to the start of the parent bone shape
                vec.x -= rig_obj.data.edit_bones.get('c_slider_ref_parent').length / 1.5
                b.name = 'c_{}_slider_txt'.format(name)
                b.hide_select = True
            elif 'parent' in b.name:
                b.name = 'c_{}_slider_parent'.format(name)
                b.hide_select = True
            else:
                b_name = b.name = 'c_{}_slider'.format(name)
                slider_existing_already.append(b_name)

            # Move the bone
            b.translate(vec)

            b.layers[2] = True
            b.layers[31] = False

        return True

    ##### Create #####
    pos = init_pos.copy()
    total_slider_count = 0
    if slider_existing_already:
        total_slider_count = len(slider_existing_already)
        slider_pos_x = total_slider_count // max_rows * ref_length * 2
        slider_pos_z = total_slider_count % max_rows * ref_length / 2
        pos = Vector((
            pos.x + slider_pos_x,
            pos.y,
            init_pos.z + slider_pos_z)
        )
    result = new_bone_pair_at_location(shape_name, pos, overwrite)
    if result is False:
        bpy.ops.object.mode_set(mode='OBJECT')
        return

    total_slider_count += 1
    if (total_slider_count % max_rows) == 0:
        # Vertical gap
        pos = Vector((pos.x + ref_length * 2, pos.y, init_pos.z))
    # Horizontal gap
    pos.z += ref_length / 2

    bpy.ops.object.mode_set(mode='POSE')

    # Add the slider property to the control bones
    for bone in rig_obj.pose.bones:
        if bone.name in slider_existing_already:
            bone['faceit_slider'] = 1

    bpy.ops.object.mode_set(mode='OBJECT')
    rig_obj.data.layers = layer_state[:]
    rig_obj.data.layers[2] = True
    rig_obj.data.use_mirror_x = mirror_settings

    bone = rig_obj.pose.bones.get(f'c_{shape_name}_slider_txt')
    if bone:
        txt_obj = generate_custom_curve_text(shape_name)

        bone.custom_shape = txt_obj
    return f'c_{shape_name}_slider'


def get_all_slider_bones(rig, filter='', only_controllers=False):
    '''Return all (pose) bones that belong to sliders (include txt and parent bone)
    @filter [String]: use to filter for specific slider bone.
    '''
    slider_bones = []
    for bone in rig.pose.bones:
        if filter not in bone.name:
            continue
        if '_ref' in bone.name:
            continue
        if only_controllers:
            if bone.get('faceit_slider'):
                slider_bones.append(bone.name)
                continue
            continue

        if 'slider' in bone.name:
            # if filter:
            #     if filter in bone.name:
            #         slider_bones.append(bone.name)
            # else:
            slider_bones.append(bone.name)

    return slider_bones


def cleanup_unused_bone_shapes(name):

    txt_objects = [ob for ob in bpy.data.objects if 'WGT_' + name + '_txt' in ob.name and ob.users == 0]
    for obj in txt_objects:
        bpy.data.objects.remove(obj)

    txt_curves = [ob for ob in bpy.data.curves if 'WGT_' + name + '_txt' in ob.name and ob.users == 0]
    for crv in txt_curves:
        bpy.data.curves.remove(crv)

    txt_meshes = [ob for ob in bpy.data.meshes if 'WGT_' + name + '_txt' in ob.name and ob.users == 0]
    for mesh in txt_meshes:
        bpy.data.meshes.remove(mesh)


def generate_custom_curve_text(name):
    cleanup_unused_bone_shapes(name)

    txt_crv = bpy.data.curves.new(type='FONT', name='WGT_' + name + '_txt')
    txt_crv.body = name
    txt_crv.fill_mode = 'NONE'

    txt_obj_temp = bpy.data.objects.new('text_temp', txt_crv)

    txt_mesh = txt_obj_temp.to_mesh()

    txt_obj = bpy.data.objects.new('WGT_' + name + '_txt', txt_mesh.copy())

    bpy.data.curves.remove(txt_crv)

    return txt_obj


def get_custom_crv_obj(bs_name):
    obj_name = 'WGT_{}_{}'.format(bs_name, type)
    crv_obj = bpy.data.objects.get(obj_name)
    return crv_obj


def generate_spline(crv_data, list_of_vectors, type='POLY'):
    # weight
    w = 1
    if not list_of_vectors:
        return
    polyline = crv_data.splines.new(type)
    polyline.points.add(len(list_of_vectors) - 1)
    for num in range(len(list_of_vectors)):
        polyline.points[num].co = (list_of_vectors[num]) + (w,)

    polyline.order_u = len(polyline.points) - 1
    polyline.use_endpoint_u = True


def generate_custom_curve_box(bs_name, h, w, pos=Vector((0, 0, 0)), list_vectors=None):

    crv = bpy.data.curves.new(bs_name, type='CURVE')
    crv.dimensions = '3D'
    crv.resolution_u = 2

    p0 = (0, 0, 0)
    p1 = (0, w, 0)
    p2 = (0, w, h)
    p3 = (0, 0, h)
    p4 = (0, 0, 0)
    list_vectors = [p0, p1, p2, p3, p4]

    generate_spline(crv, list_vectors, type='POLY')

    # crv.fill_mode = fill_mode
    # new obj from curve
    obj_name = 'csf_{}_{}'.format(bs_name, 'box')
    crv_obj = bpy.data.objects.new(obj_name, crv)
    crv_obj.location = pos
    return crv_obj
