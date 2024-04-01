
import bpy

from ..core.faceit_utils import (get_faceit_armature, get_faceit_objects_list, get_hide_obj, get_object)
from ..core.modifier_utils import get_faceit_armature_modifier
from ..core.shape_key_utils import has_shape_keys
from . import corrective_shape_keys_utils


class FACEIT_OT_ReevaluateCorrectiveShapeKeys(bpy.types.Operator):
    ''' Sync Corrective Shape Keys. re-evaluate the keyframes and properties for each expression. '''
    bl_idname = 'faceit.reevaluate_corrective_shape_keys'
    bl_label = 'Re-evaluate Corrective Shape Keys'
    bl_options = {'UNDO', 'INTERNAL'}

    expression: bpy.props.StringProperty(
        name='Expression',
        default='ALL'
    )

    @classmethod
    def poll(cls, context):
        rig = context.scene.faceit_armature
        if rig:
            if get_hide_obj(rig):
                return False
        return context.scene.faceit_expression_list

    def execute(self, context):
        expression_list = context.scene.faceit_expression_list
        corrective_shape_keys_utils.reevaluate_corrective_shape_keys(expression_list, get_faceit_objects_list())

        self.report({'INFO'}, 'Re-evaluated the corrective shape keys.')

        return {'FINISHED'}


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
                if get_faceit_armature():
                    if get_faceit_armature_modifier(obj, force_original=False):
                        return True

    def execute(self, context):
        scene = context.scene
        objects = context.selected_objects
        if objects:
            for obj in objects:
                if obj.name not in scene.faceit_face_objects:
                    obj.select_set(False)
                    objects.remove(obj)
        if not objects:
            self.report({'ERROR'}, 'Select at least one registered Object!')
            return {'CANCELLED'}
        expression_list = scene.faceit_expression_list
        exp = expression_list.get(self.expression)
        exp_index = expression_list.find(exp.name)
        sk_name = 'faceit_cc_' + exp.name
        frame = exp.frame
        scene.frame_current = frame
        scene.faceit_expression_list_index = exp_index
        mirror_x = (exp.mirror_name == '')
        for obj in objects:
            if obj.mode in ('SCULPT', 'EDIT'):
                if obj.active_shape_key:
                    if obj.active_shape_key.name == sk_name:
                        bpy.ops.object.mode_set()
                        self.report({'INFO'}, 'Exit editing corrective Shape Key.')
                        return {'FINISHED'}
            obj.data.use_mirror_x = mirror_x
            obj.use_shape_key_edit_mode = True
            obj.show_only_shape_key = False
            # Add Shape Key
            has_sk = has_shape_keys(obj)
            sk_added = False
            if not has_sk:
                basis_shape = obj.shape_key_add(name='Basis')
                basis_shape.interpolation = 'KEY_LINEAR'
                sk = obj.shape_key_add(name=sk_name, from_mix=False)
                sk_added = True
            else:
                obj.data.shape_keys.reference_key.name = 'Basis'
                sk = obj.data.shape_keys.key_blocks.get(sk_name)
                if not sk:
                    sk = obj.shape_key_add(name=sk_name, from_mix=False)
                    sk_added = True
            obj.active_shape_key_index = obj.data.shape_keys.key_blocks.find(sk.name)
            corrective_shape_keys_utils.assign_corrective_sk_action(obj)
        exp.corr_shape_key = True
        corrective_shape_keys_utils.keyframe_corrective_sk_action(exp)
        if scene.faceit_corrective_shape_keys_edit_mode == 'SCULPT':
            bpy.ops.object.mode_set(mode='SCULPT')
        else:
            bpy.ops.object.mode_set(mode='EDIT')
        if sk_added:
            self.report(
                {'INFO'},
                f'Added new corrective Shape Key "{sk_name}" to object {", ".join([obj.name for obj in objects])}.')
        else:
            self.report(
                {'INFO'},
                f'Edit corrective Shape Key "{sk_name}" on object {", ".join([obj.name for obj in objects])}.')

        return {'FINISHED'}


def get_objects_with_corrective_sk_enum(self, context):
    global objects
    objects = []

    if context is None:
        print('Context is None')
        return objects

    found_objects = corrective_shape_keys_utils.get_objects_with_corrective_shape_key_for_expression(self.expression)
    txt = 'Remove from'
    if found_objects:
        idx = 0
        if len(found_objects) > 1:
            objects.append(('ALL', f'{txt} All Objects', 'Remove all Corrective Shape Keys for this expression', idx))
            idx += 1
        for obj in found_objects:
            name = obj.name
            objects.append((name, f'{txt}  {name}', name, idx))
            idx += 1
    else:
        objects.append(('None', 'None', 'None'))
    return objects


class FACEIT_OT_RemoveCorrectiveShapeKey(bpy.types.Operator):
    '''Remove Corrective Shape Key from spec expression'''
    bl_idname = 'faceit.remove_corrective_shape_key'
    bl_label = 'Remove Corrective Shape Key'
    bl_property = 'operate_objects'
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    expression: bpy.props.StringProperty(
        name='Expression',
        default='ALL'
    )
    operate_objects: bpy.props.EnumProperty(
        name='Operate Objects',
        items=get_objects_with_corrective_sk_enum,
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):

        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.prop(self, 'operate_objects', text='')

    def execute(self, context):
        scene = context.scene

        operate_objects = []
        if self.operate_objects == 'ALL':
            operate_objects = get_faceit_objects_list()
            objects_txt = 'all objects'
        else:
            obj = get_object(self.operate_objects)
            operate_objects.append(obj)
            objects_txt = f'object {obj.name}'

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        expression_list = scene.faceit_expression_list

        exp = expression_list.get(self.expression)
        if not exp:
            self.report({'WARNING'}, 'Expression not found')
            return {'CANCELLED'}

        frame = exp.frame
        scene.frame_current = frame
        scene.faceit_expression_list_index = expression_list.find(exp.name)

        success = corrective_shape_keys_utils.remove_corrective_shape_key(
            expression_list, operate_objects, expression_name=exp.name)

        if success:
            self.report({'INFO'}, f'Removed the corrective sculpt from {objects_txt} for expression {exp.name}')
        else:
            self.report({'WARNING'}, f'No corrective sculpt found for {objects_txt}')

        return {'FINISHED'}


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

        expression_list = scene.faceit_expression_list

        faceit_objects = get_faceit_objects_list()

        if self.expression:
            corrective_shape_keys_utils.remove_corrective_shape_key(
                expression_list, faceit_objects, expression_name=self.expression)
        else:
            corrective_shape_keys_utils.clear_all_corrective_shape_keys(faceit_objects, expression_list=expression_list)

        return {'FINISHED'}
