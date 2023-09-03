from uvflow.addon_utils import Register
from uvflow.addon_utils.types import EventType, EventValue, Mouse, ToolAction, ToolActionModal, Vector2i, OpsReturn, ModalTrigger
from uvflow.addon_utils.types.event import Mouse
from uvflow.addon_utils.utils.raycast import BVHTreeRaycastInfo
from uvflow.addon_utils.utils.cursor import Cursor
from uvflow.addon_utils.utils.math import distance_between, map_value, lineseg_dist
from uvflow.addon_utils.gpu import idraw
from uvflow.globals import GLOBALS, print_debug

from .tool_settings import UVFlowToolSettings
from uvflow.prefs import UVFLOW_Preferences
from uvflow.operators.op_pack import UVPack
from uvflow.operators.op_unwrap import UVUnwrap
from uvflow.tool.attributes import save_attributes
from uvflow.addon_utils.gpu.handler import DrawHandler

from bpy import ops as OPS
from bpy.types import Context, Event, Mesh

import bpy

from gpu.shader import from_builtin as gpu_shader_from_builtin
from gpu.types import GPUBatch, GPUShader
from gpu_extras.batch import batch_for_shader as gpu_batch
from gpu import state as gpu_state

import bmesh
from bmesh.types import BMesh, BMEdge, BMVert, BMFace, BMLoop
from bpy_extras import view3d_utils
from mathutils import Vector, Matrix, Quaternion

from time import time

import os


# Constants.
EDGE_SHADER: GPUShader = gpu_shader_from_builtin('POLYLINE_UNIFORM_COLOR')
FACE_SHADER: GPUShader = gpu_shader_from_builtin('UNIFORM_COLOR')
THEME_EDGE = bpy.context.preferences.themes[0].view_3d.edge_select
THEME_FACE = bpy.context.preferences.themes[0].view_3d.face_select
seam_color = bpy.context.preferences.themes[0].view_3d.edge_seam
select_color = bpy.context.preferences.themes[0].view_3d.edge_select
THEME_TOOL_SELECTION = (select_color[0], select_color[1], select_color[2], .92)
THEME_TOOL_SUGGESTION_ADD = (select_color[0], select_color[1], select_color[2], .92)
THEME_TOOL_SUGGESTION_REMOVE = (1, .2, .16, .92)



