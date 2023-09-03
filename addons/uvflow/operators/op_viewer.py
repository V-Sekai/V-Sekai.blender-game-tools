import bpy
from bpy.types import NodeTree, NodeGroup, SpaceNodeEditor, Window, Area, Context

from uvflow.addon_utils import Register
from .op_editor_management import get_gn_editor


@Register.OPS.GENERIC
class ActivateViewer:
    label: str = 'Activate Viewer'
    
    @classmethod
    def poll(cls, context) -> bool:
        return context.object and get_gn_editor(context.window) is not None

    def action(self, context: Context):
        print("Operator: Activate Viewer", context, context.area.type, context.region.type)
        # gn_editor, is_new = ensure_gn_editor(context.window)
        for area in context.screen.areas:
            if area.type == 'NODE_EDITOR' and area.ui_type == 'GeometryNodeTree':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        space_node = area.spaces.active
                        with context.temp_override(window=context.window, area=area, region=region, space_data=space_node):
                            bpy.ops.node.link_viewer()
                return
