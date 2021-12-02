import io
import bpy
import time
from mathutils import Vector
from contextlib import redirect_stdout
from bpy.props import BoolProperty, IntProperty

from . import bind_utils
from ..core import shape_key_utils
from ..core import mesh_utils
from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils


class FACEIT_OT_SmartBind(bpy.types.Operator):
    '''Bind main objects (Face, Eyes, Teeth, Tongue)'''
    bl_idname = 'faceit.smart_bind'
    bl_label = 'Bind'
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    # -------- DEBUG OPTIONS -----------
    show_advanced_settings: BoolProperty(
        name='Show Advanced Options',
        default=False,
    )
    # duplicate: BoolProperty(
    #     default=True
    # )
    bind_scale_objects: BoolProperty(
        name='Scale Geometry',
        description='Temporarilly scales the geometry for Binding. Use if Auto Weights fails.',
        default=True
    )
    bind_scale_factor: IntProperty(
        name='',
        description='Factor to scale by. Tweak this if your binding fails',
        default=100
    )
    keep_vertex_groups: BoolProperty(
        name='Keep Vertex Groups',
        description='If this is unchecked Faceit will remove all Vertex Groups except the Faceit groups. This destroys other armature bindings.',
        default=True)
    keep_shape_keys: BoolProperty(
        name='Keep Shape keys',
        description='If this is unchecked Faceit will remove all Shape Keys from the bind object. This can destroy the looks of your meshes and aniamtions.',
        default=True
    )
    hide_other_armature_modifers: BoolProperty(
        name='Disable Other Armature Modifiers',
        description='Other Armature Modifiers can disturb the Faceit results. Use them only if you know what you are doing.',
        default=False,)
    auto_weight: BoolProperty(
        name='Auto Weight',
        description='Apply Automatic Weights to the Main Object(s)',
        default=True
    )
    smart_weights: BoolProperty(
        name='Smart Weights',
        description='Improves weights for most characters, by detecting rigid skull vertices and assigning them to DEF-face group',
        default=True)
    transfer_weights: BoolProperty(
        name='Transfer Weights',
        description='Transfer the Weights to all Geometry without Faceit Vertex Groups',
        default=True
    )
    secondary_weights: BoolProperty(
        name='Secondary Weights',
        description='Overwrite Faceit Vertex Groups with specific bone weights (Eyes, Teeth, Rigid...)',
        default=True
    )
    keep_split_objects: BoolProperty(
        name='Keep Split Objects',
        description='Keep the Split objects for inspection. This can be useful when binding fails.',
        default=False
    )
    smooth_bind: BoolProperty(
        name='Apply Smoothing',
        description='Applies automatic weight-smoothing after binding.',
        default=True
    )
    remove_old_faceit_weights: BoolProperty(
        name='Remove Old Faceit Weights',
        description='Removes all weights associated with the FaceitRig before rebinding.',
        default=True
    )
    make_single_user: BoolProperty(
        name='Make Single User',
        description='Makes single user copy before binding. Otherwise Binding will likely fail.',
        default=True
    )

    @classmethod
    def poll(cls, context):
        rig = futils.get_faceit_armature(force_original=True)
        if rig and context.scene.faceit_face_objects:
            if rig.hide_viewport == False and context.mode == 'OBJECT':
                return True

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        col_bind = layout.column()
        row = col_bind.row()
        row.label(text='OPTIONS')
        row = col_bind.row(align=True)
        row.prop(self, 'bind_scale_objects', icon='EMPTY_DATA')
        if self.bind_scale_objects:
            row.prop(self, 'bind_scale_factor')
        # row = col_bind.row()
        # row.prop(self, 'hide_other_armature_modifers')
        row = col_bind.row()
        row.prop(self, 'show_advanced_settings', icon='COLLAPSEMENU')
        if self.show_advanced_settings:
            row = col_bind.row()
            row.label(text='ADVANCED')
            row = col_bind.row()
            row.prop(self, 'auto_weight')
            row.prop(self, 'smart_weights')
            row = col_bind.row()
            row.prop(self, 'transfer_weights')
            row.prop(self, 'secondary_weights')
            row = col_bind.row()
            row.prop(self, 'smooth_bind')
            row.prop(self, 'remove_old_faceit_weights')
            row = col_bind.row()
            row.prop(self, 'make_single_user')
            row.prop(self, 'keep_split_objects')

    def execute(self, context):
        scene = context.scene

        # --------------- RELEVANT OBJECTS -------------------

        start_time = time.time()
        face_objects = futils.get_faceit_objects_list()

        if not face_objects:
            self.report({'ERROR'}, 'No objects registered! Complete Setup')
            return{'FINISHED'}

        lm_obj = futils.get_object('facial_landmarks')

        if not lm_obj:
            self.report({'ERROR'}, 'Faceit landmarks not found!')
            return{'FINISHED'}

        rig = futils.get_faceit_armature()

        if not rig:
            self.report({'ERROR'}, 'Faceit rig not found!')
            return{'FINISHED'}

        # --------------- CHECK MAIN GROUP/OBJECT ---------------
        face_obj = futils.get_main_faceit_object()
        found_main = bind_utils.check_main_faceit_group(face_obj, face_objects)
        if not found_main:
            self.report(
                {'ERROR'},
                'There are multiple islands in the Main face object. Please assign the Main group to the face before Binding.')
            return{'CANCELLED'}

        # return{'CANCELLED'}

        # --------------- SCENE SETTINGS -------------------
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        use_auto_normalize = scene.tool_settings.use_auto_normalize
        scene.tool_settings.use_auto_normalize = False
        mesh_select_mode = scene.tool_settings.mesh_select_mode[:]
        scene.tool_settings.mesh_select_mode = (True, True, True)

        scene.tool_settings.use_keyframe_insert_auto = False
        pivot_setting = scene.tool_settings.transform_pivot_point

        simplify_value = scene.render.use_simplify
        simplify_subd = scene.render.simplify_subdivision
        scene.render.use_simplify = True
        scene.render.simplify_subdivision = 0

        # --------------- OBJECT & ARMATURE SETTINGS -------------------
        # | - Unhide Objects
        # | - Hide Generators (Modifier)
        # | - Set Mirror Settings (asymmetry or not)
        # -------------------------------------------------------
        obj_mod_show_dict = {}

        # key - Object, Value - Dict containing shape key data, values
        obj_sk_dict = {}

        for obj in face_objects:

            if obj.data.users > 1:
                if self.make_single_user:
                    obj.data = obj.data.copy()
                    print('Making Single user copy of objects {} data'.format(obj.name))
                else:
                    self.report(
                        {'WARNING'}, 'The object {} has multiple users. Check Make Single User in Bind Settings if binding fails.'.format(obj.name))

            futils.set_hidden_state_object(obj, False, False)

            futils.clear_object_selection()
            futils.set_active_object(obj.name)
            # return{'FINISHED'}

            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.reveal()
            bpy.ops.object.mode_set(mode='OBJECT')

            obj.data.use_mirror_x = False if scene.faceit_asymmetric else True

            # Store Shape Keys + delete (for data transfer to work!)
            if shape_key_utils.has_shape_keys(obj):

                sk_dict = shape_key_utils.store_shape_keys(obj, store_drivers=True)
                sk_action = None
                if obj.data.shape_keys.animation_data:
                    sk_action = obj.data.shape_keys.animation_data.action

                obj_sk_dict[obj] = {
                    'sk_dict': sk_dict,
                    'sk_action': sk_action,
                }

                # Remove all Shape Keys and apply basis in case it contains shape data
                shape_key_utils.remove_all_sk_apply_basis(obj, apply_basis=True)

            other_rigs = []
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE' and mod.object != rig:
                    other_rigs.append(mod.object)
                try:
                    obj_mod_show_dict[obj.name][mod.name] = mod.show_viewport
                except KeyError:
                    obj_mod_show_dict[obj.name] = {mod.name: mod.show_viewport}

                mod.show_viewport = False

            # Remove all FaceitRig vertex groups
            if self.remove_old_faceit_weights:
                other_deform_groups = []
                if other_rigs:
                    for o_rig in other_rigs:
                        other_deform_groups.extend(vg_utils.get_deform_bones_from_armature(o_rig))
                # Just get current vertex groups

                deform_groups = vg_utils.get_deform_bones_from_armature(rig)

                vertex_group_intersect = (set(deform_groups).intersection(set(other_deform_groups)))
                if vertex_group_intersect:
                    self.report(
                        {'WARNING'},
                        'There seems to be another rig with similar bone names: {}. This can lead to weight conflicts. Faceit will add the influence.'.
                        format(vertex_group_intersect))
                for grp in obj.vertex_groups:
                    if grp.name in deform_groups:
                        if grp.name not in other_deform_groups:
                            obj.vertex_groups.remove(grp)
            # return{'FINISHED'}

        futils.set_hidden_state_object(lm_obj, False, False)
        futils.set_hidden_state_object(rig, False, False)

        rig.data.pose_position = 'REST'
        # enable all armature layers
        layer_state = rig.data.layers[:]
        for i in range(len(rig.data.layers)):
            rig.data.layers[i] = True

        # --------------- DUPLICATE OBJECT(S) -------------------
        # | - Preserve Data (Vertex Groups + Shape Keys)
        # | - Remove parent hierarchies! Keep Transform
        # -------------------------------------------------------
        dup_objects_dict = {}
        dup_face_objects = []

        futils.clear_object_selection()

        for obj in face_objects:
            dup_obj = obj.copy()
            dup_obj.data = obj.data.copy()
            dup_objects_dict[obj] = dup_obj
            dup_face_objects.append(dup_obj)

            # Link to the scene to process with Faceit.
            scene.collection.objects.link(dup_obj)
            dup_obj.select_set(state=True)

            # Remove all vertex groups from duplicates, except for faceitgroups
            for grp in dup_obj.vertex_groups:
                if not 'faceit_' in grp.name:
                    dup_obj.vertex_groups.remove(grp)

        # Remove parent - keep transform! Parent objects with Transforms can mess up the process!
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

        # Get the main obj
        face_obj_dup = dup_objects_dict[face_obj]

        # --------------- SCALE OBJECT(S) -------------------
        # | - Scale armature, bind objects, landmarks to avoid Auto Weight error. Known Issue in Blender
        # -------------------------------------------------------
        # scene.cursor.location = face_obj_dup.location
        scene.cursor.location = Vector()
        scene.tool_settings.transform_pivot_point = 'CURSOR'

        if self.bind_scale_objects:
            scale_factor = self.bind_scale_factor
            bind_utils._scale_bind_objects(factor=scale_factor, objects=[rig, *dup_face_objects, lm_obj])

        # --------------- MAIN BINDING PROCESS -------------------
        # | - Bind (main geo) +
        # | - Data Transfer (hair, beard,brows etc.) +
        # | - Secondary Assigns (eyes, teeth, tongue)
        # -------------------------------------------------------

        bind_success = self._bind(
            context,
            bind_objects=dup_face_objects,
            rig=rig,
            landmarks_object=lm_obj,
        )

        # --------------- RESTORE SCALE(S) -------------------

        # scene.cursor.location = face_obj_dup.location
        scene.cursor.location = Vector()
        scene.tool_settings.transform_pivot_point = 'CURSOR'

        if self.bind_scale_objects:
            bind_utils._scale_bind_objects(factor=scale_factor, objects=[rig, *dup_face_objects, lm_obj], reverse=True)

        # --------------- RESTORE OBJECT DATA -------------------
        # | - Data Transfer the original data
        # -------------------------------------------------------

        for obj, dup_obj in dup_objects_dict.items():

            # futils.clear_object_selection()
            # # transfer from active to selected
            # obj.select_set(state=True)
            # futils.set_active_object(dup_obj)

            # bpy.ops.object.data_transfer(
            #     data_type='VGROUP_WEIGHTS',
            #     vert_mapping='POLYINTERP_NEAREST',
            #     layers_select_src='ALL',
            #     layers_select_dst='NAME',
            #     islands_precision=10,
            # )
            bind_utils._data_transfer_vertex_groups(obj_from=dup_obj, obj_to=obj, apply=True, method='NEAREST')
            # Apply stored Shape Keys
            bpy.data.objects.remove(dup_obj, do_unlink=True)

            futils.clear_object_selection()
            futils.set_active_object(obj.name)

            # --------------- OBJECT & ARMATURE SETTINGS -------------------
            # | - Unhide Objects
            # | - Restore Modifier States
            # -------------------------------------------------------
            show_mod_dict = obj_mod_show_dict.get(obj.name)
            if show_mod_dict:
                for mod, show_value in show_mod_dict.items():
                    mod = obj.modifiers.get(mod)
                    if mod:
                        if self.hide_other_armature_modifers:
                            if mod.type == 'ARMATURE' and mod.object != rig:
                                continue
                        mod.show_viewport = show_value

            # ----------------- REAPPLY SHAPE KEYS --------------------------
            # | - Shape Keys and Drivers!
            # ---------------------------------------------------------------
            sk_data_dict = obj_sk_dict.get(obj)
            if sk_data_dict:
                sk_dict = sk_data_dict['sk_dict']
                sk_action = sk_data_dict['sk_action']

                shape_key_utils.apply_stored_shape_keys(obj, sk_dict, apply_drivers=True)

            if shape_key_utils.has_shape_keys(obj):
                if sk_action:
                    if not obj.data.shape_keys.animation_data:
                        obj.data.shape_keys.animation_data_create()
                    obj.data.shape_keys.animation_data.action = sk_action

            # ----------------- FACEIT MODIFIER --------------------------
            # | - Check for bind groups and ensure the modifier is applied
            # -------------------------------------------------------------
            deform_groups = vg_utils.get_deform_bones_from_armature(rig)
            if not any([grp in obj.vertex_groups for grp in deform_groups]):
                continue
            futils.add_faceit_armature_modifier(obj, rig)

        rig.data.pose_position = 'POSE'
        rig.data.layers = layer_state[:]

        futils.set_hidden_state_object(lm_obj, True, True)

        # --------------- FACEIT LOGIC -------------------
        if bind_success:
            rig['bound'] = 1
        else:
            self.report({'INFO'}, 'Binding completed!')

        # --------------- RESTORE SETTINGS -------------------
        scene.tool_settings.transform_pivot_point = pivot_setting
        context.scene.tool_settings.use_auto_normalize = use_auto_normalize
        scene.tool_settings.use_keyframe_insert_auto = auto_key
        scene.render.use_simplify = simplify_value
        scene.render.simplify_subdivision = simplify_subd
        scene.tool_settings.mesh_select_mode = mesh_select_mode

        futils.clear_object_selection()
        futils.set_active_object(rig.name)

        bpy.ops.outliner.orphans_purge()

        print('Bound in {}'.format(round(time.time() - start_time, 2)))

        return {'FINISHED'}

    def _bind(self, context, bind_objects, rig, landmarks_object):
        '''Start the Faceit Binding progress on the passed bind objects
        @face_obj: the main object, can also be retrieved from bind_objects (main group)
        @bind_objects: the bind objects. Should have cleared vertex groups except for faceit groups
        @rig: the armature object to bind to
        '''
        faceit_vertex_groups = [
            'faceit_right_eyeball',
            'faceit_left_eyeball',
            'faceit_left_eyes_other',
            'faceit_right_eyes_other',
            'faceit_upper_teeth',
            'faceit_lower_teeth',
            'faceit_tongue',
            'faceit_rigid'
            # 'faceit_main',
            # 'faceit_eyelashes'
        ]

        # ----------------------- SPLIT OBJECTS BEFORE BIND ----------------------------
        # | - Split by Faceit Group assignments + put all non-assigned in one obj
        # | -
        # ------------------------------------------------------------------------------
        bind_problem = False

        auto_weight_objects = []
        transfer_weights_objects = []
        secondary_bind_objects = []

        all_split_objects = []
        split_bind_objects_dict = {}

        for obj in bind_objects:
            # Unlock all groups:
            for grp in obj.vertex_groups:
                grp.lock_weight = False

            split_objects = bind_utils.split_by_faceit_groups(obj)
            all_split_objects.extend(split_objects)
            split_bind_objects_dict[obj] = split_objects

        # Remove double entries
        all_split_objects = list(set(all_split_objects))

        futils.clear_object_selection()

        for s_obj in all_split_objects:
            if 'faceit_main' in s_obj.vertex_groups:  # or 'faceit_tongue' in s_obj.vertex_groups:
                auto_weight_objects.append(s_obj)

            # elif 'faceit_eyelashes' in s_obj.vertex_groups:
            elif any([grp.name in faceit_vertex_groups for grp in s_obj.vertex_groups]):
                secondary_bind_objects.append(s_obj)
            else:
                transfer_weights_objects.append(s_obj)

        if self.keep_split_objects:
            print('------- SPLIT OBJECTS ----------')
            print(all_split_objects)
            print('------- Auto Bind ----------')
            print(auto_weight_objects)
            print('------- Data Transfer ----------')
            print(transfer_weights_objects)
            print('------- Secondary Bind ----------')
            print(secondary_bind_objects)

        # --------------- AUTO WEIGHT ---------------------------
        # | - ...
        # -------------------------------------------------------
        if self.auto_weight:
            start_time = time.time()

            bind_problem, warning = self._auto_weight_objects(
                auto_weight_objects,
                rig,
            )
            if warning:
                self.report(
                    {'WARNING'},
                    'Automatic Weights failed! {}'.format(
                        'Try to active the "Scale Geometry" in Bind settings.'
                        if not self.bind_scale_objects else ' Try to use a higher Scale factor.'))
            print('Auto Weights in {}'.format(round(time.time() - start_time, 2)))

        # ----------------------- SMART WEIGHTS ---------------------------
        # | Remove weights out of the face.
        # -----------------------------------------------------------------
        if self.smart_weights:
            start_time = time.time()
            self._apply_smart_weighting(
                context,
                auto_weight_objects,
                rig,
                landmarks_object,
                faceit_vertex_groups,
                smooth_weights=self.smooth_bind
            )

            print('Smart Weights in {}'.format(round(time.time() - start_time, 2)))
        # return
        # ----------------------- TRANSFER WEIGHTS ---------------------------
        # | Transfer Weights from auto bound geo to secondary geo (hair,...)
        # -----------------------------------------------------------------
        if self.transfer_weights:
            start_time = time.time()

            if transfer_weights_objects:
                self._transfer_weights(
                    auto_weight_objects,
                    transfer_weights_objects,
                )
            else:
                self.report({'WARNING'}, 'Can\'t find any vertices to transfer weights to')

            print('Transfer Weights in {}'.format(round(time.time() - start_time, 2)))
        # ----------------------- TRANSFER WEIGHTS ---------------------------
        # | Transfer Weights from auto bound geo to secondary geo (hair,...)
        # -----------------------------------------------------------------

        if self.secondary_weights:
            start_time = time.time()
            # if secondary_bind_objects:
            self._assign_secondary_weighting(
                faceit_vertex_groups,
                objects=all_split_objects,
                rig=rig,
            )
            print('Secondary Weights in {}'.format(round(time.time() - start_time, 2)))

        # ----------------------- MERGE SPLIT OBJECTS ---------------------------

        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set()

        for obj, split_objects in split_bind_objects_dict.items():

            futils.clear_object_selection()

            for s_obj in split_objects:
                if s_obj:

                    if self.keep_split_objects:
                        debug_duplicate = s_obj.copy()
                        debug_duplicate.data = s_obj.data.copy()
                        context.scene.collection.objects.link(debug_duplicate)
                        debug_duplicate.name = debug_duplicate.name + '_debug'

                    futils.set_active_object(s_obj.name)

            futils.set_active_object(obj.name)
            bpy.ops.object.join()
            futils.add_faceit_armature_modifier(obj, rig)

        if self.smooth_bind:
            self._smooth_weights(
                objects=bind_objects,
                rig=rig,
            )

        # ----------------------- REMOVE RIGID ---------------------------
        # | Remove Weights from Verts with faceit_rigid group (pass only faceit_rigid)
        # -----------------------------------------------------------------

        start_time = time.time()
        self._assign_secondary_weighting(
            ['faceit_rigid', ],
            objects=bind_objects,
            rig=rig,
        )
        print('Removed Rigid Verts in {}'.format(round(time.time() - start_time, 2)))

        for obj in bind_objects:
            for grp in obj.vertex_groups:
                if 'faceit_' in grp.name:
                    obj.vertex_groups.remove(grp)

        return not bind_problem

    def _auto_weight_objects(self, auto_weight_objects, rig):
        '''
        Apply Automatic Weights to main geometry.
        Optionally apply Smart Weighting and Smoothing
        Split Main geo
        '''
        bind_problem = False
        return_warning = []

        # Disable bones for auto weighting
        no_auto_weight = [
            'DEF-tongue',
            'DEF-tongue.001',
            'DEF-tongue.002',
            'DEF-teeth.B',
            'DEF-teeth.T',
            'DEF_eye.R',
            'DEF_eye.L',
        ]
        for b in no_auto_weight:
            bone = rig.data.bones.get(b)
            if bone:
                bone.use_deform = False

        warning = 'Warning: Bone Heat Weighting: failed to find solution for one or more bones'

        futils.clear_object_selection()

        for obj in auto_weight_objects:
            obj.select_set(state=True)

        futils.set_active_object(rig.name)

        _stdout_warning = ''

        stdout = io.StringIO()

        with redirect_stdout(stdout):

            bpy.ops.object.parent_set(type='ARMATURE_AUTO', keep_transform=True)

        stdout.seek(0)
        _stdout_warning = stdout.read()
        del stdout

        if warning in _stdout_warning:
            return_warning.append(
                warning + ' for object {}. Check the Docs for work-arounds'.format(auto_weight_objects))
            bind_problem = True

        # Reenable Auto weight for bones
        for b in no_auto_weight:
            bone = rig.data.bones.get(b)
            if bone:
                bone.use_deform = True

        return not bind_problem, return_warning

    def _apply_smart_weighting(
            self, context, objects, rig, landmarks_object, faceit_vertex_groups, smooth_weights=True):
        '''
        Remove weights outside of the face.
        '''

        # Create the facial hull object encompassing the facial geometry.
        bpy.ops.object.mode_set(mode='OBJECT')
        face_hull = bind_utils._create_facial_hull(context, landmarks_object)

        for obj in objects:

            futils.clear_object_selection()
            futils.set_active_object(obj.name)

            deform_groups = vg_utils.get_deform_bones_from_armature(rig)

            if any([grp in obj.vertex_groups for grp in deform_groups]):
                bind_utils._remove_weights_from_non_facial_geometry(obj, face_hull, faceit_vertex_groups)
            else:
                print('found no auto weights on object {}. Skipping smart weights'.format(obj.name))

        # remove the hull helper object
        bpy.data.objects.remove(face_hull)

        for obj in objects:

            futils.clear_object_selection()
            rig.select_set(state=True)
            futils.set_active_object(obj.name)

            # Make Def-face the active vertex group before normalizing
            face_grp_idx = obj.vertex_groups.find('DEF-face')
            if face_grp_idx != -1:
                obj.vertex_groups.active_index = face_grp_idx

            if smooth_weights:

                use_mask = obj.data.use_paint_mask_vertex
                obj.data.use_paint_mask_vertex = False

                bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

                # ------------------------- SMOOTH  WEIGHTS -------------------------------
                if face_grp_idx != -1:
                    bpy.ops.object.vertex_group_smooth(group_select_mode='ACTIVE',
                                                       factor=0.5,
                                                       repeat=10,
                                                       expand=0.1,
                                                       )

                bpy.ops.object.vertex_group_smooth(group_select_mode='BONE_DEFORM',
                                                   factor=0.5,
                                                   repeat=1,
                                                   expand=0,
                                                   )
                obj.data.use_paint_mask_vertex = use_mask

            # ------------------------- NORMALIZE WEIGHTS -------------------------------
            # lock and normalize - so the facial influences get restricted

            if face_grp_idx != -1:
                bpy.ops.object.vertex_group_normalize_all(lock_active=True)

            bpy.ops.object.mode_set()
            vg_utils.remove_zero_weights_from_verts(obj, thres=0.0001)
            vg_utils.remove_unused_vertex_groups_thresh(obj, thres=0.0001)

    def _smooth_weights(self, objects, rig):

        for obj in objects:

            futils.clear_object_selection()
            rig.select_set(state=True)

            futils.set_active_object(obj.name)

            use_mask = obj.data.use_paint_mask_vertex
            obj.data.use_paint_mask_vertex = False

            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

            bpy.ops.object.vertex_group_smooth(group_select_mode='BONE_DEFORM',
                                               factor=0.5,
                                               repeat=1,
                                               expand=0,
                                               )

            obj.data.use_paint_mask_vertex = use_mask

            bpy.ops.object.mode_set()

    def _transfer_weights(self, transfer_from_objects, transfer_to_objects):

        # ----------------------- TRANSFER WEIGHTS ---------------------------

        if transfer_to_objects and transfer_from_objects:

            for from_obj in transfer_from_objects:
                futils.clear_object_selection()

                for obj in transfer_to_objects:

                    faceit_groups_per_obj = set(vg_utils.get_faceit_vertex_grps(obj))

                    # get objects that were not bound and are registered in faceit objects
                    bind_utils._data_transfer_vertex_groups(obj_from=from_obj, obj_to=obj, method='NEAREST')

                    # remove all non lid deform groups
                    if 'faceit_eyelashes' in obj.vertex_groups:
                        for vgroup in obj.vertex_groups:
                            if 'DEF' in vgroup.name:
                                if not 'lid' in vgroup.name:
                                    obj.vertex_groups.remove(vgroup)

                    # remove all faceit groups that were transferred from the auto bind objects. These will messup re-binding.
                    for grp in set(vg_utils.get_faceit_vertex_grps(obj)) - faceit_groups_per_obj:
                        false_assigned_faceit_group = obj.vertex_groups.get(grp)
                        obj.vertex_groups.remove(false_assigned_faceit_group)

        # for obj in transfer_to_objects:
        #     futils.clear_object_selection()
        #     futils.set_active_object(obj.name)

        #     bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        #     # smooth deform
        #     bpy.ops.object.vertex_group_clean(group_select_mode='ALL', limit=0.05)
        #     bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=.5, repeat=3)

        #     # normalize removes all wheights from the verts that are locked
        #     bpy.ops.object.vertex_group_clean(group_select_mode='ALL', limit=0.001)
        #     bpy.ops.object.vertex_group_normalize_all()

        bpy.ops.object.mode_set()

    def _auto_weight_selection_to_bones(self, auto_weight_objects, rig, bones, vgroup='ALL'):
        '''Bind a vertex selection to specific bones'''

        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set()
        futils.clear_object_selection()
        # select rig
        futils.set_active_object(rig.name)
        bpy.ops.object.mode_set(mode='POSE')
        # enable deform bones layer

        bpy.ops.pose.select_all(action='DESELECT')

        # select bones
        any_selected = False
        for bone in bones:
            pbone = rig.pose.bones.get(bone)
            if pbone:
                pbone.bone.select = True
                any_selected = True
            else:
                continue

        if not any_selected:
            self.report({'WARNING'}, 'Tongue bones do not exist. Regenerate the rig.')
            return

        bpy.ops.object.mode_set(mode='OBJECT')

        for obj in auto_weight_objects:

            # select object
            futils.clear_object_selection()

            futils.set_active_object(rig.name)
            futils.set_active_object(obj.name)

            if vgroup == 'ALL':
                vs = obj.data.vertices
            else:
                vs = vg_utils.get_verts_in_vgroup(obj, vgroup)

            if not vs:
                continue

            # Add Faceit_Armature mod
            # obj.modifiers
            futils.add_faceit_armature_modifier(obj, rig)

            # remove all weights of other bones that got weighted in autoweighting process

            vg_utils.remove_vgroups_from_verts(obj, vs=vs, filter_keep='faceit_tongue')

            vg_utils.remove_zero_weights_from_verts(obj)
            vg_utils.remove_unused_vertex_groups_thresh(obj)

            # select all verts in tongue grp
            mesh_utils.unselect_flush_vert_selection(obj)
            mesh_utils.select_vertices(obj, vs=vs)

            # go weightpaint
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

            use_mask = obj.data.use_paint_mask_vertex
            obj.data.use_paint_mask_vertex = True

            bpy.ops.paint.weight_from_bones(type='AUTOMATIC')
            # return not bind_problem, return_warning

            # smooth tongue deform
            bpy.ops.object.vertex_group_smooth(
                group_select_mode='BONE_SELECT', factor=.5, repeat=2, expand=1.5)

            # reset settings
            obj.data.use_paint_mask_vertex = use_mask

            bpy.ops.object.mode_set(mode='OBJECT')

    def _assign_secondary_weighting(self, faceit_vertex_groups, objects, rig):

        def overwrite_faceit_group(obj, faceit_vertex_group, new_grp=''):
            '''
            bind user defined vertices to respective bones with constant weight of 1 on all vertices
            @obj - the object holding the vertex group defined by user
            @faceit_vertex_group - the user defined groups holding all vertices that should be assigned to new group
            i.e. faceit_teeth
            @new_grp - the name of the newly assigned vertex group
            '''
            # get all vertices in the faceit group
            vs = vg_utils.get_verts_in_vgroup(obj, faceit_vertex_group)
            if not vs:
                return

            vg_utils.remove_all_weight(obj, vs)

            # assign new group weight or...
            if new_grp:
                if new_grp != 'rigid':
                    # indices needed for group assignment
                    vs = [v.index for v in vs]
                    vg_utils.assign_vertex_grp(obj, vs, new_grp)
                else:
                    pass

        eye_grps = [
            'faceit_left_eyeball',
            'faceit_right_eyeball',
            'faceit_left_eyes_other',
            'faceit_right_eyes_other'
        ]
        teeth_grps = [
            'faceit_upper_teeth',
            'faceit_lower_teeth'
        ]
        rigid_grps = [
            'faceit_rigid',
        ]

        tongue_grps = [
            'faceit_tongue',
        ]

        for vgroup in faceit_vertex_groups:

            secondary_objects = vg_utils.get_objects_with_vertex_group(vgroup, objects=objects, get_all=True)

            for obj in secondary_objects:

                new_grp = ''
                if vgroup in eye_grps:
                    new_grp = 'DEF_eye.L' if 'left' in vgroup else 'DEF_eye.R'

                if vgroup in teeth_grps:

                    if 'lower_teeth' in vgroup:
                        if rig.pose.bones.get('DEF-teeth.B'):
                            new_grp = 'DEF-teeth.B'
                        else:
                            self.report(
                                {'WARNING'},
                                'Lower Teeth bone "DEF-teeth.B" does not exist. Create the bone manually or specify Teeth Vertex Groups and regenerate the Rig.')
                            continue
                    if 'upper_teeth' in vgroup:
                        if rig.pose.bones.get('DEF-teeth.T'):
                            new_grp = 'DEF-teeth.T'
                        else:
                            self.report(
                                {'WARNING'},
                                'Uppper Teeth bone "DEF-teeth.T" does not exist. Create the bone manually or specify Teeth Vertex Groups and regenerate the Rig.')
                            continue

                if vgroup in rigid_grps:  # or vgroup in tongue_grps:
                    new_grp = 'rigid'

                if new_grp:
                    overwrite_faceit_group(obj, vgroup, new_grp)

                # ----------------------- BIND TONGUE ---------------------------

                if vgroup in tongue_grps:  # or vgroup in tongue_grps:

                    tongue_bones = [
                        'DEF-tongue',
                        'DEF-tongue.001',
                        'DEF-tongue.002'
                    ]

                    self._auto_weight_selection_to_bones(secondary_objects, rig, tongue_bones, 'faceit_tongue')


