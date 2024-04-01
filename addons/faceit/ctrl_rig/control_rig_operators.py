import bpy
from bpy.props import (BoolProperty, EnumProperty,
                       FloatProperty, StringProperty)
from mathutils import Vector


from ..core.pose_utils import copy_pose_bone_constraints, copy_pose_bone_data, remove_all_pose_bone_constraints, reset_pose
from ..core import faceit_utils as futils
from ..core import shape_key_utils
from ..core.faceit_data import get_control_rig_file
from . import control_rig_data as ctrl_data
from . import control_rig_utils as ctrl_utils


class FACEIT_OT_UpdateControlRig(bpy.types.Operator):
    '''Update the active Faceit control rig object'''
    bl_idname = 'faceit.update_control_rig'
    bl_label = 'Update Control Rig'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        ctrl_rig = futils.get_faceit_control_armature()
        if ctrl_rig:
            if ctrl_rig.library or ctrl_rig.override_library:
                return False
            ctrl_rig_version = ctrl_rig.get('ctrl_rig_version', 1.0)
            return ctrl_rig_version < ctrl_data.CNTRL_RIG_VERSION

    def execute(self, context):
        if futils.get_object_mode_from_context_mode(context.mode) != 'OBJECT' and context.object is not None:
            bpy.ops.object.mode_set()

        c_rig = futils.get_faceit_control_armature()
        futils.set_hide_obj(c_rig, False)

        crig_version = c_rig.get('ctrl_rig_version', 1.0)

        if crig_version == 1.0:
            if 'FaceitControlRig' in c_rig.name:
                if 'ctrl_rig_id' not in c_rig:
                    c_rig['ctrl_rig_id'] = ctrl_data.get_random_rig_id()

        if crig_version < 1.2:
            if not context.scene.faceit_face_objects:
                self.report(
                    {'WARNING'},
                    'Cannot populate the control rig objects. Please load them manually or register them in setup panel first.')
            ctrl_utils.populate_control_rig_target_shapes_from_scene(
                c_rig, update=True)
            if not context.scene.faceit_arkit_retarget_shapes:
                self.report(
                    {'WARNING'},
                    'Cannot populate the control rig target shapes.')
            ctrl_utils.populate_control_rig_target_objects_from_scene(c_rig)

        if crig_version <= 1.3:
            # Get the slider range and populate the property
            # get_properties_for_sliders(c_rig, custom_only=False)
            # # add the slider parent bone for moving the custom sliders.
            # obj = bpy.data.objects.new('WGT_sliders_parent', None)
            # obj.empty_display_size = 5
            # obj.empty_display_type = 'PLAIN_AXES'
            # bpy.ops.object.mode_set(mode='EDIT')
            # slider_ref_bone = c_rig.data.edit_bones.get('c_slider_ref')
            # slider_parent_ref_bone = c_rig.data.edit_bones.get('c_slider_ref_parent')
            # slider_parent = c_rig.data.edit_bones.new('All_Sliders_Parent')
            # slider_parent.head = (0, 0, 0)  # if the head and tail are the same, the bone is deleted
            # slider_parent.tail = (0, 0, 1)    # upon returning to object mode
            # new_position = slider_parent_ref_bone.head.copy()
            # new_position.x -= slider_parent_ref_bone.length
            # new_position.z -= slider_ref_bone.length
            # slider_parent.translate((new_position - slider_parent.head))
            # # Parent all slider below the new bone
            # for bone in c_rig.data.edit_bones:
            #     if bone.name.endswith('slider_parent'):
            #         bone.parent = slider_parent
            # # Create a new bone (c_look_at_target)
            # main_bone = c_rig.data.edit_bones.get('c_face_main')
            # lookat_mch = c_rig.data.edit_bones.new('c_lookat_mch')
            # eye_L = c_rig.data.edit_bones.get('c_eyelid_upper.L')
            # eye_R = c_rig.data.edit_bones.get('c_eyelid_upper.R')
            # pos = futils.get_median_pos((eye_L.head, eye_R.head))
            # lookat_mch.head = (0, 0, 0)
            # lookat_mch.tail = (0, -1, 0)
            # lookat_mch.translate(pos)
            # lookat_mch.parent = main_bone
            # target = c_rig.data.edit_bones.get('c_eye_lookat')
            # target.parent = None
            # target_L = c_rig.data.edit_bones.get('c_eye.L')
            # target_L.parent = None
            # target_R = c_rig.data.edit_bones.get('c_eye.R')
            # target_R.parent = None  # target
            # bpy.ops.object.mode_set(mode='POSE')
            # # Create the constraint
            # lookat_mch = c_rig.pose.bones.get('c_lookat_mch')
            # target = c_rig.pose.bones.get('c_eye_lookat')
            # target.custom_shape = obj
            # target.lock_location = (False, False, False)
            # c = target.constraints.get('Limit Location')
            # if c:
            #     target.constraints.remove(c)
            # c = lookat_mch.constraints.new('DAMPED_TRACK')
            # c.target = c_rig
            # c.subtarget = 'c_eye_lookat'
            # c.track_axis = 'TRACK_Y'

            # c_rig.pose.bones['All_Sliders_Parent'].custom_shape = obj
            # self.report({'INFO'}, 'Slider parent bone added. Control Rig updated.')
            # # Get the inner brow bones and update the constraints
            # inner_L = c_rig.pose.bones.get('c_brow_inner.L')
            # inner_R = c_rig.pose.bones.get('c_brow_inner.R')
            # for pb in (inner_L, inner_R):
            #     c = pb.constraints.get('Child Of')
            #     if c:
            #         pb.constraints.remove(c)
            #         c = pb.constraints.new('COPY_LOCATION')
            #         c.target = c_rig
            #         c.subtarget = 'c_brow_master.L' if pb.name.endswith('L') else 'c_brow_master.R'
            #         c.use_x = True
            #         c.use_y = True
            #         c.use_z = False
            #         c.invert_x = True

            #         c.invert_y = True

            #         c.invert_z = False
            #         c.use_offset = True
            #         c.target_space = 'LOCAL'
            #         c.owner_space = 'LOCAL'
            # # Replace the old child of constraint with the new copy location constraint
            # c = c_rig.constraints.get('Child Of Body')
            # if c:
            #     _target = c.target
            #     _subtarget = c.subtarget
            #     # _bone = _target.pose.bones.get(_subtarget)
            #     # if _bone:
            #     for pb in _target.pose.bones:
            #         reset_pb(pb)
            #     # _target.data.pose_position = 'REST'
            #     c_rig.constraints.remove(c)
            #     main_bone = c_rig.pose.bones.get('c_face_main')
            #     c = main_bone.constraints.new('CHILD_OF')
            #     c.name = 'Child Of Body'
            #     c.target = _target
            #     c.subtarget = _subtarget
            #     # _target.data.pose_position = 'POSE'
            # # bpy.ops.object.mode_set(mode='POSE')
            # # Update the bone colors!
            # bone_groups = c_rig.pose.bone_groups
            # left_grp = bone_groups.get('Left')
            # left_grp.color_set = 'CUSTOM'
            # left_grp.colors.normal.hsv = (0.5745097398757935, 1.0, 1.0)
            # left_grp.colors.select.hsv = (0.6235293745994568, 0.6666666269302368, 1.0)
            # left_grp.colors.active.hsv = (0.5516223907470703, 0.47280335426330566, 0.9372549653053284)
            # right_grp = bone_groups.get('Right')
            # right_grp.color_set = 'CUSTOM'
            # right_grp.colors.normal.hsv = (0.9170437455177307, 0.8666666746139526, 1.0)
            # right_grp.colors.select.hsv = (0.8824662566184998, 0.6784313917160034, 1.0)
            # right_grp.colors.active.hsv = (0.8596490621566772, 0.22352933883666992, 1.0)
            # # Replace with new constraint
            # # Generate the new sliders
            # generate_extra_2dslider('LookAt2D', rig_obj=c_rig)
            # pos = c_rig.pose.bones['c_look_at'].location.copy()
            # # Settings bones
            # generate_extra_sliders(
            #     context, 'SwitchLookAt', 'pos_range', rig_obj=c_rig, in_2d_layout=True, n=2)
            # generate_extra_sliders(
            #     context, 'forceMouthClose', 'pos_range', rig_obj=c_rig, in_2d_layout=True, n=3)
            action = c_rig.animation_data.action
            if action:
                action.use_fake_user = True
            # Store the properties of the rig (target shapes, target objects, custom sliders)
            tmp_data = ctrl_utils.save_control_rig_template(
                c_rig, save_target_objects=True)
            apply_scale = c_rig.scale == Vector((1, 1, 1))
            old_armature = c_rig.data
            old_armature.name = 'FaceitControlRigArmatureOld'
            # Load the new control rig.
            c_rig_filepath = get_control_rig_file()
            faceit_collection = futils.get_faceit_collection(
                force_access=True, create=True)
            with bpy.data.libraries.load(c_rig_filepath) as (data_from, data_to):
                data_to.objects = data_from.objects
            # add only the armature
            obj = None
            for obj in data_to.objects:
                if obj:
                    if obj.type == 'ARMATURE' and 'FaceitControlRig' in obj.name:
                        faceit_collection.objects.link(obj)
                        obj['ctrl_rig_id'] = ctrl_data.get_random_rig_id()
                        break
            print('linking', obj.name)
            futils.clear_object_selection()
            futils.set_active_object(obj.name)
            context.scene.faceit_control_armature = obj
            # Generate the collections in 4.0
            if bpy.app.version >= (4, 0, 0):
                bpy.ops.faceit.update_bone_collections()
            bpy.ops.faceit.match_control_rig(
                'EXEC_DEFAULT', apply_scale=apply_scale)
            # obj.data.name = 'FaceitControlRigArmature'
            c_rig.data = obj.data
            bpy.data.armatures.remove(old_armature, do_unlink=True)
            context.scene.faceit_control_armature = c_rig
            futils.set_active_object(c_rig)
            # Copy the custom bone shapes from the new rig to the old rig
            # Copy the custom bone groups from the new rig to the old rig
            if bpy.app.version < (4, 0, 0):
                for bone_group in c_rig.pose.bone_groups:
                    new_bg = obj.pose.bone_groups.get(bone_group.name)
                    if not new_bg:
                        # delete the bone group
                        c_rig.pose.bone_groups.remove(bone_group)
                        continue
                    bone_group.color_set = new_bg.color_set
                    bone_group.colors.normal = new_bg.colors.normal.copy()
                    bone_group.colors.select = new_bg.colors.select.copy()
                    bone_group.colors.active = new_bg.colors.active.copy()
            # Copy the bone constraints from the new rig to the old rig
            for name, pb in c_rig.pose.bones.items():
                print('copying bone', name)
                src_bone = obj.pose.bones.get(name)
                if not src_bone:
                    # delete the bone
                    print(
                        f'the bone {name} was not found in the new rig and will be removed')
                    c_rig.pose.bones.remove(pb)
                    continue
                # Copy the constraints
                copy_pose_bone_data(src_bone, pb)
                remove_all_pose_bone_constraints(pb)
                copy_pose_bone_constraints(src_bone, pb)
                # copy new bone groups
                # bg = src_bone.bone_group
                # if bg:
                #     bone_group = c_rig.pose.bone_groups.get(bg.name)
                #     if bone_group:
                #         print('setting bone group', bone_group.name, 'for bone', pb.name)
                #         pb.bone_group = bone_group
                #     else:
                #         print('bone group', bg.name, 'not found')
            # Update the driver targets
            for dr in c_rig.data.animation_data.drivers:
                for var in dr.driver.variables:
                    for t in var.targets:
                        if t.id_type == 'OBJECT':
                            t.id = c_rig

            bpy.data.objects.remove(obj, do_unlink=True)
            # bpy.data.armatures.remove(old_armature, do_unlink=True)
            # c_rig.name = ctrl_rig_name
            # c_rig.animation_data_create()
            # Load the properties.
            ctrl_utils.load_control_rig_template(
                context, c_rig, tmp_data, load_target_objects=True)
            # if action:
            #     c_rig.animation_data.action = action
        if crig_version < 1.7:
            ctrl_utils.create_eye_lookat_driver_mechanics(c_rig)
        bpy.ops.faceit.rearrange_custom_controllers()
        c_rig['ctrl_rig_version'] = ctrl_data.CNTRL_RIG_VERSION
        try:
            bpy.ops.faceit.setup_control_drivers()
        except RuntimeError:
            print('Wasn\'t able to connect the drivers.')

        return {'FINISHED'}


