
from operator import attrgetter
import bpy
from mathutils import Vector
from bpy.props import BoolProperty, StringProperty


from ..core.modifier_utils import add_faceit_armature_modifier, get_faceit_armature_modifier

from ..core.pose_utils import reset_pose
from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..core import vgroup_utils as vg_utils
from ..ctrl_rig.control_rig_data import get_random_rig_id
from ..landmarks import landmarks_data as lm_data
from . import rig_data, rig_utils

rig_create_warning = False


class FACEIT_OT_GenerateRig(bpy.types.Operator):
    '''Generates the Rig that holds the shapekey animation'''
    bl_idname = 'faceit.generate_rig'
    bl_label = 'Generate Rig'
    bl_options = {'UNDO', 'INTERNAL'}

    use_existing_weights: BoolProperty(
        name='Bind with Existing Weights',
        default=False,
    )

    use_existing_expressions: BoolProperty(
        name='Activate Existing Expressions',
        default=False,
    )
    use_existing_corr_sk: BoolProperty(
        name='Use Existing Corrective Shape Keys',
        default=False,
    )
    weights_restorable = False
    expressions_restorable = False
    corr_sk_restorable = False

    @classmethod
    def poll(cls, context):
        return context.scene.faceit_face_objects

    def invoke(self, context, event):
        if context.scene.faceit_armature_missing:
            self.weights_restorable = True
            self.expressions_restorable = True
            self.use_existing_corr_sk = self.corr_sk_restorable = True
        else:
            self.weights_restorable = context.scene.faceit_weights_restorable
            self.expressions_restorable = context.scene.faceit_expressions_restorable
            self.use_existing_corr_sk = self.corr_sk_restorable = context.scene.faceit_corrective_sk_restorable
        if self.weights_restorable or self.expressions_restorable:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout
        if self.weights_restorable:
            row = layout.row()
            row.prop(self, 'use_existing_weights', icon='GROUP_VERTEX')
        if self.expressions_restorable:
            row = layout.row()
            row.prop(self, 'use_existing_expressions', icon='ACTION')
            row = layout.row()
            row.prop(self, 'use_existing_corr_sk', icon='SCULPTMODE_HLT')
            row.enabled = self.corr_sk_restorable and self.use_existing_expressions

    def execute(self, context):
        scene = context.scene
        global rig_create_warning
        rig_create_warning = False
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False
        if scene.is_nla_tweakmode:
            futils.exit_nla_tweak_mode(context)
        landmarks = futils.get_object('facial_landmarks')
        if not landmarks:
            self.report(
                {'WARNING'},
                'You need to setup the Faceit Landmarks for your character in order to fit the Control Rig to your character.')
            return {'CANCELLED'}
        if context.object:
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except RuntimeError:
                pass
        if not all(x in scene.objects for x in ("eye_locator_L", "eye_locator_R")):
            body_rig = None
            if scene.faceit_use_eye_pivots:
                body_rig = scene.faceit_body_armature
            if body_rig:
                if scene.faceit_anime_ref_eyebone_l in body_rig.data.bones and scene.faceit_anime_ref_eyebone_r in body_rig.data.bones:
                    bpy.ops.faceit.generate_locator_empties(
                        'EXEC_DEFAULT',
                        eye_locators=True,
                        teeth_locators=False,
                        jaw_locator=False,
                    )
        bpy.ops.faceit.unmask_main('EXEC_DEFAULT')
        bpy.ops.faceit.edit_locator_empties('EXEC_DEFAULT', hide_value=True)
        rig_filepath = fdata.get_rig_file()
        faceit_collection = futils.get_faceit_collection()
        rig = futils.get_faceit_armature(force_original=True)
        if rig:
            bpy.data.objects.remove(rig)
        # load the objects data in the rig file
        with bpy.data.libraries.load(rig_filepath) as (data_from, data_to):
            data_to.objects = data_from.objects
        # add only the armature
        for obj in data_to.objects:
            if obj.type == 'ARMATURE' and obj.name == 'FaceitRig':
                faceit_collection.objects.link(obj)
                rig = obj
                break
        rig['faceit_rig_id'] = get_random_rig_id()

        futils.clear_object_selection()
        futils.set_active_object(rig.name)

        # bpy.ops.faceit.match()
        scene.faceit_armature = rig
        if rig.animation_data:
            rig.animation_data.action = None

        edit_bones = rig.data.edit_bones
        # adapt scale
        bpy.ops.object.mode_set(mode='EDIT')
        # bones that fall too far off the rigs dimensions, hinder the scale adaption
        bones = ['eyes', 'eye.L', 'eye.R', 'DEF-face', 'MCH-eyes_parent']
        bone_translation = {}
        # temporarilly move bones to center of rig (only Y Axis/ dimensions[1] matters)
        for bone in bones:
            bone = edit_bones.get(bone)
            # store bone position
            bone_translation[bone.name] = (bone.head[1], bone.tail[1])
            # move to rig center
            bone.head[1] = bone.tail[1] = 0

        bpy.ops.object.mode_set(mode='OBJECT')
        rig.location = landmarks.location
        rig.rotation_euler = landmarks.rotation_euler
        # get average dimensions
        dim_lm = landmarks.dimensions.copy()
        avg_dim_lm = sum(dim_lm) / len(dim_lm)

        dim_rig = rig.dimensions.copy()
        avg_dim_rig = sum(dim_rig) / len(dim_rig)

        scale_factor = avg_dim_lm / avg_dim_rig  # landmarks.dimensions[0] / rig.dimensions[0]
        rig.dimensions = dim_rig * scale_factor  # rig.dimensions.copy() * scale_factor
        bpy.ops.object.mode_set(mode='EDIT')

        # restore the original positions
        for bone, pos in bone_translation.items():
            bone = edit_bones.get(bone)
            bone.head[1], bone.tail[1] = pos

        # the dictionary containing
        if scene.faceit_asymmetric:
            vert_dict = rig_data.bone_dict_asymmetric
        else:
            vert_dict = rig_data.bone_dict_symmetric

        # the mesh world matrix
        w_mat = rig.matrix_world
        # the bone space local matrix
        l_mat = rig.matrix_world.inverted()

        # save Settings
        layer_state = rig.data.layers[:]
        # enable all armature layers; needed for armature operators to work properly
        for i in range(len(rig.data.layers)):
            rig.data.layers[i] = True

        for i, bone_dict in vert_dict.items():
            target_point = None

            if i in (101, 111):
                rig.data.use_mirror_x = False
            else:
                rig.data.use_mirror_x = not scene.faceit_asymmetric

            # all vertices in the reference mesh
            if i < 100:
                # the world coordinates of the specified vertex
                target_point = landmarks.matrix_world @ landmarks.data.vertices[i].co

            ############# Special Cases ##############

            # eyes extra positions
            elif i == 101:
                empty_locator = bpy.data.objects.get('eye_locator_L')
                if empty_locator:
                    target_point = empty_locator.location
                else:
                    eye_obj_L = vg_utils.get_objects_with_vertex_group("faceit_left_eyeball")
                    if eye_obj_L:
                        vertex_locations = rig_utils.get_evaluated_vertex_group_positions(
                            eye_obj_L, "faceit_left_eyeball")
                        if vertex_locations:
                            bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'z')
                            target_point = futils.get_median_pos(bounds)
                            # if scene.faceit_asymmetric:
                            #     bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'x')
                            #     target_point.x = futils.get_median_pos(bounds).x
                            # else:
                            #     target_point.x = 0
                    if not target_point:
                        self.report({'WARNING'}, 'could not find left Eyeball, define vertex group in Setup panel first!')
                        rig_create_warning = True

                    # if target_point
            elif i == 111:
                empty_locator = bpy.data.objects.get('eye_locator_R')
                if empty_locator:
                    target_point = empty_locator.location
                else:
                    eye_obj_R = vg_utils.get_objects_with_vertex_group("faceit_right_eyeball")
                    if eye_obj_R:
                        vertex_locations = rig_utils.get_evaluated_vertex_group_positions(
                            eye_obj_R, "faceit_right_eyeball")
                        if vertex_locations:
                            bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'z')
                            target_point = futils.get_median_pos(bounds)
                    if not target_point:
                        self.report(
                            {'WARNING'},
                            'could not find right Eyeball, define vertex group in Setup panel first!')
                        rig_create_warning = True

            # jaw extra positions
            elif i == 102:
                empty_locator = bpy.data.objects.get('jaw_locator')
                if empty_locator:
                    target_point = empty_locator.location
                else:
                    jaw_L = edit_bones.get('jaw.L').head
                    jaw_R = edit_bones.get('jaw.R').head
                    target_point = w_mat @ futils.get_median_pos([jaw_L, jaw_R])
                    # target_point = w_mat @ edit_bones['jaw.L'].head
                    # target_point.x = 0
            elif i == 109:
                jaw_L = edit_bones.get('jaw.L').head
                jaw_R = edit_bones.get('jaw.R').head
                target_point = w_mat @ futils.get_median_pos([jaw_L, jaw_R])

            # nose extra positions
            elif i == 103:
                b_tip = edit_bones['nose.002'].head
                b_top = edit_bones['nose'].head
                vec = b_tip - b_top
                target_point = w_mat @ (b_top + vec * 0.7)

            elif i == 104:
                b_1 = edit_bones['nose.004'].head
                b_2 = edit_bones['lip.T'].head
                target_point = w_mat @ futils.get_median_pos([b_1, b_2])
            elif i == 105:
                b_1 = edit_bones['nose.002'].head
                b_2 = edit_bones['nose.004'].head
                target_point = w_mat @ futils.get_median_pos([b_1, b_2])

            # teeth extra positions
            elif i == 106:
                empty_locator = bpy.data.objects.get('teeth_upper_locator')
                if empty_locator:
                    target_point = empty_locator.location
                else:
                    upper_teeth_obj = vg_utils.get_objects_with_vertex_group("faceit_upper_teeth")
                    if upper_teeth_obj:
                        vertex_locations = rig_utils.get_evaluated_vertex_group_positions(
                            upper_teeth_obj, "faceit_upper_teeth")
                        if vertex_locations:
                            # target_point = max(vertex_locations, key=attrgetter('y'))
                            bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'y')
                            target_point = futils.get_median_pos(bounds)
                            if scene.faceit_asymmetric:
                                bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'x')
                                target_point.x = futils.get_median_pos(bounds).x
                            else:
                                target_point.x = 0
                if not target_point:
                    self.report(
                        {'WARNING'},
                        'could not find Upper Teeth, define vertex group in Setup panel first! Removed bones from the rig')
                    rig_create_warning = True
                    for b in vert_dict[106]['all']:
                        bone = edit_bones[b]
                        edit_bones.remove(bone)
                    continue
            elif i == 107:
                empty_locator = bpy.data.objects.get('teeth_lower_locator')
                if empty_locator:
                    target_point = empty_locator.location
                else:
                    lower_teeth_obj = vg_utils.get_objects_with_vertex_group("faceit_lower_teeth")
                    if lower_teeth_obj:
                        vertex_locations = rig_utils.get_evaluated_vertex_group_positions(
                            lower_teeth_obj, "faceit_lower_teeth")
                        if vertex_locations:
                            bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'y')
                            target_point = futils.get_median_pos(bounds)
                            if scene.faceit_asymmetric:
                                bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'x')
                                target_point.x = futils.get_median_pos(bounds).x
                            else:
                                target_point.x = 0
                if not target_point:
                    self.report(
                        {'WARNING'},
                        'could not find Lower Teeth, define vertex group in Setup panel first! Removed bones from the rig')
                    rig_create_warning = True
                    for b in vert_dict[107]['all']:
                        bone = edit_bones[b]
                        edit_bones.remove(bone)
                    continue
            elif i == 108:
                continue
            ############# Matching ##############
            if target_point:
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
        # apply same offset to all tongue bones
        tongue_obj = vg_utils.get_objects_with_vertex_group("faceit_tongue")
        if tongue_obj:
            tongue_bones = [edit_bones[b] for b in vert_dict[108]["all"]]
            vertex_locations = rig_utils.get_evaluated_vertex_group_positions(tongue_obj, "faceit_tongue")
            if vertex_locations:
                target_point = min(vertex_locations, key=attrgetter('y'))
                if scene.faceit_asymmetric:
                    bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'x')
                    target_point.x = futils.get_median_pos(bounds).x
                else:
                    target_point.x = 0
                vec = l_mat @ target_point - edit_bones["tongue"].head
                for b in tongue_bones:
                    b.translate(vec)
                # squash/stretch bones into tongue geometry range (bounds)
                bone_locations = [b.head for b in tongue_bones]
                b_max_y, b_min_y = rig_utils.get_bounds_from_locations(bone_locations, 'y')
                v_max_y, v_min_y = (l_mat @ v for v in rig_utils.get_bounds_from_locations(vertex_locations, 'y'))
                old_range = b_max_y.y - b_min_y.y
                new_range = v_max_y.y - v_min_y.y
                new_range *= .9
                for b in tongue_bones:
                    old_value = b.head.y
                    new_value = (((old_value - b_min_y.y) * new_range) / old_range) + v_min_y.y
                    add_y = new_value - old_value
                    b.head.y += add_y
                    b.tail.y += add_y
                # b_max_z, b_min_z = rig_utils.get_bounds_from_locations(bone_locations, 'z')
                # v_max_z, v_min_z = (l_mat @ v for v in rig_utils.get_bounds_from_locations(vertex_locations, 'z'))
                # old_range = b_max_z.z - b_min_z.z
                # new_range = v_max_z.z - v_min_z.z
                # for b in tongue_bones:
                #     # print(vert_dict[112].values())
                #     # if any(b.name in bl for bl in vert_dict[112].values()):
                #     if b.name in ['tongue', 'DEF-tongue']:
                #         continue
                #     old_value = b.head.z
                #     new_value = (((old_value - b_min_z.z) * new_range) / old_range) + v_min_z.z
                #     add_z = new_value - old_value
                #     b.head.z += add_z
                #     if b.name == 'tongue_master':
                #         continue
                #     b.tail.z += add_z
                # move tails to repective bones.
                for i in range(112, 116):
                    b_dict = vert_dict[i]
                    pos = edit_bones[b_dict['all'][0]].head
                    for b in b_dict['tail']:
                        b = edit_bones[b]
                        b.tail = pos
        else:
            self.report(
                {'WARNING'},
                'could not find Tongue, define vertex group in Setup panel first! Removed Tongue bones from the Rig')
            rig_create_warning = True
            for b in vert_dict[108]['all']:
                bone = edit_bones[b]
                edit_bones.remove(bone)

        # translate the extra eye bone to the proper location
        eyes = edit_bones['eyes']
        eyes_length = Vector((0, 0, eyes.length))
        eye_master_L = edit_bones['master_eye.L']
        eye_master_R = edit_bones['master_eye.R']
        vec = eye_master_L.tail - edit_bones['MCH-eye.L.001'].head
        edit_bones['MCH-eye.L.001'].translate(vec)
        vec = eye_master_R.tail - edit_bones['MCH-eye.R.001'].head
        edit_bones['MCH-eye.R.001'].translate(vec)
        # position eye target bones
        eye_target_L = edit_bones['eye.L']
        eye_target_R = edit_bones['eye.R']
        eyes.head[2] = eye_master_L.head[2]
        eyes.tail = eyes.head + eyes_length
        eye_target_L.head[2] = eye_master_L.head[2]
        eye_target_L.tail = eye_target_L.head + eyes_length
        eye_target_R.head[2] = eye_master_R.head[2]
        eye_target_R.tail = eye_target_R.head + eyes_length
        # Orient all jaw bones to chin / Y Axis.
        bpy.ops.armature.select_all(action='DESELECT')
        jaw_master = edit_bones['jaw_master']
        chin_bone = edit_bones['chin']
        jaw_master.tail = chin_bone.head
        for bone in vert_dict[102]['all']:
            edit_bone = edit_bones[bone]
            edit_bone.head.x = edit_bones['chin'].head.x
            if edit_bone is not jaw_master:
                edit_bone.align_orientation(jaw_master)
            edit_bone.select = True
        bpy.ops.armature.calculate_roll(type='POS_X')
        bpy.ops.object.mode_set(mode='OBJECT')
        if rig.scale != Vector((1, 1, 1)):
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

        rig_utils.reset_stretch(rig_obj=rig)

        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.armature_apply()
        rig_utils.set_lid_follow_constraints(rig, "L")
        rig_utils.set_lid_follow_constraints(rig, "R")
        bpy.ops.object.mode_set(mode='OBJECT')

        # restore the layer visibillity to its original state
        rig.data.layers = layer_state[:]

        landmarks.hide_viewport = True

        if self.use_existing_weights:
            bpy.ops.faceit.pair_armature()
            self.report({'INFO'}, 'Restored Existing Weights. You can regenerate weights by using the Bind operator')

        if self.use_existing_expressions:
            # sh_action = bpy.data.actions.get('faceit_shape_action')
            ow_action = bpy.data.actions.get('overwrite_shape_action')
            expression_list = scene.faceit_expression_list

            if not expression_list:
                self.report({'WARNING'}, 'The Expression List could not be found.')

            if ow_action:
                rig.animation_data_create()
                rig.animation_data.action = ow_action
            else:
                self.report({'WARNING'}, 'Could not find expressions action {}'.format('overwrite_shape_action'))

            if self.corr_sk_restorable:
                faceit_objects = futils.get_faceit_objects_list()
                corrective_sk_action = bpy.data.actions.get('faceit_corrective_shape_keys', None)
                for obj in faceit_objects:
                    if sk_utils.has_shape_keys(obj):
                        has_corrective_shape_keys = False
                        for sk in obj.data.shape_keys.key_blocks:
                            if sk.name.startswith('faceit_cc_'):
                                if self.use_existing_corr_sk:
                                    has_corrective_shape_keys = True
                                    sk.mute = False
                                else:
                                    obj.shape_key_remove(sk)
                        if len(obj.data.shape_keys.key_blocks) == 1:
                            obj.shape_key_clear()
                        else:
                            if has_corrective_shape_keys and corrective_sk_action:
                                if not obj.data.shape_keys.animation_data:
                                    obj.data.shape_keys.animation_data_create()
                                obj.data.shape_keys.animation_data.action = corrective_sk_action
                scene.faceit_corrective_sk_restorable = False
        else:
            scene.faceit_expression_list.clear()
            # START ####################### VERSION 1 ONLY #######################
            if scene.faceit_version == 1:
                bpy.ops.faceit.append_action_to_faceit_rig(
                    'EXEC_DEFAULT', expressions_type='ARKIT', load_method='OVERWRITE')
            # END ######################### VERSION 1 ONLY #######################

        if rig_create_warning:
            self.report({'WARNING'}, 'Rig generated with warnings. Please see Console Output for details.')
        else:
            self.report({'INFO'}, 'Rig generated successfully!')

        scene.tool_settings.use_keyframe_insert_auto = auto_key
        scene.tool_settings.use_snap = False

        return {'FINISHED'}


