import bpy
import bmesh
import bl_math
import math
import time
from mathutils import Matrix, Vector, Euler, Quaternion
from mathutils.bvhtree import BVHTree

def remap(value, original_range, target_range):
	(original_min, original_max) = original_range
	(target_min, target_max) = target_range
	return (value - original_min) / (original_max - original_min) * (target_max - target_min) + target_min

def project_point_on_plane(point, plane_origin, plane_normal):
	plane_normal = plane_normal.normalized()
	vec_from_origin_to_point = point - plane_origin
	vec_proj_onto_normal = vec_from_origin_to_point.project(plane_normal)
	vec_from_origin_to_projected_point = vec_from_origin_to_point - vec_proj_onto_normal
	projected_point = plane_origin + vec_from_origin_to_projected_point
	return projected_point

def intersect_ray_plane(ray_origin, ray_direction, plane_point, plane_normal):
	ray_direction = ray_direction.normalized()
	plane_normal = plane_normal.normalized()

	denom = ray_direction.dot(plane_normal)
	# If this is zero, then the ray and plane are parallel
	# and there's no intersection point.
	if math.isclose(denom, 0.0):
		return None

	t = (plane_point - ray_origin).dot(plane_normal) / denom
	# If t is less than zero, the intersection point is 'behind' the ray_origin.
	# Depending on your specific situation, you might consider this as no intersection.
	if t < 0.0:
		return None
	intersection_point = ray_origin + t * ray_direction
	return intersection_point

def intersect_line_plane_vertical(point, plane_origin, plane_normal):
	# Line: L = P + tV
	P = point
	V = Vector((0,0,1))

	# Plane: N.(X-P0) = 0
	N = plane_normal
	P0 = plane_origin

	# Calculate t: N.(L-P0) = 0 => N.((P+tV)-P0) = 0 => N.(P-P0) + tN.V = 0
	t = (N.dot(P0 - P)) / (N.dot(V) + 0.0000001)

	# Calculate intersection point: I = P + tV
	I = P + t*V

	return I

def reflect_velocity(velocity, collision_normal):
	# its not a bouncy one, rather a projection
	if collision_normal.length == 0:
		return velocity
	collision_normal = collision_normal.normalized()
	parallel_component = velocity.project(collision_normal)	# Component of velocity parallel to the collision normal
	return velocity - parallel_component

def vector_clamp(vector, min_val, max_val):
	x = bl_math.clamp(vector.x, min_val, max_val)
	y = bl_math.clamp(vector.y, min_val, max_val)
	z = bl_math.clamp(vector.z, min_val, max_val)
	return Vector((x, y, z))

def delta_quaternion(mat_a, mat_b):
	mat1_inv = mat_a.inverted()
	relative_transform = mat1_inv @ mat_b
	return relative_transform.to_3x3().to_quaternion()

def ray_sphere_intersection(ray_origin, ray_direction, sphere_center, sphere_radius):
	#return: tuple (hit, pos, normal, distance)
	
	# Calculate vectors for the quadratic formula
	oc = ray_origin - sphere_center
	a = ray_direction.dot(ray_direction)
	b = 2.0 * oc.dot(ray_direction)
	c = oc.dot(oc) - sphere_radius**2
	discriminant = b**2 - 4 * a * c
	
	if discriminant < 0:
		return None, None, None  # No intersection
	
	# Find the nearest t value that is non-negative
	sqrt_discriminant = math.sqrt(discriminant)
	t1 = (-b - sqrt_discriminant) / (2 * a)
	t2 = (-b + sqrt_discriminant) / (2 * a)
	t = min(t1, t2)
	
	if t < 0:
		t = max(t1, t2)
		if t < 0:
			return None, None, None  # No intersection
	
	# Calculate the intersection point and normal
	hit_position = ray_origin + ray_direction * t
	normal = (hit_position - sphere_center).normalized()
	distance = (hit_position - ray_origin).length
	return hit_position, normal, distance