class ToolState:
    _instance = None

    ''' Utility HACK for the CLICK/DOUBLE_CLICK Blender BUG.
        But can be useful for other purposes
        UPDATE: Yes, it is useful for the gpu drawing and global bmesh and raycast states. '''
    last_mouse: Vector2i = Vector2i(0, 0)
    last_time: float = time()
    last_action: ToolAction = None
    raycast_info: BVHTreeRaycastInfo = None
    geo_context: str = 'NONE' # {'EDGE', 'FACE'}...
    geo_index: int = -1
    geo_coords: list[Vector] = []
    geo_batch: GPUBatch = None
    modal_geo_context: str = ''
    current_tool: ToolAction = None
    skip_drawing: bool = False
    test_modal_start_time: float = 0
    custom_edge_selection: list[int] = None
    active_edge: int = -1
    prev_edge_dst: int = -1 # edge index used for shortest path.
    xy: Vector = Vector((0, 0))

    last_view_location: tuple = (0, 0, 0)
    last_view_rotation: tuple = (0, 0, 0, 0)
    last_view_distance: float
    last_view_change_time: float = 0.0

    @classmethod
    def get(cls) -> 'ToolState':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def in_edge_context(self) -> bool:
        return self.geo_context == 'EDGE'

    @property
    def in_face_context(self) -> bool:
        return self.geo_context == 'FACE'

    def get_selected_faces(self, context) -> list[BMFace]:
        if bm := self.raycast_info.ensure(context):
            return [face for face in bm.faces if face.select]
        return []

    def set_selected_faces(self, context, face_indices: list[int], deselect_all: bool = False):
        if bm := self.raycast_info.ensure(context):
            faces = bm.faces
            if deselect_all:
                if isinstance(face_indices, (list, tuple)):
                    face_indices = set(face_indices)
                for face in faces:
                    if face.index in face_indices:
                        face.select = True
                    elif face.select:
                        face.select = False
            else:
                for face_idx in face_indices:
                    faces[face_idx].select = True
        return []

    def action_repeat(self, other_action: ToolAction) -> bool:
        return other_action == self.last_action

    def time_exceed(self, time_span: float) -> bool:
        return (time() - self.last_time) >= time_span

    def mouse_distance_less(self, mouse: Mouse, distance: int) -> bool:
        return self.last_mouse.distance(mouse.current) <= distance

    def mouse_distance_greater(self, mouse: Mouse, distance: int) -> bool:
        return self.last_mouse.distance(mouse.current) >= distance

    def update_raycast(self, context: Context, coord) -> None:
        if self.raycast_info is None:
            self.raycast_info = BVHTreeRaycastInfo(context)
        self.raycast_info.update(context, coord)
        if not self.raycast_info.hit:
            self.geo_context = 'NONE'
            self.geo_coords.clear()
        elif result := self.raycast_info.get_closer_geo_primitive(context, {self.modal_geo_context} if self.modal_geo_context else {'EDGE', 'FACE'}):
            prim, hit_location = result
            reg_off = Vector((context.area.x, context.area.y))
            mat = context.object.matrix_world
            if isinstance(prim, BMEdge):
                self.geo_context = 'EDGE'
                if self.geo_index != prim.index:
                    # HACK. 3D NOT SUPPORTED FOR DRAW CURSOR METHOD :-(
                    self.geo_coords = [view3d_utils.location_3d_to_region_2d(context.region, context.region_data, mat@v.co) + reg_off for v in prim.verts]
                    self.geo_index = prim.index
                    self.geo_batch = gpu_batch(EDGE_SHADER, 'LINES', {"pos": self.geo_coords})
            elif isinstance(prim, BMFace):
                self.geo_context = 'FACE'
                if self.geo_index != prim.index:
                    # HACK. 3D NOT SUPPORTED FOR DRAW CURSOR METHOD :-(
                    self.geo_coords = [view3d_utils.location_3d_to_region_2d(context.region, context.region_data, mat@v.co) + reg_off for v in prim.verts]
                    self.geo_index = prim.index
                    # indices = geometry.convex_hull_2d(self.geo_coords)
                    # n = len(prim.verts)
                    # if n == 3:
                    #     indices = [indices]
                    # elif n == 4:
                    #     indices = [indices[0:3], [indices[3], indices[0], indices[1]]]
                    loops: list[BMLoop] = prim.loops
                    indices = []
                    geo_indices_rel = [v.index for v in prim.verts]
                    for loop in loops:
                        indices.append([
                            geo_indices_rel.index(loop.link_loop_prev.vert.index),
                            geo_indices_rel.index(loop.vert.index),
                            geo_indices_rel.index(loop.link_loop_next.vert.index)
                        ])
                    self.geo_batch = gpu_batch(FACE_SHADER, 'TRIS', {"pos": self.geo_coords}, indices=indices)
            else:
                self.geo_context = 'NONE'
        else:
            self.geo_context = 'NONE'

    def update(self, tool_action: ToolAction):
        self.last_action = tool_action
        if hasattr(tool_action, 'mouse'):
            self.last_mouse = tool_action.mouse.current.copy()
        self.last_time = time()

    def enter_tool(self, action: ToolAction) -> None:
        self.modal_geo_context = action.geo_context
        self.current_tool = action.__class__

    def exit_tool(self) -> None:
        self.modal_geo_context = ''
        self.current_tool = None

    def update_active_edge(self, context) -> None:
        bm = tool_state.raycast_info.ensure(context)
        if bm and bm.select_history:
            edge: BMEdge = bm.select_history[-1]
            tool_state.active_edge = edge.index
            print("Active Edge ->", edge.index)
        else:
            print("WARN! Active Edge not found!")
            tool_state.active_edge = -1

    def select_active_edge(self, context, deselect_all: bool = False) -> None:
        if deselect_all:
            OPS.mesh.select_all(False, action='DESELECT')
        if self.active_edge != -1:
            if bm := self.raycast_info.ensure(context):
                edge: BMEdge = bm.edges[self.active_edge]
                edge.select_set(True)
                bm.select_history.add(edge)
            else:
                print("on_action_finish() -> WARN! Invalid BMesh!")
        else:
            print("on_action_finish() -> WARN! Active Edge not found!")

    def set_test_modal(self, state: bool = True) -> None:
        if state:
            # SKIP DRAWING.
            self.geo_context = 'NONE'
            # self.test_modal_start_time = time()
        self.skip_drawing = state

    def draw_batch(self, context: Context):
        # if not context.active_operator
        if self.skip_drawing:
            return
        if self.geo_batch and self.raycast_info.hit:
            # gpu_state.depth_test_set('LESS_EQUAL')
            # gpu_state.depth_mask_set(True)
            if self.in_edge_context:
                EDGE_SHADER.bind()
                EDGE_SHADER.uniform_float('lineWidth', 1.8)
                EDGE_SHADER.uniform_float('viewportSize', (context.region.width, context.region.height))
                EDGE_SHADER.uniform_float('color', (THEME_EDGE[0], THEME_EDGE[1], THEME_EDGE[2], .9))
                self.geo_batch.draw(EDGE_SHADER)

            elif self.in_face_context:
                FACE_SHADER.bind()
                FACE_SHADER.uniform_float('color', (THEME_FACE[0], THEME_FACE[1], THEME_FACE[2], .25))
                self.geo_batch.draw(FACE_SHADER)
            # gpu_state.depth_mask_set(False)

