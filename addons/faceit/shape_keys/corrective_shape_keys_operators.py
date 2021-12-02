
import bpy
from ..core import shape_key_utils
from ..animate import animate_utils
from ..core import faceit_utils as futils


class FACEIT_OT_AddCorrectiveShapeKeyToExpression(bpy.types.Operator):
    '''Add Corrective Shape Key to this Expression (Selected Object). Sculpt additional changes!'''
    bl_idname = 'faceit.add_corrective_shape_key_to_expression'
    bl_label = 'Corrective Shape Key'
    bl_options = {'UNDO', 'INTERNAL'}

    expression: bpy.props.StringProperty(
        name='Expression',
        default='ALL'
    )

    @classmethod
    def poll(cls, context):
        if context.mode != 'POSE':
            obj = context.object
            if obj is not None:
                if futils.get_faceit_armature():
                    if futils.get_faceit_armature_modifier(obj, force_original=False):
                        return True

    def execute(self, context):
        scene = context.scene

        obj = context.object

        if not obj:
            self.report({'ERROR'}, 'Select an Object first!')
            return{'CANCELLED'}

        if not futils.get_faceit_armature_modifier(obj, force_original=False):
            self.report({'ERROR'}, 'The selected Object is not bound to the FaceitRig!')
            return{'CANCELLED'}

        expression_list = scene.faceit_expression_list

        if not self.expression:
            return{'CANCELLED'}

        exp = expression_list.get(self.expression)
        if not exp:
            self.report({'WARNING'}, 'Expression not found')
            return{'CANCELLED'}

        exp_index = expression_list.find(exp.name)

        if context.mode == 'SCULPT' and scene.faceit_expression_list_index == exp_index:
            bpy.ops.object.mode_set()
            return{'FINISHED'}

        frame = exp.frame
        scene.frame_current = frame
        scene.faceit_expression_list_index = exp_index
        mirror_x = (exp.mirror_name == '')

        obj.data.use_mirror_x = mirror_x

        sk_name = 'faceit_cc_' + exp.name

        bpy.ops.object.mode_set(mode='SCULPT')

        # Add Shape Key
        has_sk = shape_key_utils.has_shape_keys(obj)
        if not has_sk:
            basis_shape = obj.shape_key_add(name='Basis')
            basis_shape.interpolation = 'KEY_LINEAR'
            sk = obj.shape_key_add(name=sk_name, from_mix=False)
        else:
            obj.data.shape_keys.reference_key.name = 'Basis'
            sk = obj.data.shape_keys.key_blocks.get(sk_name)
            if not sk:
                sk = obj.shape_key_add(name=sk_name, from_mix=False)

        shape_keys = obj.data.shape_keys

        action_name = 'faceit_corrective_shape_keys'

        action = bpy.data.actions.get(action_name)

        if not action:
            action = bpy.data.actions.new(action_name)
            action.use_fake_user = True
        else:
            # Purge old data-paths not valid
            for fc in action.fcurves:
                if not fc.is_valid:
                    action.fcurves.remove(fc)

        if not shape_keys.animation_data:
            shape_keys.animation_data_create()

        anim_data = obj.data.shape_keys.animation_data

        anim_data.action = action

        exp.corr_shape_key = True

        sk.value = 0
        sk.keyframe_insert(data_path='value', frame=frame - 9)
        sk.keyframe_insert(data_path='value', frame=frame + 1)
        sk.value = 1
        sk.keyframe_insert(data_path='value', frame=frame)

        obj.active_shape_key_index = obj.data.shape_keys.key_blocks.find(sk.name)

        return{'FINISHED'}


