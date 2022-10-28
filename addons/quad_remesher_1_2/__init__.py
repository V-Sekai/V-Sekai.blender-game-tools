# "Quad-Remesher Bridge for Blender"
# Author : Maxime Rouca
#
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

__QR_plugin_version__ = "1.2"

bl_info = {
	#"name": "Quad Remesher "+__QR_plugin_version__+" Bridge",  # (it break the display of all plugins... in prefs>Addons)
	"name": "Quad Remesher 1.2 Bridge",
	"author": "Maxime",
	"version": (1, 2, 1),    # see __QR_plugin_version__
	"blender": (2, 80, 0),
	#"description": "Quad Remesher "+__QR_plugin_version__+" Bridge",
	"description": "Quad Remesher 1.2 Bridge",
	"location": "",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": "Mesh"
}

import bpy
import bpy.props
from rna_keymap_ui import draw_kmi
from bl_operators.presets import AddPresetBase

from .qr_operators import (QREMESHER_OT_remesh, QREMESHER_OT_reset_settings, QREMESHER_OT_license_manager, QREMESHER_OT_facemap_to_materials)

addon_name = __name__.split(".")[0]

#def addon_prefs():
#	return bpy.context.preferences.addons[addon_name].preferences

def paintDensityPropertyCB(self, context):
	#try:
	props = bpy.context.scene.qremesher
	vertexColorSliderValue = getattr(props, 'painted_quad_density')
	
	#print("vertexColorSliderValue = " + str(vertexColorSliderValue) + "\n")

	#Mapping: Slider in [0.25, 4]
	maxSliderValue = 4
	minSliderValue = 0.25
	normalizedValue = 0.0
	if vertexColorSliderValue > 1.0:
		normalizedValue = (vertexColorSliderValue - 1.0) / (maxSliderValue - 1.0)
	elif vertexColorSliderValue < 1.0:
		normalizedValue =  - ((1.0/vertexColorSliderValue) - 1.0) / ((1.0/minSliderValue) - 1.0)

	if (normalizedValue > 1):
		normalizedValue = 1
	if (normalizedValue < -1):
		normalizedValue = -1

	# -- normalizedValue to color
	r = 1.0
	g = 1.0
	b = 1.0
	if normalizedValue > 0.0:
		r = 1
		g = 1-normalizedValue
		b = 1-normalizedValue
	elif normalizedValue < 0.0:
		r = 1+normalizedValue
		g = 1
		b = 1
		
	# set the color
	mycolor=(r, g, b)
	bpy.data.brushes["Draw"].color = mycolor

	#except Exception:
	#	print("Exception: in paintDensityPropertyCB..\n")
	return
    
