from pickle import TRUE

import bpy
from bpy.props import BoolProperty, EnumProperty

from ..core.modifier_utils import get_faceit_armature_modifier

from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils
from ..shape_keys.corrective_shape_keys_utils import (
    CORRECTIVE_SK_ACTION_NAME, clear_all_corrective_shape_keys)


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
                return {'CANCELLED'}

        rig = futils.get_faceit_armature()
        deform_groups = vg_utils.get_deform_bones_from_armature(armature_obj=rig)

        sk_removed = []

        for obj in op_objects:

            if obj.type != 'MESH':
                continue

            if self.remove_faceit_armature_modifier:
                arm_mod = get_faceit_armature_modifier(obj)
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
            expression_list = scene.faceit_expression_list
            clear_all_corrective_shape_keys(op_objects, expression_list=expression_list)

        if self.remove_from_registration:
            scene.faceit_face_objects.clear()

        return {'FINISHED'}


def update_purge_all(self, context):

    for p in dir(self):
        if p in ['__doc__', '__module__', '__slots__', 'bl_rna', 'rna_type', 'purge_scope', 'operate_scope']:
            continue
        else:
            setattr(self, p, True if self.purge_scope == 'ALL' else False)


class FACEIT_OT_CleanUpScene(bpy.types.Operator):
    '''Clean up all traces of the Faceit Rigging process in the scene and other data.'''
    bl_idname = 'faceit.cleanup_scene'
    bl_label = 'Clean Up All'
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    purge_scope: EnumProperty(
        name='Quick Selection',
        items=(
            ('ALL', 'Check All', 'Checks all options, purges everything.', 'CHECKBOX_HLT', 0),
            ('NONE', 'Uncheck All', 'Unchecks all options, purges nothing.', 'CHECKBOX_DEHLT', 1),
        ),
        default='NONE',
        update=update_purge_all
    )

    # -------- Faceit Properties ---------

    reset_faceit_properties: BoolProperty(
        name='Reset Properties',
        description='Reset all Faceit Properties to defaults',
        default=True
    )
    purge_scene: BoolProperty(
        name='Remove Unused Data blocks',
        description='This will remove all kinds of unused data in the blendfile.',
        default=True
    )

    # -------- Faceit Objects ---------

    remove_control_rigs: BoolProperty(
        name='Remove Control Rigs',
        description='finds all control rigs in the scene and removes them.'
    )

    remove_landmarks: BoolProperty(
        name='Remove Landmarks'
    )
    remove_face_rig: BoolProperty(
        name='Remove the Faceit Armature'
    )
    remove_actions: BoolProperty(
        name='Remove old Expression Actions'
    )

    # -------- Registered Meshes ---------

    operate_scope: EnumProperty(
        name='Clean Scope',
        items=(
            ('ALL', 'Blend File', 'Blend File'),
            ('FACEIT', 'Faceit Objects', 'Registered Objects'),
            ('SELECTED', 'Selected Objects', 'Selected Objects in Scene'),
        ),
        default='FACEIT',
    )

    remove_faceit_armature_modifier: BoolProperty(
        name='Remove Faceit Modifier',
        description='.',
        default=False,
    )
    remove_faceit_bind_weights: BoolProperty(
        name='Remove Bind Weights',
        description='Browse registered objects and remove the old faceit bind weights',
        default=False,
    )
    remove_faceit_vertex_groups: BoolProperty(
        name='Remove Registered Vertex Groups',
        description='(faceit_main, faceit_left_eyeball, ....)',
        default=False,
    )

    remove_faceit_corrective_shapes: BoolProperty(
        name='Remove Corrective Shape Keys',
        description='Remove the Corrective Shape Keys ("faceit_cc_[...]")',
        default=False,
    )

    @ classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        self.control_rigs_found = bool(futils.get_faceit_control_armatures())
        self.faceit_rig_found = bool(futils.get_faceit_armature())
        self.faceit_landmarks_found = bool(bpy.data.objects.get('facial_landmarks'))

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text=' --- WARNING! --- ')
        row = layout.row()
        row.label(text=' --- This Operation is destructive! --- ')

        row = layout.row()
        row.prop(self, 'purge_scope', expand=True, icon='TRASH')

        row = layout.row()
        row.prop(self, 'reset_faceit_properties')

        if self.control_rigs_found:
            row = layout.row()
            row.prop(self, 'remove_control_rigs')

        if self.faceit_rig_found:
            row = layout.row()
            row.prop(self, 'remove_face_rig')

        row = layout.row()
        row.prop(self, 'remove_actions')

        if self.faceit_landmarks_found:
            row = layout.row()
            row.prop(self, 'remove_landmarks')

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

    def execute(self, context):
        scene = context.scene

        rig = futils.get_faceit_armature()

        bpy.ops.object.mode_set()

        control_rigs = futils.get_faceit_control_armatures()

        if self.remove_control_rigs:
            for crig in control_rigs:
                scene.faceit_control_armature = crig
                try:
                    bpy.ops.faceit.remove_control_drivers()
                except RuntimeError:
                    print('Failed to remove Control Rig {}'.format(crig.name))
                bpy.data.objects.remove(crig, do_unlink=True)

            scene.faceit_control_armature = None

        if self.remove_landmarks:
            lm_obj = bpy.data.objects.get('facial_landmarks')
            if lm_obj:
                bpy.data.objects.remove(lm_obj, do_unlink=True)

        bpy.ops.faceit.cleanup_objects(
            operate_scope=self.operate_scope,
            remove_faceit_armature_modifier=self.remove_faceit_armature_modifier,
            remove_faceit_bind_weights=self.remove_faceit_bind_weights,
            remove_faceit_vertex_groups=self.remove_faceit_vertex_groups,
            remove_faceit_corrective_shapes=self.remove_faceit_corrective_shapes,
            remove_from_registration=False
        )

        if self.remove_face_rig:
            rig = futils.get_faceit_armature()
            if rig:
                bpy.data.objects.remove(rig, do_unlink=True)

        fcoll = futils.get_faceit_collection(force_access=False, create=False)
        if not fcoll.objects:
            bpy.data.collections.remove(fcoll)

        action_names = ['faceit_bake_test_action', 'faceit_shape_action',
                        'overwrite_shape_action', CORRECTIVE_SK_ACTION_NAME]
        for a in action_names:
            a = bpy.data.actions.get(a)
            if a:
                bpy.data.actions.remove(a)

        if self.reset_faceit_properties:
            for p in dir(scene):
                if p.startswith('faceit_'):
                    scene.property_unset(p)

        if self.purge_scene:
            for _ in range(12):
                bpy.ops.outliner.orphans_purge()

        return {'FINISHED'}
