from ..dom import Node
from ..consts import VEC_FORWARD
from .xr_session_utils import xr_session
from .geometry_utils import Pose

from math import copysign, radians

from mathutils import Vector, Quaternion


def get_node_breadcrumb(node: Node):
    node_tree = []
    while node:
        node_tree.append(str(node) if node.parent else "root")
        node = node.parent
    node_tree.reverse()
    return " > ".join(node_tree)


def sign(v) -> int:
    "Returns 1 if `v` is positive, -1 if `v` is negative"
    return int(copysign(1, v))


def is_within_fov(point_world: Vector, max_fov_for_intersection=radians(30)) -> bool:
    "Check whether `point_world` is within the camera's FOV (in radians)"

    if point_world is None:
        return False

    viewer_loc = xr_session.viewer_camera_position
    viewer_rot = xr_session.viewer_camera_rotation

    if viewer_rot.x == 0 and viewer_rot.y == 0 and viewer_rot.z == 0 and viewer_rot.w == 0:
        return True

    fwd = viewer_rot @ VEC_FORWARD
    point_dir = (point_world - viewer_loc).normalized()
    angle = fwd.angle(point_dir) if point_dir.length > 0.001 else 0

    return angle <= max_fov_for_intersection


def is_equal(actual, expected):
    if isinstance(actual, Vector):
        return is_equal(actual.to_tuple(), expected.to_tuple())
    elif isinstance(actual, Quaternion):
        return is_equal((actual.x, actual.y, actual.z, actual.w), (expected.x, expected.y, expected.z, expected.w))
    elif isinstance(actual, Pose):
        return is_equal(
            (actual.position, actual.rotation, actual.scale_factor),
            (expected.position, expected.rotation, expected.scale_factor),
        )
    elif isinstance(actual, float):
        return abs(actual - expected) < 0.001
    elif isinstance(actual, (list, tuple)):
        if len(actual) != len(expected):
            return False
        return all(is_equal(a, e) for a, e in zip(actual, expected))
    elif isinstance(actual, set):
        if len(actual) != len(expected):
            return False
        for a in actual:
            found = False
            for e in expected:
                if is_equal(a, e):
                    found = True
                    break
            if not found:
                return False
        return True

    return actual == expected
