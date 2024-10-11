# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from math import pi, radians, cos, sin, degrees, sqrt
from dataclasses import dataclass
from copy import deepcopy

import bpy
import bl_math
from mathutils import Vector, Quaternion, Matrix

from bl_xr.consts import VEC_ZERO, VEC_ONE, VEC_UP, VEC_RIGHT, EPSILON, VEC_FORWARD


@dataclass
class Pose:
    position: Vector = Vector()
    rotation: Quaternion = Quaternion()
    scale_factor: float = 1.0

    @property
    def up(self) -> Vector:
        return self.rotation @ VEC_UP

    @property
    def right(self) -> Vector:
        return self.rotation @ VEC_RIGHT

    @property
    def forward(self) -> Vector:
        return self.rotation @ VEC_FORWARD

    def difference(self, other) -> Pose:
        return Pose(
            self.position - other.position,
            quat_diff(self.rotation, other.rotation),  # self.rotation.rotation_difference(other.rotation),
            self.scale_factor / other.scale_factor if other.scale_factor > 0.001 else 1,
        )

    def transform(self, transform_by, pivot_pt: Vector):
        # apply scale
        pivot_delta = self.position - pivot_pt
        pivot_delta *= transform_by.scale_factor
        self.position = pivot_pt + pivot_delta

        self.scale_factor *= transform_by.scale_factor

        # apply translation
        self.position += transform_by.position

        # apply rotation
        r = Quaternion(self.rotation)
        self.position, self.rotation = rotate_around(self.position, r, pivot_pt, transform_by.rotation)

    def invert(self):
        self.position *= -1
        self.rotation.invert()
        self.scale_factor = 1 / self.scale_factor

    def inverted(self) -> Pose:
        p = self.clone()
        p.invert()
        return p

    def clone(self) -> Pose:
        return deepcopy(self)

    def lerp(a, b, t) -> Pose:
        return Pose(
            a.position.lerp(b.position, t),
            a.rotation.slerp(b.rotation, t),
            bl_math.lerp(a.scale_factor, b.scale_factor, t),
        )

    def to_matrix(self) -> Matrix:
        return Matrix.LocRotScale(self.position, self.rotation, self.scale_factor * VEC_ONE)

    def equals(self, other: Pose):
        return (
            vec_equal(self.position, other.position)
            and quat_equal(self.rotation, other.rotation)
            and abs(self.scale_factor - other.scale_factor) <= EPSILON
        )

    def __str__(self) -> str:
        return f"Pose(position={self.position}, rotation={tuple(degrees(a) for a in self.rotation.to_euler())}, scale_factor={self.scale_factor})"


def make_class_posable(clazz):
    def pose_get(self):
        self.rotation_mode = "QUATERNION"
        p = Pose(
            self.location,
            self.rotation_quaternion,
            1,
        )
        self.rotation_mode = "XYZ"

        return p

    def pose_set(self, value):
        self.rotation_mode = "QUATERNION"

        self.location = value.position
        self.rotation_quaternion = value.rotation
        self.scale = self.scale * value.scale_factor

        self.rotation_mode = "XYZ"

    setattr(clazz, "pose_get", pose_get)
    setattr(clazz, "pose_set", pose_set)


def rotate_around(
    target_location: Vector,
    target_rotation: Quaternion,
    pivot_location: Vector,
    rotate_by: Quaternion,
):
    d = target_location - pivot_location
    d = rotate_by @ d

    if target_rotation is not None:
        target_rotation.rotate(rotate_by)

    target_location = d + pivot_location

    return target_location, target_rotation


def nearest_point_on_line_segment(point: Vector, line_start: Vector, line_end: Vector):
    a = point - line_start
    l = line_end - line_start

    p = a.project(l) + line_start
    line_len = (line_end - line_start).length

    if (p - line_start).length > line_len:
        p = line_end
    elif (p - line_end).length > line_len:
        p = line_start

    return p


