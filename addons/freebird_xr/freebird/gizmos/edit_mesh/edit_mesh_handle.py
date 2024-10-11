import bpy
import time

from bl_xr import xr_session
from bl_xr.consts import VEC_UP
from bl_xr.utils import get_mesh_mode, get_bmesh, quaternion_from_vector

from mathutils import Vector

from ..common.pull_push_handle import PullPushHandle
from ... import tools
from ...utils import make_bmesh_copy, revert_to_bmesh_copy, free_bmesh_copy, log


class EditMeshHandle(PullPushHandle):
    "A handle with a knob that's active only when editing a mesh with elements that have been selected"

    def __init__(self, undo_event_name=None, mesh_modes_allowed={"VERT", "EDGE", "FACE"}, **kwargs):
        super().__init__(**kwargs)

        self.mesh_modes_allowed = mesh_modes_allowed
        self._last_update_time = 0
        self._do_not_update_every_frame = True
        self._undo_event_name = undo_event_name

        # check if the mesh mode is correct
        self.add_event_listener("handle_drag_start", self.check_if_mesh_mode_is_valid)
        self.add_event_listener("handle_drag", self.check_if_mesh_mode_is_valid)

        # keep a copy of the BMesh to work on
        self.add_event_listener("handle_drag_start", lambda *x: make_bmesh_copy())
        self.add_event_listener("handle_drag", lambda *x: revert_to_bmesh_copy())
        self.add_event_listener("handle_drag_end", lambda *x: free_bmesh_copy())
        self.add_event_listener("handle_drag_end", self.register_undo_event)

    def check_if_mesh_mode_is_valid(self, event_name, event):
        if get_mesh_mode() not in self.mesh_modes_allowed:
            event.stop_propagation_immediate = True

    def update(self):
        if self._is_dragging:
            return

        ob = bpy.context.view_layer.objects.active
        if ob is None or ob.mode != "EDIT" or ob.type != "MESH" or tools.active_tool != "select":
            self.contents.style["visible"] = False
            return

        if self._do_not_update_every_frame and time.time() < self._last_update_time + 0.1:
            return

        self._last_update_time = time.time()

        origin, self.direction = EditMeshHandle.get_selected_center(get_bmesh(ob))
        if origin is None:
            self.contents.style["visible"] = False
            return

        self.contents.style["visible"] = True

        self.position_world = origin
        self.rotation_world = quaternion_from_vector(self.direction)

        d = self.knob.position_world - xr_session.controller_main_aim_position
        should_highlight = d.length <= self.knob.radius * xr_session.viewer_scale
        if should_highlight:
            if not self._is_highlighted:
                self.highlight(True)
        elif self._is_highlighted:
            self.highlight(False)

    def get_selected_center(bm):
        vert_mode, edge_mode, face_mode = bpy.context.scene.tool_settings.mesh_select_mode

        avg_local_location = Vector()
        avg_local_normal = Vector()

        if vert_mode:
            selected_verts = [v for v in bm.verts if v.select]
        elif edge_mode:
            selected_verts = {v for e in bm.edges if e.select for v in e.verts}
        elif face_mode:
            selected_faces = [f for f in bm.faces if f.select]
            face_normals = [f.normal for f in selected_faces]
            selected_verts = {v for f in selected_faces for v in f.verts}

            for v in selected_verts:
                avg_local_location += v.co

            for n in face_normals:
                avg_local_normal += n

        if len(selected_verts) == 0:
            return None, None

        if vert_mode or edge_mode:
            for v in selected_verts:
                avg_local_location += v.co
                avg_local_normal += v.normal

        avg_local_location /= len(selected_verts)
        avg_local_normal /= len(selected_verts)

        m = bpy.context.view_layer.objects.active.matrix_world
        m_inv = m.inverted()
        m_norm = m_inv.transposed().to_3x3()  # https://blender.stackexchange.com/a/61250

        avg_world_location = m @ avg_local_location
        avg_world_normal = m_norm @ avg_local_normal

        if avg_world_normal.length < 0.001:
            avg_world_normal = Vector(VEC_UP)
        else:
            avg_world_normal.normalize()

        return avg_world_location, avg_world_normal

    def register_undo_event(self, event_name, event):
        if self._undo_event_name:
            bpy.ops.ed.undo_push(message=self._undo_event_name)
