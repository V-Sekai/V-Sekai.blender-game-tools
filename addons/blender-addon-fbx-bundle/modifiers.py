import bpy
import bmesh
import operator
import mathutils
from mathutils import Vector

from . import modifier_rename
from . import modifier_merge
from . import modifier_make_inst_real
from . import modifier_copy_modifiers
from . import modifier_collider
from . import modifier_LOD
from . import modifier_vertex_ao
from . import modifier_offset_transform
from . import modifier_lightmap
from . import modifier_manifold

# from . import modifier_rename

import imp
imp.reload(modifier_rename) 
imp.reload(modifier_merge)
imp.reload(modifier_make_inst_real)
imp.reload(modifier_copy_modifiers) 
imp.reload(modifier_collider) 
imp.reload(modifier_LOD) 
imp.reload(modifier_vertex_ao) 
imp.reload(modifier_offset_transform) 
imp.reload(modifier_lightmap)
imp.reload(modifier_manifold)

# imp.reload(modifier_rename) 

modifiers = list([
	modifier_rename.Modifier(),
	modifier_offset_transform.Modifier(),
	modifier_copy_modifiers.Modifier(),
	modifier_merge.Modifier(),
    modifier_make_inst_real.Modifier(),
	modifier_collider.Modifier(),
	modifier_LOD.Modifier(),
	modifier_vertex_ao.Modifier(),
	modifier_lightmap.Modifier(),
	modifier_manifold.Modifier()
	# TODO add apply negative scale modifier
])
