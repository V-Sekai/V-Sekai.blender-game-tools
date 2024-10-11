import bpy
import bmesh
from bpy.types import PoseBone

from bl_xr.utils import get_bmesh_elements

import logging


def set_select_state_all(state):
    from freebird.utils import log

    ob = bpy.context.view_layer.objects.active
    if ob is None:
        return False

    if ob.mode == "OBJECT":
        for prev_ob in bpy.context.selected_objects:
            prev_ob.select_set(state)
    elif ob.mode in ("EDIT", "POSE"):
        if ob.type == "MESH":
            mesh = ob.data
            el = get_bmesh_elements(ob)

            for e in el:
                e.select_set(state)
            bmesh.update_edit_mesh(mesh)
            log.debug(f"SET edit mesh select to: {state}")
        elif ob.type == "CURVE":
            curve = ob.data
            if len(curve.splines) == 0:
                return

            spline = curve.splines[0]
            for v in spline.points:
                v.select = state
        elif ob.type == "ARMATURE":
            bones = ob.data.edit_bones if ob.mode == "EDIT" else ob.data.bones

            for bone in bones:
                bone.select = state
                bone.select_head = state
                bone.select_tail = state


def set_select_state(elements, state):
    from freebird.utils import log

    ob = bpy.context.view_layer.objects.active
    if ob is None:
        return False

    if ob.mode == "OBJECT":
        for prev_ob in elements:
            prev_ob.select_set(state)
    elif ob.mode in ("EDIT", "POSE"):
        if ob.type == "MESH":
            mesh = ob.data

            for e in elements:
                e.select_set(state)
            bmesh.update_edit_mesh(mesh)
            if log.isEnabledFor(logging.DEBUG):
                log.debug(f"SET {[e.index for e in elements]} in edit mesh select to {state}")
        elif ob.type == "CURVE":
            for v in elements:
                v.select = state
        elif ob.type == "ARMATURE":
            for bone, el_type in elements:
                bone = bone.bone if isinstance(bone, PoseBone) else bone
                bone.select = state if el_type == "BOTH" else False
                bone.select_head = state if el_type in ("HEAD", "BOTH") else False
                bone.select_tail = state if el_type in ("TAIL", "BOTH") else False
