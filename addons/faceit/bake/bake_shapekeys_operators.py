import bpy
import numpy as np
from addon_utils import check
from bpy.props import BoolProperty, EnumProperty

from .. panels.draw_utils import draw_text_block


from ..core.detection_manager import get_expression_name_double_entries
from ..core.modifier_utils import add_faceit_armature_modifier, bind_valid_bake_modifiers, get_faceit_armature_modifier, populate_bake_modifier_items, reorder_armature_in_modifier_stack, restore_bake_modifiers, restore_modifier_order
from ..core.pose_utils import reset_pb
from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import shape_key_utils
from ..shape_keys.corrective_shape_keys_utils import (
    mute_corrective_shape_keys, reevaluate_corrective_shape_keys)


def get_load_action_items(self, context):
    items = [
        ('TEST', 'Test', 'Load the shape key test action'),
        ('NONE', 'None', 'Do not load any action'),
    ]
    if context.scene.faceit_mocap_action or context.scene.faceit_head_action or context.scene.faceit_eye_action:
        items.insert(1, ('MOCAP', 'Mocap', 'Load the last motion capture action'))
    return items


class FACEIT_OT_GenerateShapekeys(bpy.types.Operator):
    '''Bakes all deformation stored in the created expressions to shape keys on the registered objects'''
    bl_idname = 'faceit.generate_shapekeys'
    bl_label = 'Bake Shape Keys'
    bl_options = {'UNDO', 'INTERNAL'}

    modifier_action: EnumProperty(
        name="Modifier Action",
        items=(
            ('FACEIT', 'Keep Active', 'All bake modifiers will be preserved as is. Only remove the Faceit modifiers.'),
            ('HIDE', 'Hide', 'All bake modifiers will be hidden (Show Viewport disabled). Re-enable them individually after baking.'),
            ('REMOVE', 'Remove', 'All bake modifiers will be removed. Warning: modifier drivers might not be restored properly.'),
        ),
        # description="In order to avoid double deformation, the bake modifiers should be removed or hidden after baking the shape keys. All modifiers are restored upon Back to Rigging.",
        default='FACEIT'
    )
    load_action: EnumProperty(
        name="Load Action",
        items=get_load_action_items,
    )
    init_arkit_shape_list: BoolProperty(
        name='Initialize ARKit Shapes',
        default=False,
        description='Populate the ARKit target shapes automatically.',
    )
    init_a2f_shape_list: BoolProperty(
        name='Initialize Audio2Face Shapes',
        default=False,
        description='Populate the Audio2Face target shapes automatically.',
    )
    keep_faceit_rig_active: BoolProperty(
        name='Keep Faceit Rig Active',
        default=False,
        description='Keep the Bone Rig active after baking the shape keys. Activate this if you want to use the Faceit rig beyond generating shapes.',
    )
    disable_auto_keying: BoolProperty(
        name='Disable Auto Keying',
        description='Disable the Auto Keying functionality after baking (Re-enable when going back to rigging).',
        default=True,
    )
    bake_duplicate_option: EnumProperty(
        name="Bake Duplicate Option",
        items=(
            ('OVERWRITE', 'Overwrite',
                'Overwrite the existing shape keys when baking. Use this if you want to replace the existing shape keys.'),
            ('RENAME', 'Rename Existing',
                'Rename the existing shape key with an index as suffix. Use this if you want to keep the existing shape key, but use the new one as default mocap target.'),
            ('DUPLICATE', 'Create Duplicate',
             'Create a duplicate shape key with an index as suffix. Use this if you want to keep the existing shape key.'),
        ),
        default='OVERWRITE')

    # TODO
    # Regenerate mouthClose
    # Reconnect control rig
    # test all bake modifiers
    # hide specific modifiers?

    faceit_action_found = False
    expressions_generated = False
    arkit_expressions_found = False
    a2f_expressions_found = False
    faceit_original_rig = True
    auto_keying_enabled = False
    found_bake_modifiers = False
    some_objects_without_bake_modifiers = False
    shapes_already_exist = False

    @ classmethod
    def poll(cls, context):
        if context.scene.faceit_shapes_generated is False:
            if context.scene.faceit_face_objects:
                if futils.get_faceit_armature():
                    return context.scene.faceit_expression_list and 'overwrite_shape_action' in bpy.data.actions

    def invoke(self, context, event):
        self.disable_auto_keying = self.auto_keying_enabled = context.scene.tool_settings.use_keyframe_insert_auto
        faceit_objects = context.scene.faceit_face_objects
        rig = futils.get_faceit_armature()
        self.faceit_original_rig = bool(futils.get_faceit_armature(force_original=True))
        action = None
        if rig.animation_data:
            action = rig.animation_data.action
        if action:
            self.faceit_action_found = True
        expression_list = context.scene.faceit_expression_list
        if expression_list:
            self.expressions_generated = True
            # Check if there are ARKit expressions among the expression list.
            arkit_names = fdata.get_arkit_shape_data().keys()
            self.init_arkit_shape_list = self.arkit_expressions_found = any(
                [n.name in arkit_names for n in expression_list])
            # Check if there are Audio2Face expressions among the expression list.
            a2f_names = fdata.get_a2f_shape_data().keys()
            self.init_a2f_shape_list = self.a2f_expressions_found = any(
                [n.name in a2f_names for n in expression_list])
        for obj_item in faceit_objects:
            if obj_item.modifiers:
                if any((m.bake is True for m in obj_item.modifiers)):
                    self.found_bake_modifiers = True
                    continue
                self.some_objects_without_bake_modifiers = True
        shape_names = shape_key_utils.get_shape_key_names_from_objects()
        if shape_names:
            self.shapes_already_exist = any((n.name in shape_names for n in expression_list))
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        # layout.use_property_split = True
        # layout.use_property_decorate = False
        if not self.found_bake_modifiers:
            box = draw_text_block(
                context,
                layout,
                heading="Warning",
                heading_icon='ERROR',
                text='No active bake modifiers found on any of the registered objects. Please activate at least one bake modifier before baking.',
                in_operator=True,
            )
            # box.label(text='No active bake modifiers.')
        else:
            box = draw_text_block(
                context,
                layout,
                heading="Bake Modifier Action",
                heading_icon='MODIFIER_DATA',
                in_operator=True,
            )
            row = box.row()
            row.prop(self, 'modifier_action', expand=True)

        box = draw_text_block(
            context,
            layout,
            heading="Action",
            heading_icon='ACTION',
            in_operator=True,
        )
        row = box.row(align=True)
        row.prop(self, 'load_action', expand=True, icon='BLANK1')

        if self.arkit_expressions_found or self.a2f_expressions_found:
            box = draw_text_block(
                context,
                layout,
                heading="Target Shapes",
                heading_icon='SHAPEKEY_DATA',
                in_operator=True,
            )
            if self.arkit_expressions_found:
                row = box.row()
                row.prop(self, 'init_arkit_shape_list', icon='BLANK1')
            if self.a2f_expressions_found:
                row = box.row()
                row.prop(self, 'init_a2f_shape_list', icon='BLANK1')
        if self.shapes_already_exist:
            box = draw_text_block(
                context,
                layout,
                heading="Some Shapes Already Exist",
                heading_icon='ERROR',
                in_operator=True,
            )
            row = box.row()
            row.prop(self, 'bake_duplicate_option', expand=True, icon='BLANK1')
        if self.faceit_original_rig:
            box = draw_text_block(
                context,
                layout,
                heading="Rig Options",
                heading_icon='ARMATURE_DATA',
                in_operator=True,
            )
            row = box.row()
            row.prop(self, 'keep_faceit_rig_active', icon='BLANK1')  # icon='ARMATURE_DATA')
        if self.auto_keying_enabled:
            box = draw_text_block(
                context,
                layout,
                heading="Other",
                in_operator=True,
            )
            row = box.row()
            row.prop(self, 'disable_auto_keying', icon='RADIOBUT_OFF')

    def execute(self, context):
        state_dict = futils.save_scene_state(context)
        scene = context.scene
        if futils.get_object_mode_from_context_mode(context.mode) != 'OBJECT' and context.object is not None:
            bpy.ops.object.mode_set()
        # Hide these modifiers during baking.
        rig_obj = futils.get_faceit_armature()
        expression_list = scene.faceit_expression_list
        if not self.expressions_generated:
            self.report({'WARNING'}, 'No Expressions found. Please load Faceit Expressions in Animate Tab first.')
        if not self.faceit_action_found:
            self.report({'WARNING'}, 'No Action found on the Faceit Armature')
        bake_objects = futils.get_faceit_objects_list()
        # Double check if the bake modifiers are populated...
        populate_bake_modifier_items(bake_objects)
        bpy.ops.faceit.reset_expression_values()

        obj_settings = dict()
        if scene.faceit_use_corrective_shapes:
            reevaluate_corrective_shape_keys(expression_list, bake_objects)
        # hidden states of all objects
        futils.set_hidden_states(overwrite=True, objects=bake_objects, hide_value=False)
        save_frame = scene.frame_current
        scene.frame_set(0)
        dg = context.evaluated_depsgraph_get()
        for obj_item in scene.faceit_face_objects:
            obj = scene.objects.get(obj_item.name)
            _show_vp_drivers = []
            _mods = []
            # disable non bake modifiers
            for mod in obj.modifiers:
                mod_item = obj_item.modifiers.get(mod.name)
                if mod_item:
                    if not mod_item.bake:
                        if mod.show_viewport is True:
                            # Mute all show viewport drivers, enable after baking.
                            if obj.animation_data:
                                dp = f'modifiers["{mod.name}"].show_viewport'
                                dr = obj.animation_data.drivers.find(dp)
                                if dr:
                                    if dr.mute:
                                        continue
                                    _show_vp_drivers.append(dr.data_path)
                                    dr.mute = True
                            mod.show_viewport = False
                            _mods.append(mod.name)
            # Rebind surface deform / corrective smooth after hiding mods.
            bind_valid_bake_modifiers(obj, obj_item.modifiers)

            has_sk = shape_key_utils.has_shape_keys(obj)
            _has_corrective_sk = False
            if not has_sk:
                basis_shape = obj.shape_key_add(name='Basis')
                basis_shape.interpolation = 'KEY_LINEAR'
            else:
                obj.data.shape_keys.reference_key.name = 'Basis'
            obj_settings[obj] = {
                "mirror_x": obj.data.use_mirror_x,
                "modifiers": _mods,
                "drivers": _show_vp_drivers,
                "has_corrective_sk": _has_corrective_sk,
            }
            obj.data.use_mirror_x = False
            obj.show_only_shape_key = False
            dg.update()
            # without modifiers and shape keys
            basis_data = shape_key_utils.get_mesh_data(obj, evaluated=False)
            # with modifiers and shape keys
            eval_mesh_data = shape_key_utils.get_mesh_data(obj, dg)
            mat_rest = obj.matrix_world.copy()
            obj_settings[obj].update(
                {"basis_data": basis_data, "eval_data": eval_mesh_data, "matrix_world": mat_rest})
        # Apply the difference matrix (object transforms) to the evaluated mesh data (shape keys and modifiers applied) and bake it as a shape key.
        for expression in expression_list:
            scene.frame_set(expression.frame)
            for obj, settings in obj_settings.items():
                basis_data = settings["basis_data"]
                eval_mesh_data = settings["eval_data"]
                mat_rest = settings["matrix_world"]
                mat_pose = obj.matrix_world.copy()
                if self.shapes_already_exist:
                    if shape_key_utils.has_shape_keys(obj):
                        sk = obj.data.shape_keys.key_blocks.get(expression.name)
                        if sk:
                            if self.bake_duplicate_option == 'OVERWRITE':
                                obj.shape_key_remove(sk)
                            elif self.bake_duplicate_option == 'RENAME':
                                sk.name = get_expression_name_double_entries(sk.name, obj.data.shape_keys.key_blocks)
                # Get the evaluated mesh data (with modifiers and shape keys)
                exp_data = shape_key_utils.get_mesh_data(obj, dg)
                exp_data = basis_data + exp_data - eval_mesh_data
                # Apply the difference world matrix to the evaluated mesh data
                sk_data = shape_key_utils.apply_matrix_to_all_mesh_data(exp_data, mat_pose @ mat_rest.inverted())
                # Bake the mesh data into a shape key
                shape = obj.shape_key_add(name=expression.name)
                shape.data.foreach_set('co', sk_data.ravel())
        if all(x in expression_list.keys() for x in ['mouthClose', 'jawOpen']):
            for obj in bake_objects:
                mouthClose_sk = obj.data.shape_keys.key_blocks.get('mouthClose')
                jawOpen_sk = obj.data.shape_keys.key_blocks.get('jawOpen')
                if not mouthClose_sk or not jawOpen_sk:
                    continue
                vert_count = len(obj.data.vertices)
                mClose_sk_data = np.zeros(vert_count * 3, dtype=np.float32)
                mouthClose_sk.data.foreach_get('co', mClose_sk_data.ravel())

                jOpen_sk_data = np.zeros(vert_count * 3, dtype=np.float32)
                jawOpen_sk.data.foreach_get('co', jOpen_sk_data.ravel())

                basis_sk = mouthClose_sk.relative_key
                basis_sk_data = np.zeros(vert_count * 3, dtype=np.float32)
                basis_sk.data.foreach_get('co', basis_sk_data.ravel())

                new_sk_data = basis_sk_data + mClose_sk_data - jOpen_sk_data
                mouthClose_sk.data.foreach_set('co', new_sk_data.ravel())

        # ------------ MODIFIERS --------------
        # | - enable modifiers that have been enabled before.
        # | - hide corrective smooth
        for obj, settings in obj_settings.items():
            # stored_drivers = []
            for dr_dp in settings["drivers"]:
                obj.animation_data.drivers.find(dr_dp).mute = False
            for mod in settings["modifiers"]:
                obj.modifiers[mod].show_viewport = True
            obj.data.use_mirror_x = settings["mirror_x"]

            obj_item = scene.faceit_face_objects.get(obj.name)
            # remove only the Faceit armature modifier
            if not self.keep_faceit_rig_active:
                armature_mod = get_faceit_armature_modifier(obj)
                if armature_mod:
                    mod_item = obj_item.modifiers.get(armature_mod.name)
                    if mod_item.bake:
                        mod_item.recreate = True
                        obj.modifiers.remove(armature_mod)
            # remove / hide all bake modifiers
            for mod_item in obj_item.modifiers:
                if mod_item.bake:
                    mod = obj.modifiers.get(mod_item.name)
                    if mod:
                        if self.modifier_action == 'REMOVE':
                            if obj.animation_data:
                                # Store drivers to re-enable them upon back to rigging.
                                mod_drivers = [dr for dr in obj.animation_data.drivers
                                               if f'modifiers["{mod.name}"]' in dr.data_path]
                                for dr in mod_drivers:
                                    dr_item = mod_item.drivers.add()
                                    dr_item.data_path = dr.data_path
                                    dr_item.is_muted = True
                                    dr.mute = True
                                    # stored_drivers.append(copy_driver_data(dr))
                            print("remove modifier", mod.name)
                            mod_item.recreate = True
                            obj.modifiers.remove(mod)
                        elif self.modifier_action == 'HIDE':
                            if obj.animation_data:
                                dp = f'modifiers["{mod.name}"].show_viewport'
                                dr = obj.animation_data.drivers.find(dp)
                                if dr:
                                    dr_item = mod_item.drivers.add()
                                    dr_item.data_path = dr.data_path
                                    dr_item.is_muted = True
                                    dr.mute = True
                            print("hide modifier", mod.name)
                            mod.show_viewport = False
        # Mute corrective shape keys
        if scene.faceit_use_corrective_shapes:
            mute_corrective_shape_keys(expression_list, bake_objects)
        # Set Fake user before removing the action
        overwrite_action = bpy.data.actions.get('overwrite_shape_action')
        if overwrite_action:
            overwrite_action.use_fake_user = True
        shape_action = bpy.data.actions.get('faceit_shape_action')
        if shape_action:
            shape_action.use_fake_user = True
        if rig_obj.animation_data:
            rig_obj.animation_data.action = None
        # Don't reset the entire pose, instead just reset the relevant bones. (Get bones with animation data.)
        bones_to_reset = fdata.FACEIT_CTRL_BONES
        for fc in overwrite_action.fcurves:
            if fc.data_path.startswith('pose.bones["'):
                bone_name = fc.data_path.split('"')[1]
                if bone_name not in bones_to_reset:
                    bones_to_reset.append(bone_name)
        for bone_name in bones_to_reset:
            bone = rig_obj.pose.bones.get(bone_name)
            if bone:
                reset_pb(bone)
        scene.frame_current = save_frame
        scene.faceit_shapes_generated = True
        expression_sets = ''
        if self.init_arkit_shape_list and self.init_a2f_shape_list:
            expression_sets = 'ALL'
            scene.faceit_display_retarget_list = 'ARKIT'
        elif not self.init_arkit_shape_list and self.init_a2f_shape_list:
            expression_sets = 'A2F'
            scene.faceit_display_retarget_list = 'A2F'
        elif self.init_arkit_shape_list and not self.init_a2f_shape_list:
            expression_sets = 'ARKIT'
            scene.faceit_display_retarget_list = 'ARKIT'
        if expression_sets:
            bpy.ops.faceit.init_retargeting('EXEC_DEFAULT', expression_sets=expression_sets)
        if self.load_action == 'TEST':
            # load the test action
            bpy.ops.faceit.test_action()
        elif self.load_action == 'MOCAP':
            # Populate motion capture actions
            if scene.faceit_mocap_action:
                bpy.ops.faceit.populate_action(action_name=scene.faceit_mocap_action.name, set_mocap_action=False)
            if scene.faceit_head_action:
                bpy.ops.faceit.populate_head_action(action_name=scene.faceit_head_action.name, set_mocap_action=False)
            if scene.faceit_eye_action:
                bpy.ops.faceit.populate_eye_action(action_name=scene.faceit_eye_action.name, set_mocap_action=False)
        else:
            pass
        futils.restore_scene_state(context, state_dict)
        if self.disable_auto_keying:
            scene.tool_settings.use_keyframe_insert_auto = False
        lm_obj = bpy.data.objects.get('facial_landmarks')
        if lm_obj:
            lm_obj.hide_viewport = True
        if futils.get_object_mode_from_context_mode(context.mode) != 'OBJECT' and context.object != None:
            bpy.ops.object.mode_set()
        if self.faceit_original_rig and not self.keep_faceit_rig_active:
            rig_obj.hide_viewport = True
        return {'FINISHED'}


