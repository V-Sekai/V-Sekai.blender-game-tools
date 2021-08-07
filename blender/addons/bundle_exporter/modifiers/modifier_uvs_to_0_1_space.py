import bpy
from collections import defaultdict
import math
from mathutils import Vector

from . import modifier


class BGE_mod_uvs_to_0_1_space(modifier.BGE_mod_default):
    label = "UVs to 0-1 space"
    id = 'uvs_to_0_1_space'
    type = 'MESH'
    icon = 'STICKY_UVS_LOC'
    tooltip = 'Moves all UV shells to the same 0-1 space'

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    uvset: bpy.props.EnumProperty(
        name="UV Set",
        items=[('ALL', 'All', 'All UV sets'), ('ACTIVE', 'Active', 'Active UV set')]
    )

    uv_coord: bpy.props.IntVectorProperty(
        name = 'UV origin',
        size = 2,
        #default = [0, 0]
    )

    def get_all_islands(self, obj, uv_layer):
        face_to_verts = defaultdict(set)
        vert_to_faces = defaultdict(set)
        
        for face in obj.data.polygons:
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                uv_coords = obj.data.uv_layers[uv_layer].data[loop_idx].uv
                combined_id = uv_coords.to_tuple(5), vert_idx
                
                face_to_verts[face.index].add(combined_id)
                vert_to_faces[combined_id].add(face.index)
                
                #print("face idx: %i, vert idx: %i, loop: %i uvs: %f, %f" % (face.index, vert_idx, loop_idx, uv_coords.x, uv_coords.y))

        islands = []
        faces_left = set(face_to_verts.keys())

        while len(faces_left) > 0:
            face_id = list(faces_left)[0]
            current_island = set()

            face_to_visit = [face_id]
            faces_left.remove(face_id)

            # BDF search of face
            while len(face_to_visit) > 0:
                current_island.add(face_id)
                cur_face = face_to_visit.pop(0)
                # and add all faces that share uvs with this face
                verts = face_to_verts[cur_face]
                # search for connected faces: faces that have same vertex index
                # and same uv
                for vert in verts:
                    connected_faces = vert_to_faces[vert]
                    for face in connected_faces:
                        current_island.add(face)
                        if face in faces_left:
                            face_to_visit.append(face)
                            faces_left.remove(face)
            # finally add the discovered island to the list of islands
            islands.append(current_island)
        return islands
    
    def _draw_info(self, layout):
        layout.prop(self, 'uvset')
        row = layout.row(align=True)
        row.prop(self, 'uv_coord')

    def process(self, bundle_info):
        meshes = bundle_info['meshes']

        x_coord = self.uv_coord[0]
        y_coord = self.uv_coord[1]

        for obj in meshes:
            uv_layers = []
            if self.uvset == 'ACTIVE' and obj.data.uv_layers.active:
                uv_layers.append(obj.data.uv_layers.active.name)
            elif self.uvset == 'ALL':
                uv_layers = [x.name for x in obj.data.uv_layers]
            
            for uv_layer in uv_layers:
                islands = self.get_all_islands(obj, uv_layer)

                for island in islands:
                    highest_x = -math.inf
                    highest_y = -math.inf
                    
                    for face in island:
                        for loop in obj.data.polygons[face].loop_indices:
                            uv_coords = obj.data.uv_layers[uv_layer].data[loop].uv
                            if uv_coords.x > highest_x:
                                highest_x = uv_coords.x
                            if uv_coords.y > highest_y:
                                highest_y = uv_coords.y
                    
                    x_offset = x_coord - math.floor(highest_x)
                    y_offset = y_coord - math.floor(highest_y)
                    
                    for face in island:
                        for loop in obj.data.polygons[face].loop_indices:
                            uv_coords = obj.data.uv_layers[uv_layer].data[loop].uv
                            obj.data.uv_layers[uv_layer].data[loop].uv = Vector((uv_coords.x + x_offset, uv_coords.y + y_offset))



