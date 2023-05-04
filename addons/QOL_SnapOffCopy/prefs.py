import bpy
from . import bl_info
from bpy.types import AddonPreferences
from bpy.props import (BoolProperty,)

class RH_SnapOffCopy_preferences(AddonPreferences):
    bl_idname = __package__
    pivotToSelf: BoolProperty(
        name = "Whether to recenter the pivot to the new object",
        description = "Whether to recenter the pivot to the new object",
        default = True,
        )
    stayInEditMode : BoolProperty(
        name = "Whether to stay in edit mode after the operation",
        description = "Whether to stay in edit mode after the operation",
        default = True,
        )
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "pivotToSelf")
        layout.prop(self, "stayInEditMode")



