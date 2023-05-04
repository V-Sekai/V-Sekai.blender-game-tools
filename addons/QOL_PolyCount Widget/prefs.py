import bpy
from . import bl_info
from bpy.types import AddonPreferences
from bpy.props import (BoolProperty,IntProperty,EnumProperty,StringProperty)

class RH_PolyCountWidget_preferences(AddonPreferences):
    bl_idname = __package__

    polylabel: StringProperty(
        name = "Polycount Label",
        description = "The label for the polycount widget",
        default = "Polycount: ",
        )

    mod_eval: BoolProperty(
        name = "Evaluate Modifiers",
        description = "Whether to evaluate modifiers when counting polygons",
        default = True,
        )
    header_left: BoolProperty(
        name = "Header Left (Right if unchecked)",
        description = "Whether to put the widget in the left or right side of the header",
        default = True,
        )


    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "polylabel")
        row = layout.row()
        row.prop(self, "mod_eval")
        row = layout.row()
        row.prop(self, "header_left")
        row = layout.row()
        row.label(text="note: Header location requires Blender restart for changes to take effect")


        
def RHMatPanel_get_preferences(context):
    return context.preferences.addons[__package__].preferences

