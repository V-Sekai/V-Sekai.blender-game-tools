from bpy.types import Context, Event, Object, Scene, Region, RegionView3D, SpaceView3D
from mathutils import Vector, Matrix
from bpy_extras import view3d_utils
import bmesh
from bmesh.types import BMesh, BMFace, BMEdge, BMVert
from mathutils.bvhtree import BVHTree

from typing import Union, Tuple
from math import dist

from ..utils.math import angle_between


class RaycastInfo:
    result: bool
    location: Vector
    normal: Vector
    index: int
    object: Object
    matrix: Matrix
    active_object: Object

    def update(self, context: Context, coord: Vector, target_object: Object = None):
        scene: Scene = context.scene
        region: Region = context.region
        rv3d: RegionView3D = context.region_data
        # viewlayer = context.view_layer

        if isinstance(coord, Event):
            coord = Vector((coord.mouse_region_x, coord.mouse_region_y))

        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)

        if target_object:
            result, location, normal, index = target_object.ray_cast(ray_origin, view_vector, depsgraph=context.evaluated_depsgraph_get())
            self.result = result
            self.location = location
            self.normal = normal
            self.index = index
            self.object = target_object
            self.matrix = target_object.matrix_world
        else:
            result, location, normal, index, object, matrix = scene.ray_cast(context.evaluated_depsgraph_get(), ray_origin, view_vector)
            self.result = result
            self.location = location
            self.normal = normal
            self.index = index
            self.object = object
            self.matrix = matrix

    @property
    def hit(self) -> bool:
        return self.result

    def get_face(self, context: Context, target_object: Object = None, from_eval: bool = True):
        if not self.result:
            return None
        if target_object is not None:
            self.object = target_object
        if len(self.object.modifiers) > 0 and from_eval:
            depsgraph = context.evaluated_depsgraph_get()
            eval_obj: Object = self.object.evaluated_get(depsgraph)
            return eval_obj.data.polygons[self.index]
        return target_object.data.polygons[self.index]

    def get_face_verts(self, context: Context, target_object: Object = None, from_eval: bool = True) -> list:
        if not self.result:
            return None
        if target_object is None:
            self.object = target_object
        if len(self.object.modifiers) > 0 and from_eval:
            depsgraph = context.evaluated_depsgraph_get()
            eval_obj: Object = self.object.evaluated_get(depsgraph)
            poly = eval_obj.data.polygons[self.index]
            vertices = eval_obj.data.vertices
        else:
            poly = target_object.data.polygons[self.index]
            vertices = target_object.data.vertices
        return [vertices[v_index] for v_index in poly.vertices]

    def get_material_index(self, context: Context, from_eval: bool = True):
        poly = self.get_poly(context, from_eval=from_eval)
        if poly is None:
            return None
        return poly.material_index



