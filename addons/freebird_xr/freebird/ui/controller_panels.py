import bpy

import bl_xr
from bl_xr import root, xr_session
from bl_xr import Node, Button, Image

from ..undo_redo import undo, redo

from mathutils import Vector

RIGHT_BG = "images/controller_right.png"
RIGHT_BTN_B_POSITION = Vector((-0.025, -0.043, 0.001))
RIGHT_BTN_A_POSITION = Vector((-0.021, -0.062, 0.001))
RIGHT_UNDO_POSITION = Vector((-0.009, -0.033, 0.001))
RIGHT_REDO_POSITION = Vector((0.009, -0.033, 0.001))

LEFT_BG = "images/controller_left.png"
LEFT_BTN_B_POSITION = Vector((0.008, -0.043, 0.001))
LEFT_BTN_A_POSITION = Vector((0.004, -0.062, 0.001))
LEFT_UNDO_POSITION = Vector((-0.028, -0.033, 0.001))
LEFT_REDO_POSITION = Vector((-0.011, -0.033, 0.001))

RIGHT_EXIT_POSITION = Vector((0.02, -0.115, 0.001))
LEFT_EXIT_POSITION = Vector((-0.04, -0.115, 0.001))

Node.STYLESHEET.update(
    {
        "#controller_main_a": {
            "position": RIGHT_BTN_A_POSITION,
            "visible": False,
        },
        "#controller_main_b": {
            "position": RIGHT_BTN_B_POSITION,
        },
        "#controller_alt_a": {
            "position": LEFT_BTN_A_POSITION,
            "visible": False,
        },
        "#controller_alt_b": {
            "position": LEFT_BTN_B_POSITION,
        },
        "#undo_btn": {
            "position": LEFT_UNDO_POSITION,
        },
        "#redo_btn": {
            "position": LEFT_REDO_POSITION,
        },
        "#stop_vr_btn": {
            "position": LEFT_EXIT_POSITION,
            "scale": 0.02,
        },
        ".controller": {
            "fixed_scale": True,
            "scale": 0.85,
        },
        ".controller_btn": {
            "scale": 0.018,
        },
        ".controller_bg": {
            "scale": 0.1,
            "position": Vector((-0.05, -0.1, 0)),
        },
    }
)


def toggle_menu():
    menu_group = root.q("#main_menu_group")
    menu_group.style["visible"] = not menu_group.style["visible"]


controller_alt = Node(
    id="controller_alt",
    class_name="controller",
    position=Vector((-1, 0, 0)),
    child_nodes=[
        Image(
            id="controller_alt_bg",
            src=LEFT_BG,
            class_name="controller_bg",
            intersects=None,
        ),
        Button(
            id="redo_btn",
            class_name="controller_btn",
            icon="images/redo.png",
            tooltip="REDO",
            tooltip_only_on_highlight=False,
            haptic_feedback_hand=None,
            on_pointer_main_press_end=lambda *x: redo(),
        ),
        Button(
            id="undo_btn",
            class_name="controller_btn",
            icon="images/undo.png",
            tooltip="UNDO",
            tooltip_only_on_highlight=False,
            haptic_feedback_hand=None,
            on_pointer_main_press_end=lambda *x: undo(),
        ),
        Button(
            id="controller_alt_b",
            class_name="controller_btn",
            icon="images/menu.png",
            tooltip="MENU",
            haptic_feedback_hand=None,
            on_pointer_main_press_end=lambda *x: toggle_menu(),
        ),
        Button(
            id="controller_alt_a",
            class_name="controller_btn",
            icon="images/undo.png",
            tooltip="UNUSED",
            haptic_feedback_hand=None,
            on_pointer_main_press_end=lambda *x: undo(),
        ),
        Button(
            id="stop_vr_btn",
            class_name="controller_bg",
            icon="images/exit.png",
            tooltip="STOP VR",
            haptic_feedback_hand="alt",
            on_pointer_main_press_end=lambda self, *x: on_stop_vr_update(self),
        ),
    ],
)
controller_main = Node(
    id="controller_main",
    class_name="controller",
    position=Vector((-0.5, 0, 0)),
    intersects=None,
    child_nodes=[
        Image(id="controller_main_bg", src=RIGHT_BG, class_name="controller_bg"),
        Button(
            id="controller_main_b",
            class_name="controller_btn",
            icon="images/quicktools.png",
            tooltip="QUICKTOOLS",
            haptic_feedback_hand=None,
        ),
        Button(
            id="controller_main_a",
            class_name="controller_btn",
            icon="images/clone.png",
            tooltip="CLONE",
            haptic_feedback_hand=None,
        ),
    ],
)


