import bpy
from bl_xr import root

from .edit_mesh_handle import EditMeshHandle


def on_bevel_drag(self, event_name, drag_amt):
    if drag_amt < 0:  # rounded bevel
        bevel_segments = 5
        show_smooth = True
        drag_amt *= -1
    else:
        bevel_segments = 1
        show_smooth = False

    vert_mode, _, _ = bpy.context.scene.tool_settings.mesh_select_mode
    bevel_affect = "VERTICES" if vert_mode else "EDGES"

    bpy.ops.mesh.bevel(offset=drag_amt, segments=bevel_segments, affect=bevel_affect, harden_normals=show_smooth)


gizmo = EditMeshHandle(id="bevel_gizmo", undo_event_name="bevel", mesh_modes_allowed={"VERT", "EDGE", "FACE"})
gizmo.add_event_listener("handle_drag", on_bevel_drag)


def enable_gizmo():
    root.append_child(gizmo)


def disable_gizmo():
    root.remove_child(gizmo)
