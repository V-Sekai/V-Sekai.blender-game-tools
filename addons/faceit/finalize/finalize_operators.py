import bpy
from bpy.props import BoolProperty, EnumProperty

from ..core import shape_key_utils
from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils


class FACEIT_OT_CleanUpObjects(bpy.types.Operator):
    '''Clean up all traces of the Faceit Rigging process for faceit objects.'''
    bl_idname = 'faceit.cleanup_objects'
    bl_label = 'Clean Up Objects'
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    operate_scope: EnumProperty(
        name='Clean Scope',
        items=(
            ('ALL', 'Blend File', 'Blend File'),
            ('FACEIT', 'Faceit Objects', 'Registered Objects'),
            ('SELECTED', 'Selected Objects', 'Selected Objects in Scene'),
        ),
        default='SELECTED',
        options={'SKIP_SAVE', },
    )

    remove_faceit_armature_modifier: BoolProperty(
        name='Remove Faceit Modifier',
        description='.',
        default=True,
        options={'SKIP_SAVE', }
    )
    remove_faceit_bind_weights: BoolProperty(
        name='Remove Bind Weights',
        description='.',
        default=True,
        options={'SKIP_SAVE', }
    )
    remove_faceit_vertex_groups: BoolProperty(
        name='Remove Registered Vertex Groups',
        description='(faceit_main, faceit_left_eyeball, ....)',
        default=True,
        options={'SKIP_SAVE', }
    )

    remove_faceit_corrective_shapes: BoolProperty(
        name='Remove Corrective Shape Keys',
        description='Remove the Corrective Shape Keys ("faceit_cc_[...]")',
        default=True,
        options={'SKIP_SAVE', }
    )

    remove_from_registration: BoolProperty(
        name='Remove Object from Setup',
        description='Remove the object from setup registration list',
        default=True,
        options={'SKIP_SAVE', }
    )

    @ classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        print(self.__annotations__)

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text=' --- WARNING! --- ')
        row = layout.row()
        row.label(text=' --- This Operation is destructive! --- ')

        row = layout.row()
        row.label(text='Choose Operator Scope')
        row = layout.row()
        row.prop(self, 'operate_scope', expand=True)
        row = layout.row()
        row.label(text='OPTIONS')
        row = layout.row()
        row.prop(self, 'remove_faceit_armature_modifier')
        row = layout.row()
        row.prop(self, 'remove_faceit_vertex_groups')
        row = layout.row()
        row.prop(self, 'remove_faceit_bind_weights')
        row = layout.row()
        row.prop(self, 'remove_faceit_corrective_shapes')
        row = layout.row()
        row.prop(self, 'remove_from_registration')

    def execute(self, context):
        scene = context.scene

        scope = self.operate_scope
        if scope == 'ALL':
            op_objects = bpy.data.objects
        elif scope == 'FACEIT':
            op_objects = futils.get_faceit_objects_list()
        elif scope == 'SELECTED':
            if context.selected_objects:
                op_objects = context.selected_objects
            else:
                self.report({'WARNING'}, 'You need to select at least one object in this scope.')
                return{'CANCELLED'}

        rig = futils.get_faceit_armature()
        deform_groups = vg_utils.get_deform_bones_from_armature(armature_obj=rig)

        sk_removed = []

        for obj in op_objects:

            if obj.type != 'MESH':
                continue

            if self.remove_from_registration:
                futils.remove_item_from_collection_prop(scene.faceit_face_objects, obj)

            if self.remove_faceit_armature_modifier:
                arm_mod = futils.get_faceit_armature_modifier(obj)
                if arm_mod:
                    obj.modifiers.remove(arm_mod)

            if self.remove_faceit_bind_weights:
                if not obj.vertex_groups:
                    pass
                else:
                    for grp in obj.vertex_groups:
                        if not grp.lock_weight:
                            if grp.name in deform_groups:
                                obj.vertex_groups.remove(grp)

            if self.remove_faceit_vertex_groups:
                vg_utils.remove_faceit_vertex_grps(obj)

            if self.remove_faceit_corrective_shapes:
                sk_prefix = 'faceit_cc_'

                if shape_key_utils.has_shape_keys(obj):

                    for sk in obj.data.shape_keys.key_blocks:
                        if sk.name.startswith(sk_prefix):
                            sk_removed.append(sk.name.split(sk_prefix)[1])
                            obj.shape_key_remove(sk)

                    if len(obj.data.shape_keys.key_blocks) == 1:
                        obj.shape_key_clear()

        if self.remove_faceit_corrective_shapes:

            all_sk = shape_key_utils.get_shape_key_names_from_objects()

            exp_list = scene.faceit_expression_list
            for sk in sk_removed:
                if sk in all_sk:
                    # There is still a corrective sk on another object
                    continue
                else:
                    exp = exp_list.get(sk)
                    exp.corr_shape_key = False

            # Remove the corrective sk action if all sk removed
            if not any([sk.startswith('faceit_cc') for sk in all_sk]):
                action = bpy.data.actions.get('faceit_corrective_shape_keys')
                if action:
                    bpy.data.actions.remove(action)

        return{'FINISHED'}


