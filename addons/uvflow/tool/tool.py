from time import time
import os

from bpy import ops as OPS
from bpy.types import Context, Event, Mesh, Object

import bmesh
from bmesh.types import BMesh, BMEdge, BMVert, BMFace, BMLoop
from mathutils import Vector, Matrix, Quaternion

from uvflow.addon_utils import Register
from uvflow.addon_utils.types import EventType, EventValue, Mouse, ToolAction, ToolActionModal, Vector2i, OpsReturn, ModalTrigger
from uvflow.addon_utils.types.event import Mouse
from uvflow.utils.raycast import BVHTreeRaycastInfo
from uvflow.utils.cursor import Cursor
from uvflow.utils.math import distance_between, map_value, lineseg_dist
from uvflow.gpu import idraw
from uvflow.globals import GLOBALS, print_debug
from .tool_settings import UVFlowToolSettings
from uvflow.prefs import UVFLOW_Preferences
from uvflow.operators.op_pack import UVPack
from uvflow.operators.op_unwrap import UVUnwrap
from uvflow.tool.attributes import save_attributes
from uvflow.gpu.handler import DrawHandler
from .tool_state import ToolState
from uvflow.utils.editor_uv import frame_select_uvs_from_view3d_selection, select_uvs_from_view3d_selection


# Our ToolState Instance.
tool_state = ToolState.get()



########################################################
########################################################
# UV-FLOW TOOL.
########################################################

def prepare_tool(tool: ToolAction, toggle: bool = False, deselect_all: bool = True, do_select: bool = True, select_extend: bool = False):
    if deselect_all: OPS.mesh.select_all(False, action='DESELECT')
    OPS.mesh.select_mode(False, type=tool.geo_context)
    if tool.geo_context == 'FACE':
        OPS.mesh.select_mode(False, type=tool.geo_context, use_expand=True, use_extend=True, action='ENABLE')
    if do_select: OPS.view3d.select('INVOKE_DEFAULT', False, toggle=toggle, deselect_all=True, extend=select_extend)


def select_mirror(active_object: Object, expand: bool = True) -> None:
    mirror_axis = set()
    if active_object.use_mesh_mirror_x:
        mirror_axis.add('X')
    if active_object.use_mesh_mirror_x:
        mirror_axis.add('Y')
    if active_object.use_mesh_mirror_x:
        mirror_axis.add('Z')
    if len(mirror_axis) != 0:
        OPS.mesh.select_mirror('INVOKE_DEFAULT', False, axis=mirror_axis, extend=True)


def on_action_finish(tool_action: ToolAction, context: Context, event: Event):
    select_mirror(context.active_object, expand=True)

    OPS.mesh.mark_seam('INVOKE_DEFAULT', True, clear=event.alt)

    # Avoid unwrap, pack and mark_Seam to trigger the update mesh update.
    # NOTE: We skip mesh updates right after the mark_seam operator call,
    # to avoid issues with fake UpdateAttributes calls when we perform any action over UVMaps, etc...
    # So the depsgraph handler will trigger and the op_id pointer will be updated correctly with the tool_state condition.
    GLOBALS.skip_mesh_updates = True

    # NOTE: Probably we just need to save seams.
    save_attributes(context, seams=True, pinned=True, selected=True, hidden=True)

    bm = tool_state.raycast_info.ensure(context)
    if bm and bm.select_history:
        edge: BMEdge = bm.select_history.active
        tool_state.active_edge = edge.index
        ## print("on_action_finish() -> Active Edge ->", edge.index)
    else:
        print_debug("TOOL|\t> on_action_finish() -> WARN! Active Edge not found!")
        tool_state.active_edge = -1
        OPS.mesh.select_all(False, action='DESELECT')
        GLOBALS.skip_mesh_updates = False
        return

    prefs = UVFLOW_Preferences.get_prefs(context)

    if prefs.use_auto_unwrap:
        # Get selected edges.
        edges_sel: list[BMEdge] = tuple(edge for edge in bm.edges if edge.select)

        # Ensure everything is deselected and no active edge.
        OPS.mesh.select_all(False, action='DESELECT')

        # Iterate edges and perform linked selection.
        bm.select_mode = {'FACE'}
        for edge in edges_sel:
            for face in edge.link_faces:
                face.select_set(True)
        # bm.to_mesh(context.object.data)
        OPS.mesh.select_linked(False, delimit={'SEAM'})

        # Do unwrap!
        UVUnwrap.run()

        # Restore selection mode.
        # OPS.mesh.select_all(False, action='DESELECT')
        # bm = tool_state.raycast_info.ensure(context)
        # bm.select_mode = {'EDGE'}
        # for edge_index in edges_sel:
        #     bm.edges[edge_index].select_set(True)

    # Auto packing is slow has not shown to be a good workflow. Disabling for now
    # if prefs.use_auto_pack:
    #    UVPack.run()

    # Ensure last edge is active and selected (only one).
    # if not tool_action._is_modal:
    OPS.mesh.select_all(False, action='DESELECT')
    if not event.alt:
        bm = tool_state.raycast_info.ensure(context)
        bm.select_mode = {'EDGE'}
        edge = bm.edges[tool_state.active_edge]
        bm.select_history.add(edge)
        edge.select_set(True)
    else:
        tool_state.active_edge = -1

    GLOBALS.skip_mesh_updates = False



