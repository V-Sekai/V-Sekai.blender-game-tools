import bpy
import bmesh
import numpy as np
from bpy.types import Object

from bl_xr import root
from bl_xr.utils import filter_event_by_buttons, filter_event_by_attr, get_bmesh, sync_bmesh_selection
import logging

from ..settings_manager import settings
from ..utils import set_select_state_all, enable_bounds_check, disable_bounds_check, log

is_select_drag_starting_from_outside = False
is_object_being_transformed = False
state_before_selection = None
elements_toggled_this_selection = set()
is_selecting = False
cleared_selection_before_click = False


def on_select_object(self, event_name, event):
    event.stop_propagation = True

    if not is_selecting or self in elements_toggled_this_selection:
        return

    bpy.context.view_layer.objects.active = self

    toggle_object_selections(event)


def toggle_object_selections(event):
    event.targets = list(target for target in event.targets if isinstance(target, Object))
    for el in event.targets:
        if el in elements_toggled_this_selection:
            continue

        select = not el.select_get()
        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"SET {el} from {el.select_get()} to {select}")
        el.select_set(select)

        elements_toggled_this_selection.add(el)


def on_select_edit_mesh(self, event_name, event):
    event.stop_propagation = True

    if not is_selecting:
        return

    toggle_edit_mesh_selections(self, event)


def toggle_edit_mesh_selections(ob, event):
    if event.sub_targets is None:
        return

    for el in event.sub_targets:
        if el in elements_toggled_this_selection:
            continue

        select = not el.select
        el.select_set(select)
        elements_toggled_this_selection.add(el)

    bmesh.update_edit_mesh(ob.data)


def on_select_edit_curve(self, event_name, event):
    event.stop_propagation = True

    if not is_selecting:
        return

    toggle_edit_curve_selections(event)


def toggle_edit_curve_selections(event):
    if event.sub_targets is None:
        return

    for el in event.sub_targets:
        if el in elements_toggled_this_selection:
            continue

        select = not el.select
        el.select = select
        elements_toggled_this_selection.add(el)


def set_edit_bone_selection(bone, dir, selected, force=False):
    if force or (bone, dir) not in elements_toggled_this_selection:
        prev = getattr(bone, f"select_{dir}")

        setattr(bone, f"select_{dir}", selected)

        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"{dir} SET {bone} from {prev} to {getattr(bone, f'select_{dir}')} force: {force}")

        elements_toggled_this_selection.add((bone, dir))

    if dir == "head" and bone.parent:
        if force or (bone.parent, "tail") not in elements_toggled_this_selection:
            if log.isEnabledFor(logging.DEBUG):
                log.debug(f"SET {bone.parent} tail from {bone.parent.select_tail} to {selected} force {force}")

            bone.parent.select_tail = selected
            elements_toggled_this_selection.add((bone.parent, "tail"))

        # select the siblings, e.g. at a joint
        for sibling in bone.parent.children:
            if sibling == bone:
                continue

            if force or (sibling, "head") not in elements_toggled_this_selection:
                if log.isEnabledFor(logging.DEBUG):
                    log.debug(f"SET {sibling} head from {sibling.select_head} to {bone.select_head} force: {force}")

                sibling.select_head = bone.select_head
                elements_toggled_this_selection.add((sibling, "head"))

    elif dir == "tail" and bone.children:
        for c in bone.children:
            if force or (c, "head") not in elements_toggled_this_selection:
                if log.isEnabledFor(logging.DEBUG):
                    log.debug(f"SET {c} head from {c.select_head} to {selected} force: {force}")

                c.select_head = selected
                elements_toggled_this_selection.add((c, "head"))


def on_select_edit_armature(self, event_name, event):
    event.stop_propagation = True

    if not is_selecting:
        return

    toggle_edit_bone_selections(event)


def toggle_edit_bone_selections(event):
    if event.sub_targets is None:
        return

    ob = bpy.context.view_layer.objects.active
    edit_bones = ob.data.edit_bones

    for bone_name, el_type in event.sub_targets:
        bone = edit_bones[bone_name]
        if el_type == "BOTH":
            set_edit_bone_selection(bone, "head", not bone.select)
            set_edit_bone_selection(bone, "tail", not bone.select)
        elif el_type == "HEAD":
            set_edit_bone_selection(bone, "head", not bone.select_head)
        elif el_type == "TAIL":
            set_edit_bone_selection(bone, "tail", not bone.select_tail)

        if el_type == "BOTH" and (bone, "both") not in elements_toggled_this_selection:
            select = not bone.select
            bone.select = select
            if log.isEnabledFor(logging.DEBUG):
                log.debug(f"SET {bone} {select} to {bone.select}")

            elements_toggled_this_selection.add((bone, "both"))

    # repair
    ## (X)==( ) should become:
    ## 1. (X)==(X) if the selected bone (==) was selected again this frame
    ## 2. (X)--( ) if the selected bone (==) wasn't selected again this frame
    for bone in edit_bones:
        if not bone.select or (bone.select_head and bone.select_tail):
            continue

        missing = "tail" if bone.select_head else "head"
        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"{bone.name} is selected. head: {bone.select_head} tail: {bone.select_tail} missing: {missing}")

        if (bone.name, missing.upper()) in event.sub_targets:  # specifically asked to toggle this joint
            if log.isEnabledFor(logging.DEBUG):
                log.debug(f"{bone.name} setting select to False")

            bone.select = False
        else:
            if log.isEnabledFor(logging.DEBUG):
                log.debug(f"{bone.name} setting {missing} to True")

            set_edit_bone_selection(bone, missing, True, force=True)

    ## (X)--(X) should become (X)==(X)
    for bone in edit_bones:
        if bone.select:
            continue

        if bone.select_head and bone.select_tail:
            bone.select = True


