import bl_xr
from bl_xr import root, xr_session
from bl_xr import Node, Button, Grid2D
from bl_xr.utils import apply_haptic_feedback

from mathutils import Vector

from .. import tools
from ..settings_manager import settings
from ..utils import set_tool

qt_start_pos = None
prev_tool = None

Node.STYLESHEET.update(
    {
        "#quicktools": {
            "visible": False,
            "position": Vector((0.1, 0.02, -0.02)),
            "fixed_scale": True,
        },
        "#quicktools_button_group": {
            "position": Vector((-0.065, 0, 0)),
        },
        ".quicktool_btn": {
            "scale": 0.03,
        },
    }
)

select_btn = Button(
    id="select_quicktool_btn",
    icon="images/select.png",
    tooltip="SELECT",
    class_name="quicktool_btn",
)
erase_btn = Button(
    id="erase_quicktool_btn",
    icon="images/erase.png",
    tooltip="ERASE",
    class_name="quicktool_btn",
)

quicktools = Node(
    id="quicktools",
    intersects=None,
    child_nodes=[
        Grid2D(
            id="quicktools_button_group",
            num_rows=1,
            num_cols=2,
            cell_width=0.1,
            child_nodes=[
                erase_btn,
                select_btn,
            ],
        ),
    ],
)


def get_focused_button(event):
    d = event.position - qt_start_pos  # world
    d = event.rotation.inverted() @ d  # local

    d.x *= 1 if bl_xr.main_hand == "right" else -1  # invert dir for left-handed

    if abs(d.x) > settings["quicktools.min_move_distance"] * xr_session.viewer_scale:
        return select_btn if d.x > 0 else erase_btn

    return None


def on_qt_controller_move(self, event_name, event):
    btn = get_focused_button(event)

    select_btn.highlight(btn == select_btn)
    erase_btn.highlight(btn == erase_btn)


def on_qt_button_start(self, event_name, event):
    global qt_start_pos

    qt_start_pos = event.position

    quicktools.style["visible"] = True
    quicktools.position = event.position
    quicktools.rotation = event.rotation

    root.add_event_listener("button_b_main_press", on_qt_controller_move)


def on_qt_button_end(self, event_name, event):
    global prev_tool
    quicktools.style["visible"] = False

    root.remove_event_listener("button_b_main_press", on_qt_controller_move)

    btn = get_focused_button(event)
    if btn:
        prev_tool = tools.active_tool

        if btn.tooltip.text == "ERASE":
            set_tool("erase")
        elif btn.tooltip.text == "SELECT":
            set_tool("select")
    elif prev_tool:
        set_tool(prev_tool)
        apply_haptic_feedback(type="SHORT_STRONG")

    select_btn.highlight(False)
    erase_btn.highlight(False)


def apply_handedness(hand):
    # reverse the quicktools buttons
    qt_buttons = quicktools.q("#quicktools_button_group")
    btn_top = qt_buttons.child_nodes[0]
    qt_buttons.append_child(btn_top)  # detaches and re-attaches at the bottom


if bl_xr.main_hand != "right":  # assumed "right" while creating the DOM nodes
    apply_handedness(bl_xr.main_hand)


def on_setting_change(self, event_name, change: dict):
    if "app.main_hand" in change:
        apply_handedness(change["app.main_hand"])


# register the listeners
def enable():
    root.append_child(quicktools)

    root.add_event_listener("button_b_main_start", on_qt_button_start)
    root.add_event_listener("button_b_main_end", on_qt_button_end)

    root.add_event_listener("fb.setting_change", on_setting_change)


def disable():
    root.remove_child(quicktools)

    root.remove_event_listener("button_b_main_start", on_qt_button_start)
    root.remove_event_listener("button_b_main_end", on_qt_button_end)

    root.remove_event_listener("fb.setting_change", on_setting_change)
