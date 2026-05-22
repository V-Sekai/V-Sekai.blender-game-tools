"""Blender MCP addon — connects Blender to Claude via the Model Context Protocol.

Originally created by Siddharth Ahuja (https://github.com/ahujasid/blender-mcp).
Forked and maintained by K. S. Ernest (iFire) Lee.
"""

import bpy

from . import state
from .operators import (
    BLENDERMCP_OT_SetFreeTrialHyper3DAPIKey,
    BLENDERMCP_OT_StartServer,
    BLENDERMCP_OT_StopServer,
)
from .panel import BLENDERMCP_PT_Panel
from .preferences import BlenderMCPPreferences
from .server import BlenderMCPServer

# Legacy bl_info for Blender 3.x/4.0/4.1 installs that pre-date the manifest.
# Blender 4.2+ reads blender_manifest.toml instead and ignores this dict.
bl_info = {
    "name": "Blender MCP",
    "author": "BlenderMCP",
    "version": (2, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > BlenderMCP",
    "description": "Connect Blender to Claude via MCP",
    "category": "Interface",
}

_CLASSES = (
    BlenderMCPPreferences,
    BLENDERMCP_PT_Panel,
    BLENDERMCP_OT_SetFreeTrialHyper3DAPIKey,
    BLENDERMCP_OT_StartServer,
    BLENDERMCP_OT_StopServer,
)


def _autostart():
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
    except (KeyError, AttributeError):
        return None
    if not prefs.blendermcp_autostart:
        return None
    if state.server is None:
        state.server = BlenderMCPServer(port=prefs.blendermcp_port)
    state.server.start()
    return None


@bpy.app.handlers.persistent
def _re_enable_after_reset(_dummy=None):
    """Re-enable this add-on after a factory reset / load-factory-preferences.

    ``bpy.ops.wm.read_factory_settings()`` and friends wipe the user prefs and
    disable every add-on, including this one — which kills the MCP socket and
    leaves the client stranded. Hooking ``load_factory_*_post`` lets us boot
    the add-on back up automatically as soon as Blender finishes the reset.
    """
    import addon_utils

    pkg = __package__
    try:
        addon_utils.enable(pkg, default_set=True, persistent=True)
    except Exception as exc:
        print(f"BlenderMCP: failed to re-enable {pkg!r} after reset: {exc!r}")


def _install_persistence_hooks():
    for hook_name in ("load_factory_preferences_post", "load_factory_startup_post"):
        hook = getattr(bpy.app.handlers, hook_name, None)
        if hook is None:
            continue
        if _re_enable_after_reset not in hook:
            hook.append(_re_enable_after_reset)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.app.timers.register(_autostart, first_interval=0.5)
    _install_persistence_hooks()
    print("BlenderMCP addon registered")


def unregister():
    # Leave the persistence hooks in place: factory reset disables every add-on
    # *before* the load_factory_preferences_post handlers run, so removing the
    # hook here would prevent re-enable. The handler is idempotent, and Blender
    # garbage-collects stale handler references on the next full reload.

    if state.server is not None:
        state.server.stop()
        state.server = None

    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)

    print("BlenderMCP addon unregistered")