class FACEIT_OT_UpdateBoneCollections(bpy.types.Operator):
    '''Updates control rigs to Blender 4.0'''
    bl_idname = 'faceit.update_bone_collections'
    bl_label = 'Update to Blender 4+'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        ctrl_rig = futils.get_faceit_control_armature()
        return ctrl_rig is not None and bpy.app.version >= (4, 0, 0)

    def execute(self, context):
        ctrl_rig = futils.get_faceit_control_armature()
        # control rig is loaded from a 3.6 blend file
        # Create new collections and assign the bones
        collections = ctrl_rig.data.collections
        coll3d = collections.new("3D Sliders")
        coll2d = collections.new("2D Sliders")  # TODO rename to 2D Board
        collMCH = collections.new("Mechanism Bones")
        collRef = collections.new("Reference Sliders")
        # Assign the bones
        for b in ctrl_rig.data.bones:
            if "_slider" in b.name:
                if "_ref" in b.name:
                    collRef.assign(b)
                    continue
                coll2d.assign(b)
                continue
            if b.name in ('c_face_main', 'c_lower_lips', 'c_jaw_target_master', 'c_lips_parent', 'c_lookat_mch.L', 'c_lookat_mch.R', 'c_eye_lookat_target.L', 'c_eye_lookat_target.R'):
                collMCH.assign(b)
            else:
                coll3d.assign(b)
        collMCH.is_visible = False
        collRef.is_visible = False

        # remove old bone groups.
        for coll in ctrl_rig.data.collections[:]:
            if coll.name not in [coll3d.name, coll2d.name, collMCH.name, collRef.name]:
                ctrl_rig.data.collections.remove(coll)
        return {'FINISHED'}


