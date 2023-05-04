import bpy
import bmesh
from mathutils.geometry import barycentric_transform, intersect_point_tri_2d
from mathutils import Vector, Euler
from math import radians, floor, ceil, sqrt, acos, degrees
import numpy as np
import mathutils
from . props import MeshMaterializerCustomObjectProperty

MESH_SUFFIX = " Mesh Mat"

def process_materials(pattern_obj, me_new, bm_temp):
    #add any materials from the source objects to the generated object if they do not exist there already.
    #also material ids on the bmesh to map to any new material ids.
    material_map = {}
    source_object_material_count = len(pattern_obj.data.materials)
    remove_mat = False

    # assign a default material if there was none on the source object.
    if source_object_material_count == 0:
        pattern_obj.data.materials.append(get_default_material())
        remove_mat = True
        source_object_material_count+=1
    
    # Go through the source object materials, see if they are already there, if not create a mapping of old
    # material ids to potentially new ones.
    for i in range(0, source_object_material_count):
        material = pattern_obj.data.materials[i]
        found_mat = False
        for c in range(0, len(me_new.materials)):            
            existing_material = me_new.materials[c]
            if material.name == existing_material.name:
                # material already exists - get slot number
                material_map[i] = c
                found_mat = True
                break
        if not found_mat:
            me_new.materials.append(material)
            material_map[i] = len(me_new.materials) - 1
            
    # assign any new transformed material id mappings.
    for f in bm_temp.faces:
            f.material_index = material_map[f.material_index]

    # Remove the generic material from the original source object to keep it tidy.
    if (remove_mat):
        pattern_obj.data.materials.pop(index=0)

def translate(value, leftMin, leftSpan, rightMin, rightSpan):
    """Translate a given value from the left hand range to the right hand range. min is the minimum possible value, span is the range."""

    # Convert the left range into a 0-1 range (float)
    if leftSpan != 0:
        valueScaled = float(value - leftMin) / float(leftSpan)
    else:
        return 0

    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)

def calc_normal(point, face):
    """Calculate the required normal for a point on a triangular face using barycentric transformation."""

    first_loop = face.loops[0]
    all_loops = [first_loop]
    loop = first_loop.link_loop_next
    while loop != first_loop:
        all_loops.append(loop)
        loop = loop.link_loop_next

    v0, v1, v2 = [loop.vert for loop in all_loops]

    return barycentric_transform(point, v0.co, v1.co, v2.co, v0.normal, v1.normal, v2.normal)

def find_coord(loc, u, v, w, face):
    """Find the coordinate on a triangular face from supplied UV coordinates."""

    first_loop = face.loops[0]
    all_loops = [first_loop]
    loop = first_loop.link_loop_next
    while loop != first_loop:
        all_loops.append(loop)
        loop = loop.link_loop_next


    x, y, z = [loop.vert.co for loop in all_loops]
    co = barycentric_transform(loc, u, v, w, x, y, z)
    return co

def get_or_create_layer(layer, key):
    """Either create a new BMesh layer of a given object, or return the existing one of the same name."""
    if key in layer:
        return layer[key]
    else:
        return layer.new(key)

default_mat_name = "Mesh Materializer Default"
def get_default_material():
    """Get a default material as a singleton."""
    if default_mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=default_mat_name)
    else:
        mat = bpy.data.materials.get(default_mat_name)
    return mat

def get_or_create_obj(context, target_object):
    """Either get an existing mesh material object or create a new one."""
    new_obj_name = target_object.name + MESH_SUFFIX
    
    if new_obj_name in context.scene.objects:
        ob_new = context.scene.objects[new_obj_name]
        me_new = ob_new.data
        is_new_obj = False
    else:
        # create a new object based on the target object that was selected.
        ob_new = target_object.copy()
        # Remove any modifiers as we don't want them on the new object.
        for modifier in ob_new.modifiers:
            ob_new.modifiers.remove(modifier)
        ob_new.select_set(False)
        ob_new.name = new_obj_name
        ob_new.data = bpy.data.meshes.new(new_obj_name)

        me_new = ob_new.data
        is_new_obj = True
    return ob_new, me_new, is_new_obj

def finish_mesh(context, ob_new, is_new_obj, add_edge_split=True):
    """Complete the creation of a Mesh Material object."""
    if is_new_obj:        
        # Add object to a collection.
        if context.active_object.users_collection is not None and len(context.active_object.users_collection) > 0:
            context.active_object.users_collection[0].objects.link(ob_new)
        else:
            context.scene.collection.objects.link(ob_new)

    if add_edge_split:
        # add a split modifier to help presentation.
        modifier = ob_new.modifiers.get('Edge Split')
        if modifier is None:
            ob_new.modifiers.new('Edge Split', 'EDGE_SPLIT')
    else:
        modifier = ob_new.modifiers.get('Edge Split')
        if modifier is not None:
            ob_new.modifiers.remove(modifier)

    # deselect the object.
    ob_new.select_set(False)

