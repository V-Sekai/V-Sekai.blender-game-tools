import bpy
from math import pi as PI
from .mocap_base import MocapImporterBase
from .mocap_importers import OSCLiveAnimator
from .osc_receiver import QueueManager, Receiver, osc_queue
from ..core.faceit_utils import get_faceit_objects_list, restore_scene_state, save_scene_state, ui_refresh_all, get_faceit_control_armature, set_active_object, get_object_mode_from_context_mode, clear_active_object, set_hide_obj
from ..core.pose_utils import get_edit_bone_roll
from ..ctrl_rig.control_rig_utils import is_control_rig_connected

queue_mgr: QueueManager = QueueManager()
receiver: Receiver = Receiver(queue_mgr)
live_animator: OSCLiveAnimator = OSCLiveAnimator()
reconnect_ctrl_rig: bool = False
head_base_rotation = None
head_base_location = None


def get_head_base_transform():
    return head_base_rotation, head_base_location


class FACEIT_OT_ReceiverStart(bpy.types.Operator):
    '''Start receiving animation data from the given connection. Enable the recorder in order to import recorded data'''
    bl_idname = "faceit.receiver_start"
    bl_label = "Start Receiver"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        global receiver, live_animator, reconnect_ctrl_rig
        state_dict = save_scene_state(context)
        live_animator.clear_animation_targets()
        scene = context.scene
        animate_loc = scene.faceit_osc_animate_head_location
        animate_rot = scene.faceit_osc_animate_head_rotation
        animate_shapes = scene.faceit_osc_animate_shapes
        if not (animate_loc or animate_rot or animate_shapes):
            self.report({'ERROR'}, "You need to enable at least one type of motion.")
            return {'CANCELLED'}
        live_animator.init_new_recording()
        live_animator.set_rotation_units(scene.faceit_osc_rotation_units)
        # Shapes animation properties
        live_animator.flip_animation = scene.faceit_osc_flip_animation
        live_animator.animate_shapes = animate_shapes
        live_animator.animate_head_location = animate_loc
        live_animator.animate_head_rotation = animate_rot
        if animate_shapes:
            objects = get_faceit_objects_list()
            target_shapes = scene.faceit_arkit_retarget_shapes
            if not objects:
                self.report({'WARNING'}, "You need to register the target objects in Setup tab.")
            elif not target_shapes:
                self.report({'WARNING'}, "You need to populate the ARKit target shapes list in the Shapes tab.")

            live_animator.set_use_region_filter(scene.faceit_osc_use_region_filter)
            live_animator.set_face_regions_dict(scene.faceit_osc_face_regions.get_active_regions())
            live_animator.set_shape_targets(
                objects=objects,
                retarget_shapes=target_shapes
            )
        # Head animation properties
        if animate_loc or animate_rot:
            head_loc_multiplier = scene.faceit_osc_head_location_multiplier
            head_obj = scene.faceit_head_target_object
            head_bone_name = scene.faceit_head_sub_target
            head_bone_roll = 0
            if head_obj:
                if head_obj.type == 'ARMATURE':
                    set_active_object(head_obj.name)
                    set_hide_obj(head_obj, False)
                    pb = head_obj.pose.bones.get(head_bone_name)
                    head_bone_roll = get_edit_bone_roll(pb)
                    # bpy.ops.object.mode_set(mode='EDIT')
                    # edit_bone = head_obj.data.edit_bones.get(head_bone_name)
                    # if edit_bone:
                    #     head_bone_roll = round(edit_bone.roll % (2 * PI), 3)
                    # bpy.ops.object.mode_set()
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
                head_bone_roll=head_bone_roll,
            )
        if bpy.context.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel()
        ctrl_rig = scene.faceit_control_armature
        if ctrl_rig:
            if scene.faceit_auto_disconnect_ctrl_rig and is_control_rig_connected(ctrl_rig):
                bpy.ops.faceit.remove_control_drivers('EXEC_DEFAULT')
                reconnect_ctrl_rig = True
        try:
            receiver.start(scene.faceit_osc_address, scene.faceit_osc_port)
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
        reconnect_ctrl_rig = False
        return {'FINISHED'}


class FACEIT_OT_ImportLiveMocap(MocapImporterBase, bpy.types.Operator):
    '''Import the recorded data into a Blender Action in order to permanently store it.'''
    bl_idname = "faceit.import_live_mocap"
    bl_label = "Import OSC Recording"
    bl_description = "Import the recorded data to an animation."

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def _get_engine_specific_settings(self):
        self.animate_shapes = live_animator.animate_shapes
        self.animate_head_rotation = live_animator.animate_head_rotation
        self.animate_head_location = live_animator.animate_head_location
        self.can_import_head_rotation = bpy.context.scene.faceit_osc_animate_head_rotation
        self.can_import_head_location = bpy.context.scene.faceit_osc_animate_head_location
        self.use_region_filter = live_animator.use_region_filter
        self.flip_animation = live_animator.flip_animation
        self.filename = ""

    def invoke(self, context, event):
        global reconnect_ctrl_rig
        self._get_engine_specific_settings()
        self.new_action_name = "LiveRecording"
        if not osc_queue:
            self.report({'WARNING'}, "No recorded data found.")
            return {'CANCELLED'}
        faceit_objects = get_faceit_objects_list()
        if not faceit_objects:
            self.report({'WARNING'}, "You need to register the character meshes in the setup tab.")
        # live_animator.set_use_region_filter(context.scene.faceit_osc_use_region_filter)
        # self._set_face_regions_dict()
        self.set_active_regions(context.scene.faceit_osc_face_regions.get_active_regions())
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

    # def _set_face_regions_dict(self, context):
    #     self.active_regions_dict = context.scene.faceit_osc_face_regions.get_active_regions()


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