class FACEIT_OT_LoadCrigSettingsFromScene(bpy.types.Operator):
    ''' Populates the Crig Objects and Target Shapes based on the active scene settings. '''
    bl_idname = 'faceit.load_crig_settings_from_scene'
    bl_label = 'Load to Control Rig'
    bl_options = {'UNDO', 'INTERNAL'}

    load_target_objects: BoolProperty(
        name='Load Target Objects',
        default=True,
        options={'SKIP_SAVE'},
    )
    load_arkit_target_shapes: BoolProperty(
        name='Load ARKit Target Shapes',
        default=True,
        options={'SKIP_SAVE'},
    )

    @ classmethod
    def poll(cls, context):
        if context.mode in ('OBJECT', 'POSE'):
            ctrl_rig = futils.get_faceit_control_armature()
            if ctrl_rig:
                if ctrl_rig.library or ctrl_rig.override_library:
                    return False
                return True

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):

        layout = self.layout

        c_rig = futils.get_faceit_control_armature()

        row = layout.row()
        row.label(
            text='Warning! This will override target shapes and objects'.format(c_rig.name))
        row = layout.row()
        row.prop(self, 'load_target_objects', icon='OBJECT_DATA')
        row = layout.row()
        row.prop(self, 'load_arkit_target_shapes', icon='SHAPEKEY_DATA')

    def execute(self, context):
        scene = context.scene

        c_rig = futils.get_faceit_control_armature()
        futils.set_hide_obj(c_rig, False)

        if self.load_target_objects:
            if scene.faceit_face_objects:
                ctrl_utils.populate_control_rig_target_objects_from_scene(
                    c_rig)
            else:
                self.report(
                    {'WARNING'}, 'Didn\'t find any registered objects to load as control rig target objects.')
        if self.load_arkit_target_shapes:
            if scene.faceit_arkit_retarget_shapes:
                ctrl_utils.populate_control_rig_target_shapes_from_scene(
                    c_rig, populate_amplify_values=True)
            else:
                self.report(
                    {'WARNING'}, 'Didn\'t find any arkit target shapes to load as control rig target shapes.')

        return {'FINISHED'}