class BVHTreeRaycastInfo:
    bm: BMesh
    bvhtree: BVHTree

    result: bool
    location: Vector
    normal: Vector
    index: int
    distance: float
    mesh_uuid: int

    last_mouse_pos: Vector

    def __init__(self, context=None) -> None:
        self.result = False
        self.last_mouse_pos = Vector((0, 0))
        if context:
            self.bm = bmesh.from_edit_mesh(context.object.data)
            self.bm.select_mode = {'EDGE'}
            self.bvhtree = BVHTree.FromBMesh(self.bm)
            self.mesh_uuid = id(context.object.data)
        else:
            self.mesh_uuid = -1

    @property
    def hit(self) -> bool:
        return self.result and isinstance(self.index, int)

    def clear(self):
        if self.bm:
            self.bm.free()
        self.bm = None
        self.result = False
        self.index = -1

    def ensure(self, context):
        if self.bm is None or not self.bm.is_valid or\
           self.mesh_uuid != id(context.object.data):
            self.mesh_uuid = id(context.object.data)
            if self.bm is not None:
                self.bm.free()
            bm: BMesh = bmesh.from_edit_mesh(context.object.data)
            bm.edges.ensure_lookup_table()
            bm.edges.index_update()
            bm.faces.ensure_lookup_table()
            bm.faces.index_update()
            bm.select_mode = {'EDGE'}
            self.bvhtree = BVHTree.FromBMesh(bm)
            self.bm = bm
        return self.bm
    

    def raycast_bvhtree(self, context: Context, ray_origin: Vector, view_vector: Vector, ignore_back_faces: bool = False):
        self.result = False
        if res := self.bvhtree.ray_cast(ray_origin, view_vector):
            self.result = True
            self.location, self.normal, self.index, self.distance = res

            if self.index is None or not isinstance(self.index, int):
                # MISS-HIT.
                self.result = False
                self.index = -1

            else:
                if self.index >= len(self.bm.faces):
                    # Geometry has changed!
                    self.bm.free()
                    self.bm = None
                    self.ensure(context)
                    self.raycast_bvhtree(context, ray_origin, view_vector, ignore_back_faces=ignore_back_faces)
                    return 
                face = self.bm.faces[self.index]

                if ignore_back_faces:
                    angle = angle_between(face.normal, view_vector, as_degrees=True)
                    # print("ANGLE: ", angle)
                    if angle < 90:
                        self.result = False
                        self.index = -1
                        return

                if face.hide:
                    ray_origin = self.location + view_vector * 0.001 # 0.001 is the threshold to move the hit point
                    self.raycast_bvhtree(context, ray_origin, view_vector, ignore_back_faces=ignore_back_faces)


    def update(self, context: Context, event: Event, raycast_type: str = 'BVHTREE'):
        if context.region_data is None:
            return

        coord = Vector((event.mouse_region_x, event.mouse_region_y)) if isinstance(event, Event) else event
        self.ensure(context)

        if raycast_type == 'BVHTREE':
            space_view3d: SpaceView3D = context.space_data
            ignore_back_faces = space_view3d.shading.show_backface_culling
            
            mw = context.object.matrix_world
            loc, rot, sca = mw.decompose()
            mat_origin = Matrix.LocRotScale(Vector((0, 0, 0)), rot, sca)
            mwi = mat_origin.inverted()
            view_vector = mwi @ view3d_utils.region_2d_to_vector_3d(context.region, context.region_data, coord).normalized()
            ray_origin = mwi @ (view3d_utils.region_2d_to_origin_3d(context.region, context.region_data, coord) - loc)

            self.raycast_bvhtree(context, ray_origin, view_vector, ignore_back_faces=ignore_back_faces)

        else:
            # mw = context.object.matrix_world
            # mwi = mw.inverted()

            # src and dst in local space of cb
            # origin = mwi * src.matrix_world.translation
            # dest = mwi * dst.matrix_world.translation
            # direction = (dest - origin).normalized()

            # ray_origin = view3d_utils.region_2d_to_location_3d(context.region, context.region_data, coord, depth_location=)
            view_vector = view3d_utils.region_2d_to_vector_3d(context.region, context.region_data, coord).normalized()
            ray_origin = view3d_utils.region_2d_to_origin_3d(context.region, context.region_data, coord)

            self.distance = 0

            if raycast_type == 'OBJECT':
                eval_ob = context.object.evaluated_get(context.evaluated_depsgraph_get())
                self.result, self.location, self.normal, self.index = eval_ob.ray_cast(ray_origin, view_vector)

            elif raycast_type == 'SCENE':
                self.result, self.location, self.normal, self.index, object, matrix = context.scene.ray_cast(context.evaluated_depsgraph_get(), ray_origin, view_vector)

        # print(raycast_type, event, context.object)
        # print(list(ray_origin), list(view_vector.normalized()))
        # print(self.result, list(self.location), list(self.normal), self.index)
        self.last_mouse_pos = coord

    def get_face(self, context: Context) -> BMFace:
        if not self.hit or self.location is None:
            return None
        if not isinstance(self.index, int):
            return None
        self.ensure(context)
        if self.bm is None or not self.bm.is_valid:
            return None
        if self.index < 0 or self.index >= len(self.bm.faces):
            return None
        return self.bm.faces[self.index]

    def get_face_edges(self, context: Context) -> list[BMEdge]:
        if face := self.get_face(context):
            return face.edges
        return []

    def get_face_verts(self, context: Context) -> list[BMVert]:
        if face := self.get_face(context):
            return face.verts
        return []

    def get_closest_vert(self, context: Context, exclude_verts: set[BMVert] = set()) -> BMVert:
        min_distance = 100000000000
        nearest_vert = None
        for vert in self.get_face_verts(context):
            if vert in exclude_verts:
                continue
            d = dist(vert.co, self.location)
            if d < min_distance:
                min_distance = d
                nearest_vert = vert
        return nearest_vert

    def get_closest_edge(self, context: Context) -> BMEdge:
        min_distance = 100000000000
        nearest_edge = None
        for edge in self.get_face_edges(context):
            v1, v2 = edge.verts
            edge_length: float = edge.calc_length()
            edge_corner: float = edge_length * 0.01
            edge_center: Vector = (v2.co + v1.co) * 0.5
            edge_dir_v1: Vector = (v2.co - v1.co).normalized()
            edge_v1_off: Vector = v1.co + edge_dir_v1 * edge_corner
            edge_dir_v2: Vector = edge_dir_v1 * -1 # (v1.co - v2.co).normalized()
            edge_v2_off: Vector = v2.co + edge_dir_v2 * edge_corner
            nearest_point_dist = min([dist(p, self.location) for p in (edge_center, edge_v1_off, edge_v2_off)])
            if nearest_point_dist < min_distance:
                min_distance = nearest_point_dist
                nearest_edge = edge
        return nearest_edge

    def get_closer_geo_primitive(self, context, primitives: set[str] = {'EDGE', 'FACE'}) -> Tuple[Union[BMVert, BMEdge, BMFace], Vector]:
        if not self.hit:
            return None
        coords = {}
        if 'FACE' in primitives:
            face = self.get_face(context)
            if face is None:
                return None
            face_median: Vector = face.calc_center_median()
            coords[face] = face_median, dist(face_median, self.location)
        else:
            face = None
        if 'EDGE' in primitives:
            if face:
                edges = face.edges
            else:
                edges = self.get_face_edges(context)
            for edge in edges:
                v1, v2 = edge.verts
                edge_length: float = edge.calc_length()
                # edge_length_div4: float = edge_length / 4.0
                edge_corner: float = edge_length * 0.01
                edge_center: Vector = (v2.co + v1.co) * 0.5
                edge_dir_v1: Vector = (v2.co - v1.co).normalized()
                edge_v1_corner: Vector = v1.co + edge_dir_v1 * edge_corner
                edge_dir_v2: Vector = edge_dir_v1 * -1 # (v1.co - v2.co).normalized()
                edge_v2_corner: Vector = v2.co + edge_dir_v2 * edge_corner
                # edge_v1_halfhalf: Vector = v1.co + edge_dir_v1 * edge_length_div4
                # edge_v2_halfhalf: Vector = v2.co + edge_dir_v2 * edge_length_div4
                point_distances = [(p, dist(p, self.location)) for p in (edge_center, edge_v1_corner, edge_v2_corner)]
                coords[edge] = min(point_distances, key=lambda x: x[1])

        # UNUSED __________________
        # if 'VERT' in primitives:
        #     if face:
        #         verts = face.verts
        #     else:
        #         verts = self.get_face_verts(context)
        #     for v in verts:
        #         coords[v] = v.co
        #__________________________

        min_distance = 100000000000
        nearest_primitive = None
        for primitive, (co, d) in coords.items():
            # d = dist(co, self.location)
            if d < min_distance:
                min_distance = d
                nearest_primitive = primitive
        return nearest_primitive, co