# Our ToolState Instance.
tool_state = ToolState.get()



########################################################
########################################################
# UV-FLOW TOOL.
########################################################

def prepare_tool(tool: ToolAction, deselect_all: bool = True, do_select: bool = True, select_extend: bool = False):
    if deselect_all: OPS.mesh.select_all(False, action='DESELECT')
    OPS.mesh.select_mode(False, type=tool.geo_context)
    if tool.geo_context == 'FACE':
        OPS.mesh.select_mode(False, type=tool.geo_context, use_expand=True, use_extend=True, action='ENABLE')
    if do_select: OPS.view3d.select('INVOKE_DEFAULT', False, deselect_all=True, extend=select_extend)


def on_action_finish(tool_action: ToolAction, context: Context, event: Event):
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
        bm.select_history.clear()
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

    if prefs.use_auto_pack:
        UVPack.run()

    # Ensure last edge is active and selected (only one).
    # if not tool_action._is_modal:
    OPS.mesh.select_all(False, action='DESELECT')
    bm = tool_state.raycast_info.ensure(context)
    bm.select_mode = {'EDGE'}
    edge = bm.edges[tool_state.active_edge]
    bm.select_history.add(edge)
    edge.select_set(True)

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
        tool_state.draw_batch(context)


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
            prepare_tool(self, deselect_all=(not event.shift), select_extend=event.shift)

            if tool_state.action_repeat(self) and not tool_state.time_exceed(0.33) and tool_state.mouse_distance_less(self.mouse, 3):
                UVFlowTool.FaceDoubleClick.get().action(context, event)
                return

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

        def action(self, context: Context, event: Event) -> None:
            print("FACE DOUBLE CLICK!")
            tool_state.enter_tool(self)
            prepare_tool(self, deselect_all=(not event.shift), select_extend=event.shift)
            # context.scene.tool_settings.use_uv_select_sync = True
            # OPS.uv.select_linked()
            sel_faces = [face.index for face in tool_state.get_selected_faces(context)]
            OPS.mesh.select_linked(delimit={'SEAM'})
            tool_state.set_selected_faces(context, sel_faces, deselect_all=False)

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

            if event.type == EventType.LEFTMOUSE and event.value == EventValue.RELEASE:
                # UVFlowTool.EdgeDoubleClick.get().action(context, event)
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
                THEME_TOOL_SELECTION,
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
                u_color=THEME_TOOL_SUGGESTION_ADD,
                cache_idname=self.__class__.__name__ + '_selection_suggestion_add',
                cache_tag_redraw=self.tag_redraw
            )
            if len(self.vert_path) > 2:
                idraw.point_3d(
                    coords=[mw @ verts[prev_vert_index].co],
                    point_size=12.0,
                    u_color=THEME_TOOL_SUGGESTION_REMOVE,
                    cache_idname=self.__class__.__name__ + '_selection_suggestion_remove',
                    cache_tag_redraw=self.tag_redraw
                )

            if self.cand_vert_idx != -1:
                curr_vert = verts[self.vert_path[-1]]
                cand_vert = verts[self.cand_vert_idx]

                if edge := self.find_edge_by_verts(curr_vert, cand_vert):
                    curr_vert_co_t = mw @ curr_vert.co
                    cand_vert_co_t = mw @ cand_vert.co

                    ab = cand_vert_co_t - curr_vert_co_t

                    edge_length = ab.length
                    direction = ab.normalized()

                    idraw.line_3d(
                        [
                            curr_vert_co_t,
                            curr_vert_co_t + direction * (edge_length * self.cand_factor)
                        ],
                        4.0+6.0*self.cand_factor,
                        THEME_TOOL_SUGGESTION_REMOVE if self.cand_vert_idx==prev_vert_index else THEME_TOOL_SUGGESTION_ADD,
                        cache_idname=self.__class__.__name__ + '_selection_shrink_grow',
                        cache_tag_redraw=self.tag_redraw
                    )

            self.tag_redraw = False