def on_select_pose_armature(self, event_name, event):
    event.stop_propagation = True

    if not is_selecting:
        return

    toggle_pose_bone_selections(self, event)


def toggle_pose_bone_selections(ob, event):
    if event.sub_targets is None:
        return

    pose_bones = ob.pose.bones

    for bone_name, el_type in event.sub_targets:
        bone = pose_bones[bone_name]
        if bone in elements_toggled_this_selection:
            continue

        bone.bone.select = not bone.bone.select
        bone.bone.select_head = bone.bone.select
        bone.bone.select_tail = bone.bone.select

        elements_toggled_this_selection.add(bone)


def on_select_trigger_press(self, event_name, event):
    global cleared_selection_before_click

    event.targets = list(target for target in event.targets if isinstance(target, Object))

    if len(event.targets) == 0 or is_object_being_transformed or not is_select_drag_starting_from_outside:
        return

    toggle_selection = settings.get("select.toggle_selection_on_click", False)
    if is_select_drag_starting_from_outside and not toggle_selection and not cleared_selection_before_click:
        set_select_state_all(False)
        cleared_selection_before_click = True

    event.stop_propagation = True

    if event.sub_targets:
        if event.targets[0].type == "MESH":
            toggle_edit_mesh_selections(self, event)
        elif event.targets[0].type == "CURVE":
            toggle_edit_curve_selections(event)
        elif event.targets[0].type == "ARMATURE":
            ob = bpy.context.view_layer.objects.active
            if ob.mode == "EDIT":
                toggle_edit_bone_selections(event)
            elif ob.mode == "POSE":
                toggle_pose_bone_selections(self, event)
    else:
        toggle_object_selections(event)


def get_selection_state():
    ob = bpy.context.view_layer.objects.active
    if ob is None or ob.mode == "OBJECT":
        return np.array([o.select_get() for o in bpy.data.objects], dtype=bool)

    if ob.mode in ("EDIT", "POSE"):
        if ob.type == "MESH":
            vert_mode, edge_mode, _ = bpy.context.scene.tool_settings.mesh_select_mode

            bm = get_bmesh(ob)

            if vert_mode:
                elements = bm.verts
            elif edge_mode:
                elements = bm.edges
            else:
                elements = bm.faces

            return np.array([e.select for e in elements], dtype=bool)

        if ob.type == "CURVE":
            curve = ob.data
            if len(curve.splines) == 0:
                return

            spline = curve.splines[0]
            return np.array([v.select for v in spline.points], dtype=bool)

        if ob.type == "ARMATURE":
            bones = ob.data.edit_bones if ob.mode == "EDIT" else ob.data.bones

            return np.array([[b.select, b.select_head, b.select_tail] for b in bones], dtype=bool)


def on_select_clicked(self, event_name, event):
    finish_selection()


def on_editor_trigger_start(self, event_name, event):
    global is_select_drag_starting_from_outside

    is_select_drag_starting_from_outside = True

    start_selection()

    clear_selection_before_click(self, event_name, event)


def on_object_trigger_start(self, event_name, event):
    global is_select_drag_starting_from_outside

    event.stop_propagation = True
    is_select_drag_starting_from_outside = False

    start_selection()


def start_selection():
    global is_selecting, state_before_selection, cleared_selection_before_click

    state_before_selection = get_selection_state()

    is_selecting = True
    cleared_selection_before_click = False
    elements_toggled_this_selection.clear()

    if settings["transform.grab_button"] == "squeeze":
        ui_btn = root.q("#controller_main_a")
        ui_btn.style["visible"] = False


def on_editor_trigger_end(self, event_name, event):
    global is_select_drag_starting_from_outside

    finish_selection()

    is_select_drag_starting_from_outside = False


