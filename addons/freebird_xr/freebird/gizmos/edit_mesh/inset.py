import bpy
from bl_xr import root

from .edit_mesh_handle import EditMeshHandle


def on_inset_drag(self, event_name, drag_amt):
    bpy.ops.mesh.inset(thickness=abs(drag_amt))


gizmo = EditMeshHandle(id="inset_gizmo", undo_event_name="inset", mesh_modes_allowed={"FACE"})
gizmo.add_event_listener("handle_drag", on_inset_drag)


def enable_gizmo():
    root.append_child(gizmo)


def disable_gizmo():
    root.remove_child(gizmo)
