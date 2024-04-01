import bpy
from math import pi as PI

from bpy.app.handlers import persistent

from ..properties.mocap_scene_properties import Mocap_Engine_Properties
from ..core.faceit_data import get_engine_settings, get_shape_data_for_mocap_engine
from .mocap_base import MocapImporterBase
from .mocap_importers import LiveAnimator
from .osc_receiver import QueueManager, Receiver, osc_queue
from ..core.faceit_utils import get_faceit_objects_list, restore_scene_state, save_scene_state, ui_refresh_all, get_faceit_control_armature, set_active_object, get_object_mode_from_context_mode, clear_active_object, set_hide_obj
from ..core.pose_utils import get_edit_bone_roll, reset_pb, reset_pose, restore_saved_pose, save_pose
from ..ctrl_rig.control_rig_utils import get_crig_objects_list, is_control_rig_connected

queue_mgr: QueueManager = QueueManager()
receiver: Receiver = Receiver(queue_mgr)
live_animator: LiveAnimator = LiveAnimator()
reconnect_ctrl_rig: bool = False
head_base_rotation = None
head_base_location = None


update_queries = 60
queries_per_second = 200


def process_osc_queue():
    '''runs persistent and processes all incoming messages.'''
    global osc_queue
    if osc_queue and receiver.enabled:
        anim_list = osc_queue[:-update_queries:-1]
        for _ in range(update_queries):
            if not anim_list:
                break
            else:
                data = anim_list.pop()
                live_animator.process_data(data)
        return 1 / queries_per_second
    return .01


def get_head_base_transform():
    return head_base_rotation, head_base_location


