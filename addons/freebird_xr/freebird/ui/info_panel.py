import bpy

import bl_xr
from bl_xr import root, xr_session
from bl_xr import Node, Image, Button
from bl_xr.consts import BLUE_MS
from bl_xr.utils import apply_haptic_feedback

from mathutils import Vector

RIGHT_HANDED_POSITION = Vector((-1.45, -1, 0))
LEFT_HANDED_POSITION = Vector((0.45, -1, 0))

MSG_SHOW_INTERVAL = 6  # seconds
DISCORD_URL = "https://discord.gg/X6B4ZYEWSS"

container = Node(id="info_msg", style={"scale": 0.1, "fixed_scale": True})
opened_in_browser = Image(
    src="images/opened_in_browser.png",
    position=Vector((0.2, 0.3, 0.005)),
    scale=Vector((0.6, 0.12, 1)),
)


def on_info_clicked(*x):
    bpy.ops.wm.url_open(url=DISCORD_URL)

    info_msg.append_child(opened_in_browser)

    bpy.app.timers.register(hide_toast, first_interval=MSG_SHOW_INTERVAL)

    apply_haptic_feedback(hand="alt")


def hide_toast():
    info_msg.remove_child(opened_in_browser)


def on_pointer_enter(self, event_name, event):
    self.style["border"] = (0.015, BLUE_MS)
    self.style["border_radius"] = 0.1

    apply_haptic_feedback()


def on_pointer_leave(self, event_name, event):
    if "border" in self.style:
        del self.style["border"]
    if "border_radius" in self.style:
        del self.style["border_radius"]


def on_close_press(self, event_name, event):
    container.style["visible"] = False

    event.stop_propagation = True


info_msg = Image(
    src="images/info_msg.png",
    on_pointer_main_press_end=on_info_clicked,
    on_pointer_main_enter=on_pointer_enter,
    on_pointer_main_leave=on_pointer_leave,
    child_nodes=[
        Button(
            icon="images/close.png",
            tooltip="CLOSE",
            position=Vector((0.92, 0.92, 0.005)),
            scale=0.2,
            on_pointer_main_press_end=on_close_press,
        )
    ],
)
info_msg.position = RIGHT_HANDED_POSITION if bl_xr.main_hand == "right" else LEFT_HANDED_POSITION

container.append_child(info_msg)


def on_alt_controller_update(self):
    self.position = xr_session.controller_alt_aim_position
    self.rotation = xr_session.controller_alt_aim_rotation


container.update = on_alt_controller_update.__get__(container)


def apply_handedness(hand):
    info_msg.position = RIGHT_HANDED_POSITION if hand == "right" else LEFT_HANDED_POSITION


if bl_xr.main_hand != "right":  # assumed "right" while creating the DOM nodes
    apply_handedness(bl_xr.main_hand)


def on_setting_change(self, event_name, change: dict):
    if "app.main_hand" in change:
        apply_handedness(change["app.main_hand"])


def enable():
    root.append_child(container)

    root.add_event_listener("fb.setting_change", on_setting_change)


def disable():
    root.remove_child(container)

    root.remove_event_listener("fb.setting_change", on_setting_change)