def create_bvhtree_from_visible_objects(scene, ignore_wires, ignore_animated, full_evaluation, collection_info, collection_mode):
	# Create list of all objects:
	objs = []

	if collection_mode == 'INCLUDE':
		for item in collection_info:
			collection = item.collection
			if collection:
				for obj in collection.objects:
					if obj.type == 'MESH' and obj.visible_get():
						if ignore_wires and (obj.display_type == 'WIRE' or obj.display_type == 'BOUNDS'):
							continue
						if ignore_animated:
							if is_animated(obj):
								continue
						objs.append(obj)
	elif collection_mode == 'EXCLUDE':
		exclude_collections = set(item.collection for item in collection_info if item.collection)
		for obj in scene.objects:
			if obj.type == 'MESH' and obj.visible_get():
				if ignore_wires and (obj.display_type == 'WIRE' or obj.display_type == 'BOUNDS'):
					continue
				if ignore_animated:
					if is_animated(obj):
						continue
				# Check if object is part of any excluded collections
				if not any(coll in exclude_collections for coll in obj.users_collection):
					objs.append(obj)
	elif collection_mode == 'ALL':
		for obj in scene.objects:
			if obj.type == 'MESH' and obj.visible_get():
				if ignore_wires and (obj.display_type == 'WIRE' or obj.display_type == 'BOUNDS'):
					continue
				if ignore_animated:
					if is_animated(obj):
						continue
				objs.append(obj)


	# Remove Duplicates
	objs = list(set(objs))

	# Process List
	bm = bmesh.new()


	total_objects = len(objs) #sum(1 for obj in scene.objects if obj.type == 'MESH' and obj.visible_get())
	processed_objects = 0
	bpy.context.window_manager.progress_begin(0, total_objects)
	start_time = time.time()

	depsgraph = bpy.context.evaluated_depsgraph_get()

	for obj in objs:
		if full_evaluation:
			eval_obj = obj.evaluated_get(depsgraph) # applies modifiers, constraints etc. - SLOW!
			temp_mesh = eval_obj.to_mesh()
		else:
			temp_mesh = obj.to_mesh() # direct way - much faster, but no modifiers etc.

		if temp_mesh is not None:
			temp_bm = bmesh.new()
			temp_bm.from_mesh(temp_mesh)
			#bmesh.ops.transform(temp_bm, matrix=obj.matrix_world, verts=temp_bm.verts)
			temp_bm.transform(obj.matrix_world) # a bit Faster than the bmesh.ops.transform
			temp_bm.to_mesh(temp_mesh)
			bm.from_mesh(temp_mesh)
			temp_bm.free()

			bpy.context.window_manager.progress_update(processed_objects)
			processed_objects += 1

		if full_evaluation:
			eval_obj.to_mesh_clear()
		else:
			obj.to_mesh_clear()

	end_time = time.time()
	elapsed_time = end_time - start_time
	print(f"Create BVH Mesh: {elapsed_time:.4f} seconds")

	start_time = time.time()
	bvhtree = BVHTree.FromBMesh(bm)
	end_time = time.time()
	elapsed_time = end_time - start_time
	print(f"Build BVH Tree:  {elapsed_time:.4f} seconds")

	bm.free()
	bpy.context.window_manager.progress_end()
	return bvhtree

