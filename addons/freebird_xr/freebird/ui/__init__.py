import bpy

orig_settings = {}


def reset_viewer_settings():
    context = bpy.context
    wm = context.window_manager

    if wm.xr_session_settings is None:
        return

    if wm.xr_session_state is not None:  # play nice with other VR plugins
        if wm.xr_session_state.is_running(context):
            if len(orig_settings) == 0:
                orig_settings["show_controllers"] = wm.xr_session_settings.show_controllers
                orig_settings["base_scale"] = wm.xr_session_settings.base_scale
                orig_settings["show_object_extras"] = wm.xr_session_settings.show_object_extras
                orig_settings["base_pose_type"] = wm.xr_session_settings.base_pose_type

            # freebird's choice:
            wm.xr_session_settings.show_controllers = False
            wm.xr_session_settings.base_scale = 10
            wm.xr_session_settings.show_object_extras = True
            wm.xr_session_settings.base_pose_type = "CUSTOM"
        elif len(orig_settings) > 0:
            # user/other VR plugin's choice:
            wm.xr_session_settings.show_controllers = orig_settings["show_controllers"]
            wm.xr_session_settings.base_scale = orig_settings["base_scale"]
            wm.xr_session_settings.show_object_extras = orig_settings["show_object_extras"]
            wm.xr_session_settings.base_pose_type = orig_settings["base_pose_type"]
        else:
            # sane defaults
            wm.xr_session_settings.show_controllers = True
            wm.xr_session_settings.base_scale = 1
            wm.xr_session_settings.show_object_extras = False
            wm.xr_session_settings.base_pose_type = "SCENE_CAMERA"


def enable_desktop_ui():
    from . import desktop_panels

    desktop_panels.enable()


def disable_desktop_ui():
    from . import desktop_panels

    desktop_panels.disable()


def enable_xr_ui():
    from . import controller_panels, main_menu, quicktools, info_panel
    from ..gizmos import enable_gizmo

    # panels
    controller_panels.enable()
    main_menu.enable()
    quicktools.enable()
    info_panel.enable()

    # gizmos
    enable_gizmo("controller_pointer")
    enable_gizmo("mouse_cursor")
    enable_gizmo("cursor")
    enable_gizmo("camera_preview_on_grab")


def disable_xr_ui():
    from . import controller_panels, main_menu, quicktools, info_panel
    from ..gizmos import disable_gizmo

    # panels
    controller_panels.disable()
    main_menu.disable()
    quicktools.disable()
    info_panel.disable()

    # gizmos
    disable_gizmo("controller_pointer")
    disable_gizmo("mouse_cursor")
    disable_gizmo("cursor")
    disable_gizmo("camera_preview_on_grab")