@Register.TOOLS.TOOL(context_mode='EDIT_MESH', after={'builtin.measure'}, group=False)
class UVFlowTool:
    label = 'Cut UV'
    bl_description = 'Quickly add or remove UV seams'
    icon = os.path.join(os.path.dirname(__file__), '..', 'assets', 'icons', 'cutuv')
    cursor = Cursor.CROSSHAIR.value

    @classmethod
    def pre_navigation(cls, context: Context):
        print("PRE NAVIGATION")
        tool_state.set_test_modal(True)

    @classmethod
    def post_navigation(cls, context: Context):
        print("POST NAVIGATION")
        tool_state.set_test_modal(False)

    def draw_settings(context, layout, tool):
        UVFlowToolSettings.draw(context, layout)

    def draw_cursor(context: Context, tool, xy):
        # NAVIGATION HACK.
        reg3d = context.region_data
        if tool_state.last_view_location != reg3d.view_location.to_tuple() or\
           tool_state.last_view_rotation != tuple(reg3d.view_rotation) or\
           tool_state.last_view_distance != reg3d.view_distance:
            tool_state.last_view_location = reg3d.view_location.to_tuple()
            tool_state.last_view_rotation = tuple(reg3d.view_rotation)
            tool_state.last_view_distance = reg3d.view_distance
            tool_state.last_view_change_time = time()
            tool_state.geo_context = 'NONE'
            tool_state.geo_coords.clear()
            tool_state.geo_batch = None
            tool_state.geo_index = -1
            return
        if tool_state.xy != xy:
            tool_state.xy = xy
        elif time() - tool_state.last_view_change_time < 0.15:
            return
        tool_state.update_raycast(context, Vector(xy) - Vector((context.area.x, context.area.y)))
        # tool_state.draw_batch(context) # Now using a draw_handler to draw this in 3D space.


    class MouseReleaseOutsideMesh(ToolAction):
        # TODO: Replace these with 'ModalTrigger' advanced functionality.
        event_type = EventType.LEFTMOUSE
        event_value = EventValue.RELEASE

        @classmethod
        def op_poll(self, context: Context) -> bool:
            return tool_state.geo_context == 'NONE'

        def action(self, context: Context, event: Event) -> None:
            # Do nothing atm.
            OPS.mesh.select_all(action='DESELECT')
            return OpsReturn.FINISH


    class MouseClickDragOutsideMesh(ToolAction):
        # TODO: Replace these with 'ModalTrigger' advanced functionality.
        event_type = EventType.LEFTMOUSE
        event_value = EventValue.CLICK_DRAG

        ctrl = 'TOGGLE'  # Telling the utility this can be True or False.
        shift = 'TOGGLE' # Telling the utility this can be True or False.

        @classmethod
        def op_poll(self, context: Context) -> bool:
            return tool_state.geo_context == 'NONE'

        def action(self, context: Context, event: Event) -> None:
            # Do nothing atm.
            if event.shift:
                mode = 'ADD'
            elif event.ctrl:
                mode = 'SUB'
            else:
                mode = 'SET'
            OPS.view3d.select_box('INVOKE_DEFAULT', wait_for_input=True, mode=mode)
            return OpsReturn.FINISH


    class FaceClick(ToolAction):
        event_type  = EventType.LEFTMOUSE
        event_value = EventValue.CLICK
        # alt = 'TOGGLE' # Telling the utility this can be True or False.
        # ctrl = 'TOGGLE' # Telling the utility this can be True or False.
        shift = 'TOGGLE'

        geo_context = 'FACE'

        @classmethod
        def op_poll(self, context: Context) -> bool:
            return tool_state.geo_context == self.geo_context

        def action(self, context: Context, event: Event) -> None:
            print("FACE CLICK!")
            # NOTE: Blender tools API is so awesome that even if you pass the CLICK event
            # in the operator poll or in the invoke, it won't trigger the DOUBLE_CLICK event.
            # BUT if you remove the CLICK operator and left the DOUBLE_CLICK, it will work lol.
            # So we need to catch the double click by ourselves in the CLICK operator/action. :-)
            # Thank u Blender <3
            tool_state.enter_tool(self)

            if tool_state.action_repeat(self) and not tool_state.time_exceed(0.33) and tool_state.mouse_distance_less(self.mouse, 3):
                UVFlowTool.FaceDoubleClick.get().action(context, event, skip_select=True)
                return

            prepare_tool(self, toggle=event.shift, deselect_all=(not event.shift), select_extend=event.shift)

            # on_action_finish(self, context, event)

            tool_state.update(self) # Utility HACK for the CLICK/DOUBLE_CLICK Blender BUG.
            tool_state.exit_tool()


    class FaceDoubleClick(ToolAction):
        event_type  = EventType.LEFTMOUSE
        event_value = EventValue.DOUBLE_CLICK

        shift = 'TOGGLE'

        geo_context = 'FACE'

        @classmethod
        def op_poll(self, context: Context) -> bool:
            return tool_state.geo_context == self.geo_context

        def action(self, context: Context, event: Event, skip_select: bool = False) -> None:
            print("FACE DOUBLE CLICK!")
            tool_state.enter_tool(self)
            if not skip_select:
                prepare_tool(self, deselect_all=(not event.shift), select_extend=event.shift)
            # context.scene.tool_settings.use_uv_select_sync = True
            # OPS.uv.select_linked()
            sel_faces = [face.index for face in tool_state.get_selected_faces(context)]
            OPS.mesh.select_linked(delimit={'SEAM'})
            tool_state.set_selected_faces(context, sel_faces, deselect_all=False)

            prefs = UVFLOW_Preferences.get_prefs(context)
            if prefs.use_frame_select_uvs:
                frame_select_uvs_from_view3d_selection(context, select_uvs=prefs.use_sync_select_uvs)
            elif prefs.use_sync_select_uvs:
                select_uvs_from_view3d_selection(context)

            tool_state.update(self) # Utility HACK for the CLICK/DOUBLE_CLICK Blender BUG.
            tool_state.exit_tool()

    class FaceClickDrag(ToolAction):
        event_type  = EventType.LEFTMOUSE
        event_value = EventValue.CLICK_DRAG
        #alt = 'TOGGLE' # Telling the utility this can be True or False.
        #ctrl = 'TOGGLE' # Telling the utility this can be True or False.
        #shift = 'TOGGLE'

        geo_context = 'FACE'

        @classmethod
        def op_poll(self, context: Context) -> bool:
            return tool_state.geo_context == self.geo_context

        def action(self, context: Context, event: Event) -> None:
            return -1



    class EdgeDoubleClick(ToolAction):
        event_type  = EventType.LEFTMOUSE
        event_value = EventValue.DOUBLE_CLICK
        alt = 'TOGGLE' # Telling the utility this can be True or False.
        shift = 'TOGGLE' # Telling the utility this can be True or False.

        # Hotkeys meant for compatibility with other devices or settings (eg. emulate 3 button mouse).
        additional_hotkeys = (
            {'type': EventType.RIGHTMOUSE, 'value': EventValue.DOUBLE_CLICK, 'alt': True},
        )

        geo_context = 'EDGE'

        @classmethod
        def op_poll(self, context: Context) -> bool:
            return tool_state.geo_context == self.geo_context

        def finish(self, context, event):
            # bmesh.update_edit_mesh(context.object.data, loop_triangles=False, destructive=False)
            on_action_finish(self, context, event)
            tool_state.update(self) # Utility HACK for the CLICK/DOUBLE_CLICK Blender BUG.
            tool_state.exit_tool()

        def action(self, context: Context, event: Event) -> None:
            print("EDGE DOUBLE CLICK!")
            if not hasattr(self, 'raycast_info'):
                print("\t-> WARN! No raycast info!")
                return -1

            tool_state.enter_tool(self)
            prepare_tool(self)

            if event.shift:
                OPS.mesh.loop_multi_select(False, ring=False)
                self.finish(context, event)
                return

            self.raycast_info.ensure(context)
            sel_edge: BMEdge = self.raycast_info.bm.select_history.active
            if sel_edge is None:
                return

            exclude_edges: set[BMEdge] = set()
            OPS.mesh.loop_multi_select(False, ring=False)
            if event.alt:
                loop_edges: set[BMEdge] = {edge for edge in self.raycast_info.bm.edges if edge.select and edge.seam}
            else:
                loop_edges: set[BMEdge] = {edge for edge in self.raycast_info.bm.edges if edge.select}
            OPS.mesh.select_all(False, action='DESELECT')

            # Split edges to confirm and to exclude from selection
            walked_v1: set[BMEdge] = set()
            walked_v2: set[BMEdge] = set()

            def walk_edge(edge: BMEdge, vertex: BMVert, walked: set[BMesh], deselect: bool = False):
                if deselect:
                    if edge in exclude_edges:
                        return
                    exclude_edges.add(edge)
                    for _edge in vertex.link_edges:
                        if _edge == edge:
                            continue
                        if _edge in walked:
                            continue
                        if _edge in loop_edges:
                            edge.select_set(False)
                            walk_edge(_edge, _edge.other_vert(vertex), walked, deselect=True)
                    return

                if edge in walked:
                    return

                if vertex is None:
                    return

                walked.add(edge)

                if any([_edge.seam for _edge in vertex.link_edges if _edge not in loop_edges]):
                    walk_edge(edge, vertex, walked, deselect=True)
                    return

                for _edge in vertex.link_edges:
                    if _edge == edge:
                        continue
                    if _edge in loop_edges:
                        # Continue the walk...
                        walk_edge(_edge, _edge.other_vert(vertex), walked)
                        break

            # Walk from v1:
            v1, v2 = sel_edge.verts
            walk_edge(sel_edge, v1, walked_v1)
            walk_edge(sel_edge, v2, walked_v2)
            # print(len(walked_v1), len(walked_v2))
            # print(len(loop_edges), len(exclude_edges))

            self.raycast_info.bm.select_history.clear()
            self.raycast_info.bm.select_history.add(sel_edge)

            for edge in walked_v1.union(walked_v2):
                edge.select_set(True)

            self.finish(context, event)

    class EdgeClick(ToolActionModal):
        event_type  = EventType.LEFTMOUSE
        event_value = EventValue.RELEASE
        alt = 'TOGGLE' # Telling the utility this can be True or False.
        ctrl = 'TOGGLE' # Telling the utility this can be True or False.

        # Hotkeys meant for compatibility with other devices or settings (eg. emulate 3 button mouse).
        additional_hotkeys = (
            {'type': EventType.RIGHTMOUSE, 'value': EventValue.RELEASE, 'alt': True},
        )

        geo_context = 'EDGE'

        @classmethod
        def op_poll(self, context: Context) -> bool:
            return tool_state.geo_context == self.geo_context

        def timer_poll(self, context: Context) -> bool:
            return True

        def enter(self, context: Context, event: Event) -> int:
            print("EDGE CLICK!")
            tool_state.enter_tool(self)
            prepare_tool(self)

            if tool_state.last_action == self and not tool_state.time_exceed(0.33) or tool_state.mouse_distance_less(self.mouse, 3):
                if event.type == EventType.RIGHTMOUSE and event.alt:
                    UVFlowTool.EdgeDoubleClick.action(self, context, event)
                    self.exit(context, event)
                    return OpsReturn.FINISH

            tool_state.update(self) # Utility HACK for the CLICK/DOUBLE_CLICK Blender BUG.

        def exit(self, context: Context, event: Event) -> int:
            if tool_state.last_action == self:
                on_action_finish(self, context, event)
                tool_state.exit_tool()

        def update_timer(self, context: Context, event: Event, mouse: Mouse) -> None:
            return self.update(context, event)

        def update(self, context: Context, event: Event) -> OpsReturn or None:
            if tool_state.time_exceed(0.33) or not tool_state.mouse_distance_less(self.mouse, 3):
                return OpsReturn.FINISH

            if event.type in {EventType.TIMER, EventType.MOUSEMOVE, EventType.INBETWEEN_MOUSEMOVE}:
                return OpsReturn.RUN

            if event.type == EventType.LEFTMOUSE and event.value == EventValue.RELEASE:
                UVFlowTool.EdgeDoubleClick.action(self, context, event)
                return OpsReturn.FINISH

            return OpsReturn.RUN


    class EdgeCtrlClick(ToolActionModal):
        # TODO: Replace these with 'ModalTrigger' advanced functionality.
        event_type = EventType.LEFT_CTRL
        event_value = EventValue.PRESS
        ctrl = True
        alt = 'TOGGLE' # Telling the utility this can be True or False.

        geo_context = 'EDGE'

        did_shortest_path: bool = False
        mouse_delta_limit: int = 4 # 4 px

        @classmethod
        def op_poll(self, context: Context) -> bool:
            mesh: Mesh = context.object.data
            return tool_state.geo_context != 'NONE' and tool_state.active_edge != -1 and mesh.total_edge_sel != 0

        def enter(self, context: Context, event: Event) -> int:
            print("EDGE CTRL!")
            first_time = tool_state.current_tool != self.__class__
            tool_state.enter_tool(self)
            prepare_tool(self, deselect_all=(not first_time), do_select=False)
            self.did_shortest_path = False
            self.edge_selection = []
            tool_state.prev_edge_dst = -1

            self.heavy_mesh = len(context.object.data.polygons) >= 50000 # hardcoded to test :-)
            if self.heavy_mesh: self.timer = time()

            tool_state.set_test_modal(state=True)

            # Force a start update.
            self.update_mousemove(context)

        def update(self, context: Context, event: Event) -> OpsReturn or None:
            ## print(event.type, event.value, event.type_prev, event.value_prev, event.ctrl)
            if event.type == EventType.Z and event.ctrl:
                self.exit(context, event)
                OPS.ed.undo('INVOKE_DEFAULT')
                return OpsReturn.CANCEL
            if event.type == EventType.LEFTMOUSE and event.value == EventValue.RELEASE:
                # print(event.type, event.value, event.ctrl, event.alt, event.shift)
                select_mirror(context.active_object, expand=True)
                OPS.mesh.mark_seam('INVOKE_DEFAULT', True, clear=event.alt)
                prepare_tool(self, deselect_all=True, do_select=True)
                self.did_shortest_path = False
                tool_state.update_active_edge(context)
                # on_action_finish(self, context, event)
                # self.enter(context, event)
                return

        def update_mousemove(self, context: Context) -> None:
            if self.heavy_mesh:
                if time() - self.timer < 0.1:
                    # Limit up to 10 updates per second.
                    return
            if not OPS.mesh.shortest_path_pick.poll():
                return
            if tool_state.geo_context == 'NONE':
                tool_state.update_raycast(context, self.mouse.current.to_vector())
                return

            tool_state.select_active_edge(context, deselect_all=True)

            dst_edge = tool_state.raycast_info.get_closest_edge(context)
            if not dst_edge:
                return

            if dst_edge.index == tool_state.prev_edge_dst:
                # We need to recover the previous selection between both edges.
                bm_edges = tool_state.raycast_info.bm.edges
                for edge_index in self.edge_selection:
                    bm_edges[edge_index].select_set(True)
                return

            dst_edge.select_set(True)
            tool_state.prev_edge_dst = dst_edge.index

            # When user mouse is outside editor...
            # Polling the operator doesn't work.
            # BUG: RuntimeError: Operator bpy.ops.mesh.shortest_path_pick.poll() expected a view3d region & editmesh
            OPS.mesh.shortest_path_pick('INVOKE_DEFAULT', False)
            self.did_shortest_path = True

            self.edge_selection = [edge.index for edge in tool_state.raycast_info.bm.edges if edge.select]

            if self.heavy_mesh: self.timer = time()

        def finish(self, context: Context, event: Event) -> int:
            if tool_state.active_edge == tool_state.prev_edge_dst or tool_state.prev_edge_dst == -1:
                return
            # Ensure that the last edge is active and selected.
            tool_state.select_active_edge(context, deselect_all=True)
            on_action_finish(self, context, event)

        def cancel(self, context: Context, event: Event) -> int:
            OPS.mesh.select_all(False, action='DESELECT')

        def exit(self, context: Context, event: Event) -> int:
            tool_state.prev_edge_dst = -1

            tool_state.set_test_modal(state=False)

            OPS.mesh.select_mode(False, type='FACE')
            OPS.mesh.select_mode(False, type='EDGE', action='ENABLE', use_expand=True, use_extend=True)

            tool_state.exit_tool()

    class EdgeClickDrag(ToolActionModal):
        # TODO: Replace these with 'ModalTrigger' advanced functionality.
        event_type = EventType.LEFTMOUSE
        event_value = EventValue.CLICK_DRAG
        alt = 'TOGGLE' # Telling the utility this can be True or False.

        geo_context = 'EDGE'

        vert_path: list[int]

        @classmethod
        def op_poll(self, context: Context) -> bool:
            return tool_state.geo_context == self.geo_context

        def enter(self, context: Context, event: Event) -> int:
            print("EDGE CLICK DRAG!")
            tool_state.enter_tool(self)

            self.vert_path: list[int] = [] # just the indices of the vertices
            self.vert_path_coords: list[Vector] = [] # Coordinates of the vertices
            self.mw = context.object.matrix_world
            self.edge_selection: list[int] = [] # just the indices of the edges as a set

            raycast_info: BVHTreeRaycastInfo = self.raycast_info
            if vert := raycast_info.get_closest_vert(context):
                self.add_vert_edge(context, vert, None)

                # TODO: Decide if add or remove seam...
                if edge := raycast_info.get_closest_edge(context):
                    other_vert = edge.other_vert(vert)
                    if other_vert is None:
                        print("WARN! UVFlowTool - EdgeClickDrag: Bad edge selected, other vert is Null...")
                        return -1
                    self.add_vert_edge(context, other_vert, None)
                    self.distance_threshold = edge.calc_length()
                    self.edge_selection.append(edge.index)
            else:
                # Force Cancel.
                return -1

            self.first_time = True
            self.cand_vert_idx = -1
            self.cand_factor = 0
            self.is_cand_too_far_away = False
            tool_state.skip_drawing = True
            self.tag_redraw = False

            prepare_tool(self)

            self.draw_handler = DrawHandler.start_3d(self, context)

        def update(self, context: Context, event: Event) -> OpsReturn or None:
            pass

        def find_edge_by_verts(self, v1: BMVert, v2: BMVert) -> BMEdge:
            for edge in v1.link_edges:
                if edge.other_vert(v1) == v2:
                    return edge
            return None

        def add_vert_edge(self, context: Context, vert: BMVert, edge: BMEdge = None) -> None:
            self.vert_path.append(vert.index)
            self.vert_path_coords.append(self.mw @ vert.co)

            if edge is not None:
                self.edge_selection.append(edge.index)
                edge.select_set(True)
                self.raycast_info.bm.select_history.add(edge)
                self.update_bm(context)

                # print("ADD EDGE", edge.index)

            self.cand_vert_idx = -1
            self.cand_factor = 0
            self.tag_redraw = True

        def remove_vert_edge(self, context: Context, _vert: BMVert, edge: BMEdge) -> None:
            self.edge_selection.pop(-1) #.remove(edge.index)
            edge.select_set(False)
            if edge in self.raycast_info.bm.select_history:
                self.raycast_info.bm.select_history.remove(edge)
            self.vert_path.pop(-1)
            self.vert_path_coords.pop(-1)
            self.tag_redraw = True
            self.update_bm(context)

            # print("REMOVE EDGE", edge.index)

            self.cand_vert_idx = -1
            self.cand_factor = 0
            self.tag_redraw = True

            if len(self.vert_path) == 2:
                self.first_time = True

        def update_bm(self, context: Context) -> None:
            self.raycast_info.bm.edges.ensure_lookup_table()
            bmesh.update_edit_mesh(context.object.data, loop_triangles=False, destructive=False)

        def get_nearest_vert_edge(self, context: Context) -> tuple[BMVert, BMEdge, bool]:
            if not self.raycast_info.result:
                ## print("Not raycast hit")
                return None, None, None

            hit_loc = self.raycast_info.location

            segments: float = 6
            nearest_vert = None
            nearest_edge = None
            max_distance = 1000000

            # Only 2 verts for the first time.
            if self.first_time:
                prev_vert: BMVert = self.raycast_info.bm.verts[self.vert_path[-2]]
                curr_vert: BMVert = self.raycast_info.bm.verts[self.vert_path[-1]]

                prev_dist = distance_between(prev_vert.co, hit_loc)
                curr_dist = distance_between(curr_vert.co, hit_loc)

                if curr_dist > prev_dist:
                    # 1st edge direction switch.
                    self.vert_path[0], self.vert_path[1] = self.vert_path[1], self.vert_path[0]
                    self.vert_path_coords[0], self.vert_path_coords[1] = self.vert_path_coords[1], self.vert_path_coords[0]

            prev_vert: BMVert = self.raycast_info.bm.verts[self.vert_path[-2]]
            curr_vert: BMVert = self.raycast_info.bm.verts[self.vert_path[-1]]

            edges: list[BMEdge] = curr_vert.link_edges
            vert_candidates: list[BMVert] = [edge.other_vert(curr_vert) for edge in edges]
            is_too_far_away = len(
                set(self.raycast_info.get_face_verts(context)).intersection(set(vert_candidates))
            ) == 0

            distances = [lineseg_dist(hit_loc, *[v.co for v in edge.verts]) for edge in edges]
            nearest_edge = edges[distances.index(min(distances))]
            nearest_vert = nearest_edge.other_vert(curr_vert)

            # Evaluate if we are enough far from the candidate vertice in a proportion of 64/36 in favor of candidate and against current.
            curr_dist = distance_between(curr_vert.co, hit_loc)
            cand_dist = distance_between(nearest_vert.co, hit_loc)
            tot_dist = curr_dist + cand_dist
            dist_factor = cand_dist / tot_dist

            ## print(f"Dist Factor of {dist_factor} between edges {curr_vert.index}/{nearest_vert.index}")

            self.cand_vert_idx = nearest_vert.index
            self.cand_factor = map_value(dist_factor, (1.0, 0.3), (0.0, 1.0))

            ## print(f"Candidate index [{self.cand_vert_idx}] and factor [{self.cand_factor}]")

            if dist_factor > 0.3:
                # Still within the incluence of the current vertice.
                if is_too_far_away:
                    return nearest_vert, nearest_edge, is_too_far_away
                else:
                    return None, None, is_too_far_away

            return nearest_vert, nearest_edge, is_too_far_away

        def timer_poll(self, context: Context) -> bool:
            return self.is_cand_too_far_away

        def update_timer(self, context: Context, event: Event, mouse: Mouse):
            self.update_mousemove(context)

        def update_mousemove(self, context: Context) -> None:
            raycast_info: BVHTreeRaycastInfo = self.raycast_info
            context.region.tag_redraw()

            # raycast_info.update(context, self.mouse.current.to_vector())
            cand_vert, cand_edge, self.is_cand_too_far_away = self.get_nearest_vert_edge(context)
            if not cand_vert or not cand_edge:
                if self.is_cand_too_far_away is None:
                    self.cand_vert_idx = -1
                # print("NO candidate vert_edge found")
                return

            if (self.first_time and cand_vert.index in self.vert_path) or\
                (cand_edge.index in set(self.edge_selection) and cand_vert.index != self.vert_path[-2]):
                self.cand_vert_idx = -1
                # print("INVALID candidate vert_edge index")
                return

            curr_vert: BMVert = raycast_info.bm.verts[self.vert_path[-1]]
            prev_vert: BMVert = raycast_info.bm.verts[self.vert_path[-2]]

            self.cand_vert_idx = cand_vert.index
            # self.is_cand_too_far_away = is_too_far_away # user is too far away from candidates...

            if self.first_time:
                edge_to_select = self.find_edge_by_verts(curr_vert, cand_vert)
                if edge_to_select is None:
                    print("NO edge to select", edge_to_select)
                    return

                self.add_vert_edge(context, cand_vert, edge_to_select)

                self.first_time = False

                return

            if cand_vert.index == prev_vert.index:
                if len(self.vert_path) <= 2:
                    return
                # Go bakcwards and deselect last edge.
                edge_to_deselect = self.find_edge_by_verts(prev_vert, curr_vert)
                self.remove_vert_edge(context, cand_vert, edge_to_deselect)

                print("REMOVE EDGE", edge_to_deselect.index)

            else:
                # Go forward and select new edge.
                edge_to_select = self.find_edge_by_verts(curr_vert, cand_vert)
                self.add_vert_edge(context, cand_vert, edge_to_select)

        def finish(self, context: Context, event: Event) -> int:
            on_action_finish(self, context, event)

        def exit(self, context: Context, event: Event) -> int:
            self.vert_path.clear()
            self.vert_path_coords.clear()

            tool_state.exit_tool()
            tool_state.skip_drawing = False
            self.draw_handler.stop(context)

        def draw_3d(self, context: Context) -> int:
            try:
                if not self.raycast_info.bm.is_valid:
                    return
            except ReferenceError as e:
                print("Invalid BMesh")
                return
            verts = self.raycast_info.bm.verts
            mw = self.mw

            idraw.line_3d(
                self.vert_path_coords,
                10.0,
                GLOBALS.THEME_TOOL_SELECTION,
                cache_idname=self.__class__.__name__ + '_active_edge_selection',
                cache_tag_redraw=self.tag_redraw
            )

            if self.first_time:
                vertices: tuple[BMVert] = (verts[self.vert_path[-1]], verts[self.vert_path[-2]])
            else:
                vertices: tuple[BMVert] = (verts[self.vert_path[-1]], )


            edge_selection = set(self.edge_selection)
            p_vertices: list[BMVert] = [edge.other_vert(vert)
                                        for vert in vertices
                                        for edge in vert.link_edges
                                        if edge.index not in edge_selection or\
                                           edge.index == self.edge_selection[-1]]
            prev_vert_index: int = self.vert_path[-2]
            idraw.point_3d(
                coords=[mw @ v.co for v in p_vertices if v.index != prev_vert_index],
                point_size=12.0,
                u_color=GLOBALS.THEME_TOOL_SUGGESTION_ADD,
                cache_idname=self.__class__.__name__ + '_selection_suggestion_add',
                cache_tag_redraw=self.tag_redraw
            )
            if len(self.vert_path) > 2:
                idraw.point_3d(
                    coords=[mw @ verts[prev_vert_index].co],
                    point_size=12.0,
                    u_color=GLOBALS.THEME_TOOL_SUGGESTION_REMOVE,
                    cache_idname=self.__class__.__name__ + '_selection_suggestion_remove',
                    cache_tag_redraw=self.tag_redraw
                )

            if self.cand_vert_idx != -1:
                curr_vert: BMVert = verts[self.vert_path[-1]]
                cand_vert: BMVert = verts[self.cand_vert_idx]

                if edge := self.find_edge_by_verts(curr_vert, cand_vert):
                    curr_vert_co_t: Vector = mw @ curr_vert.co
                    cand_vert_co_t: Vector = mw @ cand_vert.co

                    ab: Vector = cand_vert_co_t - curr_vert_co_t

                    edge_length = ab.length
                    direction = ab.normalized()

                    idraw.line_3d(
                        [
                            curr_vert_co_t,
                            curr_vert_co_t + direction * (edge_length * self.cand_factor)
                        ],
                        4.0+6.0*self.cand_factor,
                        GLOBALS.THEME_TOOL_SUGGESTION_REMOVE if self.cand_vert_idx==prev_vert_index else GLOBALS.THEME_TOOL_SUGGESTION_ADD,
                        cache_idname=self.__class__.__name__ + '_selection_shrink_grow',
                        cache_tag_redraw=self.tag_redraw
                    )

            self.tag_redraw = False
