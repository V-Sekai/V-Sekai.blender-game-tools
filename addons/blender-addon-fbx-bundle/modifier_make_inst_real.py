import bpy, bmesh
import imp
import string
import random
from mathutils import Vector


from . import objects_organise

from . import modifier
imp.reload(modifier) 

class Settings(modifier.Settings):
	active: bpy.props.BoolProperty(
		name="Active",
		default=False
	)

class Modifier(modifier.Modifier):
	label = "Make Instances Real"
	id = 'make_inst_real'
	url = ""
	
	def __init__(self):
		super().__init__()


	def draw(self, layout):
		super().draw(layout)
		if(self.get("active")):
			col = layout.column(align=True)

	def process_objects(self, name, objects):

		objects_organise.consolidate_objects(objects, apply_normals=False, convert_mesh=False, merge_uvs=False)

		return objects


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
	return ''.join(random.choice(chars) for _ in range(size))
