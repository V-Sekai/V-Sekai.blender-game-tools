
from math import sqrt
from operator import attrgetter
import bpy
from bpy.types import Context
import numpy as np
from mathutils import Color, Matrix, Vector
from bpy.props import BoolProperty, StringProperty, EnumProperty, IntProperty

from ..core.modifier_utils import add_faceit_armature_modifier, get_faceit_armature_modifier
from ..animate.animate_utils import exit_nla_tweak_mode
from ..core.pose_utils import reset_pose
from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..core import vgroup_utils as vg_utils
from ..ctrl_rig.control_rig_data import get_random_rig_id
from .pivot_manager import PivotManager
from . import rig_data, rig_utils

rig_create_warning = False
pivot_manual_mode = False


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
        PivotManager.save_pivots(context)
        bpy.ops.ed.undo_push()
        rig_create_warning = False
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False
        if scene.is_nla_tweakmode:
            exit_nla_tweak_mode(context)
        landmarks = futils.get_object('facial_landmarks')
        if not landmarks:
            self.report(
                {'WARNING'},
                'You need to setup the Faceit Landmarks for your character in order to fit the Control Rig to your character.')
            return {'CANCELLED'}
        # PivotManager.remove_handle()
        if context.object:
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except RuntimeError:
                pass
        bpy.ops.faceit.unmask_main('EXEC_DEFAULT')
        # set_locator_hidden_state(hide=True)
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

        # Update the bone collections to 4.0
        if bpy.app.version >= (4, 0, 0):
            face_coll = rig.data.collections["Layer 1"]
            face_coll.name = 'Face'
            rig.data.collections.get("Layer 2").name = 'Face (Primary)'
            rig.data.collections.get("Layer 3").name = 'Face (Secondary)'
            rig.data.collections["Layer 30"].name = 'DEF'
            rig.data.collections["Layer 31"].name = 'MCH'
            eye_master_L = rig.data.bones['master_eye.L']
            eye_master_R = rig.data.bones['master_eye.R']
            face_coll.assign(eye_master_L)
            face_coll.assign(eye_master_R)
            # remove old bone groups.
            for coll in rig.data.collections[:]:
                if coll.name in ['FK', 'IK', 'Special', 'Layer 32']:
                    rig.data.collections.remove(coll)

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
        if bpy.app.version < (4, 0, 0):
            layer_state = rig.data.layers[:]
            # enable all armature layers; needed for armature operators to work properly
            for i in range(len(rig.data.layers)):
                rig.data.layers[i] = True
        else:
            layer_state = [c.is_visible for c in rig.data.collections]
            for c in rig.data.collections:
                c.is_visible = True

        jaw_pivot_object = context.scene.objects.get('Jaw Pivot')
        if jaw_pivot_object:
            context.scene.faceit_use_jaw_pivot = True
            context.scene.faceit_jaw_pivot = jaw_pivot_object.location
        else:
            context.scene.faceit_use_jaw_pivot = False
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
                if context.scene.faceit_eye_pivot_placement == 'MANUAL':
                    target_point = context.scene.faceit_eye_manual_pivot_point_L
                else:
                    target_point = context.scene.faceit_eye_pivot_point_L
            elif i == 111:
                if context.scene.faceit_eye_pivot_placement == 'MANUAL':
                    target_point = context.scene.faceit_eye_manual_pivot_point_R
                else:
                    target_point = context.scene.faceit_eye_pivot_point_R
            # jaw extra positions
            elif i == 102:
                empty_locator = jaw_pivot_object
                if empty_locator:
                    target_point = context.scene.faceit_jaw_pivot
                else:
                    jaw_L = edit_bones.get('jaw.L').head
                    jaw_R = edit_bones.get('jaw.R').head
                    target_point = w_mat @ rig_utils.get_median_pos([jaw_L, jaw_R])
                    # target_point = w_mat @ edit_bones['jaw.L'].head
                    # target_point.x = 0
            elif i == 109:
                jaw_L = edit_bones.get('jaw.L').head
                jaw_R = edit_bones.get('jaw.R').head
                target_point = w_mat @ rig_utils.get_median_pos([jaw_L, jaw_R])

            # nose extra positions
            elif i == 103:
                b_tip = edit_bones['nose.002'].head
                b_top = edit_bones['nose'].head
                vec = b_tip - b_top
                target_point = w_mat @ (b_top + vec * 0.7)

            elif i == 104:
                b_1 = edit_bones['nose.004'].head
                b_2 = edit_bones['lip.T'].head
                target_point = w_mat @ rig_utils.get_median_pos([b_1, b_2])
            elif i == 105:
                b_1 = edit_bones['nose.002'].head
                b_2 = edit_bones['nose.004'].head
                target_point = w_mat @ rig_utils.get_median_pos([b_1, b_2])

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
                            target_point = rig_utils.get_median_pos(bounds)
                            if scene.faceit_asymmetric:
                                bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'x')
                                target_point.x = rig_utils.get_median_pos(bounds).x
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
                            target_point = rig_utils.get_median_pos(bounds)
                            if scene.faceit_asymmetric:
                                bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'x')
                                target_point.x = rig_utils.get_median_pos(bounds).x
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
                    target_point.x = rig_utils.get_median_pos(bounds).x
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
        if bpy.app.version < (4, 0, 0):
            rig.data.layers = layer_state[:]
        else:
            for i, c in enumerate(rig.data.collections):
                c.is_visible = layer_state[i]

        landmarks.hide_viewport = True
        if jaw_pivot_object:
            bpy.data.objects.remove(jaw_pivot_object)
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


