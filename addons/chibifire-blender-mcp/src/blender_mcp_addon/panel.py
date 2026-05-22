import bpy

from . import state
from .common import get_prefs
from .preferences import draw_settings


class BLENDERMCP_PT_Panel(bpy.types.Panel):
    bl_label = "Blender MCP"
    bl_idname = "BLENDERMCP_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderMCP'

    def draw(self, context):
        prefs = get_prefs()
        draw_settings(self.layout, prefs)

        if state.server is not None and state.server.running:
            self.layout.operator("blendermcp.stop_server", text="Disconnect from MCP server")
            self.layout.label(text=f"Running on port {prefs.blendermcp_port}")
        else:
            self.layout.operator("blendermcp.start_server", text="Connect to MCP server")