def intersect_line_sphere(p1, p2, sphere_center, sphere_radius):
    """
    Returns None, None if no intersection (or fully contained in the sphere).
    Returns the intersection points as a tuple.
    This was written because Blender's implementation has a bug.

    Try intersect_line_sphere(Vector((4200, 4201, 4200)), Vector((4200, 4202, 4200)), Vector((4200, 4199, 4200)), 1)

    Should return None, None, but Blender's returns (Vector((4200.0, 4201.23583984375, 4200.0)), None) (which is wrong).
    """
    # based on https://paulbourke.net/geometry/circlesphere/#linesphere

    s = sphere_center
    r = sphere_radius
    d = p2 - p1

    a = (p2.x - p1.x) * (p2.x - p1.x) + (p2.y - p1.y) * (p2.y - p1.y) + (p2.z - p1.z) * (p2.z - p1.z)

    # now check for the intersection points
    b = 2 * ((p2.x - p1.x) * (p1.x - s.x) + (p2.y - p1.y) * (p1.y - s.y) + (p2.z - p1.z) * (p1.z - s.z))
    c = (
        (s.x * s.x + s.y * s.y + s.z * s.z)
        + (p1.x * p1.x + p1.y * p1.y + p1.z * p1.z)
        - 2 * (s.x * p1.x + s.y * p1.y + s.z * p1.z)
        - r * r
    )
    cond = b * b - 4 * a * c

    if cond < 0:
        return None, None

    u1 = (-b - sqrt(cond)) / (2 * a)
    u2 = (-b + sqrt(cond)) / (2 * a)

    i1 = p1 + d * u1 if u1 > 0 and u1 < 1 else None
    i2 = p1 + d * u2 if u2 > 0 and u2 < 1 else None

    return i1, i2


def make_sphere(radius: float, segments: int = 8, rings: int = 12) -> tuple[list, list]:
    # source: https://blenderartists.org/t/creating-a-sphere-from-python/604778/2
    dPolar = pi / (rings - 1)
    dAzimuthal = 2.0 * pi / (segments)

    # 1/2: vertices
    verts = []
    currV = Vector((0.0, 0.0, radius))  # top vertex
    verts.append(currV)
    for iPolar in range(1, rings - 1):  # regular vertices
        currPolar = dPolar * float(iPolar)

        currCosP = cos(currPolar)
        currSinP = sin(currPolar)

        for iAzimuthal in range(segments):
            currAzimuthal = dAzimuthal * float(iAzimuthal)

            currCosA = cos(currAzimuthal)
            currSinA = sin(currAzimuthal)

            currV = Vector((currSinP * currCosA, currSinP * currSinA, currCosP)) * radius
            verts.append(currV)
    currV = Vector((0.0, 0.0, -radius))  # bottom vertex
    verts.append(currV)

    # 2/2: faces
    faces = []
    for iAzimuthal in range(segments):  # top faces
        iNextAzimuthal = iAzimuthal + 1
        if iNextAzimuthal >= segments:
            iNextAzimuthal -= segments
        faces.append([0, iAzimuthal + 1, iNextAzimuthal + 1])

    for iPolar in range(rings - 3):  # regular faces
        iAzimuthalStart = iPolar * segments + 1

        for iAzimuthal in range(segments):
            iNextAzimuthal = iAzimuthal + 1
            if iNextAzimuthal >= segments:
                iNextAzimuthal -= segments
            faces.append(
                [
                    iAzimuthalStart + iAzimuthal,
                    iAzimuthalStart + iAzimuthal + segments,
                    iAzimuthalStart + iNextAzimuthal + segments,
                ]
            )
            faces.append(
                [
                    iAzimuthalStart + iNextAzimuthal + segments,
                    iAzimuthalStart + iNextAzimuthal,
                    iAzimuthalStart + iAzimuthal,
                ]
            )

    iLast = len(verts) - 1
    iAzimuthalStart = iLast - segments
    for iAzimuthal in range(segments):  # bottom faces
        iNextAzimuthal = iAzimuthal + 1
        if iNextAzimuthal >= segments:
            iNextAzimuthal -= segments
        faces.append([iAzimuthalStart + iAzimuthal, iLast, iAzimuthalStart + iNextAzimuthal])

    return verts, faces