class FACEIT_OT_ReceiverStart(bpy.types.Operator):
    '''Start receiving animation data from the given connection. Enable the recorder in order to import recorded data'''
    bl_idname = "faceit.receiver_start"
    bl_label = "Start Receiver"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        global receiver, live_animator, reconnect_ctrl_rig
        bpy.app.timers.register(process_osc_queue, persistent=True)
        state_dict = save_scene_state(context)
        live_animator.clear_animation_targets()
        scene = context.scene
        engine_settings: Mocap_Engine_Properties = get_engine_settings(scene.faceit_live_source)
        animate_loc = engine_settings.animate_head_location
        animate_rot = engine_settings.animate_head_rotation
        animate_eye_bones = engine_settings.animate_eye_rotation_bones
        animate_eye_shapes = engine_settings.animate_eye_rotation_shapes
        animate_shapes = engine_settings.animate_shapes
        if not (animate_loc or animate_rot or animate_shapes or animate_eye_bones or animate_eye_shapes):
            self.report({'ERROR'}, "You need to enable at least one type of motion.")
            return {'CANCELLED'}
        live_animator.init_new_recording()
        live_animator.set_rotation_units(engine_settings.rotation_units)
        # Shapes animation properties
        live_animator.flip_animation = engine_settings.mirror_x
        live_animator.animate_shapes = animate_shapes
        live_animator.animate_head_location = animate_loc
        live_animator.animate_head_rotation = animate_rot
        live_animator.animate_eye_shapes = animate_eye_shapes
        live_animator.animate_eye_bones = animate_eye_bones
        if animate_eye_shapes or animate_eye_bones:
            live_animator.set_eye_bones_smoothing(
                use_smoothing=engine_settings.smooth_eye_look_animation,
                smooth_filter='SMA',
                smooth_window=engine_settings.smooth_window_eye_bones

            )
        if animate_shapes or animate_eye_shapes:
            live_animator.set_use_region_filter(engine_settings.use_regions_filter)
            live_animator.set_face_smoothing(
                use_smoothing=engine_settings.use_smooth_face_filter,
                smooth_filter='SMA',
                smooth_regions=engine_settings.smooth_regions.get_active_regions(),
                smooth_window=engine_settings.smooth_window_face,
            )
            live_animator.set_face_regions_dict(engine_settings.region_filter.get_active_regions())
            source_shape_ref = list(get_shape_data_for_mocap_engine(scene.faceit_live_source))
            live_animator.set_source_shape_reference(source_shape_ref)
            # Get objects and target shapes
            ctrl_rig = scene.faceit_control_armature
            reconnect_ctrl_rig = False
            if ctrl_rig:
                if is_control_rig_connected(ctrl_rig):
                    if scene.faceit_auto_disconnect_ctrl_rig:
                        objects = get_crig_objects_list(ctrl_rig)
                        target_shapes = ctrl_rig.faceit_crig_targets
                        bpy.ops.faceit.remove_control_drivers('EXEC_DEFAULT')
                        reconnect_ctrl_rig = True
            if reconnect_ctrl_rig is False:
                objects = get_faceit_objects_list()
                target_shapes = scene.faceit_arkit_retarget_shapes
                if not objects:
                    self.report(
                        {'WARNING'},
                        "You need to register the target objects in Setup tab or select a valid control rig.")
                elif not target_shapes:
                    self.report(
                        {'WARNING'},
                        "You need to populate the ARKit target shapes list in the Shapes tab or select a valid control rig.")

            live_animator.set_shape_targets(
                objects=objects,
                retarget_shapes=target_shapes,
                animate_eye_look_shapes=animate_eye_shapes,
                only_eye_look=not animate_shapes,
            )
        # Head animation properties
        if animate_loc or animate_rot:
            head_loc_multiplier = engine_settings.head_location_multiplier
            head_obj = scene.faceit_head_target_object
            head_bone_name = scene.faceit_head_sub_target
            saved_pose = None
            if head_obj:
                if head_obj.type == 'ARMATURE':
                    set_active_object(head_obj.name)
                    set_hide_obj(head_obj, False)
                    # It's important to reset the pose before setting the head targets to get accurate rotation data.
                    saved_pose = save_pose(head_obj)
                    reset_pose(head_obj)
                    dg = context.evaluated_depsgraph_get()
                    dg.update()
                else:
                    global head_base_rotation, head_base_location
                    if head_obj.rotation_mode == 'QUATERNION':
                        head_base_rotation = head_obj.rotation_quaternion.copy()
                    elif head_obj.rotation_mode == 'AXIS_ANGLE':
                        head_base_rotation = head_obj.rotation_axis_angle[:]
                    else:
                        head_base_rotation = head_obj.rotation_euler.copy()
                    head_base_location = head_obj.location.copy()
            live_animator.set_head_targets(
                head_obj=head_obj,
                head_bone_name=head_bone_name,
                head_loc_mult=head_loc_multiplier,
            )
            live_animator.set_head_smoothing(
                use_smoothing=engine_settings.smooth_head,
                smooth_filter='SMA',
                smooth_window=engine_settings.smooth_window_head,
            )
            if saved_pose:
                restore_saved_pose(head_obj, saved_pose)
        if animate_eye_bones:
            saved_pose = None
            eye_rig = context.scene.faceit_eye_target_rig
            if eye_rig is not None:
                eye_L_bone_name = context.scene.faceit_eye_L_sub_target
                eye_R_bone_name = context.scene.faceit_eye_R_sub_target
                set_hide_obj(eye_rig, False)
                saved_pose = save_pose(eye_rig)
                eye_L_bone = eye_rig.pose.bones.get(eye_L_bone_name)
                if eye_L_bone:
                    reset_pb(eye_L_bone)
                eye_R_bone = eye_rig.pose.bones.get(eye_R_bone_name)
                if eye_R_bone:
                    reset_pb(eye_R_bone)
                dg = context.evaluated_depsgraph_get()
                dg.update()
                live_animator.set_eye_targets(
                    eye_rig=eye_rig,
                    eye_L_bone_name=eye_L_bone_name,
                    eye_R_bone_name=eye_R_bone_name,
                )
            if saved_pose:
                restore_saved_pose(eye_rig, saved_pose)
        # if bpy.context.screen.is_animation_playing:
        #     bpy.ops.screen.animation_cancel()
        try:
            receiver.start(scene.faceit_live_source, engine_settings.address, engine_settings.port)
        except OSError as e:
            print('Socket error:', e.strerror)
            self.report({'ERROR'}, 'This port is already in use!')
            return self.cancel(context)
        scene.faceit_osc_receiver_enabled = True
        restore_scene_state(context, state_dict)
        return {'FINISHED'}

    def cancel(self, context):
        global receiver
        receiver.stop()
        queue_mgr.reset()
        return {'CANCELLED'}


def stop_receiver():
    '''Stop the receiver.'''
    receiver.stop()
    try:
        bpy.app.timers.unregister(process_osc_queue)
    except ValueError:
        pass
    bpy.context.scene.faceit_osc_receiver_enabled = False


def cancel_recording():
    '''Stop the receiver and clear recorded data.'''
    stop_receiver()
    clear_data()


def clear_data():
    '''Clear the OSC queue and the live data.'''
    # Reset the OSC queue
    queue_mgr.reset()
    live_animator.clear_animation_data()