class FACEIT_OT_UnhideRig(bpy.types.Operator):
    '''Unhide the Faceit Rig.'''
    bl_idname = 'faceit.unhide_rig'
    bl_label = 'Unhide Rig'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            rig = futils.get_faceit_armature()
            if rig:
                return futils.get_hide_obj(rig)

    def execute(self, context):
        rig = futils.get_faceit_armature()
        futils.get_faceit_collection(force_access=True)
        futils.set_hide_obj(rig, False)
        return {'FINISHED'}


class FACEIT_OT_ReconnectRig(bpy.types.Operator):
    '''Reconnect the Faceit Rig without removing the shape keys.'''
    bl_idname = 'faceit.reconnect_rig'
    bl_label = 'Reconnect Rig'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return futils.get_faceit_objects_list() and futils.get_faceit_armature()

    def execute(self, context):

        scene = context.scene
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False

        rig = futils.get_faceit_armature()
        futils.get_faceit_collection(force_access=True)

        # restore scene
        if rig:
            futils.set_hide_obj(rig, False)
        else:
            self.report({'WARNING'}, 'The Faceit Armature can\'t be found.')

        faceit_objects = futils.get_faceit_objects_list()

        reset_pose(rig)

        _reconnected_rig = False
        for obj in faceit_objects:

            mod = get_faceit_armature_modifier(obj, force_original=False)
            if mod:
                _reconnected_rig = True
                mod.show_viewport = True
            else:
                deform_groups = vg_utils.get_deform_bones_from_armature(rig)
                all_registered_objects_vgroups = vg_utils.get_vertex_groups_from_objects()
                # Check if the required vertex groups exist.
                if len([True for grp in all_registered_objects_vgroups if grp in deform_groups]) > 10:
                    _reconnected_rig = True
                    add_faceit_armature_modifier(obj, rig, force_original=False)
                else:
                    self.report(
                        {'WARNING'},
                        f'The required bind weights are missing on obj {obj.name}. Did you bind properly?')

            corrective_mod = obj.modifiers.get('CorrectiveSmooth')
            if corrective_mod:
                corrective_mod.show_viewport = True
                corrective_mod.show_render = True
        if not _reconnected_rig:
            self.report({'WARNING'}, "Reconnecting the rig failed. Please check the console for details.")
        futils.clear_object_selection()
        futils.set_active_object(rig.name)
        scene.tool_settings.use_keyframe_insert_auto = auto_key

        return {'FINISHED'}


