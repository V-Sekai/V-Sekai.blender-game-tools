
import bpy
from mathutils import Vector

from . import rig_utils
from . import rig_data
from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..ctrl_rig.control_rig_data import get_random_rig_id


rig_create_warning = False


class FACEIT_OT_GenerateRig(bpy.types.Operator):
    '''Generates the Rig that holds the shapekey animation'''
    bl_idname = 'faceit.generate_rig'
    bl_label = 'Generate Rig'
    bl_options = {'UNDO', 'INTERNAL'}

    use_existing_weights: bpy.props.BoolProperty(
        name='Bind with Existing Weights',
        default=False,
    )

    use_existing_expressions: bpy.props.BoolProperty(
        name='Activate Existing Expressions',
        default=False,
    )
    use_existing_corr_sk: bpy.props.BoolProperty(
        name='Use Existing Corrective Shape Keys',
        default=False,
    )

    @classmethod
    def poll(cls, context):
        return futils.get_main_faceit_object()

    def invoke(self, context, event):
        # if self.all_objects:
        self.weights_restorable = context.scene.faceit_weights_restorable
        self.expressions_restorable = context.scene.faceit_expressions_restorable
        self.corr_sk_restorable = context.scene.faceit_corrective_sk_restorable
        if self.weights_restorable or self.expressions_restorable:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        if self.weights_restorable:
            row.prop(self, 'use_existing_weights')
        if self.expressions_restorable:
            row.prop(self, 'use_existing_expressions')
        row = layout.row()
        if self.corr_sk_restorable and self.use_existing_expressions:
            row.prop(self, 'use_existing_corr_sk')

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
            return{'CANCELLED'}

        bpy.ops.faceit.edit_locator_empties('EXEC_DEFAULT', hide_value=True)

        if context.object:
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except RuntimeError:
                pass
        # landmarks done - reset vertex size
        bpy.context.preferences.themes[0].view_3d.vertex_size = scene.faceit_vertex_size

        rig_filepath = fdata.get_rig_file()

        faceit_collection = futils.get_faceit_collection()

        found_rig = bpy.data.objects.get('FaceitRig')
        if found_rig:
            bpy.data.objects.remove(found_rig)
        # load the objects data in the rig file
        with bpy.data.libraries.load(rig_filepath) as (data_from, data_to):
            data_to.objects = data_from.objects

        # add only the armature
        for obj in data_to.objects:
            if obj.type == 'ARMATURE' and obj.name == 'FaceitRig':
                faceit_collection.objects.link(obj)
                break

        rig = obj
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
                    target_point = rig_utils.get_median_position_from_vert_grp('faceit_left_eyeball')
                    if not target_point:
                        self.report({'WARNING'}, 'could not find left Eyeball, define vertex group in Setup panel first!')
                        rig_create_warning = True

                    # if target_point
            elif i == 111:
                empty_locator = bpy.data.objects.get('eye_locator_R')
                if empty_locator:
                    target_point = empty_locator.location
                else:
                    target_point = rig_utils.get_median_position_from_vert_grp('faceit_right_eyeball')
                    if not target_point:
                        self.report(
                            {'WARNING'},
                            'could not find right Eyeball, define vertex group in Setup panel first!')
                        rig_create_warning = True

            # jaw extra positions
            elif i == 102:
                target_point = w_mat @ edit_bones['jaw.L'].head
                target_point.x = 0

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
                    target_point = rig_utils.get_median_position_from_vert_grp('faceit_upper_teeth')
                    if target_point:
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
                    target_point = rig_utils.get_median_position_from_vert_grp('faceit_lower_teeth')
                    if target_point:
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
            elif i == 109:
                # Get position between jaw rear
                jaw_L = edit_bones.get('jaw.L').head
                jaw_R = edit_bones.get('jaw.R').head
                target_point = w_mat @ futils.get_median_pos([jaw_L, jaw_R])

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
        tip_tongue = rig_utils.get_median_position_from_vert_grp('faceit_tongue')
        if tip_tongue:
            vec = l_mat @ tip_tongue - edit_bones['tongue'].head
            for b in vert_dict[108]['all']:
                bone = edit_bones[b]
                bone.translate(vec)
        else:
            self.report(
                {'WARNING'},
                'could not find Tongue, define vertex group in Setup panel first! Removed Tongue bones from the Rig')
            warning = True
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

        eye_target_L = edit_bones['eye.L']
        eye_target_R = edit_bones['eye.R']

        eyes.head[2] = eye_master_L.head[2]
        eyes.tail = eyes.head + eyes_length

        eye_target_L.head[2] = eye_master_L.head[2]
        eye_target_L.tail = eye_target_L.head + eyes_length

        eye_target_R.head[2] = eye_master_R.head[2]
        eye_target_R.tail = eye_target_R.head + eyes_length

        # orient all jaw bones for jaw_master.tail (chin)
        jaw_master = edit_bones['jaw_master']
        jaw_master.tail = edit_bones['chin'].head
        for bone in vert_dict[102]['all']:
            if bone != jaw_master.name:
                edit_bones[bone].align_orientation(jaw_master)

        bpy.ops.object.mode_set(mode='OBJECT')
        if rig.scale != Vector((1, 1, 1)):
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        rig_utils.reset_stretch(rig_obj=rig)

        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.armature_apply()
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

        return {'FINISHED'}