def finish_selection():
    global is_selecting, state_before_selection

    if not is_selecting:
        return

    curr_state = get_selection_state()
    if len(curr_state) == len(state_before_selection):
        select_made_changes = np.any(curr_state ^ state_before_selection)
    else:  # cloned or erased
        select_made_changes = False

    if log.isEnabledFor(logging.DEBUG):
        log.debug(f"select_made_changes: {select_made_changes}")

    if settings["transform.grab_button"] == "squeeze" and len(bpy.context.selected_objects) > 0:
        ui_btn = root.q("#controller_main_a")
        ui_btn.style["visible"] = True

    if not select_made_changes:
        return

    ob = bpy.context.view_layer.objects.active
    if ob and ob.mode == "EDIT" and ob.type == "MESH":
        # copy the selection to the mesh in this way, otherwise undo won't work properly
        sync_bmesh_selection(ob)

    if not is_object_being_transformed:
        bpy.ops.ed.undo_push(message="select")
        log.debug("UNDO CREATED FOR SELECT")

    elements_toggled_this_selection.clear()
    state_before_selection = None

    is_selecting = False


def on_alt_select_start(self, event_name, event):
    settings["select.toggle_selection_on_click"] = True


def on_alt_select_end(self, event_name, event):
    settings["select.toggle_selection_on_click"] = False


def on_object_transform_start(self, event_name, event):
    global is_object_being_transformed

    is_object_being_transformed = True


def on_object_transform_end(self, event_name, event):
    global is_object_being_transformed

    is_object_being_transformed = False


def filter_3(**kwargs):
    by_buttons = filter_event_by_buttons(["trigger_main"])  # idx 0 is `self` (the object)
    by_attr = filter_event_by_attr(**kwargs)

    return lambda *args: by_buttons(*args) and by_attr(*args)


def clear_selection_before_click(self, event_name, event):
    global cleared_selection_before_click

    event.stop_propagation = True

    if cleared_selection_before_click:
        return

    toggle_selection = settings.get("select.toggle_selection_on_click", False)
    if not toggle_selection:
        set_select_state_all(False)
        cleared_selection_before_click = True


def enable_tool():
    # enable_bounds_check()

    Object.add_event_listener("click", clear_selection_before_click)
    Object.add_event_listener("click", on_select_object, {"filter_fn": filter_3(mode="OBJECT")})
    Object.add_event_listener("click", on_select_edit_mesh, {"filter_fn": filter_3(type="MESH", mode="EDIT")})
    Object.add_event_listener("click", on_select_edit_curve, {"filter_fn": filter_3(type="CURVE", mode="EDIT")})
    Object.add_event_listener("click", on_select_edit_armature, {"filter_fn": filter_3(type="ARMATURE", mode="EDIT")})
    Object.add_event_listener("click", on_select_pose_armature, {"filter_fn": filter_3(type="ARMATURE", mode="POSE")})
    Object.add_event_listener("click", on_select_clicked)
    Object.add_event_listener("trigger_main_press", on_select_trigger_press)

    Object.add_event_listener("drag_start", on_object_transform_start)
    Object.add_event_listener("drag_end", on_object_transform_end)

    Object.add_event_listener("trigger_main_start", on_object_trigger_start)
    root.add_event_listener("trigger_main_start", on_editor_trigger_start)
    root.add_event_listener("trigger_main_end", on_editor_trigger_end)

    root.add_event_listener("trigger_alt_start", on_alt_select_start)
    root.add_event_listener("trigger_alt_end", on_alt_select_end)

    if settings["transform.grab_button"] == "trigger":
        ui_btn = root.q("#controller_main_a")
        ui_btn.style["visible"] = True


def disable_tool():
    # disable_bounds_check()

    Object.remove_event_listener("click", clear_selection_before_click)
    root.remove_event_listener("click", clear_selection_before_click)
    Object.remove_event_listener("click", on_select_object)
    Object.remove_event_listener("click", on_select_edit_mesh)
    Object.remove_event_listener("click", on_select_edit_curve)
    Object.remove_event_listener("click", on_select_edit_armature)
    Object.remove_event_listener("click", on_select_pose_armature)
    Object.remove_event_listener("click", on_select_clicked)
    Object.remove_event_listener("trigger_main_press", on_select_trigger_press)

    Object.remove_event_listener("drag_start", on_object_transform_start)
    Object.remove_event_listener("drag_end", on_object_transform_end)

    Object.remove_event_listener("trigger_main_start", on_object_trigger_start)
    root.remove_event_listener("trigger_main_start", on_editor_trigger_start)
    root.remove_event_listener("trigger_main_end", on_editor_trigger_end)

    root.remove_event_listener("trigger_alt_start", on_alt_select_start)
    root.remove_event_listener("trigger_alt_end", on_alt_select_end)

    if settings["transform.grab_button"] == "trigger":
        ui_btn = root.q("#controller_main_a")
        ui_btn.style["visible"] = False