class FACEIT_OT_LoadFaceitSettingsFromCRig(bpy.types.Operator):
    ''' Populates the Faceit Objects and ARKit Target Shapes based on objects driven by active control rig. '''
    bl_idname = 'faceit.load_faceit_settings_from_crig'
    bl_label = 'Load to Scene'
    bl_options = {'UNDO', 'INTERNAL'}

    auto_sync: BoolProperty(
        name='Auto Sync',
        default=False,
        options={'SKIP_SAVE'},
    )
    load_target_objects: BoolProperty(
        name='Load Target Objects',
        default=True,
        options={'SKIP_SAVE'},
    )
    load_arkit_target_shapes: BoolProperty(
        name='Load ARKit Target Shapes',
        default=True,
        options={'SKIP_SAVE'},
    )

    @ classmethod
    def poll(cls, context):
        if context.mode in ('OBJECT', 'POSE'):
            ctrl_rig = futils.get_faceit_control_armature()
            if ctrl_rig:
                return True
                # return (ctrl_rig.faceit_crig_objects or ctrl_rig.faceit_crig_targets)

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):

        layout = self.layout

        c_rig = futils.get_faceit_control_armature()

        row = layout.row()
        row.label(
            text='Warning! This will override target shapes and objects'.format(c_rig.name))
        # row.label(text='Synchronize Scene Settings for {}?'.format(c_rig.name))
        row = layout.row()
        row.prop(self, 'load_target_objects', icon='OBJECT_DATA')
        row = layout.row()
        row.prop(self, 'load_arkit_target_shapes', icon='SHAPEKEY_DATA')

    def execute(self, context):
        scene = context.scene

        c_rig = futils.get_faceit_control_armature()
        futils.set_hide_obj(c_rig, False)

        arkit_target_shapes = {}

        target_objects = set()

        # Find the driven objects from stored settings
        target_objects = ctrl_utils.get_crig_objects_list(c_rig)
        # No objects found? Exit operator, reset faceit rig
        if self.load_target_objects:
            if target_objects:
                scene.faceit_face_objects.clear()
                for obj in target_objects:
                    item = scene.faceit_face_objects.add()
                    item.name = obj.name
                    item.obj_pointer = obj
                self.report({'INFO'}, 'Loading Objects to Setup List')
            else:
                self.report(
                    {'ERROR'},
                    'Can\'t find target objects. Please update the Control Rig first.')
                return {'CANCELLED'}
        if self.load_arkit_target_shapes:
            if any([shape_item.target_shapes for shape_item in c_rig.faceit_crig_targets]):
                scene.faceit_arkit_retarget_shapes.clear()
                # Initialize standart values
                bpy.ops.faceit.init_retargeting('EXEC_DEFAULT')
                retarget_list = scene.faceit_arkit_retarget_shapes

                for item in retarget_list:
                    item.target_shapes.clear()
                    ctrl_rig_shape_item = c_rig.faceit_crig_targets[item.name]
                    item.amplify = ctrl_rig_shape_item.amplify
                    for ts in ctrl_rig_shape_item.target_shapes:
                        target_item = item.target_shapes.add()
                        target_item.name = ts.name
                        continue
                self.report(
                    {'INFO'}, 'Loading ARKit target shapes to ARKit Shapes List')
            else:
                self.report(
                    {'ERROR'},
                    'Can\'t find target shapes. Please update the Control Rig first.')

        if target_objects and arkit_target_shapes:
            self.report(
                {'INFO'}, 'Updated registered objects and arkit target shapes.')

        return {'FINISHED'}


