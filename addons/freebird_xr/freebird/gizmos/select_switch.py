from bl_xr import root
from freebird import tools
from freebird.utils import set_tool

prev_tool = None


def on_select_start(self, event_name, event):
    global prev_tool

    prev_tool = tools.active_tool

    set_tool("select")


def on_select_end(self, event_name, event):
    global prev_tool

    set_tool(prev_tool)

    prev_tool = None


def enable_gizmo():
    root.add_event_listener("button_a_alt_start", on_select_start)
    root.add_event_listener("button_a_alt_end", on_select_end)


def disable_gizmo():
    root.remove_event_listener("button_a_alt_start", on_select_start)
    root.remove_event_listener("button_a_alt_end", on_select_end)
