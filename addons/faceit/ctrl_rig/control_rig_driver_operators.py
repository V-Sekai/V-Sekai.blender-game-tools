import bpy
from bpy.props import BoolProperty

from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import retarget_list_utils as rutils
from ..core import shape_key_utils
from ..core.fc_dr_utils import clear_invalid_drivers
from . import control_rig_data as ctrl_data
from . import control_rig_utils as ctrl_utils


class FACEIT_OT_SetupControlDrivers(bpy.types.Operator):
    '''Setup drivers to control the shape keys with control rig'''
    bl_idname = 'faceit.setup_control_drivers'
    bl_label = 'Connect Control Rig'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    debug: BoolProperty(
        default=True,
        options={'HIDDEN'}
    )

    @classmethod
    def poll(cls, context):
        if context.mode in ('OBJECT', 'POSE'):
            c_rig = futils.get_faceit_control_armature()
            if c_rig:
                return c_rig.faceit_crig_objects

    def execute(self, context):
        scene = context.scene

        c_rig = futils.get_faceit_control_armature()
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False
        futils.set_hide_obj(c_rig, False)

        bpy.ops.faceit.remove_control_drivers('EXEC_DEFAULT', remove_all=False)

        crig_targets = c_rig.faceit_crig_targets
        # crig_objects = []
        # for item in c_rig.faceit_crig_objects:
        #     obj = futils.get_object(item.name)
        #     if obj is not None:
        #         crig_objects.append(obj)
        crig_objects = ctrl_utils.get_crig_objects_list(c_rig)

        if not crig_targets:
            self.report({'ERROR'}, 'Couldn\'t find any target shapes. Please update the control rig first.')
            return {'CANCELLED'}

        if not crig_objects:
            self.report({'ERROR'}, 'Couldn\'t find any target objects. Please specify them or update the control rig first.')
            return {'CANCELLED'}

        connected_any = False

        for obj in crig_objects:

            missing_shapes = []

            shapekeys = obj.data.shape_keys

            if not shapekeys:
                self.report({'WARNING'}, 'Object {} contains no Shape Keys'.format(obj.name))
                continue

            if not hasattr(shapekeys, 'key_blocks'):
                self.report({'WARNING'}, 'Object {} contains no Shape Keys'.format(obj.name))
                continue
            jaw_open_name = 'jawOpen'
            jaw_open_item = crig_targets.get('jawOpen')
            if jaw_open_item:
                jaw_open_target = jaw_open_item.target_shapes[0]
                if jaw_open_target:
                    jaw_open_name = jaw_open_target.name

            for shape_item in crig_targets:

                shape_name = shape_item.name
                target_shape_list = [item.name for item in shape_item.target_shapes]

                for target_shape in target_shape_list:

                    result, _bone_name = ctrl_data.get_driver_from_retarget_dictionary_fixed_slider_range(
                        shape_name,
                        target_shape,
                        c_rig,
                        shapekeys,
                        custom_slider=shape_item.custom_slider,
                        jaw_open_shape=jaw_open_name
                    )

                    if result:
                        connected_any = True
                    else:
                        missing_shapes.append(target_shape)

        if connected_any:
            print('Connected')
            self.report({'INFO'}, 'Connected Control Rig')

        if context.preferences.filepaths.use_scripts_auto_execute is False:
            self.report({'WARNING'}, 'Please allow Auto Execution of Python Scripts for the Control Rig Drivers to work!')
        scene.tool_settings.use_keyframe_insert_auto = auto_key
        return {'FINISHED'}