class FACEIT_OT_SetAmplify(bpy.types.Operator):
    ''' Set an amplify value for all target shapes '''
    bl_idname = 'faceit.set_amplify_values'
    bl_label = 'Set Amplify Value'
    bl_options = {'UNDO', 'INTERNAL'}

    amplify_value: FloatProperty(
        name='Amplify Value',
        default=1.0,
    )

    regions: EnumProperty(
        name='Effect Expressions',
        items=(
            ('VISIBLE', 'Visible',
             'Effect only the currently visible regions in the amplify list.'),
            ('ALL', 'All', 'Effect all expressions in the amplify list.'),
        ),
        default='VISIBLE'
    )

    @ classmethod
    def poll(cls, context):
        return context.scene.faceit_arkit_retarget_shapes and context.scene.faceit_control_armature

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, 'regions', expand=True)
        row = layout.row()
        row.prop(self, 'amplify_value')

    def execute(self, context):

        c_rig = futils.get_faceit_control_armature()
        target_list = c_rig.faceit_crig_targets

        for item in target_list:
            if self.regions == 'VISIBLE':
                active_region_dict = c_rig.faceit_crig_face_regions.get_active_regions()

                if not active_region_dict.get(item.region.lower(), False):
                    continue
            item.amplify = self.amplify_value

        for region in bpy.context.area.regions:
            region.tag_redraw()

        return {'FINISHED'}


