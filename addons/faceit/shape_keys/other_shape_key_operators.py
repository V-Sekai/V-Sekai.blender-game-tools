import bpy
import numpy as np
from bpy.props import BoolProperty, EnumProperty, StringProperty

from ..core import fc_dr_utils
from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..retargeting import retarget_list_utils as rutils


class FACEIT_OT_GenerateTestAction(bpy.types.Operator):
    '''Generate a new Test Action to see all Shape Keys'''
    bl_idname = 'faceit.test_action'
    bl_label = 'Generate Test Action'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(self, context):
        if context.mode == 'OBJECT':
            expression_list = context.scene.faceit_expression_list
            all_shape_key_names = sk_utils.get_shape_key_names_from_objects()
            return any([x.name in all_shape_key_names for x in expression_list])

    def execute(self, context):
        print('Start Test Action...')

        scene = context.scene

        face_objects = futils.get_faceit_objects_list()

        test_action = bpy.data.actions.get('faceit_bake_test_action')

        if test_action:
            bpy.data.actions.remove(test_action)

        test_action = bpy.data.actions.new(name='faceit_bake_test_action')

        # shape_dict = fdata.get_arkit_shape_data()

        # shape_dict = {item['name']: item['index'] for item in shape_dict.values()}

        for obj in face_objects:
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
                # i = int(index) + 1
                sk = shape_keys.get(item.name)
                if not sk or sk.name == 'Basis':
                    continue

                frame = i * 10

                sk.value = 0
                sk.keyframe_insert(data_path='value', frame=frame - 9)
                sk.keyframe_insert(data_path='value', frame=frame + 1)
                sk.value = 1
                sk.keyframe_insert(data_path='value', frame=frame)
                sk.value = 0

        scene.frame_start = 1
        scene.frame_end = i * 10

        return{'FINISHED'}


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
            ('FACEIT', 'ARKIT Target Shapes', 'All ARKit Target Shapes. See ARKIT Shapes panel in Mocap Workflow'),
            ('ALL', 'All Shape Keys', 'All Shape Keys'),
            ('ACTIVE', 'Active Shape Key', 'Only selected shape key. Tries to find the shape on all objects or active object'),
        ]
    )

    @ classmethod
    def poll(self, context):
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
                return{'CANCELLED'}
            objects_to_effect.extend(faceit_objects)
        elif self.effect_objects == 'SELECTED':
            if not context.selected_objects:
                self.report({'ERROR'}, 'Select an Object first')
                return{'CANCELLED'}

            objects_to_effect.extend([obj for obj in context.selected_objects if obj.type == 'MESH'])
        elif self.effect_objects == 'ACTIVE':
            if not active_object:
                self.report({'ERROR'}, 'Select an Object first')
                return{'CANCELLED'}
            objects_to_effect.append(active_object)

        if self.effect_shapes == 'ACTIVE':
            active_key = active_object.active_shape_key
            if not active_key:
                self.report({'ERROR'}, 'Select a Shape Key in the properties panel first')
                return{'CANCELLED'}
            shapes_to_effect.append(active_key.name)
        if self.effect_shapes == 'FACEIT':
            shapes_to_effect.extend(rutils.get_all_set_target_shapes(scene.faceit_retarget_shapes))
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
            return{'CANCELLED'}

        if not shapes_to_effect:
            self.report({'ERROR'}, 'No shapes found to effect')
            return{'CANCELLED'}

        print(shapes_to_effect)
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
            return{'CANCELLED'}

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

        return{'FINISHED'}


