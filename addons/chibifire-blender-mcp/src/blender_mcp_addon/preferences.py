import bpy


def draw_settings(layout, prefs):
    layout.prop(prefs, "blendermcp_port")
    layout.prop(prefs, "blendermcp_autostart")
    layout.prop(prefs, "blendermcp_use_polyhaven", text="Use assets from Poly Haven")

    layout.prop(prefs, "blendermcp_use_hyper3d", text="Use Hyper3D Rodin 3D model generation")
    if prefs.blendermcp_use_hyper3d:
        layout.prop(prefs, "blendermcp_hyper3d_mode", text="Rodin Mode")
        layout.prop(prefs, "blendermcp_hyper3d_api_key", text="API Key")
        layout.operator("blendermcp.set_hyper3d_free_trial_api_key", text="Set Free Trial API Key")

    layout.prop(prefs, "blendermcp_use_sketchfab", text="Use assets from Sketchfab")
    if prefs.blendermcp_use_sketchfab:
        layout.prop(prefs, "blendermcp_sketchfab_api_key", text="API Key")

    layout.prop(prefs, "blendermcp_use_hunyuan3d", text="Use Tencent Hunyuan 3D model generation")
    if prefs.blendermcp_use_hunyuan3d:
        layout.prop(prefs, "blendermcp_hunyuan3d_mode", text="Hunyuan3D Mode")
        if prefs.blendermcp_hunyuan3d_mode == 'OFFICIAL_API':
            layout.prop(prefs, "blendermcp_hunyuan3d_secret_id", text="SecretId")
            layout.prop(prefs, "blendermcp_hunyuan3d_secret_key", text="SecretKey")
        if prefs.blendermcp_hunyuan3d_mode == 'LOCAL_API':
            layout.prop(prefs, "blendermcp_hunyuan3d_api_url", text="API URL")
            layout.prop(prefs, "blendermcp_hunyuan3d_octree_resolution", text="Octree Resolution")
            layout.prop(prefs, "blendermcp_hunyuan3d_num_inference_steps", text="Number of Inference Steps")
            layout.prop(prefs, "blendermcp_hunyuan3d_guidance_scale", text="Guidance Scale")
            layout.prop(prefs, "blendermcp_hunyuan3d_texture", text="Generate Texture")


class BlenderMCPPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    blendermcp_port: bpy.props.IntProperty(
        name="Port",
        description="Port for the BlenderMCP server",
        default=9876,
        min=1024,
        max=65535,
    )
    blendermcp_autostart: bpy.props.BoolProperty(
        name="Auto-connect on Blender launch",
        description="Start the MCP server automatically when the addon loads",
        default=True,
    )
    blendermcp_use_polyhaven: bpy.props.BoolProperty(
        name="Use Poly Haven",
        description="Enable Poly Haven asset integration",
        default=False,
    )
    blendermcp_use_hyper3d: bpy.props.BoolProperty(
        name="Use Hyper3D Rodin",
        description="Enable Hyper3D Rodin generation integration",
        default=False,
    )
    blendermcp_hyper3d_mode: bpy.props.EnumProperty(
        name="Rodin Mode",
        description="Choose the platform used to call Rodin APIs",
        items=[
            ("MAIN_SITE", "hyper3d.ai", "hyper3d.ai"),
            ("FAL_AI", "fal.ai", "fal.ai"),
        ],
        default="MAIN_SITE",
    )
    blendermcp_hyper3d_api_key: bpy.props.StringProperty(
        name="Hyper3D API Key",
        subtype="PASSWORD",
        description="API Key provided by Hyper3D",
        default="",
    )
    blendermcp_use_hunyuan3d: bpy.props.BoolProperty(
        name="Use Hunyuan 3D",
        description="Enable Hunyuan asset integration",
        default=False,
    )
    blendermcp_hunyuan3d_mode: bpy.props.EnumProperty(
        name="Hunyuan3D Mode",
        description="Choose a local or official APIs",
        items=[
            ("LOCAL_API", "local api", "local api"),
            ("OFFICIAL_API", "official api", "official api"),
        ],
        default="LOCAL_API",
    )
    blendermcp_hunyuan3d_secret_id: bpy.props.StringProperty(
        name="Hunyuan 3D SecretId",
        description="SecretId provided by Hunyuan 3D",
        default="",
    )
    blendermcp_hunyuan3d_secret_key: bpy.props.StringProperty(
        name="Hunyuan 3D SecretKey",
        subtype="PASSWORD",
        description="SecretKey provided by Hunyuan 3D",
        default="",
    )
    blendermcp_hunyuan3d_api_url: bpy.props.StringProperty(
        name="API URL",
        description="URL of the Hunyuan 3D API service",
        default="http://localhost:8081",
    )
    blendermcp_hunyuan3d_octree_resolution: bpy.props.IntProperty(
        name="Octree Resolution",
        description="Octree resolution for the 3D generation",
        default=256,
        min=128,
        max=512,
    )
    blendermcp_hunyuan3d_num_inference_steps: bpy.props.IntProperty(
        name="Number of Inference Steps",
        description="Number of inference steps for the 3D generation",
        default=20,
        min=20,
        max=50,
    )
    blendermcp_hunyuan3d_guidance_scale: bpy.props.FloatProperty(
        name="Guidance Scale",
        description="Guidance scale for the 3D generation",
        default=5.5,
        min=1.0,
        max=10.0,
    )
    blendermcp_hunyuan3d_texture: bpy.props.BoolProperty(
        name="Generate Texture",
        description="Whether to generate texture for the 3D model",
        default=False,
    )
    blendermcp_use_sketchfab: bpy.props.BoolProperty(
        name="Use Sketchfab",
        description="Enable Sketchfab asset integration",
        default=False,
    )
    blendermcp_sketchfab_api_key: bpy.props.StringProperty(
        name="Sketchfab API Key",
        subtype="PASSWORD",
        description="API Key provided by Sketchfab",
        default="",
    )

    def draw(self, context):
        draw_settings(self.layout, self)