class FACEIT_OT_GenerateNewRigifyRig(bpy.types.Operator):
    '''Generate the new rigify rig based on the faceit landmarks.'''
    bl_idname = 'faceit.generate_new_rigify_rig'
    bl_label = 'Generate New Rigify Rig'
    bl_options = {'UNDO', 'INTERNAL'}

    rigify_type: EnumProperty(
        name='Rigify Type',
        items=[
            ('FACE', 'Face Rig', 'Rigify Face Rig < Blender 3.0'),
            ('FACE_NEW', 'Face Rig New', 'Rigify Face Rig > Blender 3.0'),
        ],
        default='FACE_NEW',
    )
    add_temple_helper_bones: BoolProperty(
        name="Add Temple Helper Bones",
        description="Add Temple Def bones for better skin weights.",
        default=True
    )
    set_sharp_mouth_corners: BoolProperty(
        name="Sharp Corners (Old Behavior)",
        description="Set the mouth corners to sharp.",
        default=False,
    )
    mouth_subdivisions: IntProperty(
        name="Mouth Subdivisions",
        description="The number of subdivisions for the mouth.",
        default=0,
        min=0,
        max=2,
    )
    edit_meta_rig: BoolProperty(
        name="Edit Meta Rig",
        description="Keep the meta rig after generating the rigify rig.",
        default=False,
    )
    color_style: EnumProperty(
        name="Colours",
        items=(
            ('FACEIT', 'Faceit', 'The default Faceit bone colours. Can be changed in armature/bone settings.'),
            ('RIGIFY', 'Rigify', 'The default Rigify bone colours. Can be changed in armature/bone settings.')
        ),
        default='FACEIT'
    )

    @ classmethod
    def poll(cls, context):
        return context.scene.faceit_face_objects

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        # layout.prop(self, "rigify_type", expand=True)

        row = layout.row()
        row.label(text="Skinning")
        row = layout.row()
        row.prop(self, "add_temple_helper_bones")
        row = layout.row()
        row.label(text="Mouth Settings")
        row = layout.row()
        row.prop(self, "set_sharp_mouth_corners")
        row = layout.row()
        row.prop(self, "mouth_subdivisions")
        row = layout.row()
        row.label(text="Meta Rig")
        layout.prop(self, "edit_meta_rig", toggle=True)
        # row = layout.row()
        # row.label(text="Colours")
        row = layout.row()
        row.prop(self, "color_style")

    def execute(self, context):
        scene = context.scene
        global rig_create_warning
        PivotManager.save_pivots(context)
        landmarks = futils.get_object('facial_landmarks')
        if not landmarks:
            self.report(
                {'WARNING'},
                'You need to setup the Faceit Landmarks for your character in order to fit the Control Rig to your character.')
            return {'CANCELLED'}
        if not bpy.context.preferences.addons.get('rigify'):
            self.report({'WARNING'}, 'The Rigify addon is not enabled.')
            return {'CANCELLED'}
        bpy.ops.ed.undo_push()
        rig_create_warning = False
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False
        if scene.is_nla_tweakmode:
            futils.exit_nla_tweak_mode(context)
        if context.object:
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except RuntimeError:
                pass
        bpy.ops.faceit.unmask_main('EXEC_DEFAULT')
        faceit_collection = futils.get_faceit_collection()
        rig = futils.get_faceit_armature(force_original=True)
        if rig:
            bpy.data.objects.remove(rig)
        # Generate an empty armature for the rigify meta rig

        bpy.ops.object.armature_add(enter_editmode=True, location=landmarks.location)
        # bpy.ops.object.mode_set(mode='OBJECT')
        # bpy.context.view_layer.objects.active = bpy.context.object

        # bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.armature.metarig_sample_add(metarig_type="faces.super_face")
        meta_rig = context.object
        edit_bones = meta_rig.data.edit_bones
        # remove the default bone
        edit_bones.remove(edit_bones['Bone'])
        # bpy.ops.object.mode_set(mode='OBJECT')
        # check if the rigify addon is enabled
        scene.tool_settings.use_keyframe_insert_auto = auto_key
        # the BONE VERTEX MAPPING
        if scene.faceit_asymmetric:
            pass
            # vert_dict = rig_data.bone_dict_asymmetric
        else:
            vert_dict = rig_data.new_rigify_meta_bone_dict_symmetric
        # the mesh world matrix
        bpy.ops.object.mode_set(mode='OBJECT')
        meta_rig.location = landmarks.location
        meta_rig.rotation_euler = landmarks.rotation_euler
        # get average dimensions
        dim_lm = landmarks.dimensions.copy()
        avg_dim_lm = sum(dim_lm) / len(dim_lm)

        dim_rig = meta_rig.dimensions.copy()
        avg_dim_rig = sum(dim_rig) / len(dim_rig)

        scale_factor = avg_dim_lm / avg_dim_rig  # landmarks.dimensions[0] / rig.dimensions[0]
        meta_rig.dimensions = dim_rig * scale_factor  # rig.dimensions.copy() * scale_factor
        bpy.ops.object.mode_set(mode='EDIT')
        w_mat = meta_rig.matrix_world
        # the bone space local matrix
        l_mat = meta_rig.matrix_world.inverted()
        # Get the jaw pivot
        jaw_pivot_object = context.scene.objects.get('Jaw Pivot')
        if jaw_pivot_object:
            context.scene.faceit_use_jaw_pivot = True
            context.scene.faceit_jaw_pivot = jaw_pivot_object.location
        else:
            context.scene.faceit_use_jaw_pivot = False
        for i, bone_dict in vert_dict.items():
            target_point = None
            if i in (101, 111):
                meta_rig.data.use_mirror_x = False
            else:
                meta_rig.data.use_mirror_x = not scene.faceit_asymmetric

            # all vertices in the reference mesh
            if i < 100:
                # the world coordinates of the specified vertex
                target_point = landmarks.matrix_world @ landmarks.data.vertices[i].co

            ############# Special Cases ##############

            # eyes extra positions
            elif i == 101:
                if context.scene.faceit_eye_pivot_placement == 'MANUAL':
                    target_point = context.scene.faceit_eye_manual_pivot_point_L
                else:
                    target_point = context.scene.faceit_eye_pivot_point_L
            elif i == 111:
                if context.scene.faceit_eye_pivot_placement == 'MANUAL':
                    target_point = context.scene.faceit_eye_manual_pivot_point_R
                else:
                    target_point = context.scene.faceit_eye_pivot_point_R
            # jaw extra positions
            elif i == 102:
                empty_locator = jaw_pivot_object
                if empty_locator:
                    target_point = context.scene.faceit_jaw_pivot
                else:
                    jaw_L = edit_bones.get('jaw.L').head
                    jaw_R = edit_bones.get('jaw.R').head
                    target_point = w_mat @ rig_utils.get_median_pos([jaw_L, jaw_R])
                    # target_point = w_mat @ edit_bones['jaw.L'].head
                    # target_point.x = 0
            elif i == 109:
                jaw_L = edit_bones.get('jaw.L').head
                jaw_R = edit_bones.get('jaw.R').head
                target_point = w_mat @ rig_utils.get_median_pos([jaw_L, jaw_R])

            # nose extra positions
            elif i == 103:
                b_tip = edit_bones['nose.002'].head
                b_top = edit_bones['nose'].head
                vec = b_tip - b_top
                target_point = w_mat @ (b_top + vec * 0.7)

            elif i == 104:
                b_1 = edit_bones['nose.004'].head
                b_2 = edit_bones['lip.T.L'].head
                target_point = w_mat @ rig_utils.get_median_pos([b_1, b_2])
            elif i == 105:
                b_1 = edit_bones['nose.002'].head
                b_2 = edit_bones['nose.004'].head
                target_point = w_mat @ rig_utils.get_median_pos([b_1, b_2])

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
                            target_point = rig_utils.get_median_pos(bounds)
                            if scene.faceit_asymmetric:
                                bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'x')
                                target_point.x = rig_utils.get_median_pos(bounds).x
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
                            target_point = rig_utils.get_median_pos(bounds)
                            if scene.faceit_asymmetric:
                                bounds = rig_utils.get_bounds_from_locations(vertex_locations, 'x')
                                target_point.x = rig_utils.get_median_pos(bounds).x
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

        def compute_arc_length(verts):
            total_length = 0
            lengths = [0]  # start with 0 length at the first vertex

            for i in range(1, len(verts)):
                dx = verts[i][0] - verts[i - 1][0]
                dy = verts[i][1] - verts[i - 1][1]
                dz = verts[i][2] - verts[i - 1][2]
                segment_length = sqrt(dx * dx + dy * dy + dz * dz)
                total_length += segment_length
                lengths.append(total_length)

            return np.array(lengths)

        def compute_curve_points(verts, lengths):
            total_length = lengths[-1]
            target_lengths = [0, total_length / 3, 2 * total_length / 3, total_length]

            curve_points = []
            for target in target_lengths:
                # Find closest segment
                idx = np.searchsorted(lengths, target)
                if idx == 0:
                    curve_points.append(verts[0])
                elif idx == len(verts):
                    curve_points.append(verts[-1])
                else:
                    # Linearly interpolate between two vertices
                    t = (target - lengths[idx - 1]) / (lengths[idx] - lengths[idx - 1])
                    p0 = np.array(verts[idx - 1])
                    p1 = np.array(verts[idx])
                    interpolated_point = (1 - t) * p0 + t * p1
                    # Ensure the x-coordinate remains at 0 for interpolated points
                    interpolated_point[0] = 0
                    curve_points.append(Vector(interpolated_point))
            return curve_points

        # Distribute the tongue bones along the tongue vertex group
        tongue_obj = vg_utils.get_objects_with_vertex_group("faceit_tongue")
        if tongue_obj:
            tongue_bones = [edit_bones[b] for b in vert_dict[108]["all"]]
            vertex_locations = rig_utils.get_evaluated_vertex_group_positions(tongue_obj, "faceit_tongue")
            if vertex_locations:
                # Sort vertices based on Y axis
                vertex_locations.sort(key=lambda v: v[1])
                # Compute arc length
                lengths = compute_arc_length(verts=vertex_locations)
                # Compute curve points
                points = compute_curve_points(verts=vertex_locations, lengths=lengths)
                for i, b in enumerate(tongue_bones):
                    b.head = l_mat @ points[i]
                    b.tail = l_mat @ points[i + 1]
        else:
            self.report(
                {'WARNING'},
                'could not find Tongue, define vertex group in Setup panel first! Removed Tongue bones from the Rig')
            rig_create_warning = True
            for b in vert_dict[108]['all']:
                bone = edit_bones[b]
                edit_bones.remove(bone)
        meta_rig.show_in_front = True
        # Upgrade to the new rigify version
        # if self.rigify_type == 'FACE_NEW':
        bpy.ops.pose.rigify_upgrade_face('EXEC_DEFAULT')
        # Remove the ear bones
        if self.rigify_type == 'FACE_NEW':
            for b_name in vert_dict[116]['all']:
                bone = edit_bones[b_name]
                bone_r = edit_bones[b_name.replace('L', 'R')]
                edit_bones.remove(bone)
                edit_bones.remove(bone_r)
            face_bone = meta_rig.pose.bones.get('face')
            face_bone.rigify_type = 'basic.super_copy'
            face_bone.rigify_parameters.make_control = False
            face_bone.rigify_parameters.make_deform = True
        # bpy.ops.armature.rigify_add_bone_groups()
        meta_rig.data.use_mirror_x = True

        TEMPLE_BONES = {
            'forehead.L.003': {
                'head': 'forehead.L.002',
                'parent': 'face',
                'connected': False,
                'tail': 'temple.L',
                'rigify_type': 'skin.basic_chain'
            },
            'forehead.L.004': {
                'head': 'forehead.L.002',
                'parent': 'face',
                'connected': False,
                'tail': 'forehead.L.001',
                'rigify_type': 'skin.basic_chain'
            },
            'forehead.L.005': {
                'head': 'forehead.L.001',
                'parent': 'forehead.L.004',
                'connected': True,
                'tail': 'forehead.L',
                'rigify_type': ''
            },
            'forehead.L.006': {
                'head': 'forehead.L',
                'parent': 'forehead.L.005',
                'connected': True,
                'tail': '',
                'rigify_type': '',
            }
        }
        if self.add_temple_helper_bones:
            for b_name, dict in TEMPLE_BONES.items():
                b = meta_rig.data.edit_bones.new(b_name)
                b.head = meta_rig.data.edit_bones.get(dict['head']).head
                if dict['tail']:
                    b.tail = meta_rig.data.edit_bones.get(dict['tail']).head
                else:
                    tail = b.head.copy()
                    tail.x = 0
                    b.tail = tail
                if dict['parent']:
                    b.parent = meta_rig.data.edit_bones.get(dict['parent'])
                    b.use_connect = dict['connected']
            # Do the same on the other side. Replace all the L with R
            temple_bones_r = {}
            for b_name, dict in TEMPLE_BONES.items():
                b_name_r = b_name.replace('L', 'R')
                b = meta_rig.data.edit_bones.new(b_name_r)
                b.head = meta_rig.data.edit_bones.get(dict['head'].replace('L', 'R')).head
                if dict['tail']:
                    b.tail = meta_rig.data.edit_bones.get(dict['tail'].replace('L', 'R')).head
                else:
                    tail = b.head.copy()
                    tail.x = 0
                    b.tail = tail
                if dict['parent']:
                    b.parent = meta_rig.data.edit_bones.get(dict['parent'].replace('L', 'R'))
                    b.use_connect = dict['connected']
                temple_bones_r[b_name_r] = b
        lip_bones = ('lip.T.L.001', 'lip.T.R.001', 'lip.B.L.001', 'lip.B.R.001')
        if self.mouth_subdivisions > 0:
            # deselect all bones
            bpy.ops.armature.select_all(action='DESELECT')
            for b_name in lip_bones:
                b = meta_rig.data.edit_bones.get(b_name)
                b.select = True
            bpy.ops.armature.subdivide(number_cuts=self.mouth_subdivisions)
            # distribute the new bones evenly...

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.mode_set(mode='POSE')
        if self.add_temple_helper_bones:
            for b_name, dict in TEMPLE_BONES.items():
                b = meta_rig.pose.bones.get(b_name)
                b.rigify_type = dict['rigify_type']
                b_r = meta_rig.pose.bones.get(b_name.replace('L', 'R'))
                b_r.rigify_type = dict['rigify_type']
        if self.set_sharp_mouth_corners:
            lip_T_L = meta_rig.pose.bones.get('lip.T.L')
            lip_T_L.rigify_parameters.skin_chain_connect_mirror[1] = False
            lip_T_R = meta_rig.pose.bones.get('lip.T.R')
            lip_T_R.rigify_parameters.skin_chain_connect_mirror[1] = False

            # lip_T.rigify_parameters.skin_chain_connect_sharp_angle = (0,0)
        # try:
        #     import rigify
        # except ImportError:
        #     self.report({'WARNING'}, 'The Rigify addon is not enabled.')
        #     return {'CANCELLED'}
        # print('Rigify version:', rigify.bl_info['version'])

        for i in range(6):
            meta_rig.data.rigify_colors.add()

        meta_rig.data.rigify_colors[0].name = "Root"
        meta_rig.data.rigify_colors[0].active = Color((0.5490, 1.0000, 1.0000))
        meta_rig.data.rigify_colors[0].normal = Color((0.4353, 0.1843, 0.4157))
        meta_rig.data.rigify_colors[0].select = Color((0.3137, 0.7843, 1.0000))
        meta_rig.data.rigify_colors[0].standard_colors_lock = True
        if self.color_style == 'RIGIFY':
            meta_rig.data.rigify_colors[4].name = "FK"
            meta_rig.data.rigify_colors[4].active = Color((0.5490, 1.0000, 1.0000))
            meta_rig.data.rigify_colors[4].normal = Color((0.1176, 0.5686, 0.0353))
            meta_rig.data.rigify_colors[4].select = Color((0.3137, 0.7843, 1.0000))
            meta_rig.data.rigify_colors[4].standard_colors_lock = True
            meta_rig.data.rigify_colors[1].name = "IK"
            meta_rig.data.rigify_colors[1].active = Color((0.5490, 1.0000, 1.0000))
            meta_rig.data.rigify_colors[1].normal = Color((0.6039, 0.0000, 0.0000))
            meta_rig.data.rigify_colors[1].select = Color((0.3137, 0.7843, 1.0000))
            meta_rig.data.rigify_colors[1].standard_colors_lock = True
            meta_rig.data.rigify_colors[2].name = "Special"
            meta_rig.data.rigify_colors[2].active = Color((0.5490, 1.0000, 1.0000))
            meta_rig.data.rigify_colors[2].normal = Color((0.9569, 0.7882, 0.0471))
            meta_rig.data.rigify_colors[2].select = Color((0.3137, 0.7843, 1.0000))
            meta_rig.data.rigify_colors[2].standard_colors_lock = True
        else:
            meta_rig.data.rigify_colors[4].name = "FK"
            meta_rig.data.rigify_colors[4].active = Color((0.40392160415649414, 1.0, 0.0))
            meta_rig.data.rigify_colors[4].normal = Color((0.09803922474384308, 0.8235294818878174, 0.7019608020782471))
            meta_rig.data.rigify_colors[4].select = Color(
                (0.29019609093666077, 0.8156863451004028, 0.46666669845581055))
            meta_rig.data.rigify_colors[4].standard_colors_lock = True
            meta_rig.data.rigify_colors[1].name = "IK"
            meta_rig.data.rigify_colors[1].active = Color((1.0, 0.8549020290374756, 0.9490196704864502))
            meta_rig.data.rigify_colors[1].normal = Color((1.0, 0.18431372940540314, 0.6313725709915161))
            meta_rig.data.rigify_colors[1].select = Color((1.0, 0.4117647409439087, 0.9529412388801575))
            meta_rig.data.rigify_colors[1].standard_colors_lock = True
            meta_rig.data.rigify_colors[2].name = "Special"
            meta_rig.data.rigify_colors[2].active = Color((1.0, 0.9921569228172302, 0.8196079134941101))
            meta_rig.data.rigify_colors[2].normal = Color((1.0, 0.8862745761871338, 0.2196078598499298))
            meta_rig.data.rigify_colors[2].select = Color((1.0, 0.7921569347381592, 0.4392157196998596))
            meta_rig.data.rigify_colors[2].standard_colors_lock = True

        meta_rig.data.rigify_colors[3].name = "Tweak"
        meta_rig.data.rigify_colors[3].active = Color((0.5490, 1.0000, 1.0000))
        meta_rig.data.rigify_colors[3].normal = Color((0.0392, 0.2118, 0.5804))
        meta_rig.data.rigify_colors[3].select = Color((0.3137, 0.7843, 1.0000))
        meta_rig.data.rigify_colors[3].standard_colors_lock = True
        meta_rig.data.rigify_colors[5].name = "Extra"
        meta_rig.data.rigify_colors[5].active = Color((0.5490, 1.0000, 1.0000))
        meta_rig.data.rigify_colors[5].normal = Color((0.9686, 0.2510, 0.0941))
        meta_rig.data.rigify_colors[5].select = Color((0.3137, 0.7843, 1.0000))
        meta_rig.data.rigify_colors[5].standard_colors_lock = True

        if bpy.app.version < (4, 0, 0):
            bpy.ops.pose.rigify_layer_init()
            bpy.ops.armature.rigify_add_bone_groups()
            # Face -> FK
            # Face (Primary) -> IK
            # Face (Secondary) -> Special
            layer_FK = meta_rig.data.rigify_layers[0]
            layer_FK.name = 'Face'
            layer_FK.group = 5
            layer_IK = meta_rig.data.rigify_layers[1]
            layer_IK.name = 'Face (Primary)'
            layer_IK.group = 2
            layer_SPECIAL = meta_rig.data.rigify_layers[2]
            layer_SPECIAL.group = 3
            layer_SPECIAL.name = 'Face (Secondary)'
            bpy.ops.object.mode_set(mode='EDIT')
            edit_bones = meta_rig.data.edit_bones
            # set the layer of the bones -> influences the bone groups on the generated rig.
            for layer, bones in rig_data.RIGIFY_META_RIG_LAYERS.items():
                for bone in bones:
                    bone = edit_bones.get(bone)
                    if not bone:
                        continue
                    layers = [False] * 32
                    layers[layer] = True
                    bone.layers = layers
            meta_rig.data.layers[2] = True
        else:
            def add_bone_collection(name, *, ui_row=0, ui_title='', sel_set=False, color_set_id=0):
                uid = len(meta_rig.data.collections)
                new_bcoll = meta_rig.data.collections.new(name)
                new_bcoll.rigify_uid = uid
                new_bcoll.rigify_ui_row = ui_row
                new_bcoll.rigify_ui_title = ui_title
                new_bcoll.rigify_sel_set = sel_set
                new_bcoll.rigify_color_set_id = color_set_id
            add_bone_collection('Face', ui_row=1, color_set_id=5)
            add_bone_collection('Face (Primary)', ui_row=2, ui_title='(Primary)', color_set_id=2)
            add_bone_collection('Face (Secondary)', ui_row=2, ui_title='(Secondary)', color_set_id=3)
            for i, c_name in enumerate(('Face', 'Face (Primary)', 'Face (Secondary)')):
                bcoll = meta_rig.data.collections.get(c_name)
                bcoll.is_visible = True
                bone_names = rig_data.RIGIFY_META_RIG_LAYERS[i]
                for b_name in bone_names:
                    bone = meta_rig.data.bones.get(b_name)
                    if bone:
                        bcoll.assign(bone)

        bpy.ops.object.mode_set(mode='OBJECT')
        # Generate the rigify rig.
        if not self.edit_meta_rig:
            bpy.ops.faceit.generate_rig_from_meta_rig('EXEC_DEFAULT', rigify_type=self.rigify_type)
            bpy.data.objects.remove(meta_rig)
        else:
            if meta_rig.name not in faceit_collection.objects:
                faceit_collection.objects.link(meta_rig)
            meta_rig.name = 'FaceitMetaRig'

        scene.tool_settings.use_keyframe_insert_auto = auto_key
        scene.tool_settings.use_snap = False
        return {'FINISHED'}


