import bpy
import bmesh
from dataclasses import dataclass
from mathutils.bvhtree import BVHTree
from mathutils import Matrix, Vector, Euler, Quaternion

# ******************************************************************** #
@dataclass
class SceneState:
	timer: bpy.types.Timer = None
	target_timestep: float = 0.0
	current_timestep: float = 0.0		# viewport timestep (fps)
	physics_timestep: float = 0.0		# defaults to 1.0 / 120
	use_fixed_timestep: bool = False	# Animation Option
	max_timestep: float = 0.0			# upper limit to avoid glitching through walls 
	framecount: int = 0					# internal frame counter (modal frames)
	collision_samples: int = 0
	bvhtree: 'SceneBVH' = None

	camera_view: bool = False			# is the starting view a camera view?

	IDLE = "Idle"
	PREROLL = "Preroll"
	RECORDING = "Recording"
	END = "End"

	scene_state: str = IDLE
	scene_frame: int = 0				# Which frame the scene is on when playback is active
	scene_frame_fraction: float = 0.0	# in case we write fractional frames
	scene_loop_count: int = 0			# how often the timeline was played
	scene_framerate: int = 0			# set framerate of the scene
	write_frame: bool = False			# True for one loop, iteration when recording should happen

# ******************************************************************** #
class SceneBVH:
	# ---------------------------------------------------------------- #
	def __init__(self, context, base_bvh):
		self.context = context
		self.base_bvh = base_bvh
		self.dynamic_objects = {}  			# Dictionary to store dynamic objects (and their cached meshes)
		self.dynamic_bvh: BVHTree = None	# Initialize as None, build as needed

	# ---------------------------------------------------------------- #
	def dynamic_bvh_set_obj(self, objs, full_eval=False): # create or update
		if not isinstance(objs, (list, tuple)):
			objs = [objs]  # Convert a single object into a list

		unique_objs_dict = {obj.name: obj for obj in objs if obj.type == 'MESH'}

		# Clean up existing objects and remove their meshes
		for obj_name in unique_objs_dict:
			if obj_name in self.dynamic_objects:
				self.clear_cached_mesh(self.dynamic_objects[obj_name]['mesh'])
				del self.dynamic_objects[obj_name]

		# this already refreshes the basic obj props, no further action needed
		self.depsgraph = self.context.evaluated_depsgraph_get()

		# Add new objects and create cached meshes
		for obj_name, obj in unique_objs_dict.items():
			cached_mesh = self.create_cached_mesh(obj, full_eval)
			self.dynamic_objects[obj_name] = {'obj': obj, 'mesh': cached_mesh}

		self.dynamic_bvh_rebuild()

	# ---------------------------------------------------------------- #
	def dynamic_bvh_remove_obj(self, obj):
		if obj.name in self.dynamic_objects:
			print(self.dynamic_objects[obj.name]['mesh'])
			self.clear_cached_mesh(self.dynamic_objects[obj.name]['mesh'])
			del self.dynamic_objects[obj.name]
		self.dynamic_bvh_rebuild()

	# ---------------------------------------------------------------- #
	def dynamic_bvh_clear_all(self):
		self.dynamic_bvh = None
		for obj in self.dynamic_objects.values():
			bpy.data.meshes.remove(obj['mesh'])
		self.dynamic_objects = {}

	# Rebuild of blender api calls =================================== #
	def find_nearest(self, pos, distance=1.84467e+19):
		closest_base = self.base_bvh.find_nearest(pos, distance) if self.base_bvh else (None, None, None, None)
		closest_dynamic = self.dynamic_bvh.find_nearest(pos, distance) if self.dynamic_bvh else (None, None, None, None)

		# Handle cases where one or both are None
		if closest_base[3] is None and closest_dynamic[3] is None:
			return (None, None, None, None)  # No hit found in either BVHTree

		# Determine which result is closer
		if closest_base[3] is not None and (closest_dynamic[3] is None or closest_base[3] < closest_dynamic[3]):
			return closest_base
		elif closest_dynamic[3] is not None:
			return closest_dynamic

	# ---------------------------------------------------------------- #
	def ray_cast(self, pos, vec, distance=1.84467e+19):
		# Cast rays on both the base and dynamic BVHs
		hit_base = self.base_bvh.ray_cast(pos, vec, distance) if self.base_bvh else (None, None, None, None)
		hit_dynamic = self.dynamic_bvh.ray_cast(pos, vec, distance) if self.dynamic_bvh else (None, None, None, None)

		# Check for actual hits and determine which hit is closer
		if hit_base[3] is None and hit_dynamic[3] is None:
			return (None, None, None, None)  # No hit found in either BVHTree

		if hit_base[3] is not None and (hit_dynamic[3] is None or hit_base[3] < hit_dynamic[3]):
			return hit_base
		elif hit_dynamic[3] is not None:
			return hit_dynamic

	# Private Methods ================================================ #
	def create_cached_mesh(self, obj, full_eval):
		mesh = None
		if full_eval:
			eval_obj = obj.evaluated_get(self.depsgraph) # applies modifiers, constraints etc. - SLOW!
			mesh = eval_obj.to_mesh()
		else:
			mesh = obj.to_mesh()
		#mesh = obj.to_mesh(preserve_all_data_layers=False, depsgraph=self.depsgraph) if full_eval else obj.to_mesh()

		bm = bmesh.new()
		bm.from_mesh(mesh)
		bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
		# Create a new mesh to store transformed data
		cached_mesh = bpy.data.meshes.new(name=f"OmniStep_cache_{obj.name}")
		bm.to_mesh(cached_mesh)
		bm.free()

		if full_eval:
			eval_obj.to_mesh_clear()
		else:
			obj.to_mesh_clear()

		return cached_mesh

	# ---------------------------------------------------------------- #
	def clear_cached_mesh(self, mesh):
		if mesh.name in bpy.data.meshes:	
			bpy.data.meshes.remove(mesh)

	# ---------------------------------------------------------------- #
	def dynamic_bvh_rebuild(self):
		bm = bmesh.new()
		for obj in self.dynamic_objects.values():
			bm.from_mesh(obj['mesh'])

		self.dynamic_bvh = BVHTree.FromBMesh(bm)
		bm.free()