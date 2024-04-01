import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from mathutils import Vector

from ..core.vgroup_utils import get_objects_with_vertex_group

from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..rigging import rig_utils
from ..animate.animate_utils import exit_nla_tweak_mode
from . import control_rig_data as ctrl_data
from . import control_rig_utils as ctrl_utils
from . import custom_slider_utils
from ..core.shape_key_utils import set_slider_max, set_slider_min
from ..core.retarget_list_utils import get_all_set_target_shapes, get_index_of_collection_item, get_target_shape_keys, eval_target_shapes


class FACEIT_OT_GenerateControlRig(bpy.types.Operator):
    '''Generate a control rig armature to control the shape keys. Works with mocap, animation layers, mirroring, etc.'''
    bl_idname = 'faceit.generate_control_rig'
    bl_label = 'Generate Control Rig'
    bl_options = {'UNDO', 'INTERNAL'}

    apply_scale: BoolProperty(
        name='Apply Scale',
        default=False,
        description='This will result in clean transform on the control rig, but it potentially changes the slider ranges on all pose bones to weird decimal numbers making it harder to animate.'
    )
    set_child_of_head: BoolProperty(
        name='Child Of Head Bone',
        default=False,
        description='Set the control rig as child of the headbone (child of constraint).'
    )
    slider_range: EnumProperty(
        name='Slider Ranges',
        items=(
            ('FULL', 'Full Range', 'this will animate positive and negative shape keys'),
            ('POS', 'Only Positive Range',
             'this will animate only positive shape key ranges')
        ),
        default='FULL',
        description='(Can be changed later) - The ranges of inidividual bones can be extended to animate negative shape key values as well.'
    )
    auto_min_range: BoolProperty(
        name='Auto Min Range',
        default=True,
        description='Set the min slider range to -1.0 automatically for all target shape keys.'
    )
    auto_connect: BoolProperty(
        name='Connect Drivers',
        default=True,
        description='Automatically connect drivers with current scene settings. (registered objects, arkit target shapes)'
    )

    ctrl_rig_name: StringProperty(
        name='Rig Name',
        default='FaceitControlRig',
        description='Enter the name of your character or project or leave it at default. Up to you.',
    )
    copy_amplify_values: BoolProperty(
        name='Copy Amplify Values',
        default=True,
        description='Copy the amplify values from the target shapes list.'
    )

    control_rig_exists = False
    head_bone_exists = False

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return len(context.scene.faceit_face_objects) >= 1

    def invoke(self, context, event):
        c_rig_count = len(futils.get_faceit_control_armatures())
        if c_rig_count > 1:
            self.auto_connect = False
        head_obj = context.scene.faceit_head_target_object
        if head_obj is not None and head_obj.type == 'ARMATURE':
            head_bone = head_obj.pose.bones.get(
                context.scene.faceit_head_sub_target)

            self.head_bone_exists = self.set_child_of_head = head_bone is not None

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, 'ctrl_rig_name', icon='MESH_CUBE')
        # row = layout.row()
        # row.prop(self, 'slider_range', expand=True)
        # if self.slider_range == 'FULL':
        #     row = layout.row()
        #     row.prop(self, 'auto_min_range', icon='ARROW_LEFTRIGHT')
        row = layout.row()
        row.prop(self, 'auto_connect', icon='LINKED')
        row = layout.row()
        row.prop(self, 'apply_scale', icon='MESH_CUBE')
        row = layout.row()
        row.prop(self, 'copy_amplify_values', icon='DUPLICATE')
        if self.head_bone_exists:
            row = layout.row()
            row.prop(self, 'set_child_of_head', icon='CONSTRAINT_BONE')

    def execute(self, context):
        scene = context.scene
        landmarks = bpy.data.objects.get('facial_landmarks')
        if not landmarks:
            # Try to reverse engineer landmarks based on faceitrig!
            self.report(
                {'WARNING'},
                'You need to setup the Faceit Landmarks for your character in order to create the Control Rig.')
            return {'CANCELLED'}

        if not eval_target_shapes(scene.faceit_arkit_retarget_shapes):
            self.report({'WARNING'}, 'ARKit Shape list is not initiated.')
            return {'CANCELLED'}
        c_rig_filepath = fdata.get_control_rig_file()
        faceit_collection = futils.get_faceit_collection(
            force_access=True, create=True)

        with bpy.data.libraries.load(c_rig_filepath) as (data_from, data_to):
            data_to.objects = data_from.objects
        new_rig_id = ctrl_data.get_random_rig_id()
        ctrl_rig = None
        # # add only the armature
        obj = None
        for obj in data_to.objects:
            if obj:
                if obj.type == 'ARMATURE' and 'FaceitControlRig' in obj.name:
                    faceit_collection.objects.link(obj)
                    obj['ctrl_rig_id'] = new_rig_id
                    ctrl_rig = obj
                    break
        if ctrl_rig is None:
            self.report({'ERROR'}, 'Could not append the control rig.')
            return {'CANCELLED'}
        context.space_data.overlay.show_relationship_lines = False
        futils.clear_object_selection()
        futils.set_active_object(ctrl_rig.name)
        ctrl_rig.name = self.ctrl_rig_name
        context.scene.faceit_control_armature = ctrl_rig
        # Generate the collections in 4.0
        if bpy.app.version >= (4, 0, 0):
            bpy.ops.faceit.update_bone_collections()
        ctrl_rig.animation_data_create()
        ctrl_rig['ctrl_rig_version'] = ctrl_data.CNTRL_RIG_VERSION
        bpy.ops.faceit.match_control_rig(
            'EXEC_DEFAULT', apply_scale=self.apply_scale)
        ctrl_utils.populate_control_rig_target_objects_from_scene(ctrl_rig)
        ctrl_utils.populate_control_rig_target_shapes_from_scene(
            ctrl_rig,
            populate_amplify_values=True,
            range=self.slider_range
        )
        if self.slider_range == 'POS':
            bpy.ops.faceit.control_rig_set_slider_ranges(
                'EXEC_DEFAULT', new_range='POS', reconnect=False)
        else:
            if self.auto_min_range:
                target_objects = ctrl_utils.get_crig_objects_list(ctrl_rig)
                all_target_shapes = get_all_set_target_shapes(
                    ctrl_rig.faceit_crig_targets)
                for obj in target_objects:
                    for shape_name in all_target_shapes:
                        if obj.data.shape_keys:
                            keys = obj.data.shape_keys.key_blocks
                            sk = keys.get(shape_name)
                            if sk:
                                set_slider_min(sk, value=-1.0)
        if self.auto_connect:
            bpy.ops.faceit.setup_control_drivers('EXEC_DEFAULT')
        if self.set_child_of_head:
            bpy.ops.faceit.constrain_to_body_rig(
                'EXEC_DEFAULT', target_bone='HEAD')
        return {'FINISHED'}


