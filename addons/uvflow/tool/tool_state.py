from time import time

from bpy import ops as OPS
from bpy.types import Context, Mesh

import gpu
from gpu.types import GPUBatch
from gpu_extras.batch import batch_for_shader as gpu_batch
from gpu import state as gpu_state

import bmesh
from bmesh.types import BMesh, BMEdge, BMVert, BMFace, BMLoop
from bpy_extras import view3d_utils
from mathutils import Vector, Matrix, Quaternion

from uvflow.addon_utils.types import Mouse, ToolAction, Vector2i
from uvflow.addon_utils.types.event import Mouse
from uvflow.utils.raycast import BVHTreeRaycastInfo
from uvflow.globals import GLOBALS




class ToolState:
    _instance = None

    ''' Utility HACK for the CLICK/DOUBLE_CLICK Blender BUG.
        But can be useful for other purposes
        UPDATE: Yes, it is useful for the gpu drawing and global bmesh and raycast states. '''
    enabled: bool = True
    
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

    draw_type: str = '3D' # {'2D', '3D'}

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
        if not self.enabled:
            return

        def update_edge_geo_coords(prim: BMEdge | BMFace) -> None:
            mat = context.object.matrix_world
            reg_off = Vector((context.area.x, context.area.y))
            self.geo_coords.clear()
            if self.draw_type == '2D':
                for v in prim.verts:
                    if proj_coord := view3d_utils.location_3d_to_region_2d(context.region, context.region_data, mat @ v.co):
                        self.geo_coords.append(proj_coord + reg_off)
            elif self.draw_type == '3D':
                self.geo_coords = [mat @ v.co for v in prim.verts]

            context.region.tag_redraw()

        if self.raycast_info is None:
            self.raycast_info = BVHTreeRaycastInfo(context)
        self.raycast_info.update(context, coord)
        if not self.raycast_info.hit:
            self.geo_context = 'NONE'
            self.geo_coords.clear()
        elif result := self.raycast_info.get_closer_geo_primitive(context, {self.modal_geo_context} if self.modal_geo_context else {'EDGE', 'FACE'}):
            prim, hit_location = result
            if isinstance(prim, BMEdge):
                self.geo_context = 'EDGE'
                if self.geo_index != prim.index:
                    # HACK. 3D NOT SUPPORTED FOR DRAW CURSOR METHOD :-(
                    update_edge_geo_coords(prim)
                    self.geo_index = prim.index
                    self.geo_batch = gpu_batch(GLOBALS.SHADER_EDGE, 'LINES', {"pos": self.geo_coords})
            elif isinstance(prim, BMFace):
                self.geo_context = 'FACE'
                if self.geo_index != prim.index:
                    # HACK. 3D NOT SUPPORTED FOR DRAW CURSOR METHOD :-(
                    update_edge_geo_coords(prim)
                    self.geo_index = prim.index
                    indices = []
                    bm = self.raycast_info.bm
                    tris: BMLoop = bm.calc_loop_triangles()
                    loops: list[BMLoop] = prim.loops
                    loop_indices = set(loop.index for loop in loops)

                    geo_indices_rel = [v.index for v in prim.verts]
                    for i, tri in enumerate(tris):
                        if len(set(loop.index for loop in tri).intersection(loop_indices)) == 0:
                            continue
                        vert_indices = [geo_indices_rel.index(loop.vert.index) for loop in tri]
                        indices.append(vert_indices)

                    self.geo_batch = gpu_batch(GLOBALS.SHADER_FACE, 'TRIS', {"pos": self.geo_coords}, indices=indices)
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
        bm = self.raycast_info.ensure(context)
        if bm and bm.select_history:
            edge: BMEdge = bm.select_history[-1]
            self.active_edge = edge.index
            print("Active Edge ->", edge.index)
        else:
            print("WARN! Active Edge not found!")
            self.active_edge = -1

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
        self.skip_drawing = state

    def draw_batch(self, context: Context):
        if not self.enabled or self.skip_drawing:
            return

        if self.geo_batch and self.raycast_info.hit:
            if self.in_edge_context:
                shader = GLOBALS.SHADER_EDGE
                shader.uniform_float('color', GLOBALS.THEME_EDGE)
                x, y, w, h = gpu.state.active_framebuffer_get().viewport_get()
                shader.uniform_float('lineWidth', 2.0 * context.preferences.system.ui_line_width)
                shader.uniform_float('viewportSize', (w, h))

            elif self.in_face_context:
                shader = GLOBALS.SHADER_FACE
                shader.uniform_float('color', GLOBALS.THEME_FACE)
            
            else:
                return

            gpu_state.blend_set('ALPHA')
            self.geo_batch.draw(shader)
            gpu_state.blend_set('NONE')