class FACEIT_OT_GenerateRigFromMetaRig(bpy.types.Operator):
    '''Generate the rigify rig based on the active meta rig.'''
    bl_idname = 'faceit.generate_rig_from_meta_rig'
    bl_label = 'Generate Rig From Meta Rig'
    bl_options = {'UNDO'}

    rigify_type: EnumProperty(
        name='Rigify Type',
        items=[
            ('FACE', 'Face Rig', 'Rigify Face Rig < Blender 3.0'),
            ('FACE_NEW', 'Face Rig New', 'Rigify Face Rig > Blender 3.0'),
        ],
        default='FACE_NEW',
    )

    @ classmethod
    def poll(cls, context):
        return rig_utils.is_metarig(context.object)

    def execute(self, context):
        bone_collections = ('Face', 'Face(Primary)', 'Face(Secondary)')
        faceit_collection = futils.get_faceit_collection()
        meta_rig = context.object
        bpy.ops.pose.rigify_generate()
        rig = context.object
        rig.show_in_front = True
        faceit_collection.objects.link(rig)
        rig.name = 'FaceitRig'
        rig['faceit_rig_id'] = get_random_rig_id()
        # Move the eye target bones further away from the face
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = rig.data.edit_bones
        if self.rigify_type == 'FACE_NEW':
            pass
            # vec = Vector((0, -dim.y / 3, 0))
            # eye_target_bones = ('MCH-eye_common.parent', 'eye.L', 'eye.R', 'eye_common')
            # for b in eye_target_bones:
            #     b = edit_bones.get(b)
            #     b.translate(vec)
        else:
            org_face_bone = edit_bones.get('ORG-face')
            # def_face_bone = org_face_bone.copy()
            def_face_bone = edit_bones.new('DEF-face')
            def_face_bone.head = org_face_bone.head
            def_face_bone.tail = org_face_bone.tail
            # def_face_bone.name = 'DEF-face'
            def_face_bone.use_deform = True
            # move to deform layer
            if bpy.app.version < (4, 0, 0):
                layers = [False] * 32
                layers[29] = True
                def_face_bone.layers = layers
        bpy.ops.object.mode_set(mode='OBJECT')
        context.scene.faceit_armature = rig
        rig.pose.use_mirror_x = True
        rig.data.display_type = 'BBONE'
        # for bcoll_name in bone_collections:
        #     bcoll = rig.data.collections.get(bcoll_name)
        #     if bcoll:
        #         bcoll.is_visible = True
        # hide the meta_rig
        meta_rig.hide_set(True)
        # bpy.data.objects.remove(meta_rig)

        # TODO: set the eyelid constraints to animate the proper distance.
        rig_utils.set_lid_follow_constraints_new_rigify(rig, "L")
        rig_utils.set_lid_follow_constraints_new_rigify(rig, "R")

        landmarks = futils.get_object('facial_landmarks')
        if landmarks:
            landmarks.hide_viewport = True
        jaw_pivot_object = context.scene.objects.get('Jaw Pivot')
        if jaw_pivot_object:
            bpy.data.objects.remove(jaw_pivot_object)
        return {'FINISHED'}
