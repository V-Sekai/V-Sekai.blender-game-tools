import bpy
import numpy as np
from addon_utils import check
from bpy.props import BoolProperty

from ..core import shape_key_utils
from ..core import faceit_utils as futils
from ..core import faceit_data as fdata
from ..core import fc_dr_utils

# gen_mods = ['ARRAY', 'BEVEL', 'BOOLEAN', 'BUILD', 'DECIMATE',
#            'EDGE_SPLIT', 'MASK', 'MIRROR', 'MULTIRES', 'REMESH',
#            'SCREW', 'SKIN', 'SOLIDIFY', 'SUBSURF', 'TRIANGULATE', 'WIREFRAME'
#            ]


class FACEIT_OT_GenerateShapekeys(bpy.types.Operator):
    '''Bakes the poses of the FaceitRig to Shape Keys on the registered objects'''
    bl_idname = 'faceit.generate_shapekeys'
    bl_label = 'Bake Shape Keys'
    bl_options = {'UNDO', 'INTERNAL'}

    generate_test_action: BoolProperty(
        name='Generate Test Action',
        default=True,
    )
    regenerate_mouth_close: BoolProperty(
        name='Regenerate MouthClose',
        default=True,
        description='The mouth Close Shape is the opposite \
of the jaw Open shape and ideally needs to be generated \
again based on the new edits. '
    )

    use_corrective_shape_keys: BoolProperty(
        name='Use Corrective Shape Keys',
        default=True,
        description='Generate Corrective Shape Keys in rigging phase (Animate Tab). Prefix: "faceit_cc_" '
    )

    use_all_shape_keys: BoolProperty(
        name='Use all available Shape Keys',
        default=False,
        description='Use all Shape Key values applied to the mesh to bake into Faceit Expressions. '
    )

    use_other_armatures_deformation: BoolProperty(
        name='Use Other Armatures',
        default=False,
        description='Bake Shape Keys with deformation from other Armatures. Otherwise only FaceitRig.'
    )

    use_transform_animation: BoolProperty(
        name='Use Other Transformations',
        default=False,
        description='Bake Shape Keys with deformation from object transform.'
    )

    init_arkit_shape_list: BoolProperty(
        name='Initialize ARKit Shapes',
        default=False,
        description='This try to populate the ARKit target shapes automatically.',
    )

    faceit_action_found = False
    expressions_generated = False

    @classmethod
    def poll(self, context):
        # if context.mode == 'OBJECT':
        if context.scene.faceit_face_objects and context.scene.faceit_expression_list and futils.get_faceit_armature() and context.scene.faceit_shapes_generated == False:
            return True

    def invoke(self, context, event):
        rig = futils.get_faceit_armature()
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
            self.init_arkit_shape_list = any([n.name in arkit_names for n in expression_list])

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, 'use_corrective_shape_keys', icon='SCULPTMODE_HLT')
        row = layout.row()
        row.prop(self, 'generate_test_action', icon='ACTION')
        row = layout.row(align=True)
        row.prop(self, 'regenerate_mouth_close', icon='FILE_REFRESH')
        row = layout.row()
        row.prop(self, 'init_arkit_shape_list', icon='OUTLINER_DATA_GP_LAYER')

        row = layout.row()
        row.label(text='(Experimental)')
        row = layout.row()
        row.prop(self, 'use_all_shape_keys', icon='SCULPTMODE_HLT')
        row = layout.row()
        row.prop(self, 'use_other_armatures_deformation', icon='MOD_ARMATURE')
        row = layout.row()
        row.prop(self, 'use_transform_animation', icon='DRIVER_TRANSFORM')

    def execute(self, context):

        scene = context.scene
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set()
        # Hide Generators
        hide_generator_modifiers = ['ARRAY', 'BEVEL', 'BOOLEAN', 'BUILD', 'DECIMATE',
                                    'EDGE_SPLIT', 'MASK', 'MIRROR', 'MULTIRES', 'REMESH',
                                    'SCREW', 'SKIN', 'SOLIDIFY', 'SUBSURF', 'TRIANGULATE', 'WIREFRAME']

        hide_modifier_drivers = ['show_viewport', ]

        if self.use_corrective_shape_keys:
            scene.faceit_use_corrective_shapes = True

        corrective_sk_action = bpy.data.actions.get('faceit_corrective_shape_keys')

        rig_obj = futils.get_faceit_armature()

        expression_list = scene.faceit_expression_list
        if not self.expressions_generated:
            self.report({'WARNING'}, 'No Expressions found. Please load Faceit Expressions in Animate Tab first.')

        if not self.faceit_action_found:
            self.report({'WARNING'}, 'No Action found on the Faceit Armature')

        bake_objects_mod = list()
        bake_objects_tr = list()
        bake_objects = list()

        obj_mod_show = dict()
        obj_mirror_x_dict = dict()

        obj_driver_mute = dict()

        faceit_objects = futils.get_faceit_objects_list()

        for obj in faceit_objects:

            arm_mod = futils.get_faceit_armature_modifier(obj, force_original=False)

            obj.show_only_shape_key = False

            other_armature_mod = False
            # Find other aramture modifiers (not Faceit rig)
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE' and mod != arm_mod:
                    if mod.object:
                        other_armature_mod = True
                    if mod.show_viewport:
                        mod.show_viewport = self.use_other_armatures_deformation
                        if not self.use_other_armatures_deformation:
                            try:
                                obj_mod_show[obj.name].append(mod.name)
                            except KeyError:
                                obj_mod_show[obj.name] = [mod.name]

            if self.use_other_armatures_deformation and other_armature_mod:
                bake_objects_mod.append(obj)
                continue

            if arm_mod:
                bake_objects_mod.append(obj)
                continue

            if self.use_transform_animation:
                bake_objects_tr.append(obj)
                continue

                # else:
            self.report(
                {'WARNING'},
                'The registered object {} cannot be baked, because it is not effected by Faceit armature or transforms'.format(obj.name))
            continue

        # bake_objects_mod.copy().extend(bake_objects_tr)
        bake_objects = [obj for obj in bake_objects_mod] + [obj for obj in bake_objects_tr]
        if not bake_objects:
            self.report({'ERROR'}, 'No Objects match baking criteria. Did you bind properly?')
            return{'CANCELLED'}

        # hidden states of all objects
        objects_hidden_states = futils.get_hidden_states(bake_objects)
        futils.set_hidden_states(overwrite=True, objects=bake_objects, hide_value=False)

        for obj in bake_objects:

            arm_mod = futils.get_faceit_armature_modifier(obj, force_original=False)

            # Mute drivers on modifiers
            if obj.animation_data:
                for dr in obj.animation_data.drivers:
                    # If it's muted anyways, continue
                    if dr.mute:
                        continue
                    if 'modifiers' in dr.data_path:
                        # if any([keyword in dr.data_path for keyword in hide_modifier_drivers]):
                        for driver_value in hide_modifier_drivers:
                            if driver_value in dr.data_path:
                                try:
                                    obj_driver_mute[obj.name].append(dr.data_path)
                                except KeyError:
                                    obj_driver_mute[obj.name] = [dr.data_path]
                                dr.mute = True

            # disable subsurface modifiers
            for mod in obj.modifiers:
                if mod.type == 'MIRROR':
                    self.report(
                        {'WARNING'},
                        'The object {} contains a mirror mirror modifier. Results may not be as expected.'.format(
                            obj.name))

                if mod.type in hide_generator_modifiers:
                    if mod.show_viewport == True:

                        mod.show_viewport = False
                        try:
                            obj_mod_show[obj.name].append(mod.name)
                        except KeyError:
                            obj_mod_show[obj.name] = [mod.name]

            # --------------- Shape Key Settings -----------------
            # | Mute/Unmute Shape Keys
            # --------------------------------------------------
            has_sk = shape_key_utils.has_shape_keys(obj)

            if not has_sk:
                basis_shape = obj.shape_key_add(name='Basis')
                basis_shape.interpolation = 'KEY_LINEAR'

            else:
                shape_keys = obj.data.shape_keys

                # Remove eventual actions on the shape keys because the deformation will be baked into the shapes once created
                if shape_keys.animation_data:
                    shape_keys.animation_data.action = None

                has_corrective_shape_keys = False

                # ------------ DE-/ACTIVATE CORRECTIVE SHAPES --------------

                for sk in obj.data.shape_keys.key_blocks:
                    if sk.name.startswith('faceit_cc_'):
                        has_corrective_shape_keys = True
                        sk.mute = not self.use_corrective_shape_keys
                    else:
                        sk.mute = not self.use_all_shape_keys

                # Ensure that the corrective shape key action is active!

                if self.use_corrective_shape_keys and has_corrective_shape_keys:
                    if corrective_sk_action:
                        if not shape_keys.animation_data:
                            shape_keys.animation_data_create()
                        shape_keys.animation_data.action = corrective_sk_action

                obj.data.shape_keys.reference_key.name = 'Basis'

            use_mirror_x_state = obj.data.use_mirror_x
            obj_mirror_x_dict[obj.name] = use_mirror_x_state
            obj.data.use_mirror_x = False

        save_frame = scene.frame_current
        scene.frame_set(0)
        # return{'CANCELLED'}

        # redo the procedural animation in case something changed
        if self.regenerate_mouth_close:
            bpy.ops.faceit.procedural_arkit_shapes('INVOKE_DEFAULT', shape='MOUTHCLOSE')

        depth = context.evaluated_depsgraph_get()

        for expression in expression_list:

            scene.frame_set(expression.frame)

            if self.use_transform_animation and bake_objects_tr:

                for obj in bake_objects_tr:

                    dup_obj = obj.copy()
                    dup_obj.data = obj.data.copy()

                    scene.collection.objects.link(dup_obj)

                    futils.clear_object_selection()
                    futils.set_active_object(dup_obj)

                    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
                    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

                    depth = context.evaluated_depsgraph_get()

                    obj_eval = dup_obj.evaluated_get(depth)
                    new_mesh = bpy.data.meshes.new_from_object(
                        obj_eval, preserve_all_data_layers=True, depsgraph=depth)

                    sk_obj = bpy.data.objects.new('temp', new_mesh)

                    verts = sk_obj.evaluated_get(depth).data.vertices
                    vert_count = len(verts)

                    sk_data = np.zeros(vert_count*3, dtype=np.float32)
                    verts.foreach_get('co', sk_data.ravel())

                    shape = obj.shape_key_add(name=expression.name)

                    try:
                        shape.data.foreach_set('co', sk_data.ravel())
                    except:
                        self.report(
                            {'ERROR'}, 'Could not bake the shape keys on object {}. Are there drivers on generative modifiers?'.format(obj.name))

                    shape.interpolation = 'KEY_LINEAR'
                    # scene.collection.objects.link(dup_obj)
                    bpy.data.objects.remove(dup_obj, do_unlink=True)
                    bpy.data.objects.remove(sk_obj, do_unlink=True)
                    bpy.data.meshes.remove(new_mesh, do_unlink=True)

            for obj in bake_objects_mod:

                # Remove shape key if existing.

                if shape_key_utils.has_shape_keys(obj):
                    sk = obj.data.shape_keys.key_blocks.get(expression.name)
                    if sk:
                        obj.shape_key_remove(sk)

                # Create new shape key

                verts = obj.evaluated_get(depth).data.vertices
                vert_count = len(verts)

                sk_data = np.zeros(vert_count*3, dtype=np.float32)
                verts.foreach_get('co', sk_data.ravel())

                shape = obj.shape_key_add(name=expression.name)

                try:
                    shape.data.foreach_set('co', sk_data.ravel())
                except:
                    self.report(
                        {'ERROR'}, 'Could not bake the shape keys on object {}. Are there drivers on generative modifiers?'.format(obj.name))

                shape.interpolation = 'KEY_LINEAR'

        # ------------ MODIFIERS --------------
        # | - enable modifiers that have been enabled before.
        # | - hide corrective smooth
        for obj_name in obj_mod_show.keys():
            for mod in obj_mod_show[obj_name]:
                futils.get_object(obj_name).modifiers[mod].show_viewport = True

        for obj_name in obj_driver_mute.keys():
            dr_dict = obj_driver_mute.get(obj_name)
            if dr_dict:
                for dr_dp in dr_dict:
                    futils.get_object(obj_name).animation_data.drivers.find(dr_dp).mute = False

        for obj in bake_objects:
            mod_show_dict = obj_mod_show.get(obj.name)
            if mod_show_dict:
                for mod in mod_show_dict:
                    mod = obj.modifiers.get(mod)
                    if mod:
                        mod.show_viewport = True
            dr_dict = obj_driver_mute.get(obj.name)
            if dr_dict:
                for dr_dp in dr_dict:
                    if obj.animation_data:
                        dr = obj.animation_data.drivers.find(dr_dp)
                        if dr:
                            dr.mute = False

            obj.data.use_mirror_x = obj_mirror_x_dict.get(obj.name, False)
            # Hide Corrective Smooth / Remove Armature Modifier
            if rig_obj.name == 'FaceitRig':
                for m in obj.modifiers:
                    if m.name == 'Faceit_Armature':
                        obj.modifiers.remove(m)
                        continue
                    if m.name == 'CorrectiveSmooth':
                        m.show_viewport = False
                        m.show_render = False

            # ------------ DE-/ACTIVATE CORRECTIVE SHAPES --------------

            has_corrective_shape_keys = False
            for sk in obj.data.shape_keys.key_blocks:
                if sk.name.startswith('faceit_cc_'):
                    sk.mute = True
                    has_corrective_shape_keys = True
                else:
                    sk.mute = False
            if has_corrective_shape_keys:
                obj.data.shape_keys.animation_data.action = None

        all_shape_key_names = shape_key_utils.get_shape_key_names_from_objects()  # .data.shape_keys.key_blocks.get('mouthClose')
        # mouthClose_sk = all_shape_keys.get('mouth')
        if 'mouthClose' in all_shape_key_names:
            for obj in bake_objects:
                mouthClose_sk = obj.data.shape_keys.key_blocks.get('mouthClose')
                jawOpen_sk = obj.data.shape_keys.key_blocks.get('jawOpen')
                if not mouthClose_sk or not jawOpen_sk:
                    continue
                vert_count = len(obj.data.vertices)
                mClose_sk_data = np.zeros(vert_count*3, dtype=np.float32)
                mouthClose_sk.data.foreach_get('co', mClose_sk_data.ravel())

                jOpen_sk_data = np.zeros(vert_count*3, dtype=np.float32)
                jawOpen_sk.data.foreach_get('co', jOpen_sk_data.ravel())

                basis_sk = mouthClose_sk.relative_key
                basis_sk_data = np.zeros(vert_count*3, dtype=np.float32)
                basis_sk.data.foreach_get('co', basis_sk_data.ravel())

                new_sk_data = basis_sk_data + mClose_sk_data - jOpen_sk_data
                mouthClose_sk.data.foreach_set('co', new_sk_data.ravel())

        lm_obj = bpy.data.objects.get('facial_landmarks')
        if lm_obj:
            lm_obj.hide_viewport = True
        if futils.get_faceit_armature(force_original=True):
            rig_obj.hide_viewport = True
        scene.frame_set(0)

        # Set Fake user before removing the action
        overwrite_action = bpy.data.actions.get('overwrite_shape_action')
        if overwrite_action:
            overwrite_action.use_fake_user = True
        shape_action = bpy.data.actions.get('faceit_shape_action')
        if shape_action:
            shape_action.use_fake_user = True

        if rig_obj.animation_data:
            rig_obj.animation_data.action = None

        # restore
        futils.set_hidden_states(objects_hidden_states=objects_hidden_states)
        scene.frame_current = save_frame
        futils.clear_object_selection()
        scene.faceit_shapes_generated = True

        if self.generate_test_action:
            bpy.ops.faceit.test_action()

        if self.init_arkit_shape_list:
            scene.faceit_retarget_shapes.clear()
            bpy.ops.faceit.init_retargeting('EXEC_DEFAULT')

        return{'FINISHED'}


