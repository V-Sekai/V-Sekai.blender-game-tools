import bpy
from addon_utils import check
from bpy.props import BoolProperty

from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..retargeting import retarget_list_utils as rutils


class FACEIT_OT_SetupAddRoutes(bpy.types.Operator):
    '''Setup the OSC connection with addroutes addon for all registered objects'''
    bl_idname = 'faceit.add_routes'
    bl_label = 'Setup FaceCap OSC Routes'
    bl_options = {'UNDO', 'INTERNAL'}

    reorder_shape_keys: BoolProperty(
        name='Auto Reorder',
        default=True,
        description='The Face Cap OSC messages are received in a predefined order. The Shape Key Indices need to match that order, otherwise the motion will look weird at best.'
    )

    @classmethod
    def poll(self, context):
        if context.mode == 'OBJECT':
            return len(context.scene.faceit_face_objects) >= 1

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        scene = context.scene
        setup_any = False

        # Check loaded state of addon AddRoutes
        if not check(module_name="AddRoutes")[1]:
            self.report({'WARNING'}, 'Install AddRoutes first!')
            return {'CANCELLED'}

        read_shape_keys, read_head_rotation, read_eye_rotation = \
            scene.faceit_mocap_motion_types.read_settings()
        if not(read_shape_keys or read_head_rotation or read_eye_rotation):
            self.report({'ERROR'}, 'You did not specify any target motion')
            return {'CANCELLED'}

        warnings = False

        bpy.ops.faceit.clear_routes()

        retarget_list = scene.faceit_retarget_shapes
        target_shapes = rutils.get_all_set_target_shapes(retarget_list)
        # scene_shape_keys = sk_utils.get_shape_key_names_from_objects()

        if read_shape_keys:
            face_objects = futils.get_faceit_objects_list()
            for obj in face_objects:

                if sk_utils.has_shape_keys(obj):
                    pass
                else:
                    self.report({'WARNING'}, 'Skipping object {}, because it does not hold any shapekeys'.format(obj.name))
                    warnings = True
                    continue

                if target_shapes:
                    shapes_not_found = [s for s in target_shapes if s not in obj.data.shape_keys.key_blocks]
                    if shapes_not_found:
                        self.report(
                            {'WARNING'},
                            'ARKIT Target Shape Keys {} could not be found on object {}. \n Check expression panel for Face Cap order. You should consider to add placeholder shape keys to meet Face Cap requirements.'.
                            format(shapes_not_found, obj.name))
                        warnings = True

                if self.reorder_shape_keys:
                    bpy.ops.faceit.reorder_keys('EXEC_DEFAULT', order='FACECAP',
                                                keep_motion=True, process_objects=obj.name)

                setup_any = True
                bpy.ops.addroutes.addprop()
                new_prop = scene.MOM_Items[-1]
                new_prop.id.objects = obj
                new_prop.data_path = 'data.shape_keys.key_blocks[VAR].value'
                new_prop.is_multi = True
                new_prop.number = 52
                new_prop.offset = 1
                new_prop.VAR_use = 'dp'
                new_prop.engine = 'OSC'
                new_prop.osc_address = '/W'
                new_prop.osc_select_rank = 1
                new_prop.osc_select_n = 51
                new_prop.mode = 'Receive'
                if scene.faceit_record_face_cap:
                    new_prop.record = True

        # Setup for head rotation/location
        if read_head_rotation:
            head_empty = futils.get_object(scene.faceit_mocap_target_head)
            if head_empty:

                reroute_YZ = {
                    0: 0,
                    1: 2,
                    2: 1,
                }

                # Rotation
                for i in range(3):

                    bpy.ops.addroutes.addprop()
                    new_prop = scene.MOM_Items[-1]
                    new_prop.id.objects = head_empty
                    new_prop.data_path = 'rotation_euler'
                    new_prop.VAR_use = 'dp'
                    new_prop.engine = 'OSC'
                    new_prop.osc_address = '/HR'
                    new_prop.mode = 'Receive'
                    # rerouting YZ
                    new_prop.array = i
                    if i == 1:
                        new_prop.eval_mode = 'expr'
                        new_prop.eval_expr = 'IN * -1'
                    new_prop.osc_select_rank = reroute_YZ[i]
            else:
                self.report({'WARNING'}, 'You need to setup a target to capture head motion')

        # Setup for Eyes rotations
        if read_eye_rotation:
            eyes = list(filter(None, [futils.get_object(scene.faceit_mocap_target_eye_l),
                                      futils.get_object(scene.faceit_mocap_target_eye_r)]))
            for eye_obj in eyes:

                for i in range(2):

                    bpy.ops.addroutes.addprop()
                    new_prop = scene.MOM_Items[-1]
                    new_prop.id.objects = eye_obj
                    new_prop.data_path = 'rotation_euler'
                    new_prop.VAR_use = 'dp'
                    new_prop.engine = 'OSC'
                    new_prop.osc_address = '/ELR' if eye_obj.name == scene.faceit_mocap_target_eye_l else '/ERR'
                    new_prop.mode = 'Receive'
                    # rerouting YZ
                    new_prop.array = i
                    new_prop.osc_select_rank = i
            if not eyes:
                self.report({'WARNING'}, 'You need to setup a target to capture eyes motion')

        # reports
        if setup_any:
            if warnings:
                self.report(
                    {'WARNING'},
                    'Setting up OSC routing finished with Warnings. Please see the console output for details!')
            else:
                self.report({'INFO'}, 'Setting up AddRoutes all registered objects with shapekeys.')

        # Set record to update props
        context.scene.faceit_record_face_cap = context.scene.faceit_record_face_cap

        return {'FINISHED'}


