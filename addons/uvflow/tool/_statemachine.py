from uvflow.addon_utils import Register
from uvflow.addon_utils.types import StateMachineModalOperator, Mouse, ModalTrigger, OpsReturn, EventType, EventValue, EventStateMachineAction, EventStateMachineNode
from uvflow.addon_utils.utils.math import direction, angle_between, distance_between
from uvflow.addon_utils.utils.raycast import BVHTreeRaycastInfo

from uvflow.operators.op_checker import ToggleUvCheckerMaterial
from uvflow.operators.op_geo_overlay import UpdateGeoOverlays

import bpy
from bpy.types import Event, Context, UILayout, Object, Mesh
from bl_ui.space_view3d import VIEW3D_HT_header
import bmesh
from bmesh.types import BMesh, BMEdge, BMVert, BMFace
from bpy_extras import view3d_utils
import mathutils
from mathutils.bvhtree import BVHTree

from dataclasses import dataclass


class ToolPoll:
    @staticmethod
    def vert(context: Context, event: Event, op: 'UVFlowTool') -> bool:
        if not context.tool_settings.mesh_select_mode[0]:
            return False
        bm = op.raycast_info.bm
        # bm.select_mode = {'VERT'}
        # bm.select_flush_mode()
        if active_vert := bm.select_history.active:
            if isinstance(active_vert, BMEdge):
                return op.raycast_info.bm.verts[active_vert.index].select
        return False

    @staticmethod
    def edge(context: Context, event: Event, op: 'UVFlowTool') -> bool:
        if not context.tool_settings.mesh_select_mode[1]:
            return False
        bm = op.raycast_info.bm
        # bm.select_mode = {'EDGE'}
        # bm.select_flush_mode()
        if active_edge := bm.select_history.active:
            # print(active_edge)
            if isinstance(active_edge, BMEdge):
                return op.raycast_info.bm.edges[active_edge.index].select
        return False

    @staticmethod
    def face(context: Context, event: Event, op: 'UVFlowTool') -> bool:
        if not context.tool_settings.mesh_select_mode[2]:
            return False
        if active_face := op.raycast_info.bm.faces.active:
            return op.raycast_info.bm.faces[active_face.index].select
        return False


class EdgeClick:
    @staticmethod
    def start(context: Context, event: Event, op: 'UVFlowTool') -> None:
        op.mouse_start = op.mouse.current.copy() # For double-click control.

    @staticmethod
    def update(context: Context, event: Event, op: 'UVFlowTool') -> bool:
        return 1

    @staticmethod
    def done(context: Context, event: Event, op: 'UVFlowTool') -> None:
        bpy.ops.mesh.mark_seam(clear=event.alt)

    @staticmethod
    def cancel(context: Context, event: Event, op: 'UVFlowTool') -> None:
        pass


def EdgeDoubleClick(context: Context, event: Event, op: 'UVFlowTool'):
    bpy.ops.view3d.select('INVOKE_DEFAULT', True, extend=False)
    bpy.ops.mesh.loop_multi_select(ring=False)
    bpy.ops.mesh.mark_seam(clear=event.alt)


class EdgeCtrlClick:
    @staticmethod
    def start(context: Context, event: Event, op: 'UVFlowTool') -> None:
        ''' First Click. '''
        # if not op.first_shortest_path:
        #     bpy.ops.mesh.mark_seam(clear=False)
        # To avoids issues with faces on repeating actions.
        bpy.ops.mesh.select_mode(type='EDGE')

        bpy.ops.view3d.select('INVOKE_DEFAULT', True, extend=False)
        op.did_shortest_path = False

    @staticmethod
    def update(context: Context, event: Event, op: 'UVFlowTool') -> bool:
        ''' Maybe Moving Mouse or whatever. '''
        if event.type == EventType.LEFTMOUSE:
            bpy.ops.mesh.mark_seam(clear=event.alt)
            # bpy.ops.ed.undo_push(message="UndoPush to prevent 'shortest_path_pick' undo")
            EdgeCtrlClick.start(context, event, op)
            return 1
        if event.type in {EventType.MOUSEMOVE, EventType.INBETWEEN_MOUSEMOVE}:
            if op.did_shortest_path:
                bpy.ops.ed.undo()
            bpy.ops.mesh.shortest_path_pick('INVOKE_DEFAULT', True)
            op.did_shortest_path = True
        return 1

    @staticmethod
    def done(context: Context, event: Event, op: 'UVFlowTool') -> None:
        bpy.ops.mesh.mark_seam(clear=event.alt)

        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.mesh.select_mode(type='EDGE', action='ENABLE', use_expand=True, use_extend=True)

    @staticmethod
    def cancel(context: Context, event: Event, op: 'UVFlowTool') -> None:
        # TODO: Deselect.
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.mesh.select_mode(type='EDGE', action='ENABLE', use_expand=True, use_extend=True)