# ----- Properties container ------
class QRSettingsPropertyGroup(bpy.types.PropertyGroup):
	# Target Quad Count
	target_count: bpy.props.IntProperty(name="Quad Count", description="Set the desired number of Quads",
										default=5000, soft_min=100, soft_max=10000, step=20, min = 1)

	curvatureAdaptivness_Tooltip = "Allows to control how quad's size locally adapts to curvatures.\nThe higher it is, the smaller the quads will be on high curvature areas.\nSet it at 0, to get uniform quads size"
	adaptQuadCount_Tooltip = "Adaptive Quad-Count :\nOn: Creates more polygons than asked to fit high curvatures area. \nOff(default): Respect the Target-Quad-Count more exactly.\nIt's advised to let it 'Off' to better respect the Target-Quad-Count. see the doc for more explanations. "
	useVertexColors_Tooltip = "Use 'Vertex Colors' to control Quads size density."
	vertexColorWidget_Tooltip = "Defines the Color to paint to control locally the desired Quad Density variations (using 'Draw' Tool, in 'Vertex Paint' mode) \n . from 0.25 => 'divide density by 4'  =  Big Quads  =  Cyan color \n . to 4  => 'multiply density by 4'  =  Small Quads  =  Red color."
	useMaterials_Tooltip="If On, QuadRemesher will use existing 'Materials' to guide the quad remeshing on Materials borders.\nMaterialIds will be maintained after remeshing."
	useNormals_Tooltip="TAKE CARE: this option is usefull in specific cases, BUT should be 'Off' by default (facetted mesh). Read the doc for more informations..."
	useNormals_Tooltip+="\nIf On, QuadRemesher will use the existing 'Normals' to guide the remeshing on edge loops where the normals are split/creased.\nBy default Blenders creates mesh with normals split everywhere.\nIt usefull to enable this option only with SmoothShade + AutoSmooth enabled...\nOn smooth organic shapes, it's advised to disable it."
	detectHardEdges_Tooltip="If On, QuadRemesher will detect/compute Hard-Edges automatically based on the geometry (using a mix of edge's angles and other geometrical considerations).\nIf 'Use Normals Splitting' is checked, it's often better to uncheck 'Detect Hard Edges by angle'.\nOn smooth organic shapes, it's advised to disable it."
	symToolTip = "These options allows to perform symmetrical quad remeshing. It's possible to combine all 3 symmetry axis."
	#symToolTip += "\nTAKE CARE: The axis are Local Coordinates axis! It's advised to set the Gizmo in 'Object' mode to better see the Local Coordinates axis."
	hideInputTip = "If On (default), the input object will be hidden after remeshing."
	
	# Quads size settings
	adaptive_size: bpy.props.FloatProperty(name="Adaptive size", 
										 description=curvatureAdaptivness_Tooltip,
										 default=50, min=0, max=100, step=0.5, precision=0, subtype = 'PERCENTAGE')

	adapt_quad_count: bpy.props.BoolProperty(name="Adapt Quad Count", default=True, 
											description=adaptQuadCount_Tooltip)
	
	use_vertex_color: bpy.props.BoolProperty(name="Use Vertex Color", 
											description=useVertexColors_Tooltip,
											default=False)

	painted_quad_density: bpy.props.FloatProperty(name="Quads density (paint)", 
											description=vertexColorWidget_Tooltip,
										   default=1.0, min=0.25, max=4.0, step=0.4,
										   update=paintDensityPropertyCB)

	# Edge loops control
	use_materials: bpy.props.BoolProperty(name="Use Materials", default=False, 
											description = useMaterials_Tooltip)
	use_normals: bpy.props.BoolProperty(name="Use Normals Splitting", 
										default=False,					#because when I create a sphere, all edges are 'creased', not a good idea to enable this by default...
										description=useNormals_Tooltip)
	autodetect_hard_edges: bpy.props.BoolProperty(name="Detect Hard Edges by angle", 
													default=True, 
													description=detectHardEdges_Tooltip)

	# Misc category
	symmetry_x: bpy.props.BoolProperty(name="X", default=False, description=symToolTip)
	symmetry_y: bpy.props.BoolProperty(name="Y", default=False, description=symToolTip)
	symmetry_z: bpy.props.BoolProperty(name="Z", default=False, description=symToolTip)
	
	hide_input: bpy.props.BoolProperty(name="Hide Input Object", default=True, description=hideInputTip)
	
	# progress bar value
	progress_value: bpy.props.FloatProperty(default=0, subtype='PERCENTAGE', precision=1, min=0, soft_min=0, soft_max=100, max=100)
    

def draw_panel_content(context, layout):
	#print("draw_panel_content called")
	
	props = context.scene.qremesher
	#props = addon_prefs().props

	wm = context.window_manager

	# "REMESH IT" button