# courtesy: R. Daneel Olivaw
def make_ring_mesh(inner_radius, outer_radius, thickness, num_segments):
    vertices = []
    faces = []

    angle_increment = 2 * pi / num_segments

    # Generate vertices
    for i in range(num_segments):
        angle = i * angle_increment
        cos_angle = cos(angle)
        sin_angle = sin(angle)

        # Outer circle vertices (upper and lower)
        vertices.append((outer_radius * cos_angle, outer_radius * sin_angle, thickness / 2))  # Upper
        vertices.append((outer_radius * cos_angle, outer_radius * sin_angle, -thickness / 2))  # Lower

        # Inner circle vertices (upper and lower)
        vertices.append((inner_radius * cos_angle, inner_radius * sin_angle, thickness / 2))  # Upper
        vertices.append((inner_radius * cos_angle, inner_radius * sin_angle, -thickness / 2))  # Lower

    vertices = [Vector(v) for v in vertices]

    # Generate faces
    for i in range(num_segments):
        next_i = (i + 1) % num_segments

        # Upper faces
        faces.append([i * 4, next_i * 4, i * 4 + 2])
        faces.append([next_i * 4, next_i * 4 + 2, i * 4 + 2])

        # Lower faces
        faces.append([i * 4 + 1, next_i * 4 + 1, i * 4 + 3])
        faces.append([next_i * 4 + 1, next_i * 4 + 3, i * 4 + 3])

        # Outer faces
        faces.append([i * 4, next_i * 4, i * 4 + 1])
        faces.append([next_i * 4, next_i * 4 + 1, i * 4 + 1])

        # Inner faces
        faces.append([i * 4 + 2, next_i * 4 + 2, i * 4 + 3])
        faces.append([next_i * 4 + 2, next_i * 4 + 3, i * 4 + 3])

        # Side faces
        faces.append([i * 4, i * 4 + 1, i * 4 + 2])
        faces.append([i * 4 + 1, i * 4 + 3, i * 4 + 2])
        faces.append([next_i * 4, next_i * 4 + 1, next_i * 4 + 2])
        faces.append([next_i * 4 + 1, next_i * 4 + 3, next_i * 4 + 2])

    return vertices, faces


# courtesy: R. Daneel Olivaw
def make_pyramid(size: float = 1):
    # Define the vertices
    vertices = [
        (0, 0, 0.5),  # Apex of the pyramid
        (0.5, 0.5, -0.5),  # Base vertex 1
        (-0.5, 0.5, -0.5),  # Base vertex 2
        (-0.5, -0.5, -0.5),  # Base vertex 3
        (0.5, -0.5, -0.5),  # Base vertex 4
    ]

    vertices = [Vector(v) * size for v in vertices]

    # Define the faces
    faces = [
        [0, 1, 2],  # Side face 1
        [0, 2, 3],  # Side face 2
        [0, 3, 4],  # Side face 3
        [0, 4, 1],  # Side face 4
        [1, 2, 3],  # Base face 1
        [1, 3, 4],  # Base face 2
    ]

    return vertices, faces


# courtesy: R. Daneel Olivaw
def make_cube(size: float = 1):
    # Define the vertices
    vertices = [
        (-0.5, -0.5, -0.5),  # Vertex 0
        (0.5, -0.5, -0.5),  # Vertex 1
        (0.5, 0.5, -0.5),  # Vertex 2
        (-0.5, 0.5, -0.5),  # Vertex 3
        (-0.5, -0.5, 0.5),  # Vertex 4
        (0.5, -0.5, 0.5),  # Vertex 5
        (0.5, 0.5, 0.5),  # Vertex 6
        (-0.5, 0.5, 0.5),  # Vertex 7
    ]

    vertices = [Vector(v) * size for v in vertices]

    # Define the faces (each face is split into two triangles)
    faces = [
        # Bottom face
        [0, 1, 2],
        [0, 2, 3],
        # Top face
        [4, 5, 6],
        [4, 6, 7],
        # Front face
        [0, 1, 5],
        [0, 5, 4],
        # Back face
        [2, 3, 7],
        [2, 7, 6],
        # Left face
        [0, 3, 7],
        [0, 7, 4],
        # Right face
        [1, 2, 6],
        [1, 6, 5],
    ]

    return vertices, faces


# courtesy: R. Daneel Olivaw
def make_cone(radius: float = 1, height: float = 1, num_segments: int = 12):
    vertices = []
    faces = []

    # Apex of the cone
    vertices.append((0, 0, height / 2))

    # Base vertices
    for i in range(num_segments):
        angle = 2 * pi * i / num_segments
        x = radius * cos(angle)
        y = radius * sin(angle)
        vertices.append((x, y, -height / 2))

    vertices = [Vector(v) for v in vertices]

    # Generate side faces
    for i in range(num_segments):
        next_i = (i + 1) % num_segments
        faces.append([0, i + 1, next_i + 1])

    # Generate base faces (triangulate the base)
    for i in range(1, num_segments - 1):
        faces.append([1, i + 1, i + 2])

    return vertices, faces


# inspired by https://stackoverflow.com/questions/9028398/change-viewport-angle-in-blender-using-python
def matrix_to_camera_position(matrix):
    rp = -1 * matrix.to_3x3()
    rp.transpose()

    t = matrix.to_translation()
    return rp @ t


