import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty


from ..core import shape_key_utils
from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from . import control_rig_data as ctrl_data
from . import control_rig_utils as ctrl_utils


class FACEIT_OT_UpdateControlRig(bpy.types.Operator):
    '''Update the active Faceit control rig object'''
    bl_idname = 'faceit.update_control_rig'
    bl_label = 'Update Control Rig'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(self, context):
        ctrl_rig = futils.get_faceit_control_armature()
        if ctrl_rig:
            if ctrl_rig.library or ctrl_rig.override_library:
                return False
            ctrl_rig_version = ctrl_rig.get('ctrl_rig_version', 1.0)
            return ctrl_rig_version < ctrl_data.CNTRL_RIG_VERSION

    def execute(self, context):
        scene = context.scene
        c_rig = futils.get_faceit_control_armature()
        futils.set_hide_obj(c_rig, False)

        crig_version = c_rig.get('ctrl_rig_version', 1.0)

        if crig_version == 1.0:
            if 'FaceitControlRig' in c_rig.name:
                if not 'ctrl_rig_id' in c_rig:
                    c_rig['ctrl_rig_id'] = ctrl_data.get_random_rig_id()

        if crig_version <= 1.2:
            if not context.scene.faceit_face_objects:
                self.report(
                    {'WARNING'},
                    'Cannot populate the control rig objects. Please load them manually or register them in setup panel first.')
            ctrl_utils.populate_control_rig_target_shapes_from_scene(c_rig, update=True)
            if not context.scene.faceit_retarget_shapes:
                self.report(
                    {'WARNING'},
                    'Cannot populate the control rig target shapes.')
            ctrl_utils.populate_control_rig_target_objects_from_scene(c_rig)

        c_rig['ctrl_rig_version'] = ctrl_data.CNTRL_RIG_VERSION

        try:
            bpy.ops.faceit.setup_control_drivers()
        except:
            pass

        return{'FINISHED'}


class FACEIT_OT_ResetRegions(bpy.types.Operator):
    ''' Reset the Regions property to default values '''
    bl_idname = 'faceit.reset_regions'
    bl_label = 'Reset Regions'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(self, context):
        return True

    def execute(self, context):
        scene = context.scene
        for p in scene.faceit_face_regions.keys():
            scene.faceit_face_regions.property_unset(p)

        return{'FINISHED'}


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

    @classmethod
    def poll(self, context):
        if context.mode in ('OBJECT', 'POSE'):
            ctrl_rig = futils.get_faceit_control_armature()
            if ctrl_rig:
                if ctrl_rig.library or ctrl_rig.override_library:
                    return False
                # return (context.scene.faceit_face_objects or context.scene.faceit_retarget_shapes)
                return True

    def invoke(self, context, event):

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):

        layout = self.layout

        c_rig = futils.get_faceit_control_armature()

        row = layout.row()
        row.label(text='Warning! This will override target shapes and objects'.format(c_rig.name))
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
                ctrl_utils.populate_control_rig_target_objects_from_scene(c_rig)
            else:
                self.report({'WARNING'}, 'Didn\'t find any registered objects to load as control rig target objects.')
        if self.load_arkit_target_shapes:
            if scene.faceit_retarget_shapes:
                ctrl_utils.populate_control_rig_target_shapes_from_scene(c_rig)
            else:
                self.report({'WARNING'}, 'Didn\'t find any arkit target shapes to load as control rig target shapes.')

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

    @classmethod
    def poll(self, context):
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
        row.label(text='Warning! This will override target shapes and objects'.format(c_rig.name))
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
        if c_rig.faceit_crig_objects:
            for ob_item in c_rig.faceit_crig_objects:
                obj = futils.get_object(ob_item.name)
                if obj:
                    target_objects.add(obj)

        # Find the arkit retarget values from stored settings (better than from drivers)
        if c_rig.faceit_crig_targets:
            for shape_item in c_rig.faceit_crig_targets:
                for ts in shape_item.target_shapes:
                    try:
                        arkit_target_shapes[shape_item.name].add(ts.name)
                    except KeyError:
                        arkit_target_shapes[shape_item.name] = set([ts.name])

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
                return{'CANCELLED'}
        if self.load_arkit_target_shapes:
            if arkit_target_shapes:
                scene.faceit_retarget_shapes.clear()
                # Initialize standart values
                bpy.ops.faceit.init_retargeting('EXEC_DEFAULT')
                retarget_list = scene.faceit_retarget_shapes

                for item in retarget_list:
                    item.target_shapes.clear()
                    new_target_shapes = arkit_target_shapes[item.name]
                    for i, target_shape_name in enumerate(new_target_shapes):

                        target_item = item.target_shapes.add()
                        target_item.parent_idx = item.index
                        target_item.index = i
                        target_item.name = target_shape_name
                        continue
                self.report({'INFO'}, 'Loading ARKit target shapes to ARKit Shapes List')
            else:
                self.report(
                    {'ERROR'},
                    'Can\'t find target shapes. Please update the Control Rig first.')

        if target_objects and arkit_target_shapes:
            self.report({'INFO'}, 'Updated registered objects and arkit target shapes.')

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
            ('VISIBLE', 'Visible', 'Effect only the currently visible regions in the amplify list.'),
            ('ALL', 'All', 'Effect all expressions in the amplify list.'),
        ),
        default='VISIBLE'
    )

    @classmethod
    def poll(self, context):
        return context.scene.faceit_retarget_shapes and context.scene.faceit_control_armature

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

        scene = context.scene
        c_rig = futils.get_faceit_control_armature()
        target_list = c_rig.faceit_crig_targets

        for item in target_list:
            if self. regions == 'VISIBLE':
                active_region_dict = context.scene.faceit_face_regions.get_active_regions()

                if not active_region_dict.get(item.region.lower(), False):
                    continue
            item.amplify = self.amplify_value

        for region in bpy.context.area.regions:
            region.tag_redraw()

        return{'FINISHED'}


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

    # shape_index: IntProperty(
    #     name='RetargetList Index',
    #     default=0,
    # )

    @classmethod
    def poll(self, context):
        if context.mode in ('OBJECT', 'POSE'):
            crig = futils.get_faceit_control_armature()
            if crig != None and crig == context.object and not futils.get_hide_obj(crig):
                return True

    def execute(self, context):

        scene = context.scene

        c_rig = futils.get_faceit_control_armature()

        if not c_rig:
            self.report({'ERROR'}, 'Control Rig not found in scene')

        bone_name = ''

        try:
            dr_dict = ctrl_data.control_rig_drivers_dict[self.expression]

            bone_name, _, _ = ctrl_data.get_bone_settings_from_driver_dict(dr_dict)

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
            return{'CANCELLED'}

        if context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        for b in c_rig.data.bones:
            b.select = False
        c_rig.data.bones.active = pose_bone.bone
        pose_bone.bone.select = True

        # scene.faceit_retarget_shapes_index = self.shape_index
        return{'FINISHED'}


