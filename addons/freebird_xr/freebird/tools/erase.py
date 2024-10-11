import bpy
import bmesh
from bpy.types import Object

from bl_xr import root
from bl_xr.utils import get_mesh_mode, get_bmesh, reindex_bmesh

from ..utils import enable_bounds_check, disable_bounds_check, log

is_erasing = False
has_erased_elements = False


def on_erase_object(self, event_name, event):
    global has_erased_elements

    event.stop_propagation = True

    bpy.data.objects.remove(self)
    has_erased_elements = True


def on_erase_edit_mesh(self, event_name, event):
    global has_erased_elements

    event.stop_propagation = True

    el_type = get_mesh_mode() + "S"
    geom = list(event.sub_targets)

    bm = get_bmesh()
    bmesh.ops.delete(bm, geom=geom, context=el_type)
    bmesh.update_edit_mesh(self.data)

    has_erased_elements = True

    reindex_bmesh()


def on_erase_edit_curve(self, event_name, event):
    global has_erased_elements

    event.stop_propagation = True

    curve = self.data
    spline = curve.splines[0]
    for v in spline.points:
        v.select = v in event.sub_targets

    bpy.ops.curve.delete(type="VERT")

    has_erased_elements = True


def on_erase_edit_armature(self, event_name, event):
    global has_erased_elements

    event.stop_propagation = True

    el_types = {}
    armature = self.data
    for bone_name, el_type in event.sub_targets:
        bone = armature.edit_bones[bone_name]
        el_types[bone] = "BOTH" if bone in el_types else el_type

    full_bones = []  # need to delete these, won't dissolve them

    for bone in armature.edit_bones:
        bone.select = False
        bone.select_head = False
        bone.select_tail = False

        if bone not in el_types:
            continue

        if (
            len(armature.edit_bones) == 1
            or (el_types[bone] in ("TAIL", "BOTH") and len(bone.children) == 0)
            or el_types[bone] == "HEAD"
            and (not bone.parent or len(bone.parent.children) == 0)
        ):
            full_bones.append(bone)
            continue

        if el_types[bone] == "HEAD":
            bone.select_head = True
            log.debug(f"dissolving {bone.name} head")
        elif el_types[bone] == "TAIL":
            bone.select_tail = True
            log.debug(f"dissolving {bone.name} tail")
        else:
            full_bones.append(bone)

    bpy.ops.armature.dissolve()

    for bone in armature.edit_bones:
        bone.select = False
        bone.select_head = False
        bone.select_tail = False

    if len(full_bones) > 0:
        for bone in full_bones:
            bone.select = True
            bone.select_head = True
            bone.select_tail = True
            log.debug(f"erasing {bone.name} full")

        bpy.ops.armature.delete()

    has_erased_elements = True


def on_erase_press(self, event_name, event):
    global is_erasing, has_erased_elements

    ob = bpy.context.view_layer.objects.active
    if len(event.targets) == 0 or (ob is not None and ob.mode == "EDIT" and not event.sub_targets):
        return

    event.stop_propagation = True

    is_erasing = True
    has_erased_elements = False

    if self.type == "CURVE" and self.mode == "EDIT":
        on_erase_edit_curve(self, event_name, event)
    elif self.type == "MESH" and self.mode == "EDIT":
        on_erase_edit_mesh(self, event_name, event)
    elif self.type == "ARMATURE" and self.mode == "EDIT":
        on_erase_edit_armature(self, event_name, event)
    elif self.mode == "OBJECT":
        on_erase_object(self, event_name, event)


def on_erase_end(self, event_name, event):
    global is_erasing, has_erased_elements

    if not is_erasing:
        return

    if has_erased_elements:
        log.debug("pushed undo for ERASE")
        bpy.ops.ed.undo_push(message="erase")

    is_erasing = False
    has_erased_elements = False


def enable_tool():
    # enable_bounds_check()

    Object.add_event_listener("trigger_main_press", on_erase_press)
    root.add_event_listener("trigger_main_end", on_erase_end)


def disable_tool():
    # disable_bounds_check()

    Object.remove_event_listener("trigger_main_press", on_erase_press)
    root.remove_event_listener("trigger_main_end", on_erase_end)