class FACEIT_OT_BackToRigging(bpy.types.Operator):
    '''Reset Faceit to Rigging and Posing functionality, removes the baked Shape Keys'''
    bl_idname = 'faceit.back_to_rigging'
    bl_label = 'Back to Rigging'
    bl_options = {'UNDO', 'INTERNAL'}

    keep_baked_expressions: bpy.props.BoolProperty(
        name='Keep Baked Expressions',
        description='Enable this if you want to keep the shape keys',
        default=False
    )

    @ classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.scene.faceit_face_objects  # and futils.get_faceit_armature()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'keep_baked_expressions', icon='SHAPEKEY_DATA')

    def execute(self, context):

        scene = context.scene
        if check(module_name="AddRoutes")[1]:
            scene.MOM_Items.clear()
        rig = futils.get_faceit_armature()
        futils.get_faceit_collection(force_access=True)
        if rig:
            futils.set_hide_obj(rig, False)
        else:
            self.report({'WARNING'}, 'The Faceit Armature can\'t be found.')
        # Clear the control rig drivers.
        c_rig = futils.get_faceit_control_armature()
        if c_rig:
            bpy.ops.faceit.remove_control_drivers('EXEC_DEFAULT', remove_all=False)
        # Remove the test action.
        bake_test_action = bpy.data.actions.get('faceit_bake_test_action')
        if bake_test_action:
            bpy.data.actions.remove(bake_test_action)

        faceit_objects = futils.get_faceit_objects_list()
        expression_list = scene.faceit_expression_list
        # reset expression values
        bpy.ops.faceit.reset_expression_values()
        for obj in faceit_objects:
            obj_item = scene.faceit_face_objects.get(obj.name)
            if not self.keep_baked_expressions:
                if shape_key_utils.has_shape_keys(obj):
                    for expression in expression_list:
                        sk = obj.data.shape_keys.key_blocks.get(expression.name)
                        if sk:
                            obj.shape_key_remove(sk)
            # Restore bake modifiers
            if obj_item.modifiers:
                restore_bake_modifiers(obj, obj_item.modifiers)
                restore_modifier_order(obj)
            else:
                mod = get_faceit_armature_modifier(obj, force_original=False)
                if mod:
                    mod.show_viewport = True
                elif rig is not None:
                    if futils.is_faceit_original_armature(rig):
                        add_faceit_armature_modifier(obj, rig, force_original=False)
                # Restore the modifier order
                reorder_armature_in_modifier_stack(obj)

        head_obj = scene.faceit_head_target_object
        if head_obj is not None:
            if head_obj.animation_data is not None:
                head_action = head_obj.animation_data.action
                if head_action is not None:
                    if head_action.name not in ('overwrite_shape_action', 'faceit_shape_action'):
                        context.scene.faceit_head_action = head_action
                        head_obj.animation_data.action = None
                        bpy.ops.faceit.reset_head_pose()
        # Remove shape key animation.
        bpy.ops.faceit.populate_action(remove_action=True, set_mocap_action=False)
        # Restore corrective shape key functionality
        if scene.faceit_use_corrective_shapes:
            reevaluate_corrective_shape_keys(expression_list, faceit_objects)
        futils.clear_object_selection()
        action = None
        if rig is not None:
            futils.set_active_object(rig.name)
            action = bpy.data.actions.get('overwrite_shape_action')
            if not action:
                action = bpy.data.actions.get('faceit_shape_action')
            if action:
                if not rig.animation_data:
                    rig.animation_data_create()

                rig.animation_data.action = action
            if action:
                scene.frame_start, scene.frame_end = (int(x) for x in futils.get_action_frame_range(action))
            elif not expression_list:
                self.report({'WARNING'}, 'The Expressions could not be found.')
        # Update frame
        scene.faceit_expression_list_index = scene.faceit_expression_list_index
        # Reset properties
        scene.tool_settings.use_keyframe_insert_auto = True
        scene.faceit_shapes_generated = False
        # clear orphans / drivers
        # bpy.ops.outliner.orphans_purge()
        # fc_dr_utils.clear_invalid_drivers()
        bpy.ops.faceit.load_bake_modifiers("EXEC_DEFAULT", object_target='ALL')
        # scene.frame_set(frame_current)

        return {'FINISHED'}
