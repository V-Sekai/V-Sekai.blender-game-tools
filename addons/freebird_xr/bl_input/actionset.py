# SPDX-License-Identifier: GPL-2.0-or-later

from .bindings import make_bindings

from dataclasses import dataclass

import bpy

ACTION_SET_NAME = "bl_controller_actionset"


@dataclass
class Action:
    action_name: str = None
    binding_name: str = None
    user_paths: tuple = ("/user/hand/left", "/user/hand/right")
    action_type: str = "FLOAT"  # or "POSE" or "VIBRATION"
    pose_type: str = None


actions = [
    Action("controller_grip", binding_name="GRIP_POSE", action_type="POSE", pose_type="GRIP"),
    Action("controller_aim", binding_name="AIM_POSE", action_type="POSE", pose_type="AIM"),
    Action("haptic", binding_name="HAPTIC", action_type="VIBRATION"),
    Action("trigger", binding_name="TRIGGER"),
    Action("squeeze", binding_name="SQUEEZE"),
    Action("joystick_x_lefthand", binding_name="JOYSTICK_X", user_paths=["/user/hand/left"]),
    Action("joystick_y_lefthand", binding_name="JOYSTICK_Y", user_paths=["/user/hand/left"]),
    Action("joystick_x_righthand", binding_name="JOYSTICK_X", user_paths=["/user/hand/right"]),
    Action("joystick_y_righthand", binding_name="JOYSTICK_Y", user_paths=["/user/hand/right"]),
    Action("button_a_lefthand", binding_name="BUTTON_A_LEFTHAND", user_paths=["/user/hand/left"]),
    Action("button_b_lefthand", binding_name="BUTTON_B_LEFTHAND", user_paths=["/user/hand/left"]),
    Action("button_a_righthand", binding_name="BUTTON_A_RIGHTHAND", user_paths=["/user/hand/right"]),
    Action("button_b_righthand", binding_name="BUTTON_B_RIGHTHAND", user_paths=["/user/hand/right"]),
    Action("button_a_touch_lefthand", binding_name="BUTTON_A_TOUCH_LEFTHAND", user_paths=["/user/hand/left"]),
    Action("button_b_touch_lefthand", binding_name="BUTTON_B_TOUCH_LEFTHAND", user_paths=["/user/hand/left"]),
    Action("button_a_touch_righthand", binding_name="BUTTON_A_TOUCH_RIGHTHAND", user_paths=["/user/hand/right"]),
    Action("button_b_touch_righthand", binding_name="BUTTON_B_TOUCH_RIGHTHAND", user_paths=["/user/hand/right"]),
]


def make_actions(actionset):
    for a in actions:
        action = actionset.actionmap_items.new(a.action_name, True)
        action.type = a.action_type

        if hasattr(action, "user_paths"):  # introduced in Blender 3.2
            for path in a.user_paths:
                action.user_paths.new(path)
        else:
            action.user_path0 = a.user_paths[0]
            if len(a.user_paths) > 1:
                action.user_path1 = a.user_paths[1]

        make_bindings(action, a.binding_name)

        if a.action_type == "FLOAT":
            action.op = make_operator(a.action_name)
            action.op_mode = "MODAL"
            action.bimanual = len(a.user_paths) == 2
            action.haptic_name = ""
            action.haptic_match_user_paths = False
            action.haptic_duration = 0.0
            action.haptic_frequency = 0.0
            action.haptic_amplitude = 0.0
            action.haptic_mode = "PRESS"
        elif a.action_type == "POSE":
            action.pose_is_controller_grip = a.pose_type == "GRIP"
            action.pose_is_controller_aim = a.pose_type == "AIM"


def make_operator(action_name):
    import bl_input

    op = f"dispatch.{action_name}_event_op"

    class EventOperator(bpy.types.Operator):
        bl_idname = op
        bl_label = f"Dispatch {action_name} event op"

        def modal(self, context, event):
            if event.type != "XR_ACTION" or event.xr.action != action_name:
                return {"PASS_THROUGH"}

            bl_input.event_callback(event.type, event)

            if event.value == "RELEASE":
                return {"FINISHED"}

            return {"RUNNING_MODAL"}

        def invoke(self, context, event):
            if context.area.type != "VIEW_3D":
                self.report({"WARNING"}, "View3D not found, cannot run operator")
                return {"CANCELLED"}

            context.window_manager.modal_handler_add(self)
            return {"RUNNING_MODAL"}

    bpy.utils.register_class(EventOperator)

    return op


class MouseEventOperator(bpy.types.Operator):
    bl_idname = "bl_input.mouse_event_op"
    bl_label = f"Dispatch mouse event op"

    def modal(self, context, event):
        import bl_input

        if event.type == "MOUSEMOVE":
            xr_session = context.window_manager.xr_session_state
            if xr_session and xr_session.is_running(context):
                bl_input.event_callback(event.type, event)
                return {"PASS_THROUGH"}

            return {"CANCELLED"}

        return {"PASS_THROUGH"}

    def execute(self, context):
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}


bpy.utils.register_class(MouseEventOperator)