class FACEIT_OT_ControlRigSetSliderRanges(bpy.types.Operator):
    '''Set the slider ranges on all controllers. Value in [Full range (-1,1), Positive range (0,1)]'''
    bl_idname = 'faceit.control_rig_set_slider_ranges'
    bl_label = 'Set Ranges for Control Rig'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    new_range: EnumProperty(
        items=(
            ('ALL', 'Full Range', 'this will animate positive and negative shape keys'),
            ('POS', 'Only Positive Range', 'this will animate only positive shape key ranges')
        )
    )

    reconnect: BoolProperty(
        name='Reconnect Drivers',
        default=True,
    )

    @classmethod
    def poll(self, context):
        if context.mode in ('OBJECT', 'POSE'):
            ctrl_rig = futils.get_faceit_control_armature()
            if ctrl_rig and context.scene.faceit_face_objects:
                if ctrl_rig.library or ctrl_rig.override_library:
                    return False
                return True

    def invoke(self, context, event):
        # if self.all_objects:
        # if context.scene.faceit_weights_restorable:
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
            self.report({'WARNING'}, 'The control rig has to be generated first.')
            return{'CANCELLED'}
        else:
            bpy.ops.faceit.remove_control_drivers('EXEC_DEFAULT', remove_all=False)

        retarget_shapes = context.scene.faceit_retarget_shapes
        for shape_item in retarget_shapes:
            arkit_name = shape_item.name
            dr_info = ctrl_data.control_rig_drivers_dict[arkit_name]
            if dr_info.get('range', 'pos') == 'all':
                bone_name, transform_type, transform_space = ctrl_data.get_bone_settings_from_driver_dict(dr_info)
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
                                c.max_x, c.max_y, c.max_z = (new_value,)*3
                            else:
                                pass
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

        if self.new_range == 'ALL':
            self.report({'INFO'}, 'New Range applied. Make sure to allow negative slider ranges for all Shape Keys.')
        else:
            self.report({'INFO'}, 'New Range applied. Only positive Shape Key values utilized.')

        if self.reconnect:
            bpy.ops.faceit.setup_control_drivers()

        return {'FINISHED'}


class FACEIT_OT_ConstrainToBodyRig(bpy.types.Operator):
    '''Set child of constraint for the active bone in a selected armature'''
    bl_idname = 'faceit.constrain_to_body_rig'
    bl_label = 'Set Child Of'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(self, context):
        # if context.mode == ''
        c_rig = futils.get_faceit_control_armature()
        if c_rig is not None:
            active_obj = context.active_object
            if active_obj and active_obj is not c_rig:
                return active_obj.type == 'ARMATURE'

    def execute(self, context):

        # scene = context.scene

        c_rig = futils.get_faceit_control_armature()

        rig = context.active_object

        if rig == c_rig:
            self.report({'ERROR'}, 'Select another armature as target')
            return{'CANCELLED'}

        current_mode = context.mode

        rig.data.pose_position = 'REST'

        bpy.ops.object.mode_set(mode='OBJECT')
        futils.clear_object_selection()
        futils.set_active_object(rig.name)
        bpy.ops.object.mode_set(mode='POSE')
        bone = context.active_pose_bone
        if bone == None:
            self.report({'ERROR'}, 'A bone needs to be selected as target!')
            return{'CANCELLED'}

        # bpy.ops.object.mode_set(mode='OBJECT')
        c_found = c_rig.constraints.get('Child Of Body')
        if c_found:
            c_rig.constraints.remove(c_found)
        # if 'Child Of Body' in c_rig.constraints:

        c = c_rig.constraints.new('CHILD_OF')
        c.name = 'Child Of Body'
        c.target = rig
        c.subtarget = bone.name

        bpy.ops.object.mode_set(mode=current_mode)
        rig.data.pose_position = 'POSE'

        return{'FINISHED'}
