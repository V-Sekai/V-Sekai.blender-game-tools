from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from math import atan2, cos, radians, sin
from typing import TYPE_CHECKING

import bmesh
import bpy
from bmesh.types import BMesh, BMVert
from bpy.props import FloatProperty
from bpy.types import Armature, Bone, Context, Event, Mesh, Operator
from mathutils import Matrix, Vector

from ..common.logging import get_logger
from .make_armature import IcypTemplateMeshMaker

logger = get_logger(__name__)


class ICYP_OT_detail_mesh_maker(Operator):
    bl_idname = "icyp.make_mesh_detail"
    bl_label = "(Don't work currently)detail mesh"
    bl_description = "Create mesh with a simple setup for VRM export"
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    # init before execute
    # https://docs.blender.org/api/2.82/Operator.html#invoke-function
    # pylint: disable=W0201
    def invoke(self, context: Context, _event: Event) -> set[str]:
        self.base_armature_name = next(
            o for o in context.selected_objects if o.type == "ARMATURE"
        ).name
        self.face_mesh_name = next(
            o for o in context.selected_objects if o.type == "MESH"
        ).name
        face_mesh = bpy.data.objects[self.face_mesh_name]
        face_mesh.display_type = "WIRE"
        rfd = face_mesh.bound_box[4]
        lfd = face_mesh.bound_box[0]
        rfu = face_mesh.bound_box[5]
        rbd = face_mesh.bound_box[7]
        self.neck_depth_offset = rfu[2]
        self.head_tall_size = rfu[2] - rfd[2]
        self.head_width_size = rfd[0] - lfd[0]
        self.head_depth_size = rfd[1] - rbd[1]
        return self.execute(context)

    def execute(self, context: Context) -> set[str]:
        self.base_armature = bpy.data.objects[self.base_armature_name]
        self.face_mesh = bpy.data.objects[self.face_mesh_name]
        head_bone = self.get_humanoid_bone("head")
        head_matrix = IcypTemplateMeshMaker.head_bone_to_head_matrix(
            head_bone, self.head_tall_size, self.neck_depth_offset
        )

        self.neck_tail_y = self.head_tall_size - (
            head_bone.tail_local[2] - head_bone.head_local[2]
        )

        self.mesh = bpy.data.meshes.new("template_face")
        self.make_face(context, self.mesh)
        obj = bpy.data.objects.new("template_face", self.mesh)
        scene = context.scene
        scene.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.matrix_local = head_matrix
        bpy.ops.object.modifier_add(type="MIRROR")
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        obj.scale[2] = -1
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        obj.select_set(False)
        context.view_layer.objects.active = self.face_mesh
        return {"FINISHED"}

    def get_humanoid_bone(self, bone: str) -> Bone:
        armature_data = self.base_armature.data
        if not isinstance(armature_data, Armature):
            message = f"{type(armature_data)} is not an Armature"
            raise TypeError(message)
        return armature_data.bones[str(armature_data[bone])]

    face_center_ratio: FloatProperty(  # type: ignore[valid-type]
        default=1,
        min=0.2,
        max=1,
        soft_min=0.6,
        name="Face center ratio",
    )

    eye_width_ratio: FloatProperty(  # type: ignore[valid-type]
        default=2,
        min=0.5,
        max=4,
        name="Eye width ratio",
    )

    nose_head_height: FloatProperty(  # type: ignore[valid-type]
        default=1,
        min=0,
        max=1,
        name="nose head",
    )

    nose_top_pos: FloatProperty(  # type: ignore[valid-type]
        default=0.2,
        min=0,
        max=0.6,
        name="nose top position",
    )

    nose_height: FloatProperty(  # type: ignore[valid-type]
        default=0.015,
        min=0.01,
        max=0.1,
        step=1,
        name="nose height",
    )

    nose_width: FloatProperty(  # type: ignore[valid-type]
        default=0.5,
        min=0.01,
        max=1,
        name="nose width",
    )

    eye_depth: FloatProperty(  # type: ignore[valid-type]
        default=0.01,
        min=0.01,
        max=0.1,
        name="Eye depth",
    )

    eye_angle: FloatProperty(  # type: ignore[valid-type]
        default=radians(15),
        min=0,
        max=0.55,
        name="Eye angle",
    )

    eye_rotate: FloatProperty(  # type: ignore[valid-type]
        default=0.43,
        min=0,
        max=0.86,
        name="Eye rotation",
    )

    cheek_ratio: FloatProperty(  # type: ignore[valid-type]
        default=0.5,
        min=0,
        max=1,
        name="cheek position",
    )

    cheek_width: FloatProperty(  # type: ignore[valid-type]
        default=0.85,
        min=0.5,
        max=1,
        name="cheek width ratio",
    )

    mouth_width_ratio: FloatProperty(  # type: ignore[valid-type]
        default=0.5,
        min=0.3,
        max=0.9,
        name="Mouth width",
    )

    # 口角結節
    mouth_corner_nodule: FloatProperty(  # type: ignore[valid-type]
        default=0.1,
        min=0.01,
        max=1,
        name="oris width",
    )

    mouth_position_ratio: FloatProperty(  # type: ignore[valid-type]
        default=2 / 3,
        min=0.3,
        max=0.7,
        name="Mouth position",
    )

    mouth_flatten: FloatProperty(  # type: ignore[valid-type]
        default=0.1,
        min=0.0,
        max=1,
        name="Mouth flat",
    )

    @staticmethod
    def add_point(bm: BMesh, point: Sequence[float]) -> BMVert:
        return bm.verts.new(point)

    @staticmethod
    def make_circle(
        bm: BMesh,
        center: Sequence[float],
        radius: float,
        axis: str,
        divide: int,
        angle: int = 360,
        x_ratio: float = 1,
        y_ratio: float = 1,
    ) -> None:
        if axis == "X":
            axis_n = (0, 1)
        elif axis == "Y":
            axis_n = (1, 2)
        else:
            axis_n = (2, 0)
        if divide < 3:
            logger.error("Wrong divide set")
            divide = 3
        if angle == 0:
            logger.error("Wrong angle set")
            angle = 180
        verts: list[BMVert] = []
        for i in range(divide + 1):
            pi2 = 3.14 * 2 * radians(angle) / radians(360)
            vert = ICYP_OT_detail_mesh_maker.add_point(bm, center)
            xy = (sin(pi2 * i / divide) * y_ratio, cos(pi2 * i / divide) * x_ratio)
            for n, j in zip(axis_n, xy):
                vert.co[n] = vert.co[n] + j * radius
            verts.append(vert)

        bm.faces.new(verts)

    @staticmethod
    def width_add(point: Sequence[float], add_loc: float) -> Vector:
        return Vector([p + a for p, a in zip(point, [0, 0, add_loc])])

    @staticmethod
    def depth_add(point: Vector, add_loc: float) -> Vector:
        return Vector([p + a for p, a in zip(point, [add_loc, 0, 0])])
        # X depth Y up Z width

    @staticmethod
    def add_mesh(bm: BMesh, points: list[BMVert]) -> None:
        bm.faces.new(points)

    def make_face(self, _context: Context, mesh: Mesh) -> None:
        bm = bmesh.new()

        face_tall = self.head_tall_size * self.face_center_ratio

        self.add_point(bm, [-self.head_depth_size / 2, 0, 0])

        eye_point = Vector(
            [
                -self.eye_depth - self.head_depth_size / 2,
                face_tall / 2,
                self.head_width_size / 5,
            ]
        )

        eye_iris_size = eye_point[2] * self.eye_width_ratio * 0.25 / 2
        eye_width = eye_iris_size * 5 / 3

        eye_height = eye_iris_size * 0.9
        eye_axis = -self.eye_angle
        eye_quad_lu_point = eye_point + Matrix.Rotation(eye_axis, 4, "Y") @ Vector(
            [0, eye_height, -eye_iris_size]
        )
        eye_quad_ld_point = eye_point + Matrix.Rotation(eye_axis, 4, "Y") @ Vector(
            [0, -eye_height, -eye_iris_size]
        )
        eye_quad_rd_point = eye_point + Matrix.Rotation(eye_axis, 4, "Y") @ Vector(
            [0, -eye_height, eye_iris_size]
        )
        eye_quad_ru_point = eye_point + Matrix.Rotation(eye_axis, 4, "Y") @ Vector(
            [0, eye_height, eye_iris_size]
        )
        eye_inner_point = eye_point + Matrix.Rotation(
            -eye_axis, 4, "Y"
        ) @ Matrix.Rotation(self.eye_rotate, 4, "X") @ Vector(
            [0, -eye_height, -eye_width]
        )
        eye_outer_point = eye_point + Matrix.Rotation(
            eye_axis, 4, "Y"
        ) @ Matrix.Rotation(self.eye_rotate, 4, "X") @ Vector(
            [0, eye_height, eye_width]
        )
        if eye_inner_point[2] < self.head_width_size / 12:
            eye_inner_point[2] = self.head_width_size / 12
        eye_quad_lu_vert = self.add_point(bm, eye_quad_lu_point)
        eye_quad_ld_vert = self.add_point(bm, eye_quad_ld_point)
        eye_quad_rd_vert = self.add_point(bm, eye_quad_rd_point)
        eye_quad_ru_vert = self.add_point(bm, eye_quad_ru_point)
        eye_inner_vert = self.add_point(bm, eye_inner_point)
        eye_outer_vert = self.add_point(bm, eye_outer_point)

        bm.edges.new((eye_inner_vert, eye_quad_lu_vert))
        bm.edges.new((eye_quad_lu_vert, eye_quad_ru_vert))
        bm.edges.new((eye_quad_ru_vert, eye_outer_vert))
        bm.edges.new((eye_outer_vert, eye_quad_rd_vert))
        bm.edges.new((eye_quad_rd_vert, eye_quad_ld_vert))
        bm.edges.new((eye_quad_ld_vert, eye_inner_vert))

        self.make_circle(
            bm,
            self.depth_add(eye_point, eye_quad_ru_point[0] - eye_point[0]),
            eye_iris_size,
            "Y",
            12,
            360,
            1,
            1,
        )

        # 眉弓(でこの下ラインあたり)
        arcus_superciliaris_under_point = [
            -self.head_depth_size / 2,
            face_tall * 5 / 8,
            0,
        ]
        arcus_superciliaris_outer_under_point = [
            eye_point[0],
            face_tall * 5 / 8,
            eye_outer_point[2],
        ]

        arcus_superciliaris_under_vert = self.add_point(
            bm, arcus_superciliaris_under_point
        )
        arcus_superciliaris_outer_under_vert = self.add_point(
            bm, arcus_superciliaris_outer_under_point
        )

        # eye_brow_inner_point = self.width_add(
        #     eye_brow_point, eye_point[2] - eye_width * 1.1
        # )
        # eye_brow_outer_point = self.width_add(
        #     eye_brow_point, eye_point[2] + eye_width * 1.1
        # )
        # eye_brow_inner_vert = self.add_point(bm, eye_brow_inner_point)
        # eye_brow_outer_vert = self.add_point(bm, eye_brow_outer_point)
        # bm.edges.new([eye_brow_inner_vert, eye_brow_outer_vert])

        nose_head_height = (
            self.nose_head_height * eye_point[1]
            + (1 - self.nose_head_height) * eye_quad_rd_point[1]
        )
        nose_start_point = [
            -self.eye_depth / 2 - self.head_depth_size / 2,
            nose_head_height,
            0,
        ]
        nose_start_vert = self.add_point(bm, nose_start_point)
        nose_end_point = [self.nose_height - self.head_depth_size / 2, face_tall / 3, 0]
        nose_top_point = [
            self.nose_height - self.head_depth_size / 2,
            face_tall / 3 + self.nose_top_pos * (eye_point[1] - nose_end_point[1]),
            0,
        ]
        nose_top_vert = self.add_point(bm, nose_top_point)

        nose_end_side_point = self.depth_add(
            self.width_add(
                nose_end_point,
                max([eye_inner_point[2], self.head_width_size / 6]) * self.nose_width,
            ),
            -self.nose_height,
        )
        nose_end_side_vert = self.add_point(bm, nose_end_side_point)

        otogai_point = [-self.head_depth_size / 2, 0, 0]
        otogai_vert = self.add_point(bm, otogai_point)
        ear_hole_point = [0, eye_point[1], self.head_width_size / 2]
        ear_hole_vert = self.add_point(bm, ear_hole_point)

        # mouth_point = Vector([
        #     -self.head_depth_size / 2 + self.nose_height * 2 / 3,
        #     face_tall * 2 / 9,
        #     0,
        # ])
        mouth_point = Vector(
            [
                -self.head_depth_size / 2 + self.nose_height * 2 / 3,
                self.mouth_position_ratio * nose_top_point[1],
                0,
            ]
        )
        mouth_rotate_radian = atan2(self.nose_height, nose_top_point[1])
        rotated_height_up = Vector(
            Matrix.Rotation(-mouth_rotate_radian, 4, "Z")
            @ Vector(
                [
                    self.mouth_width_ratio * -0.01 * self.mouth_flatten,
                    self.mouth_width_ratio * 0.01,
                    0,
                ]
            )
        )
        rotated_height_down = Vector(
            Matrix.Rotation(-mouth_rotate_radian, 4, "Z")
            @ Vector(
                [
                    self.mouth_width_ratio * 0.01 * self.mouth_flatten,
                    self.mouth_width_ratio * 0.01 * 1.3,
                    0,
                ]
            )
        )
        rotated_height_mid_up = Vector(
            Matrix.Rotation(-mouth_rotate_radian, 4, "Z")
            @ Vector([0, self.mouth_width_ratio * 0.005 * self.mouth_flatten, 0])
        )
        rotated_height_mid_down = Vector(
            Matrix.Rotation(-mouth_rotate_radian, 4, "Z")
            @ Vector([0, self.mouth_width_ratio * 0.005 * 1.3 * self.mouth_flatten, 0])
        )

        mouth_point_up_vert = self.add_point(bm, mouth_point + rotated_height_up)
        mouth_point_mid_up_vert = self.add_point(
            bm, mouth_point + rotated_height_mid_up
        )
        mouth_point_mid_down_vert = self.add_point(
            bm, mouth_point - rotated_height_mid_down
        )
        mouth_point_down_vert = self.add_point(bm, mouth_point - rotated_height_down)
        mouth_outer_point = self.depth_add(
            self.width_add(
                mouth_point, self.mouth_width_ratio * self.head_width_size / 5
            ),
            (eye_point[0] - mouth_point[0]) * self.mouth_width_ratio,
        )
        mouth_outer_point_vert = self.add_point(bm, mouth_outer_point)
        mouth_center_point = self.depth_add(mouth_point, rotated_height_up[0] / 2)
        mouth_center_vert = self.add_point(bm, mouth_center_point)

        mouth_corner_nodule_point = (
            mouth_outer_point
            + (mouth_outer_point - mouth_point).normalized()
            * 0.2
            * self.mouth_corner_nodule
        )
        mouth_corner_nodule_vert = self.add_point(bm, mouth_corner_nodule_point)

        jaw_point = [0, mouth_point[1], self.head_width_size * 3 / 8]
        jaw_vert = self.add_point(bm, jaw_point)

        max_width_point = [
            0,
            arcus_superciliaris_under_point[1],
            self.head_width_size / 2,
        ]
        max_width_vert = self.add_point(bm, max_width_point)

        cheek_point = Vector(
            [
                -self.head_depth_size / 2,
                0,
                eye_inner_point[2] + (eye_quad_lu_point[2] - eye_inner_point[2]) / 2,
            ]
        )
        cheek_point[1] = min(
            [eye_quad_ld_point[1], (nose_top_point[1] + nose_start_point[1]) / 2]
        )
        cheek_point[1] = (
            cheek_point[1] - (cheek_point[1] - nose_top_point[1]) * self.cheek_ratio
        )
        tmp_cheek = Matrix.Rotation(eye_axis, 4, "Y") @ Vector(
            [
                0,
                0,
                (eye_outer_point[2] - eye_inner_point[2] * 2 / 3)
                * cos(eye_axis)
                * self.cheek_width,
            ]
        )
        cheek_top_outer_vert = self.add_point(bm, tmp_cheek + cheek_point)
        cheek_top_inner_vert = self.add_point(bm, cheek_point)
        cheek_under_inner_point = Vector(
            [
                -self.head_depth_size / 2,
                nose_top_point[1],
                eye_inner_point[2] + (eye_quad_lu_point[2] - eye_inner_point[2]) / 2,
            ]
        )
        cheek_under_outer_point = cheek_under_inner_point + tmp_cheek
        cheek_under_inner_vert = self.add_point(bm, cheek_under_inner_point)
        cheek_under_outer_vert = self.add_point(bm, cheek_under_outer_point)

        # 目尻の端っこからちょっといったとこ
        orbit_end = eye_outer_point + Matrix.Rotation(eye_axis, 4, "Y") @ Vector(
            [0, 0, eye_iris_size]
        ) * cos(eye_axis)
        orbit_vert = self.add_point(bm, orbit_end)

        bm.edges.new((otogai_vert, jaw_vert))
        bm.edges.new((jaw_vert, ear_hole_vert))

        self.add_mesh(
            bm,
            [
                eye_quad_ld_vert,
                cheek_top_inner_vert,
                cheek_top_outer_vert,
                eye_quad_rd_vert,
            ],
        )
        self.add_mesh(
            bm,
            [
                cheek_under_inner_vert,
                cheek_top_inner_vert,
                cheek_top_outer_vert,
                cheek_under_outer_vert,
            ],
        )
        # eye ring
        self.add_mesh(
            bm,
            [
                arcus_superciliaris_under_vert,
                arcus_superciliaris_outer_under_vert,
                eye_quad_ru_vert,
                eye_quad_lu_vert,
            ],
        )
        self.add_mesh(
            bm,
            [
                arcus_superciliaris_under_vert,
                eye_quad_lu_vert,
                eye_inner_vert,
                nose_start_vert,
            ],
        )
        self.add_mesh(bm, [nose_start_vert, eye_inner_vert, cheek_top_inner_vert])
        self.add_mesh(bm, [eye_inner_vert, eye_quad_ld_vert, cheek_top_inner_vert])
        self.add_mesh(
            bm, [eye_outer_vert, orbit_vert, cheek_top_outer_vert, eye_quad_rd_vert]
        )

        self.add_mesh(
            bm,
            [
                nose_start_vert,
                cheek_top_inner_vert,
                cheek_under_inner_vert,
                nose_end_side_vert,
            ],
        )
        self.add_mesh(
            bm,
            [
                nose_end_side_vert,
                cheek_under_inner_vert,
                mouth_corner_nodule_vert,
                mouth_outer_point_vert,
            ],
        )
        self.add_mesh(
            bm,
            [cheek_under_inner_vert, cheek_under_outer_vert, mouth_corner_nodule_vert],
        )

        self.add_mesh(bm, [cheek_under_outer_vert, jaw_vert, mouth_corner_nodule_vert])

        self.add_mesh(bm, [nose_start_vert, nose_top_vert, nose_end_side_vert])
        # self.add_mesh([nose_end_under_vert,nose_top_vert,nose_end_side_vert])
        self.add_mesh(
            bm,
            [
                nose_top_vert,
                nose_end_side_vert,
                mouth_outer_point_vert,
                mouth_point_up_vert,
            ],
        )

        self.add_mesh(
            bm, [mouth_point_up_vert, mouth_point_mid_up_vert, mouth_outer_point_vert]
        )
        self.add_mesh(
            bm, [mouth_point_mid_up_vert, mouth_center_vert, mouth_outer_point_vert]
        )
        self.add_mesh(
            bm, [mouth_center_vert, mouth_point_mid_down_vert, mouth_outer_point_vert]
        )
        self.add_mesh(
            bm,
            [mouth_point_mid_down_vert, mouth_point_down_vert, mouth_outer_point_vert],
        )

        self.add_mesh(
            bm,
            [
                eye_outer_vert,
                orbit_vert,
                arcus_superciliaris_outer_under_vert,
                eye_quad_ru_vert,
            ],
        )
        self.add_mesh(
            bm, [cheek_top_outer_vert, cheek_under_outer_vert, jaw_vert, ear_hole_vert]
        )
        self.add_mesh(bm, [otogai_vert, jaw_vert, mouth_corner_nodule_vert])
        self.add_mesh(
            bm,
            [
                otogai_vert,
                mouth_corner_nodule_vert,
                mouth_outer_point_vert,
                mouth_point_down_vert,
            ],
        )
        self.add_mesh(bm, [orbit_vert, ear_hole_vert, cheek_top_outer_vert])
        self.add_mesh(
            bm,
            [
                arcus_superciliaris_outer_under_vert,
                max_width_vert,
                ear_hole_vert,
                orbit_vert,
            ],
        )

        # head
        self.make_circle(
            bm,
            [0, max_width_point[1], 0],
            max_width_point[2],
            "Y",
            13,
            90,
            1,
            (self.head_tall_size - max_width_point[1]) / max_width_point[2],
        )
        self.make_circle(
            bm,
            [0, arcus_superciliaris_under_point[1], 0],
            self.head_tall_size - arcus_superciliaris_outer_under_point[1],
            "X",
            13,
            90,
            1,
            arcus_superciliaris_under_point[0]
            / (self.head_tall_size - arcus_superciliaris_outer_under_point[1]),
        )

        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()

    if TYPE_CHECKING:
        # This code is auto generated.
        # `poetry run python tools/property_typing.py`
        face_center_ratio: float  # type: ignore[no-redef]
        eye_width_ratio: float  # type: ignore[no-redef]
        nose_head_height: float  # type: ignore[no-redef]
        nose_top_pos: float  # type: ignore[no-redef]
        nose_height: float  # type: ignore[no-redef]
        nose_width: float  # type: ignore[no-redef]
        eye_depth: float  # type: ignore[no-redef]
        eye_angle: float  # type: ignore[no-redef]
        eye_rotate: float  # type: ignore[no-redef]
        cheek_ratio: float  # type: ignore[no-redef]
        cheek_width: float  # type: ignore[no-redef]
        mouth_width_ratio: float  # type: ignore[no-redef]
        mouth_corner_nodule: float  # type: ignore[no-redef]
        mouth_position_ratio: float  # type: ignore[no-redef]
        mouth_flatten: float  # type: ignore[no-redef]