class FACEIT_OT_EditLocatorEmpties(bpy.types.Operator):
    '''	Edit Locator Empties visibility or remove'''
    bl_idname = 'faceit.edit_locator_empties'
    bl_label = 'Show Locator Empties'
    bl_options = {'UNDO', 'INTERNAL'}

    remove: BoolProperty(
        name='Remove All',
        default=False,
        options={'SKIP_SAVE'}
    )

    hide_value: BoolProperty(
        name='Hide/Show',
        default=False,
        options={'SKIP_SAVE'}
    )

    @classmethod
    def poll(cls, context):
        return True
        # return any([n in bpy.data.objects for n in lm_utils.locators])

    def execute(self, context):

        for n in lm_data.LOCATOR_NAMES:
            loc_obj = futils.get_object(n)
            if loc_obj:
                if self.remove:
                    bpy.data.objects.remove(loc_obj, do_unlink=True)
                    continue
                futils.set_hidden_state_object(loc_obj, self.hide_value, self.hide_value)
                # loc_obj.hide_viewport = self.hide_value

        if self.remove:
            context.scene.show_locator_empties = True
        else:
            context.scene.show_locator_empties = not self.hide_value

        return {'FINISHED'}


class FACEIT_OT_GenerateLocatorEmpties(bpy.types.Operator):
    '''	Create empties at relevant locations to be used as new target for the bones in creating the rig '''
    bl_idname = 'faceit.generate_locator_empties'
    bl_label = 'Create Locator Empties'
    bl_options = {'UNDO', 'INTERNAL'}

    eye_locators: BoolProperty(
        name="Eye Locators",
        default=True,
        description="Create helper empties at eyes locations"
    )
    teeth_locators: BoolProperty(
        name="Teeth Locators",
        default=True,
        description="Create helper empties at upper and lower teeth locations"
    )
    jaw_locator: BoolProperty(
        name="Jaw Locator",
        default=True,
        description="Create helper empties at jaw location"
    )

    guess_location: bpy.props.BoolProperty(
        name='Guess Location',
        description='Guess the location of the empties based on the assigned vertex groups or landmark locations',
        default=True,
        options={'SKIP_SAVE'}
    )

    def invoke(self, context, event):
        if context.scene.faceit_asymmetric:
            self.jaw_locator = False
        return context.window_manager.invoke_props_dialog(self)

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw(self, context):
        layout = self.layout
        col = layout.grid_flow(row_major=True, columns=1, even_columns=True, even_rows=True, align=True)
        col.prop(self, "eye_locators", icon='BLANK1')
        col.prop(self, "teeth_locators", icon='BLANK1')
        if not context.scene.faceit_asymmetric:
            col.prop(self, "jaw_locator", icon='BLANK1')

    def execute(self, context):
        scene = context.scene
        lm_obj = futils.get_object('facial_landmarks')
        faceit_collection = futils.get_faceit_collection(force_access=True, create=True)
        if not faceit_collection:
            self.report({'ERROR'}, "Faceit Collection not found.")
            return {'CANCELLED'}
        if lm_obj:
            _lm_size = lm_obj.dimensions.x / 8
        else:
            _lm_size = 0.01
        faceit_objects = futils.get_faceit_objects_list()
        # Remove Empties that exist already
        bpy.ops.faceit.edit_locator_empties('EXEC_DEFAULT', remove=True)

        futils.clear_object_selection()

        def create_empty(name, position):
            obj = bpy.data.objects.new(name, None)
            obj.empty_display_type = 'PLAIN_AXES'
            faceit_collection.objects.link(obj)
            obj.location = position
            obj.empty_display_size = _lm_size
            obj.show_name = True
            obj.select_set(state=True)
            obj.show_in_front = True
            obj.lock_rotation[0] = True
            obj.lock_rotation[1] = True
            obj.lock_rotation[2] = True
            return obj

        body_rig = None
        if scene.faceit_use_eye_pivots:
            body_rig = scene.faceit_body_armature

        if self.eye_locators:
            # ----------------- LEFT EYE LOCATOR --------------------
            _generated = False
            if body_rig:
                eye_L = body_rig.data.bones.get(scene.faceit_anime_ref_eyebone_l)
                if eye_L:
                    pos = eye_L.matrix_local.to_4x4().to_translation()

                create_empty('eye_locator_L', pos)
                _generated = True
            if not _generated:
                vgroup_name = 'faceit_left_eyeball'
                obj = vg_utils.get_objects_with_vertex_group(vgroup_name, objects=faceit_objects)
                if obj:
                    # Get vertices
                    vs = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
                    global_vs = [obj.matrix_world @ v.co for v in vs]

                    bounds = rig_utils.get_bounds_from_locations(global_vs, 'z')
                    pos = futils.get_median_pos(bounds)
                    create_empty('eye_locator_L', pos)

                else:
                    self.report({'WARNING'}, 'Can\'t find {} vertex group. Please register it first.'.format(vgroup_name))

            # ----------------- RIGHT EYE LOCATOR --------------------

            pos = None
            _generated = False
            if body_rig:
                eye_R = body_rig.data.bones.get(scene.faceit_anime_ref_eyebone_r)
                if eye_R:
                    pos = eye_R.matrix_local.to_4x4().to_translation()
                create_empty('eye_locator_R', pos)
                _generated = True
            if not _generated:
                vgroup_name = 'faceit_right_eyeball'
                obj = vg_utils.get_objects_with_vertex_group(vgroup_name, objects=faceit_objects)
                if obj:
                    # Get vertices
                    vs = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
                    global_vs = [obj.matrix_world @ v.co for v in vs]

                    bounds = rig_utils.get_bounds_from_locations(global_vs, 'z')
                    pos = futils.get_median_pos(bounds)
                    create_empty('eye_locator_R', pos)
                else:
                    self.report({'WARNING'}, 'Can\'t find {} vertex group. Please register it first.'.format(vgroup_name))

        if self.teeth_locators:
            # ----------------- TEETH UPPER LOCATOR --------------------

            vgroup_name = 'faceit_upper_teeth'
            obj = vg_utils.get_objects_with_vertex_group(vgroup_name, objects=faceit_objects)
            if obj:
                # Get vertices
                vs = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
                global_vs = [obj.matrix_world @ v.co for v in vs]

                bounds = rig_utils.get_bounds_from_locations(global_vs, 'z')
                bounds.append(min(global_vs, key=attrgetter('y')))

                pos = futils.get_median_pos(bounds)
                pos.x = 0

                create_empty('teeth_upper_locator', pos)
            else:
                self.report({'WARNING'}, 'Can\'t find {} vertex group. Please register it first.'.format(vgroup_name))

            # ----------------- TEETH UPPER LOCATOR --------------------

            vgroup_name = 'faceit_lower_teeth'
            obj = vg_utils.get_objects_with_vertex_group(vgroup_name, objects=faceit_objects)
            if obj:
                # Get vertices
                vs = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
                global_vs = [obj.matrix_world @ v.co for v in vs]

                bounds = rig_utils.get_bounds_from_locations(global_vs, 'z')
                bounds.append(min(global_vs, key=attrgetter('y')))

                pos = futils.get_median_pos(bounds)
                pos.x = 0

                create_empty('teeth_lower_locator', pos)
            else:
                self.report({'WARNING'}, 'Can\'t find {} vertex group. Please register it first.'.format(vgroup_name))

        if self.jaw_locator:
            # if context.scene.faceit_asymmetric:
            #     l_id = 25
            #     # r_id = 24
            # else:
            if not lm_obj:
                self.report({'WARNING'}, 'Can\'t find facial landmarks object. Could not create Jaw Locator.')
                # return {'CANCELLED'}
            id = 22
            pos = lm_obj.matrix_world @ lm_obj.data.vertices[id].co
            pos.x = 0
            empty = create_empty('jaw_locator', pos)
            empty.lock_location[0] = True

            # obj = bpy.data.objects.new("jaw_locator", None)
            # obj.empty_display_type = 'PLAIN_AXES'
            # faceit_collection.objects.link(obj)
            # obj.location = target_point
            # # size = (bounds[0].z - bounds[1].z) / 2
            # obj.empty_display_size = _lm_size
            # obj.show_name = True
            # obj.select_set(state=True)
            # obj.show_in_front = True
        # ----------------- TONGUE LOCATORS --------------------
        # | - 3 Tongue bones distributed between tip and rear
        # ------------------------------------------------------

        # # apply same offset to all tongue bones
        # tip_tongue = rig_utils.get_median_position_from_vert_grp('faceit_tongue')
        # if tip_tongue:
        #     vec = l_mat @ tip_tongue - edit_bones['tongue'].head
        #     for b in vert_dict[108]['all']:
        #         bone = edit_bones[b]
        #         bone.translate(vec)
        # else:
        #     self.report({'WARNING'}, 'could not find tongue,   define teeth group first!')
        #     for b in vert_dict[108]['all']:
        #         bone = edit_bones[b]
        #         edit_bones.remove(bone)

        # tongue_0 = futils.get_object('tongue_0_locator')
        # if tongue_0:
        #     bpy.data.objects.remove(tongue_0)
        # tongue_1 = futils.get_object('tongue_1_locator')
        # if tongue_1:
        #     bpy.data.objects.remove(tongue_1)
        # tongue_2 = futils.get_object('tongue_2_locator')
        # if tongue_2:
        #     bpy.data.objects.remove(tongue_2)

        # vgroup_name = 'faceit_tongue'
        # obj = vg_utils.get_objects_with_vertex_group(vgroup_name, objects=faceit_objects)
        # if obj:

        #     # Get vertices
        #     vs = vg_utils.get_verts_in_vgroup(obj, vgroup_name)
        #     global_vs = [obj.matrix_world @ v.co for v in vs]

        #     position = min(global_vs, key=attrgetter('y'))
        #     # bounds = rig_utils.get_bounds_from_locations(global_vs, 'z')
        #     # bounds.extend(rig_utils.get_bounds_from_locations(global_vs, 'y'))
        #     for i in range(3):

        #     eye_R_empty = bpy.data.objects.new('teeth_lower_locator', None)
        #     eye_R_empty.empty_display_type = 'PLAIN_AXES'
        #     faceit_collection.objects.link(eye_R_empty)
        #     eye_R_empty.location = position

        #     up_dim = (bounds[0].z - bounds[1].z)/2
        #     eye_R_empty.empty_display_size = up_dim  # (up_dim,)*3

        return {'FINISHED'}
