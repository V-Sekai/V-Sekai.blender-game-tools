from ..utils import log

active_gizmos = set()

MODULES = {  # gizmo_name -> modules
    "3d_grid": "3d_grid",
    "controller_pointer": "controller_pointer",
    "mouse_cursor": "mouse_cursor",
    "cursor": "cursor",
    "edit_mesh.bevel": "edit_mesh.bevel",
    "edit_mesh.inset": "edit_mesh.inset",
    "edit_mesh.extrude": "edit_mesh.extrude",
    "viewport_sync": "viewport_sync",
    "camera_preview": "camera_preview",
    "camera_preview_on_grab": "camera_preview_on_grab",
    "preserve_view_across_restarts": "preserve_view_across_restarts",
    "auto_keyframe_transforms": "auto_keyframe_transforms",
    "see_through_pose_bones": "see_through_pose_bones",
    "select_switch": "select_switch",
    "transform_handles": "transform_handles",
    "fps_counter": "fps_counter",
    "joystick_for_keyframe": "joystick_for_keyframe",
    "mirror_plane": "mirror_plane",
    "proportional_edit_cursor": "proportional_edit_cursor",
}
MUTUALLY_EXCLUSIVE_GIZMOS = [  # only one of the set will be enabled at a time
    {"edit_mesh.bevel", "edit_mesh.inset", "edit_mesh.extrude"},
]


def _get_module(gizmo_name):
    import importlib

    if gizmo_name not in MODULES:
        return

    module_name = MODULES[gizmo_name]

    return importlib.import_module("." + module_name, __name__)


def enable_gizmo(gizmo_name):
    if gizmo_name in active_gizmos:
        return

    log.info(f"Enabling gizmo: {gizmo_name}")

    # check and disable mutually-exclusive gizmos (e.g. bevel, inset, extrude)
    mutually_exclusive_gizmos = next((x for x in MUTUALLY_EXCLUSIVE_GIZMOS if gizmo_name in x), set())
    for sibling_gizmo in mutually_exclusive_gizmos:
        if sibling_gizmo != gizmo_name and sibling_gizmo in active_gizmos:
            disable_gizmo(sibling_gizmo)

    # enable the gizmo
    module = _get_module(gizmo_name)
    if module:
        module.enable_gizmo()

    active_gizmos.add(gizmo_name)


def disable_gizmo(gizmo_name):
    if gizmo_name not in active_gizmos:
        return

    log.info(f"Disabling gizmo: {gizmo_name}")

    module = _get_module(gizmo_name)
    if module:
        module.disable_gizmo()

    active_gizmos.remove(gizmo_name)


def toggle_gizmo(gizmo_name):
    if gizmo_name in active_gizmos:
        disable_gizmo(gizmo_name)
    else:
        enable_gizmo(gizmo_name)