class EdgeClickDrag_Raycast:
    @staticmethod
    def start(context: Context, event: Event, op: 'UVFlowTool') -> int:
        # TODO: Raycast to do the first selection. (requires pre-highlight)
        op.vert_path: list[BMVert] = []
        # bpy.ops.mesh.select_mode(False, type='EDGE')

        raycast_info: BVHTreeRaycastInfo = op.raycast_info
        if vert := raycast_info.get_closest_vert(context):
            # vert.select_set(True)
            op.vert_path.append(vert.index)

            # TODO: Decide if add or remove seam...
            if edge := raycast_info.get_closest_edge(context):
                op.vert_path.append(edge.other_vert(vert).index)
                op.distance_threshold = edge.calc_length()

    @staticmethod
    def update(context: Context, event: Event, op: 'UVFlowTool') -> int:
        if not event.type in {EventType.MOUSEMOVE, EventType.INBETWEEN_MOUSEMOVE}:
            return 1

        raycast_info: BVHTreeRaycastInfo = op.raycast_info
        vert = raycast_info.get_closest_vert(context)
        if not vert:
            return 1

        first_time = len(op.vert_path) == 2
        if first_time:
            prev_vert = set(op.vert_path)
            if vert.select or vert.index in prev_vert:
                return 1
        else:
            if vert.select and vert.index != op.vert_path[0]: # and vert.index != op.vert_path[0]: # and not first_step:
                return 1

            prev_vert = {raycast_info.bm.verts[op.vert_path[-1]].index}

        # Check if both vertices are linked.
        no_candidate = True
        for edge in vert.link_edges:
            if edge.other_vert(vert).index in prev_vert:
                no_candidate = False
                if first_time and edge.other_vert(vert).index == op.vert_path[0]:
                    # Reorder 2 first vertex indices. Switch vertices!
                    op.vert_path[0], op.vert_path[1] = op.vert_path[1], op.vert_path[0]
                edge.select_set(True)
                raycast_info.bm.select_history.add(edge)
                # vert.select_set(True)
                raycast_info.bm.edges.ensure_lookup_table()
                op.vert_path.append(vert.index)
                # Update selection visibility.
                bmesh.update_edit_mesh(context.object.data, loop_triangles=False, destructive=False)
                break

        if no_candidate and not first_time:
            # Mouse is too far away from draw line head.
            # let's pull it and propagate to the projected mouse location.
            # m_loc = raycast_info.location
            distance_threshold = op.distance_threshold*2
            end_vert: BMVert = vert
            vert: BMVert = raycast_info.bm.verts[op.vert_path[-1]]
            new_edges_count = 0
            max_distance = 100000000
            p2 = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, end_vert.co)
            while 1:
                # PROPAGATE SELECT NEAREST VERTEX CONNECTED TO THE ACTIVE VERTEX.
                nearest_vert = None
                next_edge = None
                for edge in vert.link_edges:
                    o_vert: BMVert = edge.other_vert(vert)
                    p1 = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, o_vert.co)
                    d = distance_between(p1, p2)
                    if d < max_distance:
                        max_distance = d
                        nearest_vert = o_vert
                        next_edge = edge
                if max_distance < distance_threshold:
                    break
                if nearest_vert is None:
                    break
                vert = nearest_vert
                next_edge.select_set(True)
                raycast_info.bm.select_history.add(edge)
                op.vert_path.append(vert.index)
                new_edges_count+=1

            if new_edges_count > 0:
                raycast_info.bm.edges.ensure_lookup_table()
                bmesh.update_edit_mesh(context.object.data, loop_triangles=False, destructive=False)
        return 1

    @staticmethod
    def done(context: Context, event: Event, op: 'UVFlowTool') -> None:
        bpy.ops.mesh.mark_seam('INVOKE_DEFAULT', True, clear=event.alt)
        bpy.ops.mesh.select_all(action='DESELECT')
        op.vert_path.clear()

    @staticmethod
    def cancel(context: Context, event: Event, op: 'UVFlowTool') -> None:
        bpy.ops.mesh.select_all(action='DESELECT')
        op.vert_path.clear()


class FaceClick:
    @staticmethod
    def start(context: Context, event: Event, op: 'UVFlowTool') -> None:
        op.mouse_start = op.mouse.current.copy() # For double-click control.

    @staticmethod
    def update(context: Context, event: Event, op: 'UVFlowTool') -> int:
        return 1

    @staticmethod
    def done(context: Context, event: Event, op: 'UVFlowTool') -> None:
        pass

    @staticmethod
    def cancel(context: Context, event: Event, op: 'UVFlowTool') -> None:
        pass


