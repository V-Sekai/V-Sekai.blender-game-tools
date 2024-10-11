import bpy
from bpy.types import Object
from mathutils import Vector, Quaternion, Matrix
from math import radians
import time

from bl_xr import root, xr_session, DragEvent, ControllerEvent, Pose, Node
from bl_xr.utils import get_bmesh, quaternion_from_vector, vec_abs
from bl_xr.consts import VEC_FORWARD, VEC_RIGHT, VEC_UP, VEC_ONE, RED_MILD as RED, BLUE_MS as BLUE, GREEN_MILD as GREEN
from freebird import settings

from ..tools.transform_common import get_selected_elements
from .common.pull_push_handle import PullPushHandle
from .common.rotate_wheel_handle import RotateWheelHandle
from .edit_mesh.edit_mesh_handle import EditMeshHandle

targets = None
sub_targets = None
handle_origin = None
handle_rotation = None


class TransformHandle(Node):
    # REFRESH_INTERVAL = 0.5  # seconds

    def __init__(self, component, handle_type, **kwargs):
        super().__init__(**kwargs)

        self.id = f"transform_gizmo_{handle_type.lower()}_{component}_parent"

        self.handle_type = handle_type  # "TRANSLATE" or "ROTATE" or "SCALE"
        self.component = component  # "x" or "y" or "z"

        if component == "x":
            self.direction = VEC_RIGHT
        elif component == "y":
            self.direction = VEC_FORWARD
        elif component == "z":
            self.direction = VEC_UP

        if handle_type in ("TRANSLATE", "SCALE"):
            self.handle = PullPushHandle(
                length=settings["gizmo.transform_handles.length"],
                knob_radius=settings["gizmo.transform_handles.knob_radius"],
                knob_type="CONE" if handle_type == "TRANSLATE" else "CUBE",
            )
            self.handle.mesh_modes_allowed = {"VERT", "EDGE", "FACE"}
            self.handle.rotation = quaternion_from_vector(self.direction)
            self._world_rotation_at_start = None

            if handle_type == "TRANSLATE":
                self.handle.apply_total_offset = False
            elif handle_type == "SCALE":
                self._prev_length = None
        elif handle_type == "ROTATE":
            self.handle = RotateWheelHandle(radius=settings["gizmo.transform_handles.length"])

            if component == "x":
                self.handle.rotation = Quaternion((0, 1, 0), radians(90))
            elif component == "y":
                self.handle.rotation = Quaternion((1, 0, 0), radians(-90))
            elif component == "z":
                self.handle.rotation = Quaternion()

        if component == "x":
            self.handle.color = RED
        elif component == "y":
            self.handle.color = GREEN
        elif component == "z":
            self.handle.color = BLUE

        self.handle.id = f"transform_gizmo_{handle_type.lower()}_{component}"
        self.handle.haptic_feedback = False
        self.append_child(self.handle)

        self.handle.add_event_listener("handle_drag_start", self.on_handle_drag_start)
        self.handle.add_event_listener("handle_drag", self.on_handle_drag)
        self.handle.add_event_listener("handle_drag_end", self.on_handle_drag_end)

    def on_handle_drag_start(self, event_name, drag_amt):
        if self.handle_type == "SCALE":
            self._world_rotation_at_start = Quaternion(handle_rotation)

        transform_delta = self._get_delta(drag_amt)
        dispatch_event("drag_start", transform_delta, self.handle_type)

    def on_handle_drag(self, event_name, drag_amt):
        transform_delta = self._get_delta(drag_amt)
        dispatch_event("drag", transform_delta, self.handle_type)

    def on_handle_drag_end(self, event_name, event):
        transform_delta = Pose()
        if self.handle_type == "SCALE":
            self._prev_length = None
            self._world_rotation_at_start = None

        dispatch_event("drag_end", transform_delta, self.handle_type)

    def _get_delta(self, drag_amt):
        if self.handle_type == "TRANSLATE":
            axis = self.rotation_world @ self.direction
            return Pose(position=axis * drag_amt)
        if self.handle_type == "ROTATE":
            axis = self.rotation_world @ self.direction
            return Pose(rotation=Quaternion(axis, drag_amt))
        elif self.handle_type == "SCALE":
            scale = Vector(VEC_ONE)
            if self._prev_length is not None and self._prev_length > 0.001:
                setattr(scale, self.component, abs(self.handle.rod.length) / self._prev_length)

            transform_space = bpy.context.scene.transform_orientation_slots[0].type
            if transform_space == "GLOBAL":
                axis_local = self._world_rotation_at_start.inverted() @ self.direction
                scale_amt = getattr(scale, self.component)
                m = Matrix.Scale(scale_amt, 4, axis_local)
                scale = m.to_scale()

            self._prev_length = abs(self.handle.rod.length)
            return Pose(scale_factor=scale)