def create_bvhtree_from_visible_objects_instances(scene, ignore_wires, ignore_animated, full_evaluation, collection_info, collection_mode):
	include_collections = set(item.collection for item in collection_info if item.collection)
	exclude_collections = set(item.collection for item in collection_info if item.collection)

	bm = bmesh.new()
	depsgraph = bpy.context.evaluated_depsgraph_get()

	def process_object(obj, linked, instance, parent_transform=None):
		# linked or instanced objects can be in inactive collections, and further can be off in the view layer
		# this (linked or (instance and not obj.hide_viewport) or obj.visible_get()) - takes care of all states
		if obj.type == 'MESH' and (linked or (instance and not obj.hide_viewport) or obj.visible_get()):
			if ignore_wires and (obj.display_type == 'WIRE' or obj.display_type == 'BOUNDS'):
				return
			if collection_mode == 'INCLUDE' and not any(coll in include_collections for coll in obj.users_collection):
				return
			if collection_mode == 'EXCLUDE' and any(coll in exclude_collections for coll in obj.users_collection):
				return
			if ignore_animated:
				if is_animated(obj):
					return

			final_transform_matrix = parent_transform @ obj.matrix_world if parent_transform else obj.matrix_world

			if linked:
				temp_mesh = obj.to_mesh() #data
			else:
				if full_evaluation:
					eval_obj = obj.evaluated_get(depsgraph)
					temp_mesh = eval_obj.to_mesh()
				else:
					temp_mesh = obj.to_mesh()

			if temp_mesh is not None:
				temp_bm = bmesh.new()
				temp_bm.from_mesh(temp_mesh)
				#bmesh.ops.transform(temp_bm, matrix=final_transform_matrix, verts=temp_bm.verts)
				temp_bm.transform(final_transform_matrix) # a bit Faster
				temp_bm.to_mesh(temp_mesh)
				bm.from_mesh(temp_mesh)
				temp_bm.free()

			if not linked and full_evaluation:
				eval_obj.to_mesh_clear()
			if linked:
				obj.to_mesh_clear()

		elif obj.type == 'EMPTY' and obj.instance_collection and obj.instance_type == 'COLLECTION':
			collection = obj.instance_collection
			# Start with the transformation of the empty object
			empty_transform = obj.matrix_world.copy()
			# Combine with parent transformation if provided
			full_transform = parent_transform @ empty_transform if parent_transform else empty_transform
			# Apply the collection's offset
			offset_matrix = Matrix.Translation(-collection.instance_offset)
			full_transform_with_offset = full_transform @ offset_matrix

			#for inst_obj in collection.objects:
			#	process_object(inst_obj, full_transform_with_offset)
			if collection.library:  # Check if this collection is linked
				# Process objects in the linked collection
				for linked_obj in collection.objects:
					process_object(linked_obj, True, True, full_transform_with_offset)
			else:
				# Process objects in the local collection
				for inst_obj in collection.objects:
					process_object(inst_obj, False, True, full_transform_with_offset)



	# Iterate over all objects in the scene
	for obj in scene.objects:
		process_object(obj, False, False)

	bvhtree = BVHTree.FromBMesh(bm)
	bm.free()
	bpy.context.window_manager.progress_end()
	return bvhtree

def update_panel_values(self, context):
	if self.target_scale == 'M':
		self.custom_scale = 1.0
		self.current_scale = 1.0
	if self.target_scale == 'CM':
		self.custom_scale = 100.0
		self.current_scale = 100.0
	if self.target_scale == 'INCH':
		self.custom_scale = 39.37
		self.current_scale = 39.37
	if self.target_scale == 'FEET':
		self.custom_scale = 3.281
		self.current_scale = 3.281

	if self.target_framerate == '30':
		self.custom_framerate = 30
		self.current_framerate = 30
	if self.target_framerate == '60':
		self.custom_framerate = 60
		self.current_framerate = 60
	if self.target_framerate == '120':
		self.custom_framerate = 120
		self.current_framerate = 120
	if self.target_framerate == '240':
		self.custom_framerate = 240
		self.current_framerate = 240

	if self.target_gravity == '20.00':
		self.custom_gravity = 20.0
		self.current_gravity = 20.0
	if self.target_gravity == '15.24':
		self.custom_gravity = 15.24
		self.current_gravity = 15.24
	if self.target_gravity == '9.81':
		self.custom_gravity = 9.81
		self.current_gravity = 9.81

def empty_poll(self, object):
	return object.type == 'EMPTY' and object.users_scene

def is_animated(obj):
	if obj.animation_data and obj.animation_data.action:
		return True
	# Check for active constraints
	if obj.constraints:
		for constraint in obj.constraints:
			if constraint.mute == False:  # If constraint is active
				return True

	# Check for rigid body
	if obj.rigid_body and obj.rigid_body.type == 'ACTIVE':
		return True

	if obj.parent:
		return is_animated(obj.parent)
	return False

def rigidbody_poll(self, object):
	return object.rigid_body is not None and object.rigid_body.type == 'ACTIVE'

def ease_in_out_quad(t):
	if t < 0.5:
		return 2 * t * t
	else:
		return -1 + (4 - 2 * t) * t

def ease_out_quad(t):
	return -t * (t - 2)

# Scripting Helpers
def refresh_inspector_op(self, context):
	# needed for the Prop, can only run a function, and it can only be a execute, not an invoke
    bpy.ops.view3d.omnistep_userscript(command='refresh')

def inspector_change(self, context):
	# if the OMNISTEP_DynamicItem was changed by the user in the ui, needed for referesh, to know
	# what needs to be read from the script or the current ui. basically a override - ui first,
	# script values second.
	self.changed = True