import bpy
from bl_xr import root, xr_session

import textwrap

from ..settings_manager import settings, FreebirdAddonPreferences

WEBSITE_URL = "https://freebirdxr.com/"
TOGGLE_XR_OP = "freebird.xr_toggle"
DISCORD_URL = "https://discord.gg/X6B4ZYEWSS"


class XRToggleOperator(bpy.types.Operator):
    bl_idname = TOGGLE_XR_OP
    bl_label = "Freebird XR Start/Stop"

    def invoke(self, context, event):
        "Called when the 'Start/Stop VR' toggle button is pressed in the desktop UI"

        import bl_xr
        from freebird.utils import is_cycles_rendering, log

        if context.area.type != "VIEW_3D":
            self.report({"WARNING"}, "View3D not found, cannot run operator")
            return {"CANCELLED"}

        bpy.context = context

        if is_cycles_rendering():
            log.warning("Can't start XR when Cycles is being used to render images.")
            self.report(
                {"ERROR"},
                "Freebird cannot start XR editing in Cycles Rendered Mode. Try switching to EEVEE or use Object/Material Shading.",
            )
            return

        was_xr_running = xr_session.is_running
        if was_xr_running:
            bl_xr.unregister_controllers()
        else:
            bl_xr.register_controllers()

        bpy.ops.wm.xr_session_toggle()

        if was_xr_running:
            root.dispatch_event("fb.xr_end", None)
        else:
            root.dispatch_event("fb.xr_start", None)

        return {"FINISHED"}


def draw_preferences_panel(self, context):
    layout = self.layout

    layout.use_property_split = True
    layout.prop(self, "log_level", expand=False)
    layout.prop(self, "show_dev_tools", expand=False)
    layout.use_property_split = False

    split = layout.split()
    col = split.column(align=True)
    col.operator("freebird.open_log", text="Open Crash Log", icon="GHOST_ENABLED").log_type = "CRASH"
    col = split.column(align=True)
    col.operator("freebird.open_log", text="Open Previous App Log", icon="KEYFRAME_HLT").log_type = "APP_PREV"
    col = split.column(align=True)
    col.operator("freebird.open_log", text="Open Current App Log", icon="KEYFRAME_HLT").log_type = "APP"

    layout.use_property_split = True
    col = layout.column(align=True, heading="Experimental Headsets")
    col.prop(self, "headset_reverb_g2", text="HP Reverb G2")
    col.prop(self, "headset_vive_cosmos", text="HTC Vive Cosmos")
    col.prop(self, "headset_vive_focus", text="HTC Vive Focus 3")
    layout.use_property_split = False


def draw_xr_button(self, context):
    toggle_info = ("Start VR", "PLAY") if not xr_session.is_running else ("Stop VR", "SNAP_FACE")
    self.layout.operator(TOGGLE_XR_OP, text=toggle_info[0], icon=toggle_info[1])


def draw_xr_not_supported(self, context):
    layout = self.layout
    layout.operator("wm.url_open", text="VR/OpenXR not supported!", icon="ERROR").url = WEBSITE_URL


def draw_xr_options_button(self, context):
    from freebird import updater

    layout = self.layout

    if updater.needs_update:
        show_update_button(layout, location="HEADER")

    layout.popover("VIEW3D_PT_xr_options_panel", text="Freebird Settings", icon="OPTIONS")


class VIEW3D_PT_xr_options_panel(bpy.types.Panel):
    bl_label = "Freebird Settings"
    bl_idname = "VIEW3D_PT_xr_options_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        from freebird import updater, MODULE_ID

        layout = self.layout
        view3d = context.space_data
        pref = context.preferences.addons[MODULE_ID].preferences

        if updater.curr_version:
            curr_version = [str(a) for a in updater.curr_version]
            curr_version = f"v{'.'.join(curr_version)} ({updater.curr_commit})"

            split = layout.split(factor=0.9)
            col = split.column(align=True)
            col.label(text=f"Freebird - {curr_version}")
            col = split.column(align=True)
            col.operator("freebird.copy_to_clipboard", text="", icon="COPYDOWN").text = curr_version
        else:
            layout.label(text=f"Freebird")

        layout.separator()

        layout.prop(view3d, "mirror_xr_session", text="Screencast VR view")
        layout.prop(pref, "sync_with_viewport")
        layout.prop(pref, "strict_viewport_sync")
        layout.prop(pref, "lock_z_rotation")
        layout.prop(pref, "lock_pose_bone_position")

        row = layout.row()
        split = row.split(factor=0.3)
        col = split.column()
        col.label(text="Collection")
        col = split.column()
        col.prop(context.scene, "freebird_draw_collection", text="")

        layout.separator()

        layout.use_property_split = True
        layout.prop(pref, "main_hand", expand=False)
        layout.use_property_split = False

        layout.separator()

        layout.label(text=f"Updates:")
        layout.prop(pref, "early_access")
        layout.prop(pref, "auto_update")

        show_update_button(layout, location="PANEL")

        if updater.update_error:
            error_msgs = textwrap.TextWrapper(width=30).wrap(updater.update_error)
            layout.alert = True

            for msg in error_msgs:
                row = layout.row(align=True)
                row.alignment = "EXPAND"
                row.label(text=msg)
            layout.alert = False

        layout.operator("wm.url_open", text="Help & Community", icon="COMMUNITY").url = DISCORD_URL

        if pref.show_dev_tools:
            layout.separator()

            layout.label(text=f"Developer Tools:")

            layout.prop(pref, "log_filter_enabled")
            if pref.log_filter_enabled:
                box = layout.box()
                box.prop(pref, "log_filter__move_events")
                box.prop(pref, "log_filter__drag_events")
                box.prop(pref, "log_filter__pointer_events")

        layout.separator()

        layout.label(text=f"Beta Tools:")

        layout.use_property_split = True
        layout.prop(pref, "grab_button")
        layout.use_property_split = False

        split = layout.split()
        col = split.column(align=True)
        col.operator("freebird.open_log", text="Crash Log", icon="GHOST_ENABLED").log_type = "CRASH"
        col = split.column(align=True)
        col.operator("freebird.open_log", text="Prev App Log", icon="KEYFRAME_HLT").log_type = "APP_PREV"

        layout.operator("freebird.open_log", text="App Log", icon="KEYFRAME_HLT").log_type = "APP"

        layout.prop(pref, "log_level", expand=True)