class FACEIT_OT_MatchControlRig(bpy.types.Operator):
    '''matches the bones with reference mesh positions'''
    bl_idname = 'faceit.match_control_rig'
    bl_label = 'Match Control Rig'
    bl_options = {'UNDO', 'INTERNAL'}

    apply_scale: BoolProperty(
        name='Apply Scale',
        default=False,
    )

    @classmethod
    def poll(cls, context):
        if context.active_object == futils.get_faceit_control_armature():
            return True

    def execute(self, context):
        scene = context.scene
        if scene.is_nla_tweakmode:
            exit_nla_tweak_mode(context)

        rig = futils.get_faceit_control_armature()
        # the landmarks mesh holds the bone locations
        landmarks = futils.get_object('facial_landmarks')
        if not landmarks:
            self.report(
                {'WARNING'},
                'You need to setup the Faceit Landmarks for your character in order to fit the Control Rig to your character.')
            return {'CANCELLED'}
        landmarks.hide_viewport = False
        use_asymmetry = scene.faceit_asymmetric
        # save Settings
        rig.data.use_mirror_x = False if use_asymmetry else True

        if bpy.app.version < (4, 0, 0):
            layer_state = rig.data.layers[:]
            # enable all armature layers; needed for armature operators to work properly
            for i in range(len(rig.data.layers)):
                rig.data.layers[i] = True
        else:
            layer_state = [c.is_visible for c in rig.data.collections]
            for c in rig.data.collections:
                c.is_visible = True

        edit_bones = rig.data.edit_bones
        # adapt scale
        bpy.ops.object.mode_set(mode='EDIT')
        # bones that fall too far off the rigs dimensions, hinder the scale adaption
        hide_bones = ['c_slider_ref_parent', 'c_slider_ref', 'c_slider_ref_txt',
                      'c_slider_small_ref_parent', 'c_slider_small_ref', 'c_slider_small_ref_txt',
                      'c_slider2d_ref_parent', 'c_slider2d_ref', 'c_slider2d_ref_txt', 'All_Sliders_Parent',
                      'c_forceMouthClose_slider_txt', 'c_forceMouthClose_slider', 'c_forceMouthClose_slider_parent',
                      'c_SwitchLookAt_slider_txt', 'c_SwitchLookAt_slider', 'c_SwitchLookAt_slider_parent',
                      ]
        # 'c_eye_lookat.R', 'c_eye_lookat.L', 'c_eye_lookat'
        bone_translation = {}
        # temporarilly move bones to center of rig (only Y Axis/ dimensions[1] matters)
        for bone in edit_bones:
            if bone.name not in hide_bones and 'slider2d' not in bone.name:
                continue
            # store bone position
            bone_translation[bone.name] = (bone.head[0], bone.tail[0])
            # when head and tail are equal, the bone is deleted automatically...
            # move to rig center
            bone.head.x = 0
            bone.tail.x = 0.001
        bpy.ops.object.mode_set(mode='OBJECT')
        rig.location = landmarks.location
        old_dim = rig.dimensions.copy().x
        average_dim_landmarks = sum(landmarks.dimensions.copy()) / 3
        new_dim = rig.dimensions.x = average_dim_landmarks
        rig.scale[:] = (rig.scale.copy().x, ) * 3
        scale_factor = new_dim / old_dim
        bpy.ops.object.mode_set(mode='EDIT')
        # restore the original positions
        for bone, pos in bone_translation.items():
            bone = edit_bones.get(bone)
            bone.head.x, bone.tail.x = pos
        # the dictionary containing
        if use_asymmetry:
            match_dict = ctrl_data.match_bones_asymmetry_dict
        else:
            match_dict = ctrl_data.match_bones_symmetry_dict
        # the mesh world matrix
        w_mat = rig.matrix_world
        # the bone space local matrix
        l_mat = rig.matrix_world.inverted()
        for i, bone_dict in match_dict.items():
            # continue when no values are in the bone dictionary
            if all(not v for v in bone_dict.values()):
                continue
            # all vertices in the reference mesh
            if i < 100:
                # the world coordinates of the specified vertex
                target_point = landmarks.matrix_world @ landmarks.data.vertices[i].co
            ############# Special Cases ##############
            # mid brow - between inner brows
            elif i == 101:
                target_point = w_mat @ edit_bones['c_brow_inner.L'].head
                target_point.x = 0
            # innerbones all on ZY (X=0) plane at landmarks pos 22
            elif i == 102:
                vert_id = 22 if not scene.faceit_asymmetric else 25
                target_point = landmarks.matrix_world @ landmarks.data.vertices[vert_id].co
                target_point.x = 0
            # Move eyebones to the correct height.
            elif i == 103:
                if context.scene.faceit_eye_pivot_placement == 'MANUAL':
                    target_point = context.scene.faceit_eye_manual_pivot_point_L
                else:
                    target_point = context.scene.faceit_eye_pivot_point_L
                # empty_locator = bpy.data.objects.get('eye_locator_L')
                # if empty_locator:
                #     target_point = empty_locator.location
                # else:
                #     eye_obj_L = get_objects_with_vertex_group("faceit_left_eyeball")
                #     if eye_obj_L:
                    # vertex_locations = rig_utils.get_evaluated_vertex_group_positions(
                    #     eye_obj_L, "faceit_left_eyeball")
                    # if vertex_locations:
                    #     bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'z')
                    #     target_point = rig_utils.get_median_pos(bounds)
                    # if scene.faceit_asymmetric:
                    #     bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'x')
                    #     target_point.x = futils.get_median_pos(bounds).x
                    # else:
                    #     target_point.x = 0
                    # if not target_point:
                    #     self.report({'WARNING'}, 'could not find left Eyeball, define vertex group in Setup panel first!')
                    #     rig_create_warning = True
                target_bone = edit_bones.get('c_eye_lookat_target.L')
                if target_bone:
                    l_point = l_mat @ target_point
                    vec = l_point - target_bone.head
                    vec.y = 0
                    print(vec)
                    target_bone.translate(vec)
                    # if target_point
            elif i == 104:
                if context.scene.faceit_eye_pivot_placement == 'MANUAL':
                    target_point = context.scene.faceit_eye_manual_pivot_point_R
                else:
                    target_point = context.scene.faceit_eye_pivot_point_R
                # empty_locator = bpy.data.objects.get('eye_locator_R')
                # if empty_locator:
                #     target_point = empty_locator.location
                # else:
                #     eye_obj_R = get_objects_with_vertex_group("faceit_right_eyeball")
                #     if eye_obj_R:
                #         vertex_locations = rig_utils.get_evaluated_vertex_group_positions(
                #             eye_obj_R, "faceit_right_eyeball")
                #         if vertex_locations:
                #             bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'z')
                #             target_point = rig_utils.get_median_pos(bounds)
                #     if not target_point:
                #         self.report(
                #             {'WARNING'},
                #             'could not find right Eyeball, define vertex group in Setup panel first!')
                #         rig_create_warning = True
                # Position the hidden target bone.
                target_bone = edit_bones.get('c_eye_lookat_target.R')
                if target_bone:
                    l_point = l_mat @ target_point
                    b_pos = target_bone.head
                    vec = l_point - b_pos
                    vec.y = 0
                    print(vec)
                    target_bone.translate(vec)
            elif i == 105:
                vert_id = 28 if not scene.faceit_asymmetric else 41
                target_point = landmarks.matrix_world @ landmarks.data.vertices[vert_id].co
                for b in bone_dict['all']:
                    bone = edit_bones[b]
                    l_point = l_mat @ target_point
                    b_pos = bone.head
                    move_height = l_point.z - b_pos.z
                    vec = Vector((0, 0, move_height))
                    bone.translate(vec)
                continue
            ############# Matching ##############
            if not target_point:
                print('target_point missing for bone {}'.format(i))

            # all - translates head and tail by vector to target_point
            for b in bone_dict['all']:
                bone = edit_bones[b]
                l_point = l_mat @ target_point
                vec = l_point - bone.head
                bone.translate(vec)
            # head - translates head to target_point
            for b in bone_dict['head']:
                bone = edit_bones[b]
                bone.head = l_mat @ target_point
            # tail - translates tail to target_point
            for b in bone_dict['tail']:
                bone = edit_bones[b]
                bone.tail = l_mat @ target_point
        # move c_lips_closed to the moutch controller c_mouth_controller (only on YZ)
        bone = edit_bones['c_lips_closed']
        # get median point between upper and lower lips..
        point_0 = w_mat @ edit_bones['c_lips_outer_upper.R'].head
        point_1 = w_mat @ edit_bones['c_lips_outer_lower.R'].head
        target_point = rig_utils.get_median_pos([point_0, point_1])
        l_point = l_mat @ target_point
        vec = l_point - bone.head.copy()
        bone.translate(vec)
        # Move corner lips to the side.
        bone = edit_bones['c_lips_corner_adjust.L']
        b_length = bone.length
        bone.translate(b_length * Vector((1, 0, 0)))
        if use_asymmetry:
            bone = edit_bones['c_lips_corner_adjust.R']
            bone.translate(b_length * Vector((-1, 0, 0)))
        if bpy.app.version < (4, 0, 0):
            rig.data.layers = layer_state[:]
        else:
            for i, c in enumerate(rig.data.collections):
                c.is_visible = layer_state[i]
        if self.apply_scale:
            for b in rig.pose.bones:
                for c in b.constraints:
                    if c.type == 'LIMIT_LOCATION':
                        c.max_x *= scale_factor
                        c.max_y *= scale_factor
                        c.max_z *= scale_factor
                        c.min_x *= scale_factor
                        c.min_y *= scale_factor
                        c.min_z *= scale_factor
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.transform_apply(
                location=True, rotation=False, scale=True)
        # Adapt bone constraints
        bpy.ops.object.mode_set(mode='POSE')
        rig_utils.reset_stretch(rig)
        rig_utils.child_of_set_inverse(rig)
        bpy.ops.object.mode_set(mode='OBJECT')
        shape_dict = {
            'mouthPucker': 'full_range',
            'mouthFunnel': 'full_range',
            'tongueOut': 'full_range',
            'cheekPuff': 'full_range',
        }
        for shape_name, slider_range in shape_dict.items():
            custom_slider_utils.generate_extra_sliders(
                context, shape_name, slider_range, rig_obj=rig)
        # Create the eye lookat driver mechanics.
        ctrl_utils.create_eye_lookat_driver_mechanics(rig)
        for pb in rig.pose.bones:
            if pb.name.endswith('_txt') or pb.name.endswith('_parent'):
                pb.bone.hide_select = True
        landmarks.hide_viewport = True
        return {'FINISHED'}