def FaceDoubleClick(context: Context, event: Event, op: 'UVFlowTool') -> None:
    if face := op.raycast_info.get_face(context):
        context.scene.tool_settings.use_uv_select_sync = True
        bpy.ops.uv.select_linked()
        op.keep_selection = True


class Main:
    def tool_enter(context: Context, op: 'UVFlowTool') -> None:
        # Initialization stuff.
        print("TOOL INIT")
        op.keep_selection = False
        op.first_shortest_path = True
        op.raycast_info.bm.select_mode = {'FACE', 'EDGE'}
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.mesh.select_mode(type='EDGE', action='ENABLE', use_expand=True, use_extend=True)

        op.backup__shading_color_type = context.space_data.shading.color_type
        context.space_data.shading.color_type = 'TEXTURE'
        ToggleUvCheckerMaterial.run(enable=True, auto=True)
        UpdateGeoOverlays.run(enable=True)

    def idle_update(context: Context, event: Event, op: 'UVFlowTool') -> int:
        # Here we can filter which events to catch (1) or pass (2). Default is pass (2) is None value is returned.
        if event.type in {EventType.MOUSEMOVE, EventType.INBETWEEN_MOUSEMOVE}:
            if event.type_prev in {EventType.LEFTMOUSE}:
                # CLICK_DRAG.
                return 2
            return 1
        if event.type in {EventType.WHEELDOWNMOUSE, EventType.WHEELUPMOUSE}:
            return 2
        if event.type in {'LEFTMOUSE', 'MIDDLEMOUSE'}:
            # We want Blender to handle leftmouse press and release so that StateMachine can handle potential 'CLICK', 'DOUBLE_CLICK' and 'CLICK_DRAG' events.
            if event.value in {'PRESS', 'RELEASE'}:
                return 2
            # NOTE: Blender seems to have issues catching double click event by passing the pres, release and click events.
            #if event.value in {'CLICK'} and ToolPoll.face(context, op):
            #    return 2
        return 1

    def tool_exit(context: Context, op: 'UVFlowTool') -> None:
        print("TOOL EXIT")
        context.space_data.shading.color_type = op.backup__shading_color_type
        ToggleUvCheckerMaterial.run(enable=False, auto=True)
        UpdateGeoOverlays.run(enable=False)