#	if QREMESHER_OT_remesh.IsRemeshing:
#		myrow = layout.row(align=True)
#		myrow.label(text="(ESC)")
#		myrow.prop(props, 'progress_value')
#		#layout.prop(props, 'progress_value')
	layout.operator(QREMESHER_OT_remesh.bl_idname)
	layout.separator()
		
	# Settings
	col = layout.column(align=True)
	# row = col.row(align=True)
	col.prop(props, 'target_count')

	col.separator()

	# --- Quad Size settings ---
	box = col.box()
	box.label(text="  Quad Size Settings")

	box.prop(props, 'adaptive_size')
	box.prop(props, 'adapt_quad_count')
	box.prop(props, 'use_vertex_color')

	#box.separator()
	box.prop(props, 'painted_quad_density')

	col.separator()

	# --- Quad Size settings ---
	box = col.box()
	box.label(text="  Edge Loops Control")

	box.prop(props, 'use_materials')
	box.prop(props, 'use_normals')
	box.prop(props, 'autodetect_hard_edges')

	col.separator()

	# --- Misc.... ---
	box = col.box()
	box.label(text="  Misc")
	box.label(text="Symmetry:")
	myrow = box.row(align=True)
	myrow.prop(props, 'symmetry_x')
	myrow.prop(props, 'symmetry_y')
	myrow.prop(props, 'symmetry_z')
	box.prop(props, 'hide_input')
	box.operator(QREMESHER_OT_reset_settings.bl_idname)
	box.operator(QREMESHER_OT_license_manager.bl_idname)
	box.operator(QREMESHER_OT_facemap_to_materials.bl_idname)



# Side panel ui
class QREMESHER_PT_qremesher(bpy.types.Panel):
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'Quad Remesh'		# name of the VerticalTab
	bl_label = "Quad Remesher "+__QR_plugin_version__

	bl_idname = "QREMESHER_PT_qremesher"

	# bl_options = {'DEFAULT_CLOSED'}

	@classmethod
	def poll(cls, context):
		return True

	def draw(self, context):
		draw_panel_content(context, self.layout)


# Scene settings subpanel
'''
class QREMESHER_PT_qremesher_setting_panel(bpy.types.Panel):
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'QRemesher'
	bl_label = "Settings"

	bl_idname = "QREMESHER_PT_qremesher_setting_panel"
	bl_parent_id = "QREMESHER_PT_qremesher"   # NB: ca suffit a ajouter ce sub panel dans le panel QREMESHER_PT_qremesher

	# bl_options = {'DEFAULT_CLOSED'}

	@classmethod
	def poll(cls, context):
		return True

	def draw(self, context):

		self.layout.operator(QREMESHER_OT_reset_settings.bl_idname)

		self.layout.separator()

		#draw_panel_content(context, self.layout)
'''


classes = [QRSettingsPropertyGroup,

		   QREMESHER_PT_qremesher,
		   #QREMESHER_PT_qremesher_setting_panel,

		   QREMESHER_OT_remesh,
		   QREMESHER_OT_reset_settings,
		   QREMESHER_OT_license_manager,
		   QREMESHER_OT_facemap_to_materials,
		   ]
addon_keymaps = []


def hotkeys():
	wm = bpy.context.window_manager
	kc = wm.keyconfigs.addon

	if kc:
		if '3D View' not in kc.keymaps:
			km_view3d = kc.keymaps.new('3D View', space_type='VIEW_3D', region_type='WINDOW')
		else:
			km_view3d = kc.keymaps['3D View']

		kmi = km_view3d.keymap_items.new(QREMESHER_OT_remesh.bl_idname, head=True, type='R', value='PRESS',
										 ctrl=True, alt=True)

		addon_keymaps.append((km_view3d, kmi))


def register():
	for cls in classes:
		bpy.utils.register_class(cls)

	bpy.types.Scene.qremesher = bpy.props.PointerProperty(type=QRSettingsPropertyGroup)

	hotkeys()


def unregister():
	for cls in classes:
		bpy.utils.unregister_class(cls)

	del bpy.types.Scene.qremesher

	wm = bpy.context.window_manager
	kc = wm.keyconfigs.addon

	if kc:
		for km, kmi in addon_keymaps:
			km.keymap_items.remove(kmi)
	addon_keymaps.clear()