def dissolve_cuts(context, 
                    bm_new, 
                    dissolve_edges=True, 
                    use_verts=True, 
                    use_face_split_edge=False,
                    dissolve_verts=True, 
                    use_face_split_vert=True,
                    use_boundary_tear=False):
    if dissolve_edges or dissolve_verts:
        cut_verts_layer = get_or_create_layer(bm_new.verts.layers.int, 'cut_verts_layer')
        cut_edges_layer = get_or_create_layer(bm_new.edges.layers.int, 'cut_edges_layer')

        edges_to_dissolve = [e for e in bm_new.edges if e[cut_edges_layer] and e.is_boundary == False]
        verts_to_dissolve = []
        for e in edges_to_dissolve:
            for v in e.verts:
                verts_to_dissolve.append(v)
        verts_to_dissolve = list(set(verts_to_dissolve))

        if dissolve_edges:        
            bmesh.ops.dissolve_edges(bm_new, edges = edges_to_dissolve, use_verts = use_verts, use_face_split=use_face_split_edge)

        if dissolve_verts:
            bmesh.ops.dissolve_verts(bm_new, verts = [v for v in verts_to_dissolve if v.is_valid], use_boundary_tear=use_boundary_tear, use_face_split = use_face_split_vert)

def remove_doubles_for_cuts(bm_new, 
                            cut_verts_remove_doubles=True, 
                            cut_verts_remove_doubles_amount=0.0001, 
                            not_cut_verts_remove_doubles=True, 
                            not_cut_verts_remove_doubles_amount=0.0001):
    # For all the vertices close to some original geometry, make sure they are merged with the right flag (ie, marking it as original).
    
    cut_verts_layer = get_or_create_layer(bm_new.verts.layers.int, 'cut_verts_layer')
    cut_edges_layer = get_or_create_layer(bm_new.edges.layers.int, 'cut_edges_layer')
    if cut_verts_remove_doubles:
        cut_verts = [v for v in bm_new.verts if v[cut_verts_layer] == 1]
        bmesh.ops.remove_doubles(bm_new, verts=cut_verts, dist=cut_verts_remove_doubles_amount)

    if not_cut_verts_remove_doubles:
        not_cut_verts = [v for v in bm_new.verts if v[cut_verts_layer] == 0 ]
        bmesh.ops.remove_doubles(bm_new, verts=not_cut_verts, dist=not_cut_verts_remove_doubles_amount)

def fill_holes(bm_new):
    bmesh.ops.holes_fill(bm_new, edges=[e for e in bm_new.edges if e.is_boundary])

def remove_cut_objects(bm_new):
    cut_verts_layer = get_or_create_layer(bm_new.verts.layers.int, 'cut_verts_layer')
    cut_edges_layer = get_or_create_layer(bm_new.edges.layers.int, 'cut_edges_layer')
    object_prop_id_layer = get_or_create_layer(bm_new.verts.layers.int, 'object_prop_id_layer')
    current_x_layer = get_or_create_layer(bm_new.verts.layers.float, 'current_x_layer')
    current_y_layer = get_or_create_layer(bm_new.verts.layers.float, 'current_y_layer')

    edges_to_look_at = [e for e in bm_new.edges if e[cut_edges_layer] and e.is_boundary == True]

    # for each edge boundary, locate the object key and delete the geomerty from the mesh.
    geom_to_delete = []
    for e in edges_to_look_at:
        if e.is_valid:
            faces_to_delete = []
            edges_to_delete = []
            verts_to_delete = []

            # get key.
            vertA = e.verts[0]
            prop_id = vertA[object_prop_id_layer]
            current_x = vertA[current_x_layer]
            current_y = vertA[current_y_layer]

            # then go through the whole mesh and find things to delete.

            for v in bm_new.verts:
                test_prop_id = v[object_prop_id_layer]
                test_current_x = v[current_x_layer]
                test_current_y = v[current_y_layer]
                if (prop_id == test_prop_id and current_x == test_current_x and current_y == test_current_y):
                    v.select_set(True)
                    verts_to_delete.append(v)
                    edges_to_delete.extend(v.link_edges)
                    faces_to_delete.extend(v.link_faces)
            geom = []
            geom.extend(list(set(verts_to_delete)))
            geom.extend(list(set(edges_to_delete)))
            geom.extend(list(set(faces_to_delete)))
            bmesh.ops.delete(bm_new, geom = geom, context="FACES")

        

def delete_mesh_material(context,
                            bm_target,
                            target_faces,
                            me_new):
    """Internal function for deleting elements of th eMesh MAterial given a set of target faces."""
    bm_new = bmesh.new()
    try:
        bm_new.from_mesh(me_new)

        old_face_id_to_del_layer = get_or_create_layer(bm_new.faces.layers.int, 'face_id_to_del_layer')

        # iterate through and mark faces for deletion.
        bm_new.faces.ensure_lookup_table()
        for f in bm_target.faces:
            f.tag = False
        for f in target_faces:
            f.tag = True

        faces_to_delete = []
        for f_t in [f for f in bm_target.faces if f.tag]:

            # delete any previous geometry.
            
            for f in bm_new.faces:
                if f[old_face_id_to_del_layer] == f_t.index:
                    faces_to_delete.append(f)
        
        bmesh.ops.delete(bm_new, geom=faces_to_delete, context='FACES')  

        bm_new.to_mesh(me_new)
    finally:
        bm_new.free()