class FACEIT_OT_PairArmature(bpy.types.Operator):
    '''Pair the FaceitRig to the facial objects without generating weights'''
    bl_idname = 'faceit.pair_armature'
    bl_label = 'Pair Armature'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):

        face_objects = futils.get_faceit_objects_list()
        faceit_rig = futils.get_faceit_armature(force_original=True)
        if not faceit_rig:
            return{'CANCELLED'}

        for obj in face_objects:
            futils.add_faceit_armature_modifier(obj, faceit_rig)

        context.scene.faceit_weights_restorable = False

        return{'FINISHED'}


class FACEIT_OT_UnbindFacial(bpy.types.Operator):
    '''Unbind the FaceitRig from the facial objects'''
    bl_idname = 'faceit.unbind_facial'
    bl_label = 'Unbind'
    bl_options = {'UNDO', 'INTERNAL'}

    remove_deform_groups: bpy.props.BoolProperty(
        name='Remove Binding Groups',
        default=True,
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene

        rig = futils.get_faceit_armature()

        face_objects = futils.get_faceit_objects_list()

        for obj in face_objects:

            a_mod = futils.get_faceit_armature_modifier(obj)
            if a_mod:
                obj.modifiers.remove(a_mod)
                # remove all deform vert groups
            if self.remove_deform_groups:
                if rig:
                    vg_utils.remove_deform_vertex_grps(
                        obj, armature=rig)
                c_mod = obj.modifiers.get('Corrective_Smooth')
                if c_mod:
                    obj.modifiers.remove(c_mod)

        return{'FINISHED'}


class FACEIT_OT_CorrectiveSmooth(bpy.types.Operator):
    '''Add corrective smooth modifier to the active object'''

    bl_idname = 'faceit.smooth_correct'
    bl_label = 'Smooth Correct Modifier'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        if obj is not None:
            if context.mode == 'OBJECT' and obj.type == 'MESH':
                if not obj.modifiers.get('CorrectiveSmooth'):
                    return True

    def execute(self, context):
        obj = context.object
        mod = obj.modifiers.new(name='CorrectiveSmooth', type='CORRECTIVE_SMOOTH')
        mod.smooth_type = 'LENGTH_WEIGHTED'
        mod.iterations = 4
        mod.use_pin_boundary = True
        # subdiv modifiers need to be last

        # sub_mod = obj.modifiers.get('Subdivision')
        arm_mod = futils.get_faceit_armature_modifier(obj)
        if arm_mod and mod:
            safe_count = 100
            while obj.modifiers.find(mod.name) > (obj.modifiers.find(arm_mod.name) + 1):
                bpy.ops.object.modifier_move_up(modifier=mod.name)
                if safe_count <= 0:
                    break
                safe_count -= 1
        return{'FINISHED'}