class FACEIT_OT_CleanUpScene(bpy.types.Operator):
    '''Clean up all traces of the Faceit Rigging process in the scene and other data.'''
    bl_idname = 'faceit.cleanup_scene'
    bl_label = 'Clean Up All'
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    remove_faceit_collection: BoolProperty(
        name='Remove Faceit Collection',
        description='Removes the Faceit Collection and all contained Objects',
        default=True,
    )

    purge_scene: BoolProperty(
        name='Remove Unused Data blocks',
        description='This will remove all kinds of unused data in the blendfile.',
        default=True
    )

    reset_faceit_properties: BoolProperty(
        name='Reset Properties',
        description='Reset all Faceit Properties to defaults',
        default=True
    )

    keep_objects_registered: BoolProperty(
        name='Keep Objects Registered',
        description='If this is False, the operator will reset the Setup panel. You won\'t  be able to use the Control Rig or Retargeting Features.',
        default=False)

    remove_faceit_actions: BoolProperty(
        name='Remove Faceit Actions',
        description='Remove the Faceit actions.',
        default=True)

    @ classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text=' --- WARNING! --- ')
        row = layout.row()
        row.label(text=' --- This Operation is destructive! --- ')
        row = layout.row()

        row = layout.row()
        row.label(text='OPTIONS')

        row = layout.row()
        row.prop(self, 'keep_objects_registered')
        row = layout.row()
        row.prop(self, 'purge_scene')

    def execute(self, context):
        scene = context.scene

        rig = futils.get_faceit_armature()

        bpy.ops.object.mode_set()

        if self.remove_faceit_collection:

            crig = futils.get_faceit_control_armature()
            if crig:
                try:
                    bpy.ops.faceit.remove_control_drivers()
                except:
                    pass
                bpy.data.objects.remove(crig, do_unlink=True)

            fcoll = futils.get_faceit_collection(force_access=False, create=False)
            if fcoll:
                for obj in fcoll.objects:
                    bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.collections.remove(fcoll)
            lm_obj = bpy.data.objects.get('facial_landmarks')
            if lm_obj:
                bpy.data.objects.remove(lm_obj, do_unlink=True)
            rig = futils.get_faceit_armature()
            if rig:
                bpy.data.objects.remove(rig, do_unlink=True)

        if self.keep_objects_registered:
            bpy.ops.faceit.cleanup_objects('EXEC_DEFAULT', operate_scope='ALL', remove_from_registration=False)
        else:
            bpy.ops.faceit.cleanup_objects('EXEC_DEFAULT', operate_scope='ALL')
            scene.faceit_face_objects.clear()
            scene.faceit_face_index = 0

        if self.remove_faceit_actions:
            action_names = ['faceit_bake_test_action', 'faceit_shape_action', 'overwrite_shape_action']
            for a in action_names:
                a = bpy.data.actions.get(a)
                if a:
                    bpy.data.actions.remove(a)

        if self.reset_faceit_properties:
            scene.faceit_vgroup_assign_method = 'OVERWRITE'
            scene.faceit_retargeting_naming_scheme = 'ARKIT'
            scene.faceit_armature = None
            scene.faceit_use_rigify_armature = False
            scene.faceit_use_corrective_shapes = True
            scene.faceit_shapes_generated = False
            scene.faceit_weights_restorable = False
            scene.faceit_expressions_restorable = False
            scene.faceit_asymmetric = False
            scene.faceit_control_armature = None
            scene.faceit_retarget_shapes.clear()
            scene.faceit_use_auto_mirror_x = True
            scene.faceit_try_mirror_corrective_shapes = True
            scene.faceit_try_mirror_corrective_shapes = True
            scene.faceit_sync_shapes_index = False
            scene.faceit_show_warnings = False
            scene.faceit_show_crig_regions = False
            scene.faceit_shape_key_utils_expand_ui = False
            scene.faceit_shape_key_slider_max = 1.0
            scene.faceit_shape_key_slider_min = 0.0
            scene.faceit_shape_key_mirror_use_topology = False
            scene.faceit_shape_key_lock = False
            scene.faceit_retarget_shapes_index = 0
            scene.faceit_expression_list_index = 0
            scene.faceit_expression_list.clear()
            # FBX PropertyGroup
            scene.faceit_retarget_fbx_mapping.mapping_target = 'FACEIT'
            scene.faceit_retarget_fbx_mapping.mapping_source = 'OBJECT'
            scene.faceit_retarget_fbx_mapping.source_obj = None
            scene.faceit_retarget_fbx_mapping.target_obj = None
            scene.faceit_retarget_fbx_mapping.mapping_list.clear()
            scene.faceit_retarget_fbx_mapping.source_action = None
            scene.faceit_retarget_fbx_mapping.expand_ui = False

            scene.faceit_record_face_cap = False
            scene.faceit_other_utilities_expand_ui = False
            scene.faceit_mocap_target_head = ''
            scene.faceit_mocap_target_eye_r = ''
            scene.faceit_mocap_target_eye_l = ''
            # Mocap Motion Types
            scene.faceit_mocap_motion_types.blendshapes_target = True
            scene.faceit_mocap_motion_types.head_target_rotation = False
            scene.faceit_mocap_motion_types.head_target_location = False
            scene.faceit_mocap_motion_types.eye_target_rotation = False
            scene.faceit_mocap_motion_types.expand = False

            scene.faceit_mocap_general_expand_ui = False
            scene.faceit_mocap_action_expand_ui = False
            scene.faceit_expression_options_expand_ui = True
            scene.faceit_expression_init_expand_ui = True
            scene.faceit_mocap_action = None
            # Face Regions
            scene.faceit_face_regions.eyes = True
            scene.faceit_face_regions.brows = True
            scene.faceit_face_regions.cheeks = True
            scene.faceit_face_regions.nose = True
            scene.faceit_face_regions.mouth = True
            scene.faceit_face_regions.tongue = True
            scene.faceit_face_regions.other = True

            # Mocap Engines Property
            scene.faceit_face_cap_mocap_settings.filename = ''
            scene.faceit_face_cap_mocap_settings.frame_start = 0
            scene.faceit_face_cap_mocap_settings.master_expanded = False
            scene.faceit_face_cap_mocap_settings.file_import_expanded = False
            scene.faceit_face_cap_mocap_settings.live_mode_expanded = False
            scene.faceit_face_cap_mocap_settings.mocap_engine = ''
            scene.faceit_face_cap_mocap_settings.indices_order = ''
            scene.faceit_face_cap_mocap_settings.load_to_new_action = False

            scene.faceit_epic_mocap_settings.filename = ''
            scene.faceit_epic_mocap_settings.frame_start = 0
            scene.faceit_epic_mocap_settings.master_expanded = False
            scene.faceit_epic_mocap_settings.file_import_expanded = False
            scene.faceit_epic_mocap_settings.live_mode_expanded = False
            scene.faceit_epic_mocap_settings.mocap_engine = ''
            scene.faceit_epic_mocap_settings.indices_order = ''
            scene.faceit_epic_mocap_settings.load_to_new_action = False

            scene.faceit_finalize_utils_expand_ui = False

        if self.purge_scene:
            # futils.purge_file()
            bpy.ops.outliner.orphans_purge()

        return{'FINISHED'}