class FACEIT_OT_SelectBoneFromSourceShape(bpy.types.Operator):
    ''' Select the bone that drives the target shapes for this ARKit source shape '''
    bl_idname = 'faceit.select_bone_from_source_shape'
    bl_label = 'Select Bone (Pose Mode Only)'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    expression: StringProperty(
        name='ARKit Expression',
        default='',
        description='The ARkit expression driven by the bone to select.'
    )

    @ classmethod
    def poll(cls, context):
        if context.mode in ('OBJECT', 'POSE'):
            crig = futils.get_faceit_control_armature()
            if crig is not None and crig == context.object and not futils.get_hide_obj(crig):
                return True

    def execute(self, context):

        c_rig = futils.get_faceit_control_armature()
        if not c_rig:
            self.report({'ERROR'}, 'Control Rig not found in scene')
        bone_name = ''
        try:
            driver_dict = ctrl_data.get_control_rig_driver_dict(c_rig)
            dr_dict = driver_dict[self.expression]
            bone_name, _, _ = ctrl_data.get_bone_settings_from_driver_dict(
                dr_dict)
        except KeyError:
            for obj in futils.get_faceit_objects_list():
                if shape_key_utils.has_shape_keys(obj):
                    if obj.data.shape_keys.animation_data:
                        dr = obj.data.shape_keys.animation_data.drivers.find(
                            'key_blocks["{}"].value'.format(self.expression))
                        if dr:
                            driver = dr.driver
                            var = driver.variables.get('var')
                            if var:
                                t = var.targets[0]
                                bone_name = t.bone_target
                                break
        pose_bone = c_rig.pose.bones.get(bone_name)
        if not pose_bone:
            self.report(
                {'WARNING'},
                'The expression {} could not be found in driven arkit shapes.'.format(self.expression))
            return {'CANCELLED'}
        if context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        for b in c_rig.data.bones:
            b.select = False
        c_rig.data.bones.active = pose_bone.bone
        pose_bone.bone.select = True
        return {'FINISHED'}


class FACEIT_OT_ControlRigSetSliderRanges(bpy.types.Operator):
    '''Set the slider ranges on all controllers. Value in [Full range (-1,1), Positive range (0,1)]'''
    bl_idname = 'faceit.control_rig_set_slider_ranges'
    bl_label = 'Set Ranges for Control Rig'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    new_range: EnumProperty(
        items=(
            ('ALL', 'Full Range', 'this will animate positive and negative shape keys'),
            ('POS', 'Only Positive Range',
             'this will animate only positive shape key ranges')
        )
    )
    reconnect: BoolProperty(
        name='Reconnect Drivers',
        default=True,
    )

    @ classmethod
    def poll(cls, context):
        if context.mode in ('OBJECT', 'POSE'):
            ctrl_rig = futils.get_faceit_control_armature()
            if ctrl_rig and context.scene.faceit_face_objects:
                if ctrl_rig.library or ctrl_rig.override_library:
                    return False
                return True

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='Slider Ranges')
        row = layout.row()
        row.prop(self, 'new_range', expand=True)
        row = layout.row()
        row.prop(self, 'reconnect', expand=True)

    def execute(self, context):
        c_rig = futils.get_faceit_control_armature()
        if not c_rig:
            self.report(
                {'WARNING'}, 'The control rig has to be generated first.')
            return {'CANCELLED'}
        else:
            bpy.ops.faceit.remove_control_drivers(
                'EXEC_DEFAULT', remove_all=False)
        retarget_list = context.scene.faceit_arkit_retarget_shapes
        for shape_item in retarget_list:
            arkit_name = shape_item.name
            driver_dict = ctrl_data.get_control_rig_driver_dict(c_rig)
            dr_info = driver_dict[arkit_name]
            if dr_info.get('range', 'pos') == 'all':
                bone_name, transform_type, _transform_space = ctrl_data.get_bone_settings_from_driver_dict(
                    dr_info)
                bone = c_rig.pose.bones.get(bone_name)
                if not bone:
                    continue
                for c in bone.constraints:
                    if c.type in ('LIMIT_LOCATION', 'LIMIT_ROTATION', 'LIMIT_SCALE'):
                        main_dir = dr_info.get('main_dir', 1)
                        _transform, axis = transform_type.split('_')
                        if axis == 'X':
                            if main_dir == -1:
                                new_value = 0 if self.new_range == 'POS' else -c.min_x
                                c.max_x = new_value
                            else:
                                new_value = 0 if self.new_range == 'POS' else -c.max_x
                                c.min_x = new_value
                        elif axis == 'Y':
                            if main_dir == -1:
                                new_value = 0 if self.new_range == 'POS' else -c.min_y
                                c.max_y = new_value
                            else:
                                new_value = 0 if self.new_range == 'POS' else -c.max_y
                                c.min_y = new_value
                        elif axis == 'Z':
                            if main_dir == -1:
                                new_value = 0 if self.new_range == 'POS' else -c.min_z
                                c.max_z = new_value
                            else:
                                new_value = 0 if self.new_range == 'POS' else -c.max_z
                                c.min_z = new_value
                        # account for scale on nose sneer...
                        elif axis == 'AVG':
                            if main_dir == -1:
                                new_value = 1 if self.new_range == 'POS' else 1.5
                                c.max_x, c.max_y, c.max_z = (new_value,) * 3
                            else:
                                pass
        # for b in c_rig.pose.bones:
        #     if 'forceMouthClose' in b.name:
        #         continue
        #     if 'slider_parent' in b.name:
        #         if self.new_range == 'POS':
        #             ref_bone_name = 'c_slider_small_ref_parent'
        #         if self.new_range == 'ALL':
        #             ref_bone_name = 'c_slider_ref_parent'
        #         ref_bone = c_rig.pose.bones.get(ref_bone_name)
        #         if ref_bone:
        #             b.custom_shape = ref_bone.custom_shape
        if self.new_range == 'ALL':
            self.report(
                {'INFO'}, 'New Range applied. Make sure to allow negative slider ranges for all Shape Keys.')
        else:
            self.report(
                {'INFO'}, 'New Range applied. Only positive Shape Key values utilized.')
        if self.reconnect:
            bpy.ops.faceit.setup_control_drivers()
        return {'FINISHED'}


