import bpy
import numpy as np
from bpy.props import BoolProperty, EnumProperty, StringProperty

from ..core.modifier_utils import apply_modifier

from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import fc_dr_utils
from ..core import retarget_list_utils as rutils
from ..core import shape_key_utils as sk_utils


class FACEIT_OT_ClearShapeKeyAction(bpy.types.Operator):
    '''Apply Shape Keys to the active mesh'''
    bl_idname = 'faceit.clear_shape_key_action'
    bl_label = 'Clear Shape Key Action'
    bl_options = {'UNDO', 'INTERNAL'}

    obj_name: StringProperty(
        name="Object Name",
        default="",
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    def execute(self, context):
        objects = [context.scene.objects.get(self.obj_name)]
        if not objects:
            objects = futils.get_faceit_objects_list()
        for obj in objects:
            shape_keys = obj.data.shape_keys
            if shape_keys:
                if shape_keys.animation_data:
                    shape_keys.animation_data.action = None
                    item = context.scene.faceit_face_objects.get(obj.name)
                    if item:
                        item.warnings = item.warnings.strip('SHAPEKEYS,')
        return {'FINISHED'}


def get_shape_keys_apply_options(self, context):
    return (
        ('KEEP', "Keep", "Apply the current shape key values to the basis mesh. The applied shape keys will be set to 0.0."),
        ('DRIVEN', "Keep Driven", "Apply the current shape key values to the basis mesh. Remove the shape keys if they are not driven or corrective shapes"),
        ('REMOVE', "Remove", "Apply the current shape key values to the basis mesh and remove all shape keys, except corrective shapes."),
    )


class FACEIT_OT_ApplyShapeKeysToMesh(bpy.types.Operator):
    '''Apply Shape Keys to the active mesh'''
    bl_idname = 'faceit.apply_shape_keys_to_mesh'
    bl_label = 'Apply Shape Keys to Mesh'
    bl_options = {'UNDO', 'INTERNAL'}

    apply_option: EnumProperty(
        name="Apply Options",
        items=get_shape_keys_apply_options
    )
    obj_name: StringProperty(
        name="Object Name",
        default="",
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    strip_warning: BoolProperty(
        name="Strip Warning",
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    keep_corrective_shape_keys: BoolProperty(
        name="Keep Corrective Shape Keys",
        description="Keep corrective shape keys if apply option is set to REMOVE",
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    def invoke(self, context, event):
        obj = context.scene.objects.get(self.obj_name)
        if not obj:
            self.report({'ERROR'}, 'Please select an object')
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'apply_option', expand=True)

    def execute(self, context):
        state_dict = futils.save_scene_state(context)
        context.scene.tool_settings.use_keyframe_insert_auto = False

        if futils.get_object_mode_from_context_mode(context.mode) != 'OBJECT' and context.object is not None:
            bpy.ops.object.mode_set()

        obj = context.scene.objects.get(self.obj_name)
        futils.set_active_object(obj)

        shape_keys = obj.data.shape_keys
        if not shape_keys:
            # self.report({'INFO'}, 'No shape keys found')
            return {'CANCELLED'}
        driven_sk = []
        for sk in shape_keys.key_blocks[1:]:
            for dr in shape_keys.animation_data.drivers:
                if 'key_blocks["{}"].'.format(sk.name) in dr.data_path:
                    sk.mute = True
                    driven_sk.append(sk.name)

        bpy.ops.object.mode_set()
        obj.active_shape_key_index = 0
        apply_sk = obj.shape_key_add(from_mix=True)
        apply_sk.value = 1.0
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.reveal(select=False)
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.blend_from_shape(shape=apply_sk.name, add=True)
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.shape_key_remove(apply_sk)

        for sk in shape_keys.key_blocks[1:]:
            if sk.name.startswith('faceit_cc_') and self.keep_corrective_shape_keys:
                continue
            if self.apply_option == 'REMOVE':
                obj.shape_key_remove(sk)
                continue
            if sk.name in driven_sk:
                sk.mute = False
                continue
            if self.apply_option == 'DRIVEN':
                obj.shape_key_remove(sk)
            else:
                if sk.slider_min > 0:
                    sk.slider_min = 0
                if sk.slider_max < 0:
                    sk.slider_max = 0
                sk.value = 0
        if self.strip_warning:
            item = context.scene.faceit_face_objects[self.obj_name]
            if not obj.data.shape_keys:
                item.warnings = item.warnings.strip('SHAPEKEYS,')
            else:
                if all(sk.value == 0 for sk in obj.data.shape_keys.key_blocks[1:]):
                    item.warnings = item.warnings.strip('SHAPEKEYS,')
                else:
                    self.report({'WARNING'}, 'Some shape keys are not at 0.0')
        futils.restore_scene_state(context, state_dict)
        return {'FINISHED'}


class FACEIT_OT_GenerateTestAction(bpy.types.Operator):
    '''Generate a new Test Action to see all Shape Keys'''
    bl_idname = 'faceit.test_action'
    bl_label = 'Generate Test Action'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            expression_list = context.scene.faceit_expression_list
            all_shape_key_names = sk_utils.get_shape_key_names_from_objects()
            return any([x.name in all_shape_key_names for x in expression_list])

    def execute(self, context):
        print('Start Test Action...')

        scene = context.scene

        faceit_objects = futils.get_faceit_objects_list()

        test_action = bpy.data.actions.get('faceit_bake_test_action')

        if test_action:
            bpy.data.actions.remove(test_action)

        test_action = bpy.data.actions.new(name='faceit_bake_test_action')

        # shape_dict = fdata.get_arkit_shape_data()

        # shape_dict = {item['name']: item['index'] for item in shape_dict.values()}

        for obj in faceit_objects:
            # deselect all
            shape_keys = obj.data.shape_keys
            if not shape_keys:
                continue

            if not shape_keys.animation_data:
                shape_keys.animation_data_create()

            shape_keys.animation_data.action = test_action

            shape_keys = shape_keys.key_blocks

            # for expression_name, index in shape_dict.items():
            for i, item in enumerate(scene.faceit_expression_list):
                i += 1
                frame = i * 10
                # i = int(index) + 1
                sk = shape_keys.get(item.name)
                if not sk or sk.name == 'Basis':
                    continue
                if sk.name == 'mouthClose':
                    jaw_sk = shape_keys.get('jawOpen')
                    if jaw_sk:
                        jaw_sk.value = 0
                        jaw_sk.keyframe_insert(data_path='value', frame=frame - 9)
                        jaw_sk.keyframe_insert(data_path='value', frame=frame + 1)
                        jaw_sk.value = 1
                        jaw_sk.keyframe_insert(data_path='value', frame=frame)
                        jaw_sk.value = 0

                sk.value = 0
                sk.keyframe_insert(data_path='value', frame=frame - 9)
                sk.keyframe_insert(data_path='value', frame=frame + 1)
                sk.value = 1
                sk.keyframe_insert(data_path='value', frame=frame)
                sk.value = 0

        scene.frame_start = 1
        scene.frame_end = i * 10

        return {'FINISHED'}


class FACEIT_OT_SetShapeKeyRange(bpy.types.Operator):
    '''For baked shape keys... This allows to define a range for all shape key animation values.'''
    bl_idname = 'faceit.set_shape_key_range'
    bl_label = 'Set Range'
    bl_options = {'UNDO', 'REGISTER'}

    effect_objects: EnumProperty(
        name='Set Range for Objects',
        items=[
            ('ALL', 'Faceit Objects', 'All Objects registered in Faceit'),
            ('SELECTED', 'Selected Objects', 'Try to set range for all selected objects'),
            ('ACTIVE', 'Active Object', 'The Active Object'),
        ]
    )
    effect_shapes: EnumProperty(
        name='Set Range for all ARKit Target Shapes',
        items=[
            ('ARKIT', 'ARKIT Target Shapes', 'All ARKit Target Shapes. See Shapes panel in Mocap Workflow'),
            ('A2F', 'Audio2Face Target Shapes', 'All Audio2Face Target Shapes. See Shapes panel in Mocap Workflow'),
            ('FACEIT', 'All Target Shapes', 'Both ARKit and Audio2Face Target Shapes. See Shapes panel in Mocap Workflow'),
            ('ALL', 'All Shape Keys', 'All Shape Keys'),
            ('ACTIVE', 'Active Shape Key', 'Only selected shape key. Tries to find the shape on all objects or active object'),
        ]
    )

    @ classmethod
    def poll(cls, context):
        if context.mode in ('OBJECT', 'POSE'):
            return True

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='Object(s) to effect')
        row = layout.row()
        row.prop(self, 'effect_objects', expand=True,)
        row = layout.row()
        row.label(text='Shape Keys to effect')
        row = layout.row()
        row.prop(self, 'effect_shapes', expand=True,)

    def execute(self, context):
        scene = context.scene

        def set_shape_key_slider_range(sk):
            sk.slider_min = scene.faceit_shape_key_slider_min
            sk.slider_max = scene.faceit_shape_key_slider_max

        active_object = context.active_object
        faceit_objects = futils.get_faceit_objects_list()

        objects_to_effect = []
        shapes_to_effect = []

        if self.effect_objects == 'ALL':
            if not faceit_objects:
                self.report({'ERROR'}, 'Please register the character geometry in the Setup panel.')
                return {'CANCELLED'}
            objects_to_effect.extend(faceit_objects)
        elif self.effect_objects == 'SELECTED':
            if not context.selected_objects:
                self.report({'ERROR'}, 'Select an Object first')
                return {'CANCELLED'}

            objects_to_effect.extend([obj for obj in context.selected_objects if obj.type == 'MESH'])
        elif self.effect_objects == 'ACTIVE':
            if not active_object:
                self.report({'ERROR'}, 'Select an Object first')
                return {'CANCELLED'}
            objects_to_effect.append(active_object)

        if self.effect_shapes == 'ACTIVE':
            active_key = active_object.active_shape_key
            if not active_key:
                self.report({'ERROR'}, 'Select a Shape Key in the properties panel first')
                return {'CANCELLED'}
            shapes_to_effect.append(active_key.name)
        if self.effect_shapes in ('FACEIT', 'ARKIT'):
            shapes_to_effect.extend(rutils.get_all_set_target_shapes(scene.faceit_arkit_retarget_shapes))
        if self.effect_shapes in ('FACEIT', 'A2F'):
            shapes_to_effect.extend(rutils.get_all_set_target_shapes(scene.faceit_a2f_retarget_shapes))
        if self.effect_shapes == 'ALL':
            # shapes_to_effect.append([sk.name for sk in obj.data.shape_keys.key_blocks for obj in objects_to_effect])
            for obj in objects_to_effect:
                if not sk_utils.has_shape_keys(obj):
                    continue
                shape_keys = obj.data.shape_keys.key_blocks
                # for sk in shape_keys:
                shapes_to_effect.extend([sk.name for sk in shape_keys if sk.name != 'Basis'])

        if not objects_to_effect:
            self.report({'ERROR'}, 'No objects found to effect')
            return {'CANCELLED'}

        if not shapes_to_effect:
            self.report({'ERROR'}, 'No shapes found to effect')
            return {'CANCELLED'}

        effect_any = False
        for obj in objects_to_effect:
            if not sk_utils.has_shape_keys(obj):
                continue

            shape_keys = obj.data.shape_keys.key_blocks
            for shape_name in shapes_to_effect:
                # if obj.data.shape_keys.key_blocks.find()

                if shape_keys.find(shape_name) != -1:
                    set_shape_key_slider_range(shape_keys[shape_name])
                    effect_any = True
                else:
                    self.report({'WARNING'}, 'Shape Key {} not found for object {}'.format(
                        shape_name, obj.name))

        if effect_any:
            self.report({'INFO'}, 'Succesfully set new slider ranges')
        else:
            self.report({'ERROR'}, 'No Shape Keys effected, because they were not found on specified object(s)')
            return {'CANCELLED'}

        # Update Control rig
        # if scene.faceit_control_rig_connected:
        #     if futils.get_faceit_control_armature():
        #         bpy.ops.faceit.setup_control_drivers()

        # update all shape keys...
        for obj in faceit_objects:
            if sk_utils.has_shape_keys(obj):
                shape_keys = obj.data.shape_keys.key_blocks

                for sk in shape_keys:
                    sk.value = sk.value

        # update UI...
        for a in context.screen.areas:
            if a.type == 'PROPERTIES':
                a.tag_redraw()

        return {'FINISHED'}


class FACEIT_OT_ReorderKeys(bpy.types.Operator):
    '''Reorder Shape Key Indices to the specified order '''
    bl_idname = 'faceit.reorder_keys'
    bl_label = 'Reorder Shapekeys'
    bl_options = {'UNDO', 'INTERNAL'}

    order: bpy.props.EnumProperty(
        name='New Order',
        items=(
            ('ARKIT', 'ARKit', 'ARKit Order'),
            ('FACECAP', 'Face Cap', 'Face Cap Order'),
            ('EPIC', 'Live Link Face', 'Live Link Face App Order'),
        ),
        default='ARKIT',
    )

    keep_motion: bpy.props.BoolProperty(
        name='Keep Motion Applied',
        default=True,
        options={'HIDDEN', }
    )

    process_objects: StringProperty(
        name='Objects to process',
        default='',
        options={'SKIP_SAVE', 'HIDDEN'},

    )

    @ classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return True

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        scene = context.scene

        if self.order == 'ARKIT':
            shape_dict = fdata.get_arkit_shape_data()
        elif self.order == 'FACECAP':
            shape_dict = fdata.get_face_cap_shape_data()
        elif self.order == 'EPIC':
            shape_dict = fdata.get_epic_shape_data()

        shapes_init = rutils.eval_target_shapes(scene.faceit_arkit_retarget_shapes)

        arkit_order_list = []

        target_shapes_dict = rutils.get_target_shapes_dict(scene.faceit_arkit_retarget_shapes)

        i = 0
        for arkit_name, data in shape_dict.items():
            if data['index'] == i:
                i += 1
                if shapes_init:
                    target_shapes = target_shapes_dict.get(arkit_name)
                    if target_shapes:
                        arkit_order_list.append(target_shapes[0])
                        continue
                # else:
                self.report(
                    {'WARNING'},
                    'Could not find a target shape for {}. The order might not be exact.'.format(arkit_name))
                arkit_order_list.append(arkit_name)

        objects = []
        if self.process_objects:
            for obj_name in self.process_objects.split(','):
                obj = futils.get_object(obj_name)
                if obj:
                    objects.append(obj)

        else:
            objects = futils.get_faceit_objects_list()

        reordered = False
        order_exists = False

        for obj in objects:

            if not sk_utils.has_shape_keys(obj):
                continue

            action_to_keep = None
            if self.keep_motion and action_to_keep is None:
                if obj.data.shape_keys.animation_data:
                    action_to_keep = obj.data.shape_keys.animation_data.action

            # Store Shape Keys
            sk_data_dict = sk_utils.store_shape_keys(obj)

            sk_utils.remove_all_sk_apply_basis(obj, apply_basis=True)

            # Apply Shape Keys
            sk_utils.apply_stored_shape_keys(obj, sk_data_dict, new_order_list=arkit_order_list)

            shape_keys = obj.data.shape_keys

            if action_to_keep:
                if not shape_keys.animation_data:
                    shape_keys.animation_data_create()
                shape_keys.animation_data.action = action_to_keep

            reordered = True

        if order_exists:
            self.report({'INFO'}, 'Order already applied for all objects')
            return {'CANCELLED'}

        if not reordered:
            self.report({'WARNING'}, 'Failed! Did you create Shapekeys? Did you register the Objects?')
            return {'CANCELLED'}

        return {'FINISHED'}


def isolate_shape_key(obj, sk_name):
    for sk in obj.data.shape_keys.key_blocks:
        if sk.name == sk_name:
            sk.value = 1
        else:
            sk.value = 0


def _apply_modifier_to_mesh_with_shape_keys(context, obj, mod_name):
    ''' Applies a modifier and keeps the shape keys
    @obj: the object with modifier and shape keys
    @mod_name: the name of the modifier
    '''

    # Copy Object
    scene = context.scene

    dup_obj = futils.duplicate_obj(obj, link=True)

    # Remove all shape keys and apply mod on object.
    if futils.get_object_mode_from_context_mode(context.mode) != 'OBJECT' and context.object != None:
        bpy.ops.object.mode_set()
    futils.clear_object_selection()
    futils.set_active_object(obj.name)

    # obj.shape_key_clear()
    sk_utils.remove_all_sk_apply_basis(obj, apply_basis=True)

    apply_modifier(mod_name)

    shape_data = {}

    # Make another duplicate and apply shape keys
    dup_shape_keys = dup_obj.data.shape_keys.key_blocks

    relative_keys_dict = {}

    for sk in dup_shape_keys:

        if sk.name == 'Basis':
            continue

        temp_dup_obj = futils.duplicate_obj(dup_obj)

        scene.collection.objects.link(temp_dup_obj)

        rel_key = getattr(sk, 'relative_key', None)
        rel_key_name = getattr(rel_key, 'name', None)

        relative_keys_dict[sk.name] = rel_key_name

        stored_drivers = []
        if dup_obj.data.shape_keys.animation_data:
            for dr in dup_obj.data.shape_keys.animation_data.drivers:
                if 'key_blocks["{}"].'.format(sk.name) in dr.data_path:
                    stored_drivers.append(fc_dr_utils.copy_driver_data(dr))

        shape_data[temp_dup_obj.name] = {
            'name': sk.name,
            'value': sk.value,
            'mute': sk.mute,
            'relative_key': sk.relative_key.name,
            'slider_min': sk.slider_min,
            'slider_max': sk.slider_max,
            'vertex_group': sk.vertex_group,
            'interpolation': sk.interpolation,
            'drivers': stored_drivers,
        }

    for temp_dup_obj_name, sk_props in shape_data.items():

        temp_dup_obj = futils.get_object(temp_dup_obj_name)
        if temp_dup_obj:

            futils.clear_object_selection()
            futils.set_active_object(temp_dup_obj)

            isolate_shape_key(temp_dup_obj, sk_props['name'])

            sk_utils.apply_all_shape_keys(temp_dup_obj)

            apply_modifier(mod_name)

            futils.set_active_object(obj.name)
            bpy.ops.object.join_shapes()
            if not obj.data.shape_keys:
                print("found no shape keys, wth")
                continue

            new_sk = obj.data.shape_keys.key_blocks[-1]
            new_sk.name = sk_props['name']
            new_sk.slider_max = sk_props['slider_max']
            new_sk.slider_min = sk_props['slider_min']
            new_sk.value = sk_props['value']
            new_sk.mute = sk_props['mute']
            new_sk.vertex_group = sk_props['vertex_group']
            new_sk.interpolation = sk_props['interpolation']

            stored_drivers = sk_props.get('drivers')
            if stored_drivers:

                for sk_driver_dict in stored_drivers:

                    # Value will be replaced in populate_driver_data/populate_fcurve
                    dr = new_sk.driver_add('value', -1)
                    fc_dr_utils.populate_driver_data(sk_driver_dict, dr)

            bpy.data.objects.remove(temp_dup_obj)

    if sk_utils.has_shape_keys(obj):
        for sk in obj.data.shape_keys.key_blocks:
            rel_key_name = relative_keys_dict.get(sk.name, 'Basis')
            if rel_key_name:
                rel_key = obj.data.shape_keys.key_blocks.get(rel_key_name)
                if rel_key:
                    sk.relative_key = rel_key

    bpy.data.objects.remove(dup_obj)


def get_modifiers_on_object(self, context):
    global mods
    mods = []

    if context is None:
        return mods

    if self.obj_name:
        obj = context.scene.objects.get(self.obj_name)
    else:
        obj = context.object
    if obj:
        mod_names = []
        # for mod in obj.modifiers:
        mod_names.extend([mod.name for mod in obj.modifiers])

        for i, name in enumerate(mod_names):
            mods.append((name, name, name, i))
    else:
        print('no shapes found --> add None')
        mods.append(("None", "None", "None"))

    return mods


class FACEIT_OT_ApplyModifierObjectWithShapeKeys(bpy.types.Operator):
    '''Applies a modifier on an object with Shape Keys'''
    bl_idname = 'faceit.apply_modifier_object_with_shape_keys'
    bl_label = 'Apply Modifier (with Shape Keys)'
    bl_options = {'UNDO', 'INTERNAL'}

    type: EnumProperty(
        name='Modifier Name',
        items=get_modifiers_on_object,
        description='The name of the modifier to remove'
    )

    disable_other_mods: BoolProperty(
        name='Disable other Modifiers',
        description='Disables other modifiers during operation.',
        default=True
    )
    obj_name: StringProperty(
        name='Object Name',
        default="",
        description="The name of the object to apply the modifier on",
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    check_warnings: BoolProperty(
        name="Check Warnings",
        default=False,
        options={'SKIP_SAVE'}
    )

    @classmethod
    def poll(cls, context):
        if context.scene.faceit_workspace.active_tab == 'SETUP':
            return True
        if context.mode == 'OBJECT':
            obj = context.object
            if obj:
                if obj.type == 'MESH' and len(obj.modifiers) > 0:
                    return True

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        if self.obj_name:
            obj = context.scene.objects.get(self.obj_name)
        else:
            obj = context.object
        if not obj:
            self.report({'ERROR'}, 'Select an object')
            return {'CANCELLED'}

        mod_name = self.type
        if mod_name:
            if sk_utils.has_shape_keys(obj):
                mod_dict = {}
                if self.disable_other_mods:
                    for mod in obj.modifiers:
                        if mod.show_viewport:
                            if mod.name != self.type:
                                mod_dict[mod.name] = mod.show_viewport
                                mod.show_viewport = False

                if obj.modifiers.get(mod_name):
                    _apply_modifier_to_mesh_with_shape_keys(context, obj, mod_name)
                if mod_dict:
                    for mod, show in mod_dict.items():
                        mod = obj.modifiers.get(mod)
                        mod.show_viewport = show
            else:
                apply_modifier(mod_name)
        if self.check_warnings:
            bpy.ops.faceit.face_object_warning_check('EXEC_DEFAULT', item_name='ALL')
        return {'FINISHED'}
