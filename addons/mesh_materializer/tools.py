import bpy
from bpy.types import WorkSpaceTool
import os

class MeshMaterializerTool(WorkSpaceTool):
    """Mesh Materializer Tool UI for side Tool Panel."""
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_idname = "mesh_materializer.mesh_materializer_select"
    bl_label = "Mesh Materializer"
    bl_description = (
        "Add a material mesh"
    )
    bl_cursor = "PAINT_BRUSH"
    bl_icon = os.path.join (os.path.dirname (__file__), 'icons/ops.view3d.mesh_materializer')
    bl_widget = None
    # bl_keymap = (
    #     (
    #         "view3d.mesh_materializer_modal", 
    #         {"type": 'LEFTMOUSE', "value": 'PRESS'},
    #         None
    #     ),
    #     (
    #         "view3d.mesh_materializer_modal", 
    #         {"type": 'RIGHTMOUSE', "value": 'PRESS'},
    #         None
    #     ),
    #     )
    def draw_settings(context, layout, tool):
        props = tool.operator_properties("view3d.mesh_materializer_modal")
        layout.prop(props, "distance")

class MeshMaterializerToolEdit(MeshMaterializerTool):
    """Same Paint Brush Tool but for edit mesh mode."""
    bl_context_mode = 'EDIT_MESH'