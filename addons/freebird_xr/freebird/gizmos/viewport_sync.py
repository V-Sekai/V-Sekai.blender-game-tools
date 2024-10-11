from bl_xr import root, xr_session
from bl_xr import Node, Pose

from ..settings_manager import settings
from ..utils import desktop_viewport

is_xr_navigating = False


def apply_desktop_viewport_to_hmd():
    if settings["view.mirror_xr"] or is_xr_navigating:
        return

    prev_viewer_scale = xr_session.viewer_scale

    viewer_pose = desktop_viewport.pose

    if not settings["view.strict_viewport_sync"]:
        mouse_offset = settings["view.mouse_pointer_offset"]
        hand_dir = -1 if settings["app.main_hand"] == "right" else 1

        mouse_offset = hand_dir * viewer_pose.right * mouse_offset.x + viewer_pose.up * mouse_offset.z
        mouse_offset *= xr_session.viewer_scale
        viewer_pose.position += mouse_offset

    xr_session.viewer_pose = viewer_pose
    xr_session.viewer_scale = prev_viewer_scale


def on_navigate_start(self, event_name, event):
    global is_xr_navigating

    is_xr_navigating = True


def on_navigate(self, event_name, event):
    if settings["view.mirror_xr"]:
        return

    desktop_pose = xr_session.viewer_pose.clone()

    if not settings["view.strict_viewport_sync"]:
        mouse_offset = settings["view.mouse_pointer_offset"]
        hand_dir = -1 if settings["app.main_hand"] == "right" else 1

        mouse_offset = hand_dir * desktop_pose.right * mouse_offset.x + desktop_pose.up * mouse_offset.z
        mouse_offset *= xr_session.viewer_scale
        desktop_pose.position -= mouse_offset

    desktop_viewport.pose = desktop_pose


def on_navigate_end(self, event_name, event):
    global is_xr_navigating

    is_xr_navigating = False


viewport_sync_gizmo = Node(id="viewport_sync_gizmo")
viewport_sync_gizmo.update = apply_desktop_viewport_to_hmd


def enable_gizmo():
    root.append_child(viewport_sync_gizmo)

    root.add_event_listener("fb.navigate_start", on_navigate_start)
    root.add_event_listener("fb.navigate", on_navigate)
    root.add_event_listener("fb.navigate_end", on_navigate_end)


def disable_gizmo():
    root.remove_child(viewport_sync_gizmo)

    root.remove_event_listener("fb.navigate_start", on_navigate_start)
    root.remove_event_listener("fb.navigate", on_navigate)
    root.remove_event_listener("fb.navigate_end", on_navigate_end)