class MeshMaterializer:
    """The main Mesh Materializer processor"""

    # Euler rotations use to rotate vectors for slicing.
    eul_clock = Euler((0.0, 0.0, radians(90.0)), 'XYZ')
    eul_anticlock = Euler((0.0, 0.0, radians(-90.0)), 'XYZ')

    def __init__(self,
                    context,
                    source_objects_props, 
                    general_props):
        # initialise general properties.
        self.general_props = general_props

        # Check if source objects were set as we can't do anything without them.
        if len([sop for sop in source_objects_props if sop.is_enabled]) == 0:
            raise Exception('No source objects found.')

        # work out the width/height UV intervals for mapping meshes.
        self.interval_x = 1 / self.general_props.across
        self.interval_y = 1 / self.general_props.down
        self.half_interval_x = self.interval_x / 2

        # set up source object properties ready for processing.
        self.source_object_prop_lookup = {}
        i = 0
        for source_objects_prop in source_objects_props:
            if not source_objects_prop.is_enabled:
                continue

            # A pattern object for creating a mesh material object.
            pattern_obj = context.scene.objects[source_objects_prop.name]

            # create a cache of bmeshes to call upon so we do not create it every time.
            new_bm_temp = bmesh.new()
            new_bm_temp.from_object(pattern_obj, depsgraph=context.evaluated_depsgraph_get(), face_normals=True)

            # delete relevant custom layers from the bmesh object - there seems to be a bug where the properties are not carried over correctly.
            for key in new_bm_temp.faces.layers.int.keys():
                layer = new_bm_temp.faces.layers.int.get(key)
                new_bm_temp.faces.layers.int.remove(layer)

            for key in new_bm_temp.verts.layers.string.keys():
                layer = new_bm_temp.verts.layers.string.get(key)
                new_bm_temp.verts.layers.string.remove(layer)

            for key in new_bm_temp.verts.layers.float.keys():
                layer = new_bm_temp.verts.layers.float.get(key)
                new_bm_temp.verts.layers.float.remove(layer)

            for key in new_bm_temp.verts.layers.int.keys():
                layer = new_bm_temp.verts.layers.int.get(key)
                new_bm_temp.verts.layers.int.remove(layer)

            for key in new_bm_temp.edges.layers.int.keys():
                layer = new_bm_temp.edges.layers.int.get(key)
                new_bm_temp.edges.layers.int.remove(layer)

            # create a layer for holding the object name on a vertex for reference.
            object_prop_id_layer = get_or_create_layer(new_bm_temp.verts.layers.int, 'object_prop_id_layer')
            
            original_verts_layer = get_or_create_layer(new_bm_temp.verts.layers.int, 'original_verts_layer')
            original_edges_layer = get_or_create_layer(new_bm_temp.edges.layers.int, 'original_edges_layer')    

            cut_verts_layer = get_or_create_layer(new_bm_temp.verts.layers.int, 'cut_verts_layer')
            cut_edges_layer = get_or_create_layer(new_bm_temp.edges.layers.int, 'cut_edges_layer')

            # Properties for normalising the object coordinates ready for mapping to the main object.
            for v_test in new_bm_temp.verts:
                v_test[object_prop_id_layer] = i
                v_test[original_verts_layer] = 1
                v_test[cut_verts_layer] = 0

            for v_edge in new_bm_temp.edges:
                v_edge[original_edges_layer] = 1
                v_edge[cut_edges_layer] = 0

            # Create a new set of object properties for reference during processing.
            self.source_object_prop_lookup[i] = MeshMaterializerCustomObjectProperty(
                                                                        source_objects_prop,
                                                                        new_bm_temp
                                                                        )
            i+=1

    def floor_x(self, x):
        """Find the minimum most interval point given known intervals."""
        return floor(x / self.interval_x) * self.interval_x

    def floor_y(self, y):
        """Find the minimum most interval point given known intervals."""
        return floor(y / self.interval_y) * self.interval_y

    def delete_mesh_material(self,
                                context,
                                target_object,
                                bm_target,
                                target_faces):
        """Remove the mesh material for a given set of target faces."""
        try:
            ob_new, me_new, is_new_obj = get_or_create_obj(context, target_object)
            delete_mesh_material(context,
                                        bm_target,
                                        target_faces=target_faces,
                                        me_new=me_new
                                        )
            finish_mesh(context, ob_new, is_new_obj, add_edge_split=context.scene.mesh_mat_add_edge_split)
            
        except Exception as ex:
            if ('ob_new' in locals() or 'ob_new' in globals()) and is_new_obj:
                bpy.data.objects.remove(ob_new)
            if ('me_new' in locals() or 'me_new' in globals()) and is_new_obj:
                bpy.data.meshes.remove(me_new)
            raise ex

    def generate_mesh_material(self,
                                context,
                                target_object,
                                bm_target,
                                target_faces,
                                random_seed):
        """Add a mesh material object given the target object we are working on and a set of source objects."""
        try:
            ob_new, me_new, is_new_obj = get_or_create_obj(context, target_object)
            self._generate_mesh_material(
                                        context,
                                        bm_target,
                                        target_faces=target_faces,
                                        me_new=me_new,
                                        random_seed=random_seed
                                        )
            finish_mesh(context, ob_new, is_new_obj, add_edge_split=context.scene.mesh_mat_add_edge_split)

        except Exception as ex:
            if ('ob_new' in locals() or 'ob_new' in globals()) and is_new_obj:
                bpy.data.objects.remove(ob_new)
            if ('me_new' in locals() or 'me_new' in globals()) and is_new_obj:
                bpy.data.meshes.remove(me_new)
            raise ex

        

    def _generate_mesh_material(self,
                                context,
                                bm_target,
                                target_faces,
                                me_new,
                                random_seed):
        """Internal function for creating the Mesh Material  given a target object and a set of source objects."""

        # We cannot proceed without any faces selected.
        if len(target_faces) == 0:
            raise Exception('No faces identified on target object.')

        # Create a new bmesh for the result and populate with the new mesh, which may already have been created and populated.
        bm_new = bmesh.new()

        # Generate an object cache which randomly selects and stores source objects for processing based on locations in the UV Map.
        obj_cache = {}
        try:
            bm_new.from_mesh(me_new)

            # Get/Create a layer that marks faces for deletion.
            old_face_id_to_del_layer = get_or_create_layer(bm_new.faces.layers.int, 'face_id_to_del_layer')

            # tag relevant target faces for processing.
            for f in bm_target.faces:
                f.tag = False
            for f in target_faces:
                f.tag = True

            def get_object_prop_bm_in_cache(current_x, current_y, offset_vec=Vector((0,0,0))):
                """Return an object given an X and a Y coordinate in UV space."""
                if (current_x, current_y) in obj_cache:
                    return obj_cache[(current_x, current_y)]
                else:
                    # Select an object based on a unique set of seed values (position in UV space)
                    first_seed_temp = int(round(current_x / self.interval_x))
                    first_seed = abs(first_seed_temp)
                    first_seed_sign = first_seed_temp > 0
                    
                    second_seed_temp = int(round(current_y / self.interval_y))
                    second_seed = abs(second_seed_temp)
                    second_seed_sign = second_seed_temp > 0
                    
                    seeds = [random_seed, first_seed, first_seed_sign, second_seed, second_seed_sign]
                    
                    random = np.random.RandomState(seeds)

                    prop_key = random.choice([key for key in self.source_object_prop_lookup])

                    prop = self.source_object_prop_lookup[prop_key]

                    # create a bmesh from the cache.
                    bm_temp = prop.bm_cached.copy()

                    current_x_layer = get_or_create_layer(bm_temp.verts.layers.float, 'current_x_layer')
                    current_y_layer = get_or_create_layer(bm_temp.verts.layers.float, 'current_y_layer')

                    # Get appropriate scaling parameters.
                    if prop.use_custom_parameters:
                        maintain_proportions = prop.maintain_proportions
                        obj_pos = prop.obj_pos
                        if not prop.randomize_parameters:
                            location = prop.location
                            scale_x = prop.scale_x
                            scale_y = prop.scale_y
                            scale_z = prop.scale_z
                            rotate = prop.rotate
                        else:
                            randomize_parameters_seed = prop.randomize_parameters_seed
                            seeds = [randomize_parameters_seed, first_seed, first_seed_sign, second_seed, second_seed_sign]
                            random_params = np.random.RandomState(seeds)
                            # location = prop.location
                            location = Vector(random_params.uniform(prop.location - prop.location_rand, prop.location + prop.location_rand))
                            scale_x = random_params.uniform(prop.scale_x - prop.scale_x_rand, prop.scale_x + prop.scale_x_rand)
                            scale_y = random_params.uniform(prop.scale_y - prop.scale_y_rand, prop.scale_y + prop.scale_y_rand)
                            scale_z = random_params.uniform(prop.scale_z - prop.scale_z_rand, prop.scale_z + prop.scale_z_rand)
                            rotate = Vector(random_params.uniform(Vector(prop.rotate) - Vector(prop.rotate_rand), Vector(prop.rotate) + Vector(prop.rotate_rand)))
                    else:
                        maintain_proportions = self.general_props.maintain_proportions
                        obj_pos = self.general_props.obj_pos
                        if not self.general_props.randomize_parameters:
                            location = self.general_props.location
                            scale_x = self.general_props.scale_x
                            scale_y = self.general_props.scale_y
                            scale_z = self.general_props.scale_z
                            rotate = self.general_props.rotate
                        else:
                            randomize_parameters_seed = self.general_props.randomize_parameters_seed
                            seeds = [randomize_parameters_seed, first_seed, first_seed_sign, second_seed, second_seed_sign]
                            random_params = np.random.RandomState(seeds)
                            location = Vector(random_params.uniform(self.general_props.location - self.general_props.location_rand, self.general_props.location + self.general_props.location_rand))
                            scale_x = random_params.uniform(self.general_props.scale_x - self.general_props.scale_x_rand, self.general_props.scale_x + self.general_props.scale_x_rand)
                            scale_y = random_params.uniform(self.general_props.scale_y - self.general_props.scale_y_rand, self.general_props.scale_y + self.general_props.scale_y_rand)
                            scale_z = random_params.uniform(self.general_props.scale_z - self.general_props.scale_z_rand, self.general_props.scale_z + self.general_props.scale_z_rand)
                            rotate = Vector(random_params.uniform(Vector(self.general_props.rotate) - Vector(self.general_props.rotate_rand), Vector(self.general_props.rotate) + Vector(self.general_props.rotate_rand)))
                            


                    # Get relative z dimension of object
                    dim = bpy.data.objects.get(prop.name).dimensions
                    total_dim = (dim.x + dim.y + dim.z)
                    maximal = max(dim)
                    rel_maximal = maximal / total_dim
                    multiplier = 1 / rel_maximal

                    if maintain_proportions:
                        rel_x = dim.x / total_dim
                        rel_x = rel_x * multiplier
                        rel_y = dim.y / total_dim
                        rel_y = rel_y * multiplier
                        rel_z = dim.z / total_dim
                        rel_z = rel_z * multiplier
                    else:
                        rel_x = 1
                        rel_y = 1
                        rel_z = 1


                    z_offset_scale = ((self.interval_x + self.interval_y) / 2)
                    scale_z_calc = z_offset_scale * scale_z * rel_z

                    # determing the UV range for transformation.
                    rightSpan_x = self.interval_x * scale_x * rel_x
                    rightSpan_y = self.interval_y * scale_y * rel_y

                    current_x_start = current_x + ((self.interval_x - rightSpan_x) / 2)
                    current_y_start = current_y + ((self.interval_y - rightSpan_y) / 2)




                    # Properties for normalising the object coordinates ready for mapping to the main object.
                    all_x_verts = []
                    all_y_verts = []
                    all_z_verts = []

                    for v_test in bm_temp.verts:
                        all_x_verts.append(v_test.co.x)
                        all_y_verts.append(v_test.co.y)
                        all_z_verts.append(v_test.co.z)
                    
                    min_x_tmp = min( all_x_verts  ) 
                    min_y_tmp = min( all_y_verts ) 
                    min_z_tmp = min( all_z_verts )
                    
                    max_x_tmp = max( all_x_verts ) 
                    max_y_tmp = max( all_y_verts ) 
                    max_z_tmp = max( all_z_verts )
                    
                    leftSpan_x = max_x_tmp - min_x_tmp
                    leftSpan_y = max_y_tmp - min_y_tmp
                    leftSpan_z = max_z_tmp - min_z_tmp

                    if obj_pos == 0:
                        # top
                        current_z_start = 0
                        rightSpan_z = scale_z_calc
                    elif obj_pos == 1:
                        #middle
                        current_z_start = -(scale_z_calc / 2)
                        rightSpan_z = scale_z_calc
                    elif obj_pos == 2:
                        # bottom
                        current_z_start = -scale_z_calc
                        rightSpan_z = scale_z_calc


                    # create a UV later for caching what interval the vertex was on so that we can retrieve source object settings layer.
                    vcos = []
                    for v_tmp in bm_temp.verts:
                        v_tmp[current_x_layer] = current_x
                        v_tmp[current_y_layer] = current_y
                        v_tmp.co.x = translate(v_tmp.co.x, min_x_tmp, leftSpan_x, current_x_start, rightSpan_x)
                        v_tmp.co.y = translate(v_tmp.co.y, min_y_tmp, leftSpan_y, current_y_start, rightSpan_y)
                        v_tmp.co.z = translate(v_tmp.co.z, min_z_tmp, leftSpan_z, current_z_start, rightSpan_z)
                        v_tmp.co = v_tmp.co + (location * z_offset_scale) + offset_vec
                        vcos.append(v_tmp.co)


                    # apply a rotation
                    findCenter = lambda l: ( max(l) + min(l) ) / 2

                    x,y,z  = [ [ v[i] for v in vcos ] for i in range(3) ]
                    cent = [ findCenter(axis) for axis in [x,y,z] ]

                    rot_mat = mathutils.Matrix.Rotation(rotate.x, 4, 'X')
                    bmesh.ops.rotate(bm_temp, cent = cent, verts = bm_temp.verts,matrix = rot_mat)
                    rot_mat = mathutils.Matrix.Rotation(rotate.y, 4, 'Y')
                    bmesh.ops.rotate(bm_temp, cent = cent, verts = bm_temp.verts,matrix = rot_mat)
                    rot_mat = mathutils.Matrix.Rotation(rotate.z, 4, 'Z')
                    bmesh.ops.rotate(bm_temp, cent = cent, verts = bm_temp.verts,matrix = rot_mat)


                    pattern_obj = context.scene.objects[prop.name]

                    # create a temporary mesh object before we combine meshes into the bigger pattern.
                    me_temp = bpy.data.meshes.new("me_temp")
                    
                    process_materials(pattern_obj, me_new, bm_temp)
                    
                    # populate the bmesh information to a mesh object ready for processing.
                    bm_temp.to_mesh(me_temp)
                    bm_temp.free()

                    # place this in the cache for future reference.
                    cached_val = (prop_key, me_temp)
                    obj_cache[(current_x, current_y)] = cached_val

                    return cached_val
                    
                            
            # a list of all meshes to be collated into the generated object.
            # all_meshes = []

            # Get the target object's active UV layer.
            uv_layer_target = bm_target.loops.layers.uv.verify()

            # Create a triangulated version of the target mesh to do some more targeted slicing on.
            bm_triangulated_temp = bm_target.copy()

            # make a layer to hold the original face ids before triangulation to map to the orignal object.
            face_id_layer = get_or_create_layer(bm_triangulated_temp.faces.layers.int, 'face_id_layer')
            for f in bm_triangulated_temp.faces:
                f[face_id_layer] = f.index

            # triangulate this bmesh.
            result_bm_triangulated_temp = bmesh.ops.triangulate(bm_triangulated_temp, faces=[f for f in bm_triangulated_temp.faces if f.tag], quad_method='FIXED', ngon_method='EAR_CLIP')

            # create a cache of original face indexes to the triangulated faces for slicing and coordinate calculation.
            triangulation_cache = {}
            for f in result_bm_triangulated_temp['faces']:
                original_index = f[face_id_layer]
                if original_index not in triangulation_cache:
                    triangulation_cache[original_index] = [f]
                else:
                    triangulation_cache[original_index].append(f)

            # get the UVs of the triangulated target mesh.
            uv_layer_tri_temp = bm_triangulated_temp.loops.layers.uv[uv_layer_target.name]

            # The main loop - Go through each tagged face and create/slice up the right objects for that face.

            bm_potential = bmesh.new()
            # delete any previous generated geometry for this face.
            faces_to_delete = []
            for main_face in [f for f in bm_target.faces if f.tag]:

                # depending on the desired approach, we will either slice the main face or use triangles for calculating the slices.
                if context.scene.mesh_mat_approach == '0':
                    faces_to_slice = [main_face]
                elif context.scene.mesh_mat_approach == '1':
                    faces_to_slice = triangulation_cache[main_face.index]
                    uv_layer_target = uv_layer_tri_temp
                    
                
                # go through each face, get assigned objects, and slice n dice them....
                for f_t in faces_to_slice:
                    #register for deletion of old faces
                    for f in bm_new.faces:
                        if f[old_face_id_to_del_layer] == f_t.index:
                            faces_to_delete.append(f)

                    # Get the list of UVs for the face.
                    uv_list = [l[uv_layer_target].uv.to_3d() for l in f_t.loops]
                    
                    # Determing the direction of the faces so we know which way the vectors need to be for slicing.
                    sum_edges = 0
                    # Only loop 3 verts ignore others: faster!
                    for i in range(3):
                        uv_A = f_t.loops[i][uv_layer_target].uv
                        uv_B = f_t.loops[(i+1)%3][uv_layer_target].uv
                        sum_edges += (uv_B.x - uv_A.x) * (uv_B.y + uv_A.y)
                    
                    # was the direction clockwise or anti clockwise?  This will determine the direction we rotate vectors ready for slicing.
                    direction = sum_edges > 0
                    eul = self.eul_clock
                    if direction:
                        eul = self.eul_anticlock
                        
                    # find the min and max points for the supplied UVs so we can determine the range of selection of source objects.
                    uv_min_x = min( [co.x for co in uv_list ] )
                    uv_min_y = min( [co.y for co in uv_list ] )
                    uv_max_x = max( [co.x for co in uv_list ] )
                    uv_max_y = max( [co.y for co in uv_list ] )

                    # snap the minimum points to the intervals of the mesh pattern so we can select objects at the right positions in UV space.
                    current_x = self.floor_x(uv_min_x)
                    x_min_intervals = []
                    while current_x <= uv_max_x:
                        x_min_intervals.append(current_x)
                        current_x += self.interval_x
                    
                    current_y = self.floor_y(uv_min_y)
                    y_min_intervals = []
                    while current_y <= uv_max_y:
                        y_min_intervals.append(current_y)
                        current_y += self.interval_y

                    # retrieve and assemble the pattern.
                    
                    try:
                        verts_map = {}
                        all_greeble_meshes = []


                            

                        # Go through this section of the UV map and select the right objects and position them in UV space, ready for slicing around the face edges.
                        if context.scene.mesh_mat_pattern_type == '0':
                            # Checker Pattern
                            for current_y in y_min_intervals:
                                for current_x in x_min_intervals:
                                    # get the right object based on the interval.
                                    obj_prop_key, me_temp = get_object_prop_bm_in_cache(current_x, current_y)
                                    bm_potential.from_mesh(me_temp) 
                        elif context.scene.mesh_mat_pattern_type == '1':
                            # Brick Pattern
                            for current_y in y_min_intervals:
                                if (int(round(current_y / self.interval_y)) % 2):
                                    for current_x in x_min_intervals:
                                        # get the right object based on the interval.
                                        obj_prop_key, me_temp = get_object_prop_bm_in_cache(current_x, current_y)
                                        bm_potential.from_mesh(me_temp)
                                else:
                                    offset_x_brick = self.half_interval_x
                                    obj_prop_key, me_temp = get_object_prop_bm_in_cache(x_min_intervals[0] - self.interval_x, current_y, Vector((offset_x_brick,0,0)) )
                                    bm_potential.from_mesh(me_temp)
                                    for current_x in x_min_intervals:
                                        offset_x_brick = self.half_interval_x
                                        obj_prop_key, me_temp = get_object_prop_bm_in_cache(current_x, current_y, Vector((offset_x_brick,0,0)) )
                                        bm_potential.from_mesh(me_temp)

                        # if we got some geometry to process, slice it and also ready it for positioning around the target mesh.
                        if len(bm_potential.verts) > 0:


                            # get or create the layer for retrieving object names.
                            object_prop_id_layer = bm_potential.verts.layers.int['object_prop_id_layer']

                            original_verts_layer = get_or_create_layer(bm_potential.verts.layers.int, 'original_verts_layer')
                            original_edges_layer = get_or_create_layer(bm_potential.edges.layers.int, 'original_edges_layer')

                            cut_verts_layer = get_or_create_layer(bm_potential.verts.layers.int, 'cut_verts_layer')
                            cut_edges_layer = get_or_create_layer(bm_potential.edges.layers.int, 'cut_edges_layer')

                            # get the face layer for marking faces for deletion for future operations.
                            face_id_to_del_layer = get_or_create_layer(bm_potential.faces.layers.int, 'face_id_to_del_layer')
                            to_merge_layer = get_or_create_layer(bm_potential.verts.layers.int, 'to_merge_layer')
                            
                            # mark faces for deletion in the future.
                            for f in bm_potential.faces:
                                f[face_id_to_del_layer] = main_face.index

                            
                            
                            # assemble the right vectors for slicing, which are those around the face edges.
                            slices = []
                            slice_error = False
                            for i in range(0, len(uv_list) - 1):
                                # create initial slice to be the slice of the face edge in UV space.
                                to_slice = uv_list[i] - uv_list[i+1]
                                # rotate the UV edge to form the normal of the slice plane.
                                to_slice.rotate(eul)
                                if to_slice.magnitude == 0:
                                    slice_error = True
                                    break
                                # add this to the list of slices, 0 = point on slice plane, 1 = slice plane normal. Used in bmesh.ops.bisect_plane
                                slices.append((uv_list[i], to_slice))
                            to_slice = uv_list[len(uv_list) - 1] - uv_list[0]
                            to_slice.rotate(eul)
                            if to_slice.magnitude == 0:
                                slice_error = True

                            # check if there were any errors in assembling the slicing, e.g. a uv with zero distance.
                            if slice_error:
                                # We can't process this so we skip... TODO error message?
                                continue

                            slices.append((uv_list[len(uv_list) - 1], to_slice))

                            # Now, we can go through all the slices and bisect the object in UV space so that it can neatly fit on the face.
                            geom = []
                            geom.extend(bm_potential.verts)
                            geom.extend(bm_potential.edges)
                            geom.extend(bm_potential.faces)
                            for to_slice in slices:
                                result = bmesh.ops.bisect_plane(bm_potential, geom=geom, dist=0, plane_co=to_slice[0], plane_no=to_slice[1], clear_outer=True, use_snap_center = False)
                                geom = result['geom']
                                for element in result['geom_cut']:
                                    if isinstance(element, bmesh.types.BMEdge):
                                        element[cut_edges_layer] = 1
                                    elif isinstance(element, bmesh.types.BMVert):
                                        element[cut_verts_layer] = 1

                            # if we haven't sliced the object into oblivion, we can now process the mesh coordinates ready for placing on the face.
                            if len(bm_potential.verts) > 0:


                                # Go through all vertices on the generated object for the face and position appropriately.

                                for v_g in bm_potential.verts:
                                    if v_g.is_valid:

                                        # Retrieve the appropriate set of properties to apply to the object - either general of specific to the object.
                                        prop_id = v_g[object_prop_id_layer]
                                        obj_prop = self.source_object_prop_lookup[prop_id]
                                        if not obj_prop.use_custom_parameters:
                                            prop = self.general_props
                                        else:
                                            prop = obj_prop
                                        
                                        # get the location of the vertex and process it so that it maps onto the face.
                                        loc = Vector((v_g.co.x, v_g.co.y, 0)) #z is set to zero so appropriate height and normal direction can be found.

                                        # depending on the approach to slicing, either use the untriangulated mesh to determine uv coordinates or
                                        # Use the face on the triangulated mesh directly (which will have been seleted earlier).
                                        face_to_process = None
                                        if context.scene.mesh_mat_approach == '0': # face approach: use the triangulation as a cach for determining the right barycentric point.

                                            # get all triangulated faces from temp mesh so that we can process the right part of the face.
                                            tri_faces = triangulation_cache[f_t.index]
                                            
                                            # find the closest triangulated triangle.
                                            for tri_face in tri_faces:
                                                u, v, w = [l[uv_layer_tri_temp].uv.to_3d() for l in tri_face.loops]
                                                if mathutils.geometry.intersect_point_tri(loc, u, v, w):
                                                    face_to_process = tri_face
                                                    break
                                                    
                                            # some times the intersection check will fail - in this case, find the closest triangle and use that.
                                            if face_to_process is None:
                                                face_to_process = None
                                                current_magnitude = None
                                                u,v,w = (None, None, None)
                                                for tri_face in tri_faces:
                                                    u_test, v_test, w_test = [l[uv_layer_tri_temp].uv.to_3d() for l in tri_face.loops]
                                                    closest_point_on_tri = mathutils.geometry.closest_point_on_tri(loc, u_test, v_test, w_test)
                                                    magnitude = (closest_point_on_tri - loc).magnitude
                                                    if (face_to_process is None and current_magnitude is None) or (current_magnitude is not None and magnitude < current_magnitude):
                                                        face_to_process = tri_face
                                                        current_magnitude = magnitude
                                                        u, v, w = (u_test, v_test, w_test)


                                        elif context.scene.mesh_mat_approach == '1': # triangulation approach - bmesh is already triangulated.
                                            # find the triangulated face.
                                            face_to_process = f_t
                                            u, v, w = [l[uv_layer_target].uv.to_3d() for l in face_to_process.loops]
                                    
                                        # find the local coordinates of the vertex location on the face given the UVs
                                        
                                        # determine z axis coordinated based on chosen direction and the z scaling value setting
                                        proper_co = find_coord(v_g.co, u, v, w, face_to_process)

                                        # determine how we want to align the z axis based on the normal direction.
                                        normal_alignment = prop.align_normal_type
                                        if not prop.align_normal:
                                            # No alignment - just use custom value
                                            local_co=proper_co
                                        else:
                                            local_co = find_coord(loc, u, v, w, face_to_process)
                                            if normal_alignment == 0:
                                                # Align to Face Normal
                                                adjusted_normal = face_to_process.normal
                                                adjusted_normal.normalize()
                                            elif normal_alignment == 1:
                                                # Align to Vertex Normals
                                                adjusted_normal = calc_normal(local_co, face_to_process)
                                                adjusted_normal.normalize()
                                            elif normal_alignment == 2:
                                                # Custom Normal
                                                adjusted_normal = prop.custom_normal
                                            else:
                                                raise Exception('Invalid normal alignment option: ' + str(normal_alignment))
                                            local_co = local_co + ((v_g.co.z * prop.normal_height) * adjusted_normal) 
                                        
                                        
                                        # assign to vertex before processing the entire mesh's vertices.
                                        v_g.co.x = local_co.x
                                        v_g.co.y = local_co.y
                                        v_g.co.z = local_co.z

                                # create a mesh temporatily for assembling into the main generated object.
                                new_mesh = bpy.data.meshes.new("mesh datablock for created obj")
                                bm_potential.to_mesh(new_mesh)
                                bm_new.from_mesh(new_mesh)
                                bpy.data.meshes.remove(new_mesh)

 
                    finally:
                        bm_potential.clear()
                        

            bm_potential.free()
            bmesh.ops.delete(bm_new, geom=faces_to_delete, context='FACES')

            # we are now finished collated all generated meshes for the faces.

            # Free this as we won't use it any more.
            bm_triangulated_temp.free()
            
            # combine all the meshes we have created for the face into the new bmesh.
            # for new_mesh in all_meshes:
            #     bm_new.from_mesh(new_mesh)
            #     bpy.data.meshes.remove(new_mesh)

            # select none
            for f in bm_new.faces:
                f.select_set(False)

            cut_verts_layer = get_or_create_layer(bm_new.verts.layers.int, 'cut_verts_layer')
            cut_edges_layer = get_or_create_layer(bm_new.edges.layers.int, 'cut_edges_layer')

            if context.scene.mesh_mat_select_cut_geom:
                for v in bm_new.verts:
                    v.select_set(v[cut_verts_layer])
                for e in bm_new.edges:
                    e.select_set(e[cut_edges_layer])
            # finally commit to the generated bmesh.
            bm_new.to_mesh(me_new)

        finally: 
            # must free any created meshes that aren't taken care of elsewhere.
            for key in obj_cache:
                me = obj_cache[key][1]
                bpy.data.meshes.remove(me)
            bm_new.free()

    def free(self):
        for key in self.source_object_prop_lookup:
            self.source_object_prop_lookup[key].bm_cached.free()