class FACEIT_OT_TransferShapeKeys(bpy.types.Operator):
    '''For Rigged Characters... Transfer all Shape Keys from selected to active.'''
    bl_idname = 'faceit.transfer_shape_keys'
    bl_label = 'Transfer Shape Keys'
    bl_options = {'UNDO'}

    @ classmethod
    def poll(self, context):
        if context.mode == 'OBJECT':
            if len(context.selected_objects) == 2:
                return True

    def execute(self, context):
        scene = context.scene

        def store_shape_keys(obj):
            ''' Store all shapekeys data in numpy arrays for @obj'''
            vert_count = len(obj.data.vertices)
            sk_dict = {}
            for sk in obj.data.shape_keys.key_blocks[1:]:
                # numpy array with shapekey data
                sk_data = np.zeros(vert_count*3, dtype=np.float32)
                sk.data.foreach_get('co', sk_data.ravel())

                sk_dict[sk.name] = sk_data
            return sk_dict

        def apply_stored_shape_keys(obj, sk_dict):
            ''' Apply the saved shapekey data from @sk_dict to objects shapekeys in new order from @export_order_dict '''
            # The new index for the shapekey with name shapekey_name
            for shapekey_name, sk_data in sk_dict.items():
                # the new shapekey
                new_sk = obj.shape_key_add(name=shapekey_name)
                new_sk.data.foreach_set('co', sk_data.ravel())

        active_obj = context.view_layer.objects.active
        selected_obj = [obj for obj in context.selected_objects if obj is not active_obj][0]

        # check if both objects are meshes
        if not (active_obj.type == 'MESH' and selected_obj.type == 'MESH'):
            self.report({'ERROR'}, 'You can only transfer Shape Keys between Meshes.')
            return{'CANCELLED'}

        if not len(active_obj.data.vertices) == len(selected_obj.data.vertices):
            self.report({'ERROR'}, 'Both objects need the same Vertex Count to Transfer Shape Keys..')
            return{'CANCELLED'}

        if not selected_obj.data.shape_keys:
            self.report({'ERROR'}, 'No Shape Keys found on selected object.')
            return{'CANCELLED'}

        if scene.faceit_overwrite_shape_keys_on_transfer:
            active_obj.shape_key_clear()

        # Copy Shape Keys from active to selected objects...
        sk_dict = store_shape_keys(selected_obj)

        if not active_obj.data.shape_keys:
            active_obj.shape_key_add(name='Basis')

        self.report({'INFO'}, 'transfer sk from {} to {}'.format(selected_obj.name, active_obj.name))

        apply_stored_shape_keys(active_obj, sk_dict)

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
    def poll(self, context):
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

        shapes_init = rutils.eval_target_shapes()

        arkit_order_list = []

        # for arkit_shape, target_shape_list in rutils.get_target_shapes_dict().items():
        target_shapes_dict = rutils.get_target_shapes_dict(scene.faceit_retarget_shapes)

        i = 0
        # for i in range(52):
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
                try:
                    action_to_keep = obj.data.shape_keys.animation_data.action
                except:
                    pass

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
            return{'CANCELLED'}

        if not reordered:
            self.report({'WARNING'}, 'Failed! Did you create Shapekeys? Did you register the Objects?')
            return{'CANCELLED'}

        return{'FINISHED'}


def isolate_shape_key(obj, sk_name):
    for sk in obj.data.shape_keys.key_blocks:
        if sk.name == sk_name:
            sk.value = 1
        else:
            sk.value = 0


def _apply_mirror_modifier_to_mesh_with_shape_keys(context, obj, mod_name):
    ''' Applies a modifier and keeps the shape keys
    @obj: the object with modifier and shape keys
    @mod_name: the name of the modifier
    '''

    # Copy Object
    scene = context.scene

    dup_obj = futils.duplicate_obj(obj, link=True)

    # Remove all shape keys and apply mod on object.

    futils.clear_object_selection()
    futils.set_active_object(obj.name)

    # obj.shape_key_clear()
    sk_utils.remove_all_sk_apply_basis(obj, apply_basis=True)

    futils.apply_modifier(mod_name)

    shape_data = {}

    # Make another duplicate and apply shape keys
    dup_shape_keys = dup_obj.data.shape_keys.key_blocks

    relative_keys_dict = {}
    # for sk in dup_shape_keys:

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
            futils.set_active_object(temp_dup_obj.name)

            isolate_shape_key(temp_dup_obj, sk_props['name'])

            sk_utils.apply_all_shape_keys(temp_dup_obj)

            futils.apply_modifier(mod_name)

            futils.set_active_object(obj.name)
            bpy.ops.object.join_shapes()

            new_sk = obj.data.shape_keys.key_blocks[-1]
            new_sk.name = sk_props['name']
            new_sk.value = sk_props['value']
            new_sk.mute = sk_props['mute']
            new_sk.slider_max = sk_props['slider_max']
            new_sk.slider_min = sk_props['slider_min']
            new_sk.vertex_group = sk_props['vertex_group']
            new_sk.interpolation = sk_props['interpolation']

            stored_drivers = sk_props.get('drivers')
            if stored_drivers:

                for sk_driver_dict in stored_drivers:

                    # Value will be replaced in populate_driver_data/populate_fcurve
                    dr = new_sk.driver_add('value', -1)
                    fc_dr_utils.populate_driver_data(sk_driver_dict, dr)

            bpy.data.objects.remove(temp_dup_obj)

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

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            obj = context.object
            if obj:
                if obj.type == 'MESH' and len(obj.modifiers) > 0:
                    return True

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
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
                    _apply_mirror_modifier_to_mesh_with_shape_keys(context, obj, mod_name)

                if mod_dict:
                    for mod, show in mod_dict.items():
                        mod = obj.modifiers.get(mod)
                        mod.show_viewport = show

            else:
                futils.apply_modifier(mod_name)

        return {'FINISHED'}
