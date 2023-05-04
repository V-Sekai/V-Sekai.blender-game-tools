from bpy.types import AddonPreferences
from bpy.props import (BoolProperty,IntProperty,EnumProperty,StringProperty,FloatProperty)

class QOL_PolyPal_Preferences(AddonPreferences):
    bl_idname = __package__

    gridSnapping: BoolProperty( 
        name = "Grid Snapping",
        description = "Whether to snap to the grid in orthagonal views",
        default = False,
        )
    
    gridSize: FloatProperty(
        default = 1,
        )
    
    heads_up: BoolProperty(
        name = "Heads Up Display",
        description = "Whether to display the info widgets in the viewport",
        default = True,
        )

    nPanel: BoolProperty(
        name = "N Panel",
        description = "Whether to display the N panel in the viewport (requires restart)",
        default = True,
        )

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        box = row.box()
        row = box.row()
        row.prop(self, "nPanel")
        row = box.row()
        row.label(text="NOTE: NPanel state change requires a restart to take effect.")
        row = layout.row()
        row.prop(self, "gridSnapping")

        
def QOLPolyPal_get_preferences(context):
    return context.preferences.addons[__package__].preferences