class FACEIT_OT_RemoveCorrectiveShapeKey(bpy.types.Operator):
    '''Remove Corrective Shape Key from spec expression'''
    bl_idname = 'faceit.remove_corrective_shape_key'
    bl_label = 'Remove Corrective Shape Key'
    bl_options = {'UNDO', 'INTERNAL'}

    expression: bpy.props.StringProperty(
        name='Expression',
        default='ALL'
    )

    @classmethod
    def poll(cls, context):
        # if context.mode != 'OBJECT':
        obj = context.object
        if obj is not None:
            if shape_key_utils.has_shape_keys(obj):
                return True
                # return any(['faceit_cc_' in sk.name for sk in obj.data.shape_keys.key_blocks])

    def execute(self, context):
        scene = context.scene

        obj = context.object
        if not obj:
            self.report({'WARNING'}, 'Select an Object first!')
            return{'CANCELLED'}

        if not futils.get_faceit_armature_modifier(obj, force_original=False):
            self.report({'WARNING'}, 'The selected Object is not bound to the FaceitRig!')
            return{'CANCELLED'}

        if context.mode == 'SCULPT':
            bpy.ops.object.mode_set(mode='OBJECT')

        expression_list = scene.faceit_expression_list
        # curr_expression = scene.faceit_expression_list_index
        if not self.expression:
            return{'CANCELLED'}

        exp = expression_list.get(self.expression)
        if not exp:
            self.report({'WARNING'}, 'Expression not found')
            return{'CANCELLED'}

        frame = exp.frame
        scene.frame_current = frame
        scene.faceit_expression_list_index = expression_list.find(exp.name)

        sk_name = 'faceit_cc_' + exp.name

        action = bpy.data.actions.get('faceit_corrective_shape_keys')
        if action:

            # Remove Shape Key
            has_sk = shape_key_utils.has_shape_keys(obj)
            if not has_sk:
                pass
            else:
                sk = obj.data.shape_keys.key_blocks.get(sk_name)
                if sk:
                    obj.shape_key_remove(sk)
                    # animate_utils.remove_all_animation_for_frame(action, exp.frame)
                    animate_utils.remove_fcurve_from_action(action, 'key_blocks["{}"].value'.format(sk_name))

            # Purge old data-paths not valid
            for fc in action.fcurves:
                if not fc.is_valid:
                    action.fcurves.remove(fc)

            if not action.fcurves:
                bpy.data.actions.remove(action)

        exp.corr_shape_key = False

        if len(obj.data.shape_keys.key_blocks) == 1:
            obj.shape_key_clear()

        return{'FINISHED'}


class FACEIT_OT_ClearCorrectiveShapeKeys(bpy.types.Operator):
    '''Clear all Corrective Shape Keys from registered objects'''
    bl_idname = 'faceit.clear_all_corrective_shapes'
    bl_label = 'Clear all Corrective Shape Keys'
    bl_options = {'UNDO', 'INTERNAL'}

    expression: bpy.props.StringProperty(
        name='Expression',
        default='ALL',
        options={'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene

        remove_all = True

        expression_list = scene.faceit_expression_list

        faceit_objects = futils.get_faceit_objects_list()

        sk_prefix = 'faceit_cc_'

        if self.expression:
            remove_all = False

        for obj in faceit_objects:

            # Add Shape Key
            has_sk = shape_key_utils.has_shape_keys(obj)
            if not has_sk:
                continue
            else:
                shape_keys = obj.data.shape_keys.key_blocks
                if remove_all == True:
                    for sk in shape_keys:
                        if sk.name.startswith(sk_prefix):
                            obj.shape_key_remove(sk)
                else:
                    sk = shape_keys.get(sk_prefix+self.expression)
                    if sk:
                        obj.shape_key_remove(sk)

            if len(obj.data.shape_keys.key_blocks) == 1:
                obj.shape_key_clear()

        action = bpy.data.actions.get('faceit_corrective_shape_keys')
        if action:
            if remove_all:
                bpy.data.actions.remove(action)
            else:
                animate_utils.remove_fcurve_from_action(action, 'key_blocks["{}"].value'.format(
                    sk_prefix + self.expression))

        for exp in expression_list:
            exp.corr_shape_key = False

        return{'FINISHED'}
