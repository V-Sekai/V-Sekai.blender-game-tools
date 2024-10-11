import bpy

CONTROLLER_MOVE_TRACKING_FPS = 10
CONTROLLER_MOVE_TRACKING_INTERVAL = 1 / CONTROLLER_MOVE_TRACKING_FPS


class XRControllerMoveOperator(bpy.types.Operator):
    bl_idname = "bl_input.start_xr_move_timer"
    bl_label = "bl_input: Move Timer"

    _timer = None

    def modal(self, context, event):
        xr_session = context.window_manager.xr_session_state
        if event.type == "TIMER" and xr_session:
            self.dispatch_move_event(xr_session, context, "right")
            self.dispatch_move_event(xr_session, context, "left")

        if not xr_session or not xr_session.is_running:
            self.cancel(context)
            return {"FINISHED"}

        return {"PASS_THROUGH"}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(CONTROLLER_MOVE_TRACKING_INTERVAL, window=context.window)
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

    def dispatch_move_event(self, xr_session, context, hand):
        import bl_input

        hand_idx = 1 if hand == "right" else 0
        position = xr_session.controller_aim_location_get(context, hand_idx)
        rotation = xr_session.controller_aim_rotation_get(context, hand_idx)

        bl_input.event_callback("XR_CONTROLLER_MOVE", (hand, position, rotation, context))


bpy.utils.register_class(XRControllerMoveOperator)
