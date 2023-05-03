# ##### BEGIN GPL LICENSE BLOCK #####

#Copyright (C) 2021 Alberto Gonzalez & Vjaceslav Tissen
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# ##### END GPL LICENSE BLOCK #####

from . ui import MO_PT_panel
from . import ui
from . import operators
import bpy
bl_info = {
    "name": "SimplyWrapPro",
    "description": "Create cloth strips and wrap around objects.",
    "author": "Alberto Gonzalez and Vjaceslav Tissen",
    "version": (1, 3, 0),
    "blender": (3, 0, 0),
    "location": "View 3D > Tool Shelf > Tools > SimplyWrap",
    "warning": "",
    "category": "Mesh"}

# Support reloading of add-on.
if "bpy" in locals():
    import importlib
    if "functions" in locals():
        importlib.reload(functions)
    if "operators" in locals():
        importlib.reload(operators)
    if "ui" in locals():
        importlib.reload(ui)
else:
	from . import functions
	from . import operators
	from . import ui

import bpy


from . import operators
from . import ui
from . ui import MO_PT_panel
def register():
    bpy.utils.register_class(operators.OT_draw_operator)
    bpy.utils.register_class(operators.AddCollisionModifier)
    bpy.utils.register_class(operators.ApplyWrapClothModifiers)
    bpy.utils.register_class(operators.RemoveCollisionFromObject)
    bpy.utils.register_class(operators.PlayStopOperator)
    bpy.utils.register_class(operators.ResetShrinkKeyframesAnimation)
    bpy.utils.register_class(operators.GenerateWrapFromSelectedCurve)
    bpy.utils.register_class(operators.CleanUpWrapEndings)
    bpy.utils.register_class(operators.ShowCurveAndMeshInScene)
    bpy.utils.register_class(operators.AssignSelectionToPinGroup)
    bpy.utils.register_class(operators.AddCustomObjectToCurve)
    bpy.utils.register_class(operators.ShowIntersected)
    # bpy.utils.register_class(operators.ResetModal)
    bpy.utils.register_class(operators.RH_OT_reset_handlers)
    bpy.utils.register_class(ui.MO_PT_panel)

    ui.registerIcon()

bpy.types.Scene.point_count = bpy.props.IntProperty(name="point_count", default=100, description="Draw Points Resolution count")
bpy.types.Scene.offset_value = bpy.props.FloatProperty(name="offset_value", min=0.01, max=5, default=0.01, description="Distance from collision Object")

bpy.types.Scene.overlap_offset = bpy.props.FloatProperty(name="overlap_offset", min=0.1, max=10, default=0.3, description="Overlap Distance")
bpy.types.Scene.overlap_dist = bpy.props.FloatProperty(name="overlap_dist", min = 0.01, max = 5, default= 0.1, description = "Distance from last point to other points")
bpy.types.Scene.overlap_value = bpy.props.FloatProperty(name="overlap_value", min = 0.01, max = 5, default= 0.1, description = "Overlap Amount")
bpy.types.Scene.path_smoothing = bpy.props.FloatProperty(name="path_smoothing", min=0.0, max=0.35, default=0.1, description="Smoothing Drawing Path, low value = no Smoothing, high value = smoothing")

bpy.types.Scene.shorten_wrap_ends = bpy.props.FloatProperty(default=0.0, name="shorten_endings",
                                                            description="shorten endings of selected wrap", min=0.0, max=1000.0,
                                                            update=ui.shorten_endings)
bpy.types.Scene.draw_line_opacity = bpy.props.FloatProperty(
    name="draw_line_opacity", min=0.0, max=1.0, default=0.6, description="Drawing Wrap Line Opacity")
bpy.types.Scene.draw_line_width = bpy.props.IntProperty(
    name="draw_line_width", min=0, max=10, default=3, description="Drawing Line Width")

#make a bool property called offset_distance_state
bpy.types.Scene.offset_distance_state = bpy.props.BoolProperty(name="offset_distance_state", default=False, description="Offset Distance State")

bpy.types.Scene.hit_state = bpy.props.BoolProperty(
    name="hit_state", default=True, description="Current draw Orientation - Front/ Back")
bpy.types.Scene.modal_wrap_status = bpy.props.BoolProperty(
    name="modal_wrap_status", default=False, description="Is Wrap Operator running...")
bpy.types.Scene.lock_draw_orientation = bpy.props.BoolProperty(
    name="lock_draw_orientation", default=False, description="Lock switching drawing face orientation")

bpy.types.Scene.property_status = bpy.props.BoolProperty(
    name="property_status", default=False, description="Current Status of Modal Part")

bpy.types.Scene.property_state = bpy.props.EnumProperty(
    name="Property State",
    description="current state",

    items=[
        ("0", "size", "", '', 1),
        ("1", "offset", "", '', 2),
        ("2", "twist", "", '', 3),
        ("3", "runsim", "", '', 4),
        #

    ],
    default='0',

)
bpy.types.Scene.shrink_curve = bpy.props.BoolProperty(
    name="shrink_curve", default=True, description
    ="Could destroy correct overlapping offset after creating Wrap")

bpy.types.Scene.wrapMesh_visible = bpy.props.BoolProperty(
    name="wrapMesh_visible", default=True, description="Show and Hide Mesh")

bpy.types.Scene.wrapCurve_visible = bpy.props.BoolProperty(
    name="wrapCurve_visible", default=False, description="Show and Hide Curve")

bpy.types.Scene.info_box = bpy.props.BoolProperty(
    name="infobox_visible", default=False, description="Info box give you extra info")

def unregister():
    bpy.utils.unregister_class(operators.OT_draw_operator)
    bpy.utils.unregister_class(operators.AddCollisionModifier)
    bpy.utils.unregister_class(operators.ApplyWrapClothModifiers)
    bpy.utils.unregister_class(operators.RemoveCollisionFromObject)
    bpy.utils.unregister_class(operators.PlayStopOperator)
    bpy.utils.unregister_class(operators.ResetShrinkKeyframesAnimation)
    bpy.utils.unregister_class(operators.GenerateWrapFromSelectedCurve)
    bpy.utils.unregister_class(operators.CleanUpWrapEndings)
    bpy.utils.unregister_class(operators.ShowCurveAndMeshInScene)
    bpy.utils.unregister_class(operators.AssignSelectionToPinGroup)
    bpy.utils.unregister_class(operators.AddCustomObjectToCurve)
    bpy.utils.unregister_class(operators.ShowIntersected)
    # bpy.utils.unregister_class(operators.ResetModal)
    bpy.utils.unregister_class(operators.RH_OT_reset_handlers)
    bpy.utils.unregister_class(ui.MO_PT_panel)
    
    ui.registerIcon()