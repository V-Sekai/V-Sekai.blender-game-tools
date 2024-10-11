import bpy
from bl_xr import root

from .edit_mesh_handle import EditMeshHandle


def on_extrude_drag(self, event_name, drag_amt):
    # https://pioneerwiki.com/wiki/Scripting_Blender
    bpy.ops.mesh.extrude_context_move(TRANSFORM_OT_translate={"value": drag_amt * self.direction})


gizmo = EditMeshHandle(id="extrude_gizmo", undo_event_name="extrude", mesh_modes_allowed={"EDGE", "FACE"})
gizmo.add_event_listener("handle_drag", on_extrude_drag)


def enable_gizmo():
    root.append_child(gizmo)


def disable_gizmo():
    root.remove_child(gizmo)
