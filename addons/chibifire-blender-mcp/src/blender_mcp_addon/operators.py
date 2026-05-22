import bpy

from . import state
from .common import RODIN_FREE_TRIAL_KEY, get_prefs
from .server import BlenderMCPServer


class BLENDERMCP_OT_SetFreeTrialHyper3DAPIKey(bpy.types.Operator):
    bl_idname = "blendermcp.set_hyper3d_free_trial_api_key"
    bl_label = "Set Free Trial API Key"

    def execute(self, context):
        prefs = get_prefs()
        prefs.blendermcp_hyper3d_api_key = RODIN_FREE_TRIAL_KEY
        prefs.blendermcp_hyper3d_mode = 'MAIN_SITE'
        self.report({'INFO'}, "API Key set successfully!")
        return {'FINISHED'}


class BLENDERMCP_OT_StartServer(bpy.types.Operator):
    bl_idname = "blendermcp.start_server"
    bl_label = "Connect to Claude"
    bl_description = "Start the BlenderMCP server to connect with Claude"

    def execute(self, context):
        if state.server is None:
            state.server = BlenderMCPServer(port=get_prefs().blendermcp_port)
        state.server.start()
        return {'FINISHED'}


class BLENDERMCP_OT_StopServer(bpy.types.Operator):
    bl_idname = "blendermcp.stop_server"
    bl_label = "Stop the connection to Claude"
    bl_description = "Stop the connection to Claude"

    def execute(self, context):
        if state.server is not None:
            state.server.stop()
            state.server = None
        return {'FINISHED'}