class OpenLogOperator(bpy.types.Operator):
    bl_idname = "freebird.open_log"
    bl_label = "Freebird Open Log"

    log_type: bpy.props.StringProperty()

    def invoke(self, context, event):
        import webbrowser
        import tempfile
        from os import path

        from freebird.log_manager import LOG_FILE, PREV_LOG_FILE

        log_path = None
        if self.log_type == "CRASH":
            log_path = path.join(tempfile.gettempdir(), "blender.crash.txt")
        elif self.log_type == "APP":
            log_path = path.join(tempfile.gettempdir(), LOG_FILE)
        elif self.log_type == "APP_PREV":
            log_path = path.join(tempfile.gettempdir(), PREV_LOG_FILE)

        if log_path and path.exists(log_path):
            webbrowser.open(log_path)

        return {"FINISHED"}


class CopyToClipboardOperator(bpy.types.Operator):
    bl_idname = "freebird.copy_to_clipboard"
    bl_label = "Freebird Copy to Clipboard"

    text: bpy.props.StringProperty()

    def invoke(self, context, event):
        context.window_manager.clipboard = self.text

        return {"FINISHED"}


def show_update_button(layout, location):
    from freebird import updater

    if updater.update_checking_state == "CHECKING":
        layout.operator("freebird.check_update", text="Checking..", icon="IPO_ELASTIC")
    elif updater.curr_commit == updater.latest_available_commit:
        layout.operator("freebird.check_update", text="Check for Freebird update")
    elif updater.update_installing_state is None:
        if location == "HEADER":
            layout.alert = True
            layout.operator("freebird.apply_update", text="Click to update Freebird", icon="ARMATURE_DATA")
            layout.alert = False
        else:
            layout.operator("freebird.apply_update", text="Click to update Freebird")

        changelog_url = updater.get_download_info()["changelog_url"]
        layout.operator("wm.url_open", text="What's new in the update?", icon="QUESTION").url = changelog_url
    elif updater.update_installing_state == "DOWNLOADING":
        layout.operator("freebird.apply_update", text="Downloading..", icon="IPO_ELASTIC")
    elif updater.update_installing_state == "INSTALLING":
        layout.operator("freebird.apply_update", text="Installing..", icon="IPO_ELASTIC")
    elif updater.update_installing_state == "INSTALLED":
        layout.operator("wm.restart_blender", text="Updated. Click to restart Blender", icon="KEYTYPE_JITTER_VEC")
    elif updater.update_installing_state == "ERROR":
        layout.alert = True
        if location == "HEADER":
            layout.operator("freebird.apply_update", text="Error! Click to try again", icon="ERROR")
        else:
            layout.operator(
                "freebird.apply_update",
                text="Error installing update! Open 'Freebird Settings' for details",
                icon="ERROR",
            )
        layout.alert = False


FreebirdAddonPreferences.draw = draw_preferences_panel


def enable():
    if bpy.app.build_options.xr_openxr:
        bpy.types.VIEW3D_HT_header.append(draw_xr_button)
        bpy.types.VIEW3D_HT_header.append(draw_xr_options_button)
    else:
        bpy.types.VIEW3D_HT_header.append(draw_xr_not_supported)

    bpy.utils.register_class(VIEW3D_PT_xr_options_panel)
    bpy.utils.register_class(XRToggleOperator)
    bpy.utils.register_class(OpenLogOperator)
    bpy.utils.register_class(CopyToClipboardOperator)


def disable():
    if bpy.app.build_options.xr_openxr:
        bpy.types.VIEW3D_HT_header.remove(draw_xr_button)
        bpy.types.VIEW3D_HT_header.remove(draw_xr_options_button)
    else:
        bpy.types.VIEW3D_HT_header.remove(draw_xr_not_supported)

    bpy.utils.unregister_class(VIEW3D_PT_xr_options_panel)
    bpy.utils.unregister_class(XRToggleOperator)
    bpy.utils.unregister_class(OpenLogOperator)
    bpy.utils.unregister_class(CopyToClipboardOperator)
