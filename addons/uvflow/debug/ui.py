from uvflow.addon_utils import Register
from uvflow.prefs import UVFLOW_Preferences

from bpy.types import Context, UILayout


@Register.UI.PANEL.IMAGE_EDITOR
class UVEDITOR_DebugOptionsPanel:
    label = 'Debug'

    @classmethod
    def poll(cls, context: Context) -> bool:
        if context.area.ui_type != 'UV':
            return False
        prefs = UVFLOW_Preferences.get_prefs(context)
        return prefs.uv_editor_debug.enabled

    def draw_ui(self, context: Context, layout: UILayout) -> None:
        prefs = UVFLOW_Preferences.get_prefs(context)
        debug = prefs.uv_editor_debug

        layout.prop(debug, 'show_island_border')
        layout.prop(debug, 'show_sel_loop')
        layout.prop(debug, 'show_linked_loops')
        # layout.prop(debug, 'show_link_loop_next')
        # layout.prop(debug, 'show_link_loop_prev')
        # layout.prop(debug, 'show_link_loop_radial_next')
        # layout.prop(debug, 'show_link_loop_radial_prev')
        layout.prop(debug, 'show_seams')
        layout.row().prop(debug, 'show_indices', expand=True, icon_only=True)