class FACEIT_OT_RemoveControlDrivers(bpy.types.Operator):
    '''Remove all drivers for active control rig'''
    bl_idname = 'faceit.remove_control_drivers'
    bl_label = 'Disconnect Control Rig'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    remove_all: BoolProperty(
        name='Remove All Drivers',
        default=False,
        description='Removes found drivers from shape keys. Tries to remove only drivers from the ARKit shapes if False.',
        options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        if context.mode in ('OBJECT', 'POSE'):
            c_rig = futils.get_faceit_control_armature()
            if c_rig:
                return True

    def execute(self, context):
        scene = context.scene
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False

        use_faceit_scene_settings_fallback = bool(len(futils.get_faceit_control_armatures()) <= 1)

        clear_any = False
        c_rig = futils.get_faceit_control_armature()
        if c_rig:
            faceit_objects = ctrl_utils.get_crig_objects_list(c_rig)
            all_target_shapes = rutils.get_all_set_target_shapes(c_rig.faceit_crig_targets)
            if not faceit_objects:
                self.report({'WARNING'}, 'Couldn\'t find any target objects. Please update the control rig.')
                if use_faceit_scene_settings_fallback:
                    faceit_objects = futils.get_faceit_objects_list()
            if not all_target_shapes:
                self.report({'WARNING'}, 'Couldn\'t find any target shapes. Please update the control rig.')
                if use_faceit_scene_settings_fallback:
                    all_target_shapes = rutils.get_all_set_target_shapes(scene.faceit_arkit_retarget_shapes)

            for obj in faceit_objects:
                if shape_key_utils.has_shape_keys(obj):
                    shapekeys = obj.data.shape_keys
                else:
                    continue

                if not shapekeys.animation_data:
                    continue

                if self.remove_all:
                    for dr in shapekeys.animation_data.drivers:
                        shapekeys.driver_remove(dr.data_path, -1)
                    continue

                # Only remove drivers from ARKit target shape keys!!!
                for target_shape in all_target_shapes:
                    dp = 'key_blocks["{}"].value'.format(target_shape)
                    dr = shapekeys.animation_data.drivers.find(dp)
                    if dr:
                        shapekeys.animation_data.drivers.remove(dr)
                        shapekeys.key_blocks[target_shape].value = 0
                        clear_any = True

        if not clear_any:
            self.report({'INFO'}, "No drivers found on the set target objects.")
        else:
            if c_rig:
                self.report({'INFO'}, 'Disconnected Control Rig {}'.format(c_rig.name))

        for region in context.area.regions:
            region.tag_redraw()

        clear_invalid_drivers()

        scene.frame_set(scene.frame_current)
        scene.tool_settings.use_keyframe_insert_auto = auto_key

        return {'FINISHED'}


class FACEIT_OT_ClearOldCtrlRigData(bpy.types.Operator):
    '''Find inactive control rigs, remove them and clear eventual drivers.'''
    bl_idname = 'faceit.clear_old_ctrl_rig_data'
    bl_label = 'Purge Old Control Rigs and Drivers'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False

        # Check for control armatures that are not referenced in scene.
        old_control_rig_objects = []

        for obj in bpy.data.objects:
            if obj.users == 0:
                if obj.name not in context.scene.objects:
                    if 'ctrl_rig_id' in obj:
                        old_control_rig_objects.append(obj)
                        continue
                    else:
                        if 'FaceitControlRig' in obj.name:
                            old_control_rig_objects.append(obj)
        use_faceit_scene_settings_fallback = bool(len(futils.get_faceit_control_armatures()) <= 1)

        for c_rig in old_control_rig_objects:
            faceit_objects = ctrl_utils.get_crig_objects_list(c_rig)
            all_target_shapes = rutils.get_all_set_target_shapes(c_rig.faceit_crig_targets)
            if not faceit_objects:
                self.report({'WARNING'}, 'Couldn\'t find any target objects. Please update the control rig.')
                if use_faceit_scene_settings_fallback:
                    faceit_objects = futils.get_faceit_objects_list()
            if not all_target_shapes:
                self.report({'WARNING'}, 'Couldn\'t find any target shapes. Please update the control rig.')
                if use_faceit_scene_settings_fallback:
                    all_target_shapes = rutils.get_all_set_target_shapes(scene.faceit_arkit_retarget_shapes)

            for obj in faceit_objects:
                if shape_key_utils.has_shape_keys(obj):
                    shapekeys = obj.data.shape_keys
                else:
                    continue

                if not shapekeys.animation_data:
                    continue

                # Only remove drivers from ARKit target shape keys!!!
                for target_shape in all_target_shapes:
                    dp = 'key_blocks["{}"].value'.format(target_shape)
                    dr = shapekeys.animation_data.drivers.find(dp)
                    if dr:
                        shapekeys.animation_data.drivers.remove(dr)
                        shapekeys.key_blocks[target_shape].value = 0
                        clear_any = True
            self.report({'INFO'}, 'Removing old Control Rig {}'.format(c_rig.name))
            c_rig_arma = c_rig.data
            bpy.data.objects.remove(c_rig)
            bpy.data.armatures.remove(c_rig_arma)

        for region in context.area.regions:
            region.tag_redraw()

        clear_invalid_drivers()

        scene.frame_set(scene.frame_current)
        scene.tool_settings.use_keyframe_insert_auto = auto_key

        return {'FINISHED'}
