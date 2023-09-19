"""
Copyright (C) 2022 Adobe.
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# file: __init__.py
# brief: Addon registration
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

bl_info = {
    "name": "Adobe Substance 3D add-on for Blender",
    "author": "Adobe Inc.",
    "location": "Node Editor Toolbar -- Shift-Ctrl-U",
    "version": (1, 0, 2),
    "blender": (2, 90, 0),
    "description": "Adobe Substance 3D add-on for Blender",
    'tracker_url': "https://discord.gg/substance3d",
    "category": "Node"
}

try:
    import bpy

    import atexit
    from .api import SUBSTANCE_Api
    from .utils import SUBSTANCE_Utils
    from .thread_ops import SUBSTANCE_Threads
    from .dispatcher import Server_GET_Dispatcher
    from .persistance import SUBSTANCE_Persistance
    from .common import Code_Response, UI_SPACES, ADDON_PACKAGE, SHORTCUT_CLASS_NAME

    from .ui.presets import SUBSTANCE_MT_PresetOptions
    from .ui.shortcut import SubstanceShortcutMenuFactory
    from .ui.sbsar import (
        SubstanceMainPanelFactory,
        SubstanceGraphPanelFactory,
        SubstanceOutputPanelFactory,
        SubstanceParmsPanelFactory,
        SUBSTANCE_UL_SbsarList
    )

    from .preferences import SUBSTANCE_AddonPreferences

    from .ops.common import SUBSTANCE_OT_Message
    from .ops.parms import SUBSTANCE_OT_RandomizeSeed
    from .ops.material import SUBSTANCE_OT_SetMaterial
    from .ops.toolkit import SUBSTANCE_OT_InstallTools, SUBSTANCE_OT_UpdateTools, SUBSTANCE_OT_UninstallTools
    from .ops.web import (
        SUBSTANCE_OT_GoToWebsite,
        SUBSTANCE_OT_GetTools,
        SUBSTANCE_OT_GotoShare,
        SUBSTANCE_OT_GotoSource,
        SUBSTANCE_OT_GotoDocs,
        SUBSTANCE_OT_GotoForums,
        SUBSTANCE_OT_GotoDiscord
    )
    from .ops.presets import (
        SUBSTANCE_OT_AddPreset,
        SUBSTANCE_OT_DeletePreset,
        SUBSTANCE_OT_ImportPreset,
        SUBSTANCE_OT_ExportPreset
    )
    from .ops.shader import (
        SUBSTANCE_OT_ResetShaderPreset,
        SUBSTANCE_OT_InitializeShaderPresets,
        SUBSTANCE_OT_RemoveShaderPresets,
        SUBSTANCE_OT_SaveShaderPresets
    )
    from .ops.sbsar import (
        SUBSTANCE_OT_LoadSBSAR,
        SUBSTANCE_OT_ApplySBSAR,
        SUBSTANCE_OT_DuplicateSBSAR,
        SUBSTANCE_OT_ReloadSBSAR,
        SUBSTANCE_OT_RemoveSBSAR
    )

    from .props.shortcuts import SUBSTANCE_PG_Shortcuts
    from .props.common import SUBSTANCE_PG_Tiling, SUBSTANCE_PG_Resolution
    from .props.shader import SUBSTANCE_PG_ShaderPreset, SUBSTANCE_PG_ShaderParm, SUBSTANCE_PG_ShaderOutput
    from .props.sbsar import (
        SUBSTANCE_PG_Sbsar,
        SUBSTANCE_PG_SbsarGraph,
        SUBSTANCE_PG_SbsarPhysicalSize,
        SUBSTANCE_PG_SbsarTiling,
        SUBSTANCE_PG_SbsarMaterial,
        SUBSTANCE_PG_SbsarParmGroup,
        SUBSTANCE_PG_SbsarPreset,
        SUBSTANCE_PG_SbsarParm,
        SUBSTANCE_PG_SbsarOutput
    )

    SHORTCUT_KEYMAPS = []
    FACTORY_CLASSES = []
    DEFAULT_CLASSES = [
        # /props/common
        SUBSTANCE_PG_Tiling,
        SUBSTANCE_PG_Resolution,

        # /props/sbsar
        SUBSTANCE_PG_SbsarPhysicalSize,
        SUBSTANCE_PG_SbsarTiling,
        SUBSTANCE_PG_SbsarOutput,
        SUBSTANCE_PG_SbsarParm,
        SUBSTANCE_PG_SbsarPreset,
        SUBSTANCE_PG_SbsarParmGroup,
        SUBSTANCE_PG_SbsarMaterial,
        SUBSTANCE_PG_SbsarGraph,
        SUBSTANCE_PG_Sbsar,

        # /props/shader
        SUBSTANCE_PG_ShaderOutput,
        SUBSTANCE_PG_ShaderParm,
        SUBSTANCE_PG_ShaderPreset,

        # /props/shortcuts
        SUBSTANCE_PG_Shortcuts,

        # /preferences
        SUBSTANCE_AddonPreferences,

        # /ops/common
        SUBSTANCE_OT_Message,

        # /ops/toolkit
        SUBSTANCE_OT_InstallTools,
        SUBSTANCE_OT_UpdateTools,
        SUBSTANCE_OT_UninstallTools,

        # /ops/parms
        SUBSTANCE_OT_RandomizeSeed,

        # /ops/shader
        SUBSTANCE_OT_InitializeShaderPresets,
        SUBSTANCE_OT_RemoveShaderPresets,
        SUBSTANCE_OT_SaveShaderPresets,
        SUBSTANCE_OT_ResetShaderPreset,

        # /ops/web
        SUBSTANCE_OT_GoToWebsite,
        SUBSTANCE_OT_GetTools,
        SUBSTANCE_OT_GotoShare,
        SUBSTANCE_OT_GotoSource,
        SUBSTANCE_OT_GotoDocs,
        SUBSTANCE_OT_GotoForums,
        SUBSTANCE_OT_GotoDiscord,

        # /ops/sbsar
        SUBSTANCE_OT_LoadSBSAR,
        SUBSTANCE_OT_ApplySBSAR,
        SUBSTANCE_OT_DuplicateSBSAR,
        SUBSTANCE_OT_ReloadSBSAR,
        SUBSTANCE_OT_RemoveSBSAR,

        # /ops/presets
        SUBSTANCE_OT_AddPreset,
        SUBSTANCE_OT_DeletePreset,
        SUBSTANCE_OT_ImportPreset,
        SUBSTANCE_OT_ExportPreset,

        # /ops/material
        SUBSTANCE_OT_SetMaterial,

        # /ui/presets
        SUBSTANCE_MT_PresetOptions,

        # /ui/sbsar
        SUBSTANCE_UL_SbsarList
    ]

    # Callback for SBSAR
    def sbsar_index_changed(self, context):
        pass

    @atexit.register
    def on_exit():
        pass

    dispatcher_get = Server_GET_Dispatcher()

    def register():
        bpy.context.preferences.use_preferences_save = True

        # Add Panels
        if len(FACTORY_CLASSES) == 0:
            for _space in UI_SPACES:
                # Add Substance List Panel
                _cls = SubstanceMainPanelFactory(_space[1])
                FACTORY_CLASSES.append(_cls)
                _cls = SubstanceGraphPanelFactory(_space[1])
                FACTORY_CLASSES.append(_cls)
                _cls = SubstanceOutputPanelFactory(_space[1])
                FACTORY_CLASSES.append(_cls)
                _cls = SubstanceParmsPanelFactory(_space[1])
                FACTORY_CLASSES.append(_cls)

                _menu_cls = SubstanceShortcutMenuFactory(_space[1])
                FACTORY_CLASSES.append(_menu_cls)

        # Register blender classes
        from bpy.utils import register_class
        for _cls in DEFAULT_CLASSES:
            register_class(_cls)
        for _cls in FACTORY_CLASSES:
            register_class(_cls)

        # Addon Preferences
        _addon_prefs = bpy.context.preferences.addons[ADDON_PACKAGE].preferences

        # Shortcuts
        _shortcuts = _addon_prefs.shortcuts
        wm = bpy.context.window_manager
        _kc = wm.keyconfigs.addon
        for _space in UI_SPACES:
            if _kc:
                _km = wm.keyconfigs.addon.keymaps.new(name=_space[0], space_type=_space[1])
                _kmi = _km.keymap_items.new(
                    'wm.call_menu',
                    _shortcuts.menu_key,
                    'PRESS',
                    ctrl=_shortcuts.menu_ctrl,
                    shift=_shortcuts.menu_shift,
                    alt=_shortcuts.menu_alt
                )
                _kmi.properties.name = SHORTCUT_CLASS_NAME.format(_space[1])
                SHORTCUT_KEYMAPS.append((_km, _kmi))

                _kmi = _km.keymap_items.new(
                    SUBSTANCE_OT_LoadSBSAR.bl_idname,
                    _shortcuts.load_key,
                    'PRESS',
                    ctrl=_shortcuts.load_ctrl,
                    shift=_shortcuts.load_shift,
                    alt=_shortcuts.load_alt
                )
                SHORTCUT_KEYMAPS.append((_km, _kmi))

                _kmi = _km.keymap_items.new(
                    SUBSTANCE_OT_ApplySBSAR.bl_idname,
                    _shortcuts.apply_key,
                    'PRESS',
                    ctrl=_shortcuts.apply_ctrl,
                    shift=_shortcuts.apply_shift,
                    alt=_shortcuts.apply_alt
                )
                SHORTCUT_KEYMAPS.append((_km, _kmi))

        # Create scene SBSAR variables
        bpy.types.Scene.loaded_sbsars = bpy.props.CollectionProperty(type=SUBSTANCE_PG_Sbsar)
        bpy.types.Scene.sbsar_index = bpy.props.IntProperty(
            name='sbsar_index',
            default=0,
            options={'HIDDEN'},
            update=sbsar_index_changed
        )

        # Init icons
        SUBSTANCE_Utils.init_icons()

        # Shader Presets
        _addon_prefs.shader_presets.clear()
        _result = SUBSTANCE_Api.shader_presets_initialize()
        if _result[0] != Code_Response.success:
            SUBSTANCE_Utils.log_data("ERROR", "[{}] Shader presets cannot be initialized...".format(_result))
            return
        for _shader_preset in _result[1]:
            _new_shader = _addon_prefs.shader_presets.add()
            _new_shader.initialize(_shader_preset)
        SUBSTANCE_Utils.log_data("INFO", "Shader Presets initialized...")

        # Add main thread listener
        if not bpy.app.timers.is_registered(SUBSTANCE_Threads.exec_queued_function):
            bpy.app.timers.register(SUBSTANCE_Threads.exec_queued_function)

        # Initialize blender handlers
        bpy.app.handlers.load_post.append(SUBSTANCE_Persistance.load_post_handler)
        bpy.app.handlers.load_pre.append(SUBSTANCE_Persistance.load_pre_handler)
        bpy.app.handlers.save_pre.append(SUBSTANCE_Persistance.save_pre_handler)
        bpy.app.handlers.save_post.append(SUBSTANCE_Persistance.save_post_handler)
        bpy.app.handlers.undo_post.append(SUBSTANCE_Persistance.undo_post_handler)
        bpy.app.handlers.depsgraph_update_post.append(SUBSTANCE_Persistance.depsgraph_update_post)

        # Initialize SUBSTANCE_Api listeners
        SUBSTANCE_Api.listeners_add("post", dispatcher_get)

    def unregister():
        # Remove shortcuts
        for _km, _kmi in SHORTCUT_KEYMAPS:
            _km.keymap_items.remove(_kmi)
        SHORTCUT_KEYMAPS.clear()

        # Remove sbsar dynamic classes
        for _scene in bpy.data.scenes:
            for _item in _scene.loaded_sbsars:
                SUBSTANCE_Api.sbsar_unregister(_item.id)
            _scene.loaded_sbsars.clear()

        # Shutdown SUBSTANCE_Api
        SUBSTANCE_Api.listeners_remove("post", dispatcher_get)
        SUBSTANCE_Api.shutdown()

        # Remove blender handlers
        bpy.app.handlers.load_post.remove(SUBSTANCE_Persistance.load_post_handler)
        bpy.app.handlers.load_pre.remove(SUBSTANCE_Persistance.load_pre_handler)
        bpy.app.handlers.save_pre.remove(SUBSTANCE_Persistance.save_pre_handler)
        bpy.app.handlers.save_post.remove(SUBSTANCE_Persistance.save_post_handler)
        bpy.app.handlers.undo_post.remove(SUBSTANCE_Persistance.undo_post_handler)
        bpy.app.handlers.depsgraph_update_post.remove(SUBSTANCE_Persistance.depsgraph_update_post)

        # Remove main thread listener
        if bpy.app.timers.is_registered(SUBSTANCE_Threads.exec_queued_function):
            bpy.app.timers.unregister(SUBSTANCE_Threads.exec_queued_function)

        # Cleanup Shader Presets list
        bpy.ops.substance.save_shader_presets()
        bpy.ops.substance.remove_shader_presets()

        # Delete scene SBSAR variables
        del bpy.types.Scene.loaded_sbsars
        del bpy.types.Scene.sbsar_index

        # Unregister blender classes
        from bpy.utils import unregister_class
        for _cls in reversed(DEFAULT_CLASSES):
            unregister_class(_cls)
        for _cls in reversed(FACTORY_CLASSES):
            unregister_class(_cls)

    if __name__ == "__main__":
        register()
except Exception:
    pass