@Register.OPS.MODAL.STATE_MACHINE
class UVFlowTool(StateMachineModalOperator):
    use_raycast_info: bool = True
    raycast_type: str = 'BVHTREE'

    raycast_info: BVHTreeRaycastInfo
    vert_path: list[BMVert]
    keep_selection: bool = False
    mouse_start: tuple[int, int]
    backup__shading_color_type: str
    did_shortest_path: bool
    first_shortest_path: bool

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.object and context.mode == 'EDIT_MESH'

    def modal_update(self, context: Context, event: Event, mouse: Mouse) -> OpsReturn or None:
        if event.type in {EventType.LEFTMOUSE} and event.value in {EventValue.PRESS}:
            self.keep_selection = False
        return super().modal_update(context, event, mouse)

    def modal__mousemove(self, context: Context, mouse: Mouse) -> None:
        if self.tool_event_state_machine.active_node.idname == 'IDLE':
            if not getattr(self, 'keep_selection', False):
                # Highlight! TODO: Change to gpu drawing to remove this keep_selection HACK.
                bpy.ops.view3d.select('INVOKE_DEFAULT', False, extend=False)


    ''' Actions. '''
    UNWRAP: EventStateMachineAction.annot(
        EventType.U, EventValue.PRESS,
        callback=lambda *args: bpy.ops.mesh.select_all(action='SELECT') and bpy.ops.uv.unwrap('INVOKE_DEFAULT') and bpy.ops.mesh.select_all(action='DESELECT'),
        state='IDLE'
    )
    ### SELECTION_MODE__VERT: EventStateMachineAction.annot(EventType.NUM_ONE,   EventValue.PRESS, callback=lambda op, ctx: bpy.ops.mesh.select_mode(type='VERT'))
    ### SELECTION_MODE__EDGE: EventStateMachineAction.annot(EventType.NUM_TWO,   EventValue.PRESS, callback=lambda op, ctx: bpy.ops.mesh.select_mode(type='EDGE'))
    ### SELECTION_MODE__FACE: EventStateMachineAction.annot(EventType.NUM_THREE, EventValue.PRESS, callback=lambda op, ctx: bpy.ops.mesh.select_mode(type='FACE'))

    ### FACE_DOUBLE_CLICK: EventStateMachineAction.annot(
    ###     EventType.LEFTMOUSE, EventValue.DOUBLE_CLICK,
    ###     callback=FaceDoubleClick,
    ###     state='IDLE',
    ###     poll=ToolPoll.face
    ### )
    ### EDGE_DOUBLE_CLICK: EventStateMachineAction.annot(
    ###     EventType.LEFTMOUSE, EventValue.DOUBLE_CLICK,
    ###     callback=EdgeDoubleClick,
    ###     state='IDLE',
    ###     poll=ToolPoll.edge
    ### )

    ''' Nodes / States. '''
    EDGE_CLICK: EventStateMachineNode.annot(EdgeClick.update)\
        .transition_event('IDLE',
                          {EventType.MOUSEMOVE, EventType.INBETWEEN_MOUSEMOVE}, EventValue.NOTHING,
                          callback=EdgeClick.done,
                          extra_poll=lambda ctx, evt, op: op.mouse_start.distance(op.mouse.current) > 4)\
        .transition_event('IDLE',
                          EventType.LEFTMOUSE, EventValue.RELEASE,
                          callback=EdgeDoubleClick)\
        .detransition_event({EventType.RIGHTMOUSE, EventType.ESC}, EventValue.PRESS,
                            callback=EdgeClick.cancel)\
        .transition_event('EDGE_CTRL_CLICK',
                          EventType.LEFT_CTRL, EventValue.PRESS,
                          callback=EdgeCtrlClick.start,
                          extra_poll=ToolPoll.edge)

    EDGE_CTRL_CLICK: EventStateMachineNode.annot(EdgeCtrlClick.update)\
        .transition_event('IDLE',
                          EventType.LEFT_CTRL, EventValue.RELEASE,
                          callback=EdgeCtrlClick.done)\
        .transition_event('EDGE_CTRL_CLICK',
                          EventType.LEFTMOUSE, EventValue.RELEASE,
                          callback=EdgeCtrlClick.start)\
        .detransition_event({EventType.RIGHTMOUSE, EventType.ESC}, EventValue.PRESS,
                            callback=EdgeCtrlClick.cancel)

    EDGE_CLICK_DRAG__RAYCAST: EventStateMachineNode.annot(EdgeClickDrag_Raycast.update)\
        .transition_event('IDLE',
                          EventType.LEFTMOUSE, EventValue.RELEASE,
                          callback=EdgeClickDrag_Raycast.done)\
        .detransition_event({EventType.RIGHTMOUSE, EventType.ESC}, EventValue.PRESS,
                            callback=EdgeClickDrag_Raycast.cancel)

    FACE_CLICK: EventStateMachineNode.annot(FaceClick.update)\
        .transition_event('IDLE',
                          {EventType.MOUSEMOVE, EventType.INBETWEEN_MOUSEMOVE}, {EventValue.NOTHING},
                          callback=FaceClick.done,
                          extra_poll=lambda ctx, evt, op: op.mouse_start.distance(op.mouse.current) > 4)\
        .transition_event('IDLE',
                          EventType.LEFTMOUSE, EventValue.RELEASE,
                          callback=FaceDoubleClick)\
        .detransition_event({EventType.RIGHTMOUSE, EventType.ESC}, EventValue.PRESS,
                            callback=FaceClick.cancel)

    IDLE: EventStateMachineNode.annot(Main.idle_update).mark_as_head(callback=Main.tool_enter)\
        .transition_event('EXIT', EventType.ESC, EventValue.PRESS)\
        .transition_event('EDGE_CTRL_CLICK', # This one should be first as shares the same events as 'EDGE_CLICK'.
                          EventType.LEFTMOUSE, EventValue.PRESS,
                          modifier='CTRL',
                          callback=EdgeCtrlClick.start,
                          extra_poll=ToolPoll.edge)\
        .transition_event('EDGE_CLICK',
                          EventType.LEFTMOUSE, EventValue.CLICK,
                          callback=EdgeClick.start,
                          extra_poll=ToolPoll.edge)\
        .transition_event('EDGE_CLICK_DRAG__RAYCAST',
                          EventType.LEFTMOUSE, EventValue.CLICK_DRAG,
                          callback=EdgeClickDrag_Raycast.start,
                          extra_poll=ToolPoll.edge)\
        .transition_event('FACE_CLICK',
                          EventType.LEFTMOUSE, EventValue.CLICK,
                          callback=FaceClick.start,
                          extra_poll=ToolPoll.face)

    EXIT: EventStateMachineNode.annot().mark_as_tail(callback=Main.tool_exit)



####################################################
# APPEND IN THE BLENDER VIEW3D HEADER.

#@Register.UI.APPEND(VIEW3D_HT_header)
#def draw_ui(_context: Context, layout: UILayout) -> None:
#    UVFlowTool.draw_in_layout(layout, label="UVFlow Tool")