class TransformGizmo(Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.translate_handles = Node(
            id="transform_gizmo_translate",
            child_nodes=[
                TransformHandle("x", handle_type="TRANSLATE"),
                TransformHandle("y", handle_type="TRANSLATE"),
                TransformHandle("z", handle_type="TRANSLATE"),
            ],
        )
        self.rotate_handles = Node(
            id="transform_gizmo_rotate",
            child_nodes=[
                TransformHandle("x", handle_type="ROTATE"),
                TransformHandle("y", handle_type="ROTATE"),
                TransformHandle("z", handle_type="ROTATE"),
            ],
        )
        self.scale_handles = Node(
            id="transform_gizmo_scale",
            child_nodes=[
                TransformHandle("x", handle_type="SCALE"),
                TransformHandle("y", handle_type="SCALE"),
                TransformHandle("z", handle_type="SCALE"),
            ],
        )
        self.contents = Node()

        self.contents.append_child(self.translate_handles)
        self.contents.append_child(self.rotate_handles)
        self.contents.append_child(self.scale_handles)

        self.append_child(self.contents)

    def update(self):
        global targets, sub_targets
        global handle_origin, handle_rotation

        # if self._is_dragging:
        #     return

        # if time.time() < self._next_refresh_time:
        #     return

        # self._next_refresh_time = time.time() + self.REFRESH_INTERVAL

        from freebird import tools

        gizmo_type = settings["gizmo.transform_handles.type"]
        if not gizmo_type or tools.active_tool != "select":
            self.contents.style["visible"] = False
            return

        self.contents.style["visible"] = True
        self.translate_handles.style["visible"] = gizmo_type == "translate"
        self.rotate_handles.style["visible"] = gizmo_type == "rotate"
        self.scale_handles.style["visible"] = gizmo_type == "scale"

        ob = bpy.context.view_layer.objects.active
        selected_elements = get_selected_elements()
        if ob is None or len(selected_elements) == 0:
            self.contents.style["visible"] = False
            return

        el_list = list(selected_elements)
        if isinstance(el_list[0], Object):
            targets = [el_list[0]]
            sub_targets = None
        else:
            targets = [bpy.context.view_layer.objects.active]
            sub_targets = {el_list[0]}

        handle_origin, handle_rotation = get_origin(selected_elements)
        if handle_origin is None:
            self.contents.style["visible"] = False
            return

        transform_space = bpy.context.scene.transform_orientation_slots[0].type

        self.position_world = handle_origin
        self.rotation_world = handle_rotation if transform_space == "LOCAL" else Quaternion()


def get_origin(elements: set):
    if not elements:
        return None, None

    ob = bpy.context.view_layer.objects.active

    origin_world = None
    rotation_world = ob.matrix_world.to_quaternion()
    mat_world = ob.matrix_world

    if ob.mode == "OBJECT":
        origin_world = Vector()
        for el in elements:
            origin_world += el.location

        origin_world /= len(elements)
    elif ob.mode in ("EDIT", "POSE"):
        if ob.type == "MESH":
            bm = get_bmesh()
            origin_world, _ = EditMeshHandle.get_selected_center(bm)
        elif ob.type == "CURVE":
            if len(elements) == 0:
                return None, None

            origin_world = Vector()
            for el in elements:
                origin_world += Vector(el.co[:3])

            origin_world /= len(elements)

            origin_world = mat_world @ origin_world
        elif ob.type == "ARMATURE":
            origin_world = Vector()
            if ob.mode == "EDIT":
                bones = ob.data.edit_bones
                for bone_name, el_type in elements:
                    bone = bones[bone_name]
                    if el_type == "head":
                        origin_world += bone.head
                    elif el_type == "tail":
                        origin_world += bone.tail
                    else:
                        origin_world += (bone.head + bone.tail) / 2
            else:
                bones = ob.pose.bones
                for bone_name, _ in elements:
                    bone = bones[bone_name]
                    origin_world += bone.head

            origin_world /= len(elements)

            origin_world = mat_world @ origin_world
            rotation_world = bone.matrix.decompose()[1]

    return origin_world, rotation_world


def dispatch_event(event_type, transform_delta, handle_type):
    btn_name = "squeeze_main" if settings["transform.grab_button"] == "squeeze" else "trigger_main"
    pivot_pt = handle_origin

    # send trigger events if using trigger for grab
    if settings["transform.grab_button"] == "trigger" and event_type.endswith(("_start", "_end")):
        trigger_event = ControllerEvent(targets=targets, sub_targets=sub_targets, button_name="trigger_main")
        if "_start" in event_type:
            trigger_event.type = "trigger_main_start"
        elif "_end" in event_type:
            trigger_event.type = "trigger_main_end"

        targets[0].dispatch_event(trigger_event.type, trigger_event)

    event = DragEvent(
        event_type,
        targets=targets,
        sub_targets=sub_targets,
        button_name=btn_name,
        pose_delta=transform_delta,
        pivot_position=pivot_pt,
    )
    event.is_handle_drag = True
    event.handle_type = handle_type

    targets[0].dispatch_event(event.type, event)


gizmo = TransformGizmo(id="transform_gizmo")


def enable_gizmo():
    root.append_child(gizmo)


def disable_gizmo():
    root.remove_child(gizmo)
