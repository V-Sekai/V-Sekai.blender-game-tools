
import bpy
from bpy.types import NodeTree, NodeGroup, SpaceNodeEditor, Window
from typing import List, Tuple

def ensure_gn_editor(wnd: Window) -> bpy.types.Area or None:
    def _get_gn_editor() -> bpy.types.Area or None:
        for _area in wnd.screen.areas:
            if _area.type == 'NODE_EDITOR' and _area.ui_type == 'GeometryNodeTree':
                return _area
        return None

    gn_editor = _get_gn_editor()

    if gn_editor is None:
        for area in wnd.screen.areas:
            if area.type == 'VIEW_3D':
                # Create and Setup new GN Editor.
                with bpy.context.temp_override(window=wnd, area=area):
                    all_areas_memaddress = {area.as_pointer() for area in wnd.screen.areas}
                    bpy.ops.screen.area_split(factor=0.01, direction='HORIZONTAL')
                    for _area in wnd.screen.areas:
                        if _area.as_pointer() not in all_areas_memaddress:
                            _area.type = 'NODE_EDITOR'
                            _area.ui_type = 'GeometryNodeTree'
                            return _area
                break

    return gn_editor


def activate_viewer(node_groups: List[Tuple[NodeTree, NodeGroup]], wnd: Window) -> None:
    print("Activate Viewer! ________________________________________")

    gn_editor = ensure_gn_editor(wnd)
    if gn_editor is None:
        print("\t- ERROR! No GN Editor")
        return

    # print(gn_editor, gn_editor.type, gn_editor.ui_type)

    space_node: SpaceNodeEditor = gn_editor.spaces.active
    space_node.pin = True

    region = None
    for _region in gn_editor.regions:
        if _region.type == 'WINDOW':
            region = _region
            break

    processed_node_tree = set()

    with bpy.context.temp_override(window=wnd, area=gn_editor, region=region):
        for (node_tree, node_group) in node_groups:
            if node_tree is None or node_group is None:
                continue
            if node_tree in processed_node_tree:
                # May be shared between different objects? Just to ensure.
                continue

            space_node.node_tree = node_tree

            # Ensure that the viewer node is selected and active.
            # for node in node_tree.nodes:
            #     if node.type == 'VIEWER':
            #         for idx in range(1, len(node.outputs)):
            #             output = node.outputs[idx]
            #             for link in output.links:
            #                 node_tree.links.remove(link)
            #         break

            bpy.ops.node.select_all(action='DESELECT')
            node_group.select = True
            node_tree.nodes.active = node_group
            bpy.ops.node.link_viewer()

            # node.select = True
            # node_tree.nodes.active = node

            # bpy.ops.node.view_selected('INVOKE_DEFAULT', False)
            # node_region_loc = region.view2d.view_to_region(*node.location.to_tuple(), clip=True)
            # print("POST Viewer Node Location: ", node_region_loc)
            # bpy.ops.node.select(deselect_all=True, select_passthrough=True, location=(
            #     node_region_loc[0] + 10,
            #     node_region_loc[1] - 10
            # ))

            processed_node_tree.add(node_tree)
        
    print("_________________________________________________________")