class FACEIT_OT_SetupClearRoutes(bpy.types.Operator):
    '''Clear all addroutes items'''
    bl_idname = 'faceit.clear_routes'
    bl_label = 'Clear OSC routes'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return True

    def execute(self, context):
        if not check(module_name="AddRoutes")[1]:
            self.report({'WARNING'}, 'Install AddRoutes first!')
            return {'CANCELLED'}
        scene = context.scene
        scene.faceit_record_face_cap = False
        scene.MOM_Items.clear()
        return{'FINISHED'}


class FACEIT_OT_FaceCapEmpty(bpy.types.Operator):
    '''Create an empty as rotation/location target'''
    bl_idname = 'faceit.face_cap_empty'
    bl_label = 'Create Face Cap Empty'
    bl_options = {'UNDO'}

    test: bpy.props.StringProperty(name='bla')
    face_cap_empty: bpy.props.EnumProperty(
        items=[
            ('HEAD', 'Head', 'Head rot loc'),
            ('EYES', 'Eyes', 'Eyes rot'),
            ('ALL', 'All', 'All Targets')
        ],
        default='ALL'
    )

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return True

    def execute(self, context):
        scene = context.scene
        rig = futils.get_faceit_armature()

        if not rig:
            self.report({'WARNING'}, 'The FaceitRig is needed for position reference.' +
                        'Regenerate it or choose custom object')
            return{'CANCELLED'}

        def clear_previously_generated_targets(target_names):
            target_names = [target_names]
            for target in target_names:
                target = futils.get_object(target)
                if target:
                    bpy.data.objects.remove(target)

        futils.clear_object_selection()

        empty_type = self.face_cap_empty
        target_bones = {}
        if empty_type in ('HEAD', 'ALL'):
            target_name = 'FaceCapHeadTarget'
            target_bones[rig.pose.bones['DEF-face']] = target_name
            scene.faceit_mocap_target_head = target_name
            clear_previously_generated_targets(target_name)
        if empty_type in ('EYES', 'ALL'):
            target_name_L = 'FaceCapEyeLeft'
            target_bones[rig.pose.bones['master_eye.L']] = target_name_L
            scene.faceit_mocap_target_eye_l = target_name_L
            target_name_R = 'FaceCapEyeRight'
            target_bones[rig.pose.bones['master_eye.R']] = target_name_R
            scene.faceit_mocap_target_eye_r = target_name_R
            clear_previously_generated_targets([target_name_L, target_name_R])

        for bone, name in target_bones.items():
            matrix_final = rig.matrix_world @ bone.matrix
            size = [bone.length * 0.5] * 3

            obj_empty = bpy.data.objects.new(name, None)
            faceit_collection = futils.get_faceit_collection()
            if faceit_collection:
                faceit_collection.objects.link(obj_empty)

            obj_empty.location = matrix_final.decompose()[0]    # decompose yields loc rot scl as list of Vectors
            obj_empty.show_in_front = True
            obj_empty.show_axis = True
            obj_empty.scale = size

            obj_empty.animation_data_create()

            futils.set_active_object(obj_empty.name)

            # Freeze transformations
            bpy.ops.object.transforms_to_deltas(mode='LOC')
            # obj_empty.delta_rotation_euler[0] = np.radians(90)

        return{'FINISHED'}


class FACEIT_OT_PopulateFaceCapEmpty(bpy.types.Operator):
    bl_idname = "faceit.populate_face_cap_empty"
    bl_label = "Populate Empty"
    bl_options = {'UNDO'}

    face_cap_empty: bpy.props.EnumProperty(
        items=[
            ('HEAD', 'Head', 'Head rot loc'),
            ('EYE_L', 'Eyes Left', 'Eyes rot left'),
            ('EYE_R', 'Eye Right', 'Eyes rot right')
        ],
        default='HEAD'
    )

    @classmethod
    def poll(cls, context):
        if context.object:
            return True

    def execute(self, context):
        scene = context.scene
        active_object = context.object
        if not active_object.animation_data:
            active_object.animation_data_create()
        target = self.face_cap_empty
        if target == 'HEAD':
            scene.faceit_mocap_target_head = active_object.name
        if target == 'EYE_L':
            scene.faceit_mocap_target_eye_l = active_object.name
        if target == 'EYE_R':
            scene.faceit_mocap_target_eye_r = active_object.name
        return {'FINISHED'}
