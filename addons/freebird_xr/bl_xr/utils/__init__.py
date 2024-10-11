# SPDX-License-Identifier: GPL-2.0-or-later

import logging as _logging

log = _logging.getLogger("bl_xr")

from .event_utils import make_class_event_aware, filter_event_by_buttons, filter_event_by_attr, translate_event_hands

from .intersection_utils import (
    intersects_object_mesh,
    intersects_edit_mesh,
    intersects_object_curve,
    intersects_object_armature,
    intersects_edit_curve,
    intersects_edit_armature,
    intersects_pose_armature,
    intersects,
    raycast,
)

from .geometry_utils import (
    rotate_around,
    make_class_posable,
    make_sphere,
    make_ring_mesh,
    make_pyramid,
    make_cube,
    make_cone,
    quat_equal,
    vec_equal,
    vec_mul,
    quat_diff,
    vec_abs,
    vec_max_component_mask,
    vec_divide,
    vec_signed_angle,
    project_point_on_plane,
    matrix_to_camera_position,
    camera_position_to_matrix,
    nearest_point_on_line_segment,
    intersect_line_sphere,
    to_blender_axis_system,
    from_blender_axis_system,
    matrix_to_camera_position,
    camera_position_to_matrix,
    quaternion_from_vector,
    to_upright_rotation,
)

from .mesh_utils import get_bmesh, get_bmesh_elements, get_bvh, reindex_bmesh, sync_bmesh_selection, get_mesh_mode
from .haptic_utils import apply_haptic_feedback
from .misc_utils import get_node_breadcrumb, sign, is_within_fov, is_equal

from bl_math import lerp, clamp