def camera_position_to_matrix(camera_pos: Vector, camera_rot: Quaternion):
    r = camera_rot.to_matrix().transposed()
    rp = -1 * r
    rp.transpose()
    rp.invert()

    t = rp @ camera_pos
    return Matrix.LocRotScale(t, r, None)


def quat_diff(a: Quaternion, b: Quaternion) -> Quaternion:
    "Returns the quaternion equivalent of `a - b`"
    # https://stackoverflow.com/a/22167097
    return a @ b.inverted()


def quat_equal(a: Quaternion, b: Quaternion) -> float:
    return a.rotation_difference(b).angle <= EPSILON


def vec_equal(a: Vector, b: Vector) -> float:
    if a.length <= EPSILON and b.length <= EPSILON:
        return True
    elif a.length <= EPSILON or b.length <= EPSILON:
        return False
    elif abs(a.length - b.length) > EPSILON:
        return False
    return a.angle(b) <= EPSILON


def vec_divide(v1, v2):
    return Vector(v1_val / v2_val for v1_val, v2_val in zip(v1, v2))


def vec_mul(v1, v2):
    "Piecewise multiplication of corresponding elements of the two vectors. Also known as 'scale a vector by another vector'"
    return Vector(x * y for x, y in zip(v1, v2))  # https://blender.stackexchange.com/a/27759


def vec_signed_angle(v1, v2, axis):
    angle = v1.angle(v2, 0)
    c = v2.cross(v1)
    d = c.dot(axis)
    angle *= 1 if d > 0 else -1

    return angle


def vec_abs(v):
    return Vector((abs(v.x), abs(v.y), abs(v.z)))


def vec_max_component_mask(v):
    if v.x >= v.y and v.x >= v.z:
        return 1, 0, 0
    elif v.y >= v.x and v.y >= v.z:
        return 0, 1, 0
    else:
        return 0, 0, 1


def to_upright_rotation(q: Quaternion) -> Quaternion:
    """
    Projects the given rotation along the XY plane, and returns a new rotation.
    This effectively removes the "pitch" and "roll" aspects of the rotation.

    Useful when converting a rotation into something that a VR user can see comfortably.
    """

    fwd = q @ VEC_FORWARD
    return Quaternion((0, 0, 1), -fwd.angle(VEC_FORWARD))


def to_blender_axis_system(q: Quaternion | tuple) -> Quaternion:
    return pitch_rotation(q, -90)


def from_blender_axis_system(q: Quaternion | tuple) -> Quaternion:
    return pitch_rotation(q, 90)


def pitch_rotation(q, angle_deg):
    q = Quaternion(q)
    right = q @ VEC_RIGHT
    tilt_rot = Quaternion(right, radians(angle_deg))
    q.rotate(tilt_rot)
    return q


# inspired by https://stackoverflow.com/questions/9028398/change-viewport-angle-in-blender-using-python
def matrix_to_camera_position(matrix):
    rp = -1 * matrix.to_3x3()
    rp.transpose()

    t = matrix.to_translation()
    return rp @ t


def camera_position_to_matrix(camera_pos: Vector, camera_rot: Quaternion):
    r = camera_rot.to_matrix().transposed()
    rp = -1 * r
    rp.transpose()
    rp.invert()
    t = rp @ camera_pos
    return Matrix.LocRotScale(t, r, None)


def quaternion_from_vector(v):
    return VEC_FORWARD.rotation_difference(v)


def project_point_on_plane(plane_pt, plane_normal, pt_to_project):
    a = pt_to_project - plane_pt
    d = a.dot(plane_normal)
    return pt_to_project - d * plane_normal


@dataclass
class Bounds:
    min: Vector
    max: Vector

    @property
    def size(self) -> Vector:
        return vec_abs(self.max - self.min)

    def contains_point(self, point: Vector) -> bool:
        return self.contains_sphere(point, radius=0)

    def contains_sphere(self, center: Vector, radius: float) -> bool:
        return (
            center.x - radius <= self.max.x
            and center.y - radius <= self.max.y
            and center.z - radius <= self.max.z
            and center.x + radius >= self.min.x
            and center.y + radius >= self.min.y
            and center.z + radius >= self.min.z
        )

    def expand(self, amt):
        mid = (self.min + self.max) / 2
        extents = (self.max - self.min) / 2
        extents *= amt
        self.min = mid - extents
        self.max = mid + extents