class FACEIT_OT_ReceiverStop(bpy.types.Operator):
    '''Stop the active live session. You can import recorded animation data after stoping the session'''
    bl_idname = "faceit.receiver_stop"
    bl_label = "Stop Receiver"
    bl_description = "Stop receiving data from OSC stream."
    bl_options = {'INTERNAL'}

    def execute(self, context):
        global reconnect_ctrl_rig
        if not osc_queue:
            self.report({'WARNING'}, "No recorded data found.")
            bpy.ops.faceit.reset_expression_values('EXEC_DEFAULT')
            bpy.ops.faceit.reset_head_pose('EXEC_DEFAULT')
        stop_receiver()
        ctrl_rig = context.scene.faceit_control_armature
        if ctrl_rig:
            if context.scene.faceit_auto_disconnect_ctrl_rig and reconnect_ctrl_rig:
                bpy.ops.faceit.setup_control_drivers('EXEC_DEFAULT')
        return {'FINISHED'}


class FACEIT_OT_ImportLiveMocap(MocapImporterBase, bpy.types.Operator):
    '''Import the recorded data into a Blender Action in order to permanently store it.'''
    bl_idname = "faceit.import_live_mocap"
    bl_label = "Import OSC Recording"
    bl_description = "Import the recorded data to an animation."

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def _get_engine_specific_settings(self, context):
        self.engine_name = context.scene.faceit_live_source
        self.engine_settings: Mocap_Engine_Properties = context.scene.faceit_live_mocap_settings.get(self.engine_name)
        self.animate_shapes = live_animator.animate_shapes
        self.animate_head_rotation = live_animator.animate_head_rotation
        self.animate_head_location = live_animator.animate_head_location
        self.can_import_head_rotation = self.engine_settings.animate_head_rotation
        self.can_import_head_location = self.engine_settings.animate_head_location
        self.can_import_eye_transforms = self.engine_settings.can_animate_eye_rotation
        self.smooth_window_eye_bones = self.engine_settings.smooth_window_eye_bones
        self.smooth_eye_look_animation = self.engine_settings.smooth_eye_look_animation
        self.smoothing_filter_eye_bones = self.engine_settings.smoothing_filter_eye_bones
        self.smooth_head = self.engine_settings.smooth_head
        self.smoothing_filter_head = self.engine_settings.smoothing_filter_head
        self.smooth_window_head = self.engine_settings.smooth_window_head
        self.animate_eye_rotation_shapes = self.engine_settings.animate_eye_rotation_shapes
        self.animate_eye_rotation_bones = self.engine_settings.animate_eye_rotation_shapes
        self.use_region_filter = live_animator.use_region_filter
        self.flip_animation = live_animator.flip_animation
        self.filename = ""

    def invoke(self, context, event):
        global reconnect_ctrl_rig
        self._get_engine_specific_settings(context)
        self.new_action_name = "LiveRecording"
        if not osc_queue:
            self.report({'WARNING'}, "No recorded data found.")
            return {'CANCELLED'}
        faceit_objects = get_faceit_objects_list()
        if not faceit_objects:
            self.report({'WARNING'}, "You need to register the character meshes in the setup tab.")
        self.set_active_regions(self.engine_settings.region_filter.get_active_regions())
        if get_faceit_control_armature():
            if reconnect_ctrl_rig:
                self.bake_to_control_rig = True
            self.can_bake_control_rig = True
        else:
            self.can_bake_control_rig = False
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def _get_mocap_importer(self):
        return live_animator

    def _get_raw_animation_data(self):
        '''Return the raw animation data. Filename or osc queue for live animation'''
        return osc_queue


class FACEIT_OT_ClearLiveData(bpy.types.Operator):
    '''Clear the recorded data before starting a new recording (Destructive)'''
    bl_idname = "faceit.clear_live_data"
    bl_label = "Clear Recorded Data"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        clear_data()
        bpy.ops.faceit.reset_expression_values('EXEC_DEFAULT')
        bpy.ops.faceit.reset_head_pose('EXEC_DEFAULT')
        return {'FINISHED'}


class FACEIT_OT_ReceiverCancel(bpy.types.Operator):
    bl_idname = "faceit.receiver_cancel"
    bl_label = "Cancel Receiver"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        if bpy.context.scene.faceit_osc_receiver_enabled:
            self.report({'WARNING'}, 'Cancelled Receiver without writing keyframes.')
        stop_receiver()
        cancel_recording()
        ui_refresh_all()

        return {'FINISHED'}


@persistent
def close_osc_on_scene_save(self, context):
    # abort live connection, don't write data.
    bpy.ops.faceit.receiver_cancel()


def register():
    bpy.app.handlers.save_pre.append(close_osc_on_scene_save)
    bpy.app.handlers.load_pre.append(close_osc_on_scene_save)


def uregister():
    bpy.app.handlers.save_pre.remove(close_osc_on_scene_save)
    bpy.app.handlers.load_pre.remove(close_osc_on_scene_save)