class FACEIT_OT_ResetToRig(bpy.types.Operator):
    '''Reset Faceit to Rigging and Posing functionality, removes the baked Shape Keys'''
    bl_idname = 'faceit.reset_to_rig'
    bl_label = 'Back to Rigging'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(self, context):
        if context.mode == 'OBJECT':
            return futils.get_main_faceit_object() and futils.get_faceit_armature()

    def execute(self, context):

        scene = context.scene
        if check(module_name="AddRoutes")[1]:
            scene.MOM_Items.clear()

        rig = futils.get_faceit_armature()
        futils.get_faceit_collection(force_access=True)

        # restore scene
        if rig:
            futils.set_hide_obj(rig, False)
        else:
            self.report({'WARNING'}, 'The Faceit Armature can\'t be found.')

        c_rig = futils.get_faceit_control_armature()
        if c_rig:
            bpy.ops.faceit.remove_control_drivers('EXEC_DEFAULT', remove_all=False)
            # bpy.data.objects.remove(c_rig, do_unlink=True)
            # context.scene.faceit_control_armature = None
        # scene.faceit_retarget_shapes.clear()
        bake_test_action = bpy.data.actions.get('faceit_bake_test_action')
        if bake_test_action:
            bpy.data.actions.remove(bake_test_action)

        faceit_objects = futils.get_faceit_objects_list()

        expression_list = scene.faceit_expression_list

        corrective_sk_action = bpy.data.actions.get('faceit_corrective_shape_keys', None)

        for obj in faceit_objects:

            if shape_key_utils.has_shape_keys(obj):
                for expression in expression_list:
                    sk = obj.data.shape_keys.key_blocks.get(expression.name)
                    if sk:
                        obj.shape_key_remove(sk)
                # unmute corrective shapes!
                has_corrective_shape_keys = False
                if scene.faceit_use_corrective_shapes:
                    for sk in obj.data.shape_keys.key_blocks:
                        if sk.name.startswith('faceit_cc_'):
                            has_corrective_shape_keys = True
                            sk.mute = False
                if has_corrective_shape_keys:
                    if corrective_sk_action:
                        if not obj.data.shape_keys.animation_data:
                            obj.data.shape_keys.animation_data_create()
                        obj.data.shape_keys.animation_data.action = corrective_sk_action
                    else:
                        self.report({'WARNING'}, 'Could not find the corrective shape key action.')
                        pass

                if len(obj.data.shape_keys.key_blocks) == 1:
                    obj.shape_key_clear()

            else:
                continue

            # futils.add_faceit_armature_modifier(obj, rig)
            # get mod
            mod = futils.get_faceit_armature_modifier(obj, force_original=False)
            if mod:
                mod.show_viewport = True
            else:
                if rig.name == 'FaceitRig':
                    futils.add_faceit_armature_modifier(obj, rig, force_original=False)

            corrective_mod = obj.modifiers.get('CorrectiveSmooth')
            if corrective_mod:
                corrective_mod.show_viewport = True
                corrective_mod.show_render = True

        scene.faceit_shapes_generated = False

        futils.clear_object_selection()
        futils.set_active_object(rig.name)

        action = None
        if rig:
            action = bpy.data.actions.get('overwrite_shape_action')
            if not action:
                action = bpy.data.actions.get('faceit_shape_action')
            if action:
                if not rig.animation_data:
                    rig.animation_data_create()

                rig.animation_data.action = action
        if action:
            scene.frame_start, scene.frame_end = action.frame_range
        elif not expression_list:
            self.report({'WARNING'}, 'The Expressions could not be found.')

        bpy.ops.outliner.orphans_purge()
        scene.frame_set(scene.frame_current)

        fc_dr_utils.clear_invalid_drivers()

        return {'FINISHED'}