def on_main_controller_update(self):
    self.position = xr_session.controller_main_aim_position
    self.rotation = xr_session.controller_main_aim_rotation


def on_alt_controller_update(self):
    self.position = xr_session.controller_alt_aim_position
    self.rotation = xr_session.controller_alt_aim_rotation


def on_stop_vr_update(self):
    # hack to work around Blender's "invalid context" problem - https://docs.blender.org/api/current/bpy.ops.html#execution-context
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == "VIEW_3D":
                with bpy.context.temp_override(window=window, area=area):
                    bpy.ops.freebird.xr_toggle("INVOKE_DEFAULT")
                break


controller_main.update = on_main_controller_update.__get__(controller_main)
controller_alt.update = on_alt_controller_update.__get__(controller_alt)


def apply_handedness(hand):
    main_a = controller_main.q("#controller_main_a")
    main_b = controller_main.q("#controller_main_b")
    main_background = controller_main.q("#controller_main_bg")

    alt_a = controller_alt.q("#controller_alt_a")
    alt_b = controller_alt.q("#controller_alt_b")
    alt_background = controller_alt.q("#controller_alt_bg")

    undo_btn = controller_alt.q("#undo_btn")
    redo_btn = controller_alt.q("#redo_btn")

    main_a.position = RIGHT_BTN_A_POSITION if hand == "right" else LEFT_BTN_A_POSITION
    main_b.position = RIGHT_BTN_B_POSITION if hand == "right" else LEFT_BTN_B_POSITION
    alt_a.position = LEFT_BTN_A_POSITION if hand == "right" else RIGHT_BTN_A_POSITION
    alt_b.position = LEFT_BTN_B_POSITION if hand == "right" else RIGHT_BTN_B_POSITION

    undo_btn.position = LEFT_UNDO_POSITION if hand == "right" else RIGHT_UNDO_POSITION
    redo_btn.position = LEFT_REDO_POSITION if hand == "right" else RIGHT_REDO_POSITION

    stop_vr_btn = controller_alt.q("#stop_vr_btn")
    stop_vr_btn.position = LEFT_EXIT_POSITION if hand == "right" else RIGHT_EXIT_POSITION

    # hack since Blender crashes when loading images in an application timer
    t = main_background._texture
    main_background._texture = alt_background._texture
    alt_background._texture = t


if bl_xr.main_hand != "right":  # assumed "right" while creating the DOM nodes
    apply_handedness(bl_xr.main_hand)


def on_setting_change(self, event_name, change: dict):
    if "app.main_hand" in change:
        apply_handedness(change["app.main_hand"])


def on_btn_touch(btn_id):
    def on_touch(self, event_name, event):
        btn = root.q("#" + btn_id)
        btn.highlight(not event_name.endswith("_end"))

    return on_touch


def on_undo_redo_press(self, event_name, event):
    from freebird.undo_redo import JOYSTICK_THRESHOLD

    for btn_id in ("undo_btn", "redo_btn"):
        btn = root.q("#" + btn_id)
        if event_name.endswith("_end"):
            highlight = False
        elif btn_id == "undo_btn":
            highlight = event.value < JOYSTICK_THRESHOLD
        elif btn_id == "redo_btn":
            highlight = event.value > JOYSTICK_THRESHOLD

        btn.highlight(highlight)


button_touch_listeners = []

for btn in ("a", "b"):
    for hand in ("main", "alt"):
        button_touch_listeners.append((f"button_{btn}_touch_{hand}_start", on_btn_touch(f"controller_{hand}_{btn}")))
        button_touch_listeners.append((f"button_{btn}_touch_{hand}_end", on_btn_touch(f"controller_{hand}_{btn}")))


def enable():
    root.append_child(controller_alt)
    root.append_child(controller_main)

    for event_name, listener in button_touch_listeners:
        root.add_event_listener(event_name, listener)

    root.add_event_listener("joystick_x_alt_press", on_undo_redo_press)
    root.add_event_listener("joystick_x_alt_end", on_undo_redo_press)

    root.add_event_listener("fb.setting_change", on_setting_change)


def disable():
    root.remove_child(controller_alt)
    root.remove_child(controller_main)

    for event_name, listener in button_touch_listeners:
        root.remove_event_listener(event_name, listener)

    root.remove_event_listener("joystick_x_alt_press", on_undo_redo_press)
    root.remove_event_listener("joystick_x_alt_end", on_undo_redo_press)

    root.remove_event_listener("fb.setting_change", on_setting_change)
