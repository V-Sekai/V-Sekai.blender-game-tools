import bpy, bmesh
import imp
import string
import random
from mathutils import Vector


from . import objects_organise

from . import modifier
imp.reload(modifier) 

class Settings(modifier.Settings):
	active : bpy.props.BoolProperty (
		name="Active",
		default=False
	)
	lightmap_pack_type : bpy.props.EnumProperty(
		name = "Pack Type",
		items = (
			("lightmap_pack", "Lightmap Pack", "Uses Blender's Lightmap Pack Operator", 1),
			("layout_pack", "Layout", "Uses existing UVs to create Lightmap", 2)
		)
	)

class Modifier(modifier.Modifier):
	label = "Lightmap UV"
	id = 'lightmap_uv'
	url = ""
	
	def __init__(self):
		super().__init__()
	
	def draw(self, layout):
		super().draw(layout)
		if(self.get("active")):
				row = layout.row(align=True)
				row.separator()
				row.separator()


				row.prop(eval ("bpy.context.scene." + self.settings_path()), "lightmap_pack_type")

    		
			
	def process_objects(self, name, objects):
		# Catch any collection instances and convert them to real objects
		for obj in objects:
			if obj.type == 'EMPTY' and obj.instance_collection:
				bpy.ops.object.duplicates_make_real()
				# Append newly converted objects
				objects.extend(bpy.context.selected_objects)

		# Find a mesh object so we can run convert operator
		for obj in objects:
			if obj.type == 'MESH':
				bpy.context.view_layer.objects.active = obj
				break
			continue

		bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=True)

		# TODO Fix scenario where there's already a lightmap or another UV set
		
		bpy.ops.object.convert(target='MESH', keep_original=False)
		bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

		uv_name = "Light Map"
		for obj in objects:
			if obj.type == 'MESH':                
				bpy.context.view_layer.objects.active = obj
				obj.data.uv_layers.new(name=uv_name)
				obj.data.uv_layers.active = obj.data.uv_layers[uv_name]
				obj.data.uv_layers[uv_name].active_render = True

		# Enter edit mode and pack UVs
		bpy.ops.object.mode_set(mode='EDIT')
		bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
		bpy.ops.mesh.select_all(action='SELECT')
		if self.get('lightmap_pack_type') == 'lightmap_pack':
			bpy.ops.uv.lightmap_pack()
		if self.get('lightmap_pack_type') == 'layout_pack':
			bpy.ops.uv.average_islands_scale()
			bpy.ops.uv.pack_islands()
			bpy.ops.object.mode_set(mode='OBJECT')
		return objects



def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
	return ''.join(random.choice(chars) for _ in range(size))