class FACEIT_OT_SetCustomControllerSliderRange(bpy.types.Operator):
    '''Set the slider ranges on all controllers. Value in [Full range (-1,1), Positive range (0,1)]'''
    bl_idname = 'faceit.set_custom_controller_slider_range'
    bl_label = 'Set Range for Custom Controllers'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    new_range: EnumProperty(
        items=(
            ('ALL', 'Full Range', 'this will animate positive and negative shape keys'),
            ('POS', 'Only Positive Range',
             'this will animate only positive shape key ranges')
        )
    )
    affect_controllers: EnumProperty(
        items=(
            ('ALL', 'All Controllers', 'this will affect all controllers'),
            ('SELECTED', 'Selected Controllers',
             'this will affect only selected custom controllers')
        )
    )
    reconnect: BoolProperty(
        name='Reconnect Drivers',
        default=True,
    )

    @ classmethod
    def poll(cls, context):
        if context.mode in ('OBJECT', 'POSE'):
            ctrl_rig = futils.get_faceit_control_armature()
            if ctrl_rig and context.scene.faceit_face_objects:
                if ctrl_rig.library or ctrl_rig.override_library:
                    return False
                return True

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='Slider Ranges')
        row = layout.row()
        row.prop(self, 'new_range', expand=True)
        row = layout.row()
        row.prop(self, 'reconnect', expand=True)

    def execute(self, context):
        c_rig = futils.get_faceit_control_armature()
        if not c_rig:
            self.report(
                {'WARNING'}, 'The control rig has to be generated first.')
            return {'CANCELLED'}
        else:
            bpy.ops.faceit.remove_control_drivers(
                'EXEC_DEFAULT', remove_all=False)

        retarget_list = context.scene.faceit_arkit_retarget_shapes
        custom_shape_names = [
            t.name for t in c_rig.faceit_crig_targets if t.name not in retarget_list]
        if self.affect_controllers == 'SELECTED':
            selected_bones = [b for b in c_rig.pose.bones if b.bone.select]
        else:
            selected_bones = c_rig.pose.bones
        # selected_bones = [b for b in selected_bones if b.name == custom_shape_names]
        affected_bones = []
        # for b in selected_bones:
        #     if

        for b in c_rig.pose.bones:
            if 'forceMouthClose' in b.name:
                continue
            if 'slider_parent' in b.name:
                if self.new_range == 'POS':
                    ref_bone_name = 'c_slider_small_ref_parent'
                if self.new_range == 'ALL':
                    ref_bone_name = 'c_slider_ref_parent'
                ref_bone = c_rig.pose.bones.get(ref_bone_name)
                if ref_bone:
                    b.custom_shape = ref_bone.custom_shape

            bone = c_rig.pose.bones.get(bone_name)
            if not bone:
                continue
            for c in bone.constraints:
                if c.type in ('LIMIT_LOCATION', 'LIMIT_ROTATION', 'LIMIT_SCALE'):
                    main_dir = dr_info.get('main_dir', 1)
                    _transform, axis = transform_type.split('_')
                    if axis == 'X':
                        if main_dir == -1:
                            new_value = 0 if self.new_range == 'POS' else -c.min_x
                            c.max_x = new_value
                        else:
                            new_value = 0 if self.new_range == 'POS' else -c.max_x
                            c.min_x = new_value
                    elif axis == 'Y':
                        if main_dir == -1:
                            new_value = 0 if self.new_range == 'POS' else -c.min_y
                            c.max_y = new_value
                        else:
                            new_value = 0 if self.new_range == 'POS' else -c.max_y
                            c.min_y = new_value
                    elif axis == 'Z':
                        if main_dir == -1:
                            new_value = 0 if self.new_range == 'POS' else -c.min_z
                            c.max_z = new_value
                        else:
                            new_value = 0 if self.new_range == 'POS' else -c.max_z
                            c.min_z = new_value
                    # account for scale on nose sneer...
                    elif axis == 'AVG':
                        if main_dir == -1:
                            new_value = 1 if self.new_range == 'POS' else 1.5
                            c.max_x, c.max_y, c.max_z = (new_value,) * 3
                        else:
                            pass
        if self.new_range == 'ALL':
            self.report(
                {'INFO'}, 'New Range applied. Make sure to allow negative slider ranges for all Shape Keys.')
        else:
            self.report(
                {'INFO'}, 'New Range applied. Only positive Shape Key values utilized.')
        if self.reconnect:
            bpy.ops.faceit.setup_control_drivers()
        return {'FINISHED'}


