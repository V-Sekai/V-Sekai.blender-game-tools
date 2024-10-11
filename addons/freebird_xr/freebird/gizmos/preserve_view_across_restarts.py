import bpy

from bl_xr import root, xr_session
from bl_xr.utils import is_equal, log

from mathutils import Vector, Quaternion


def on_navigate(self, event_name, event):
    # save the viewer position in the scene (for restoring on restart)
    r = xr_session.viewer_rotation

    bpy.context.scene.freebird_viewer_position = xr_session.viewer_location.to_tuple()
    bpy.context.scene.freebird_viewer_rotation = (r.w, r.x, r.y, r.z)
    bpy.context.scene.freebird_viewer_scale = xr_session.viewer_scale


def on_xr_start(self, event_name, operator):
    has_saved_view = not is_equal((0.0, 0.0, 0.0, 0.0), bpy.context.scene.freebird_viewer_rotation)
    if has_saved_view:
        xr_session.viewer_location = Vector(bpy.context.scene.freebird_viewer_position)
        xr_session.viewer_rotation = Quaternion(bpy.context.scene.freebird_viewer_rotation)
        xr_session.viewer_scale = bpy.context.scene.freebird_viewer_scale

        log.debug(f"Restored view: {xr_session.viewer_pose}")
    elif bpy.context.scene and bpy.context.scene.camera:
        from bl_xr.consts import VEC_FORWARD, VEC_RIGHT
        from bl_xr.utils import to_blender_axis_system, to_upright_rotation

        cam = bpy.context.scene.camera

        prev_rot_type = cam.rotation_mode
        cam.rotation_mode = "QUATERNION"
        rot = to_blender_axis_system(Quaternion(cam.rotation_quaternion))
        rot = to_upright_rotation(rot)
        cam.rotation_mode = prev_rot_type

        offset = (rot @ (VEC_FORWARD * 0.2 + VEC_RIGHT * 0.2)) * xr_session.viewer_scale

        xr_session.viewer_location = Vector(cam.location) - offset
        xr_session.viewer_rotation = rot

        log.debug(f"Using default view (from camera): {xr_session.viewer_pose}")


def enable_gizmo():
    root.add_event_listener("fb.navigate", on_navigate)
    root.add_event_listener("fb.xr_start", on_xr_start)


def disable_gizmo():
    root.remove_event_listener("fb.navigate", on_navigate)
    root.remove_event_listener("fb.xr_start", on_xr_start)
