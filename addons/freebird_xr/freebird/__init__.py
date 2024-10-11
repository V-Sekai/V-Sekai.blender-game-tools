# set up file logging as early as possible, with zero non-stdlib/non-blender dependencies
from .log_manager import LOG_FILE, init_logging as _init_logging

_init_logging()

# initialize the rest of freebird after logging
from .settings_manager import settings, reset_settings, MODULE_ID

# Import and init logging first, and then import settings, and then import the rest. This order is important.

from bl_xr import root, xr_session

from .tools import enable_tool, disable_tool
from .gizmos import enable_gizmo, disable_gizmo, toggle_gizmo
from .undo_redo import undo, redo
from .updater import check_update


def on_xr_start(self, event_name, event):
    from . import tools
    from .utils import set_default_cursor, log
    from .ui import reset_viewer_settings, enable_xr_ui
    from .updater import check_update
    from .settings_manager import _get_preferences

    prefs = _get_preferences()

    enable_xr_ui()

    if tools.active_tool is None:
        enable_tool("draw.stroke")  # default tool
        set_default_cursor("pen")

    # temp hack for testing
    from .tools.transform_trigger import (
        enable_tool as enable_trigger_transform,
        disable_tool as disable_trigger_transform,
    )
    from .tools.transform import (
        enable_tool as enable_squeeze_transform,
        disable_tool as disable_squeeze_transform,
    )
    from .tools.clone import enable_tool as enable_clone, disable_tool as disable_clone
    from bl_xr import intersections

    log.info(f"Transform button: {settings['transform.grab_button']}")
    if settings["transform.grab_button"] == "squeeze":
        if not intersections.allow_squeeze:
            disable_trigger_transform()
            enable_squeeze_transform()
            enable_clone()

        intersections.allow_squeeze = True
    else:
        if intersections.allow_squeeze:
            disable_squeeze_transform()
            disable_clone()

            if tools.active_tool == "select":
                enable_trigger_transform()
                enable_clone()

        intersections.allow_squeeze = False
    # end of temp hack for testing

    if prefs.show_dev_tools:
        enable_gizmo("fps_counter")

    check_update(ref="xr_start")

    reset_viewer_settings()


def on_xr_end(self, event_name, event):
    from .ui import reset_viewer_settings, disable_xr_ui

    disable_xr_ui()

    disable_gizmo("fps_counter")

    reset_viewer_settings()


def register():
    import bpy

    from .utils import log

    try:
        from bl_xr import Image
        from os import path

        from .ui import enable_desktop_ui

        from .utils import enable_bounds_check, disable_bounds_check, get_device_info, watch_for_blender_mode_changes
        from .utils import misc_utils
        from .navigate import enable as enable_navigation
        from .undo_redo import enable as enable_undo_redo
        from .tools.transform import enable_tool as enable_object_transform
        from .tools.clone import enable_tool as enable_clone
        from .gizmos import enable_gizmo

        # setup the base directory for images
        Image.base_dir = path.abspath(path.join(path.dirname(__file__), ".."))
        log.debug(f"Setup image base directory to {Image.base_dir}")

        # handle the button press event sent by the Operator in ui/desktop_panels.py
        root.add_event_listener("fb.xr_start", on_xr_start)
        root.add_event_listener("fb.xr_end", on_xr_end)

        enable_bounds_check()

        enable_desktop_ui()
        enable_navigation()
        # enable_object_transform()
        # enable_clone()
        enable_undo_redo()
        enable_gizmo("preserve_view_across_restarts")
        enable_gizmo("auto_keyframe_transforms")
        enable_gizmo("see_through_pose_bones")
        enable_gizmo("select_switch")
        enable_gizmo("proportional_edit_cursor")

        if not bpy.app.background:
            log.info(f"Blender: {bpy.app.version}")
            log.info(f"Device Info: {get_device_info()}")

        watch_for_blender_mode_changes()

        settings_manager.stop_syncing = False
        misc_utils.stop_checking_mode = False
    except Exception as e:
        import traceback

        # Blender logs to stdout. Log to Freebird's file logger as well
        log.critical(f"Error while registering Freebird: {traceback.format_exc()}")
        raise e


def unregister():
    from .utils import log

    try:
        from .ui import disable_desktop_ui

        from .navigate import disable as disable_navigation
        from .undo_redo import disable as disable_undo_redo
        from .tools.transform import disable_tool as disable_object_transform
        from .tools.clone import disable_tool as disable_clone
        from . import settings_manager
        from .utils import misc_utils

        root.remove_event_listener("fb.xr_start", on_xr_start)
        root.remove_event_listener("fb.xr_end", on_xr_end)

        disable_desktop_ui()
        disable_navigation()
        disable_object_transform()
        disable_clone()
        disable_undo_redo()
        disable_gizmo("preserve_view_across_restarts")
        disable_gizmo("auto_keyframe_transforms")
        disable_gizmo("see_through_pose_bones")
        disable_gizmo("select_switch")
        disable_gizmo("proportional_edit_cursor")

        settings_manager.stop_syncing = True
        misc_utils.stop_checking_mode = True
    except Exception as e:
        import traceback

        # Blender logs to stdout. Log to Freebird's file logger as well
        log.critical(f"Error while un-registering Freebird: {traceback.format_exc()}")
        raise e