class FACEIT_OT_ConstrainToBodyRig(bpy.types.Operator):
    '''Set child of constraint for the active bone in a selected armature'''
    bl_idname = 'faceit.constrain_to_body_rig'
    bl_label = 'Set Child Of'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    target_bone: EnumProperty(
        name='Target',
        items=(
            ('HEAD', 'Head Bone', 'Head Bone set in mocap tab'),
            ('ACTIVE', 'Active Bone', 'The selected bone in the 3d viewport.')
        ),
        default='ACTIVE'
    )

    @ classmethod
    def poll(cls, context):
        c_rig = futils.get_faceit_control_armature()
        if c_rig is not None:
            return True

    def execute(self, context):
        c_rig = futils.get_faceit_control_armature()
        bone = None
        if self.target_bone == 'ACTIVE':
            rig = context.active_object
            if rig == c_rig:
                self.report({'ERROR'}, 'Select another armature as target')
                return {'CANCELLED'}
            bone = context.active_pose_bone
            if bone is None:
                self.report(
                    {'ERROR'}, 'A bone needs to be selected as target!')
                return {'CANCELLED'}
        else:
            rig = context.scene.faceit_head_target_object
            if rig and rig.type == 'ARMATURE':
                bone = rig.pose.bones.get(context.scene.faceit_head_sub_target)
            if bone is None:
                self.report({'WARNING'}, 'No Head bone specified.')
                return {'CANCELLED'}
        reset_pose(rig)
        main_bone = c_rig.pose.bones.get('c_face_main')
        c_found = c_rig.constraints.get('Child Of Body')
        if c_found:
            c_rig.constraints.remove(c_found)
        c_found = main_bone.constraints.get('Child Of Body')
        if c_found:
            main_bone.constraints.remove(c_found)
        # Create the new constraint
        c = main_bone.constraints.new('CHILD_OF')
        c.name = 'Child Of Body'
        c.target = rig
        c.subtarget = bone.name
        return {'FINISHED'}
