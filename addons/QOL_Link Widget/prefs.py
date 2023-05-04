import bpy
from bpy.types import AddonPreferences
from bpy.props import (BoolProperty,EnumProperty,)

class RH_LinkWidget_preferences(AddonPreferences):
    bl_idname = __package__

    paneltype: EnumProperty(
        name = "icon coloring",
        items = [('Colored',"Colored",""),
        ('Mono',"Monochromatic",""),],
        description = "Whether to show a colored or monochromatic icon",
        default = 'Colored',
        )

    popupEnabled: BoolProperty(
        name = "Popup Menu Enabled",
        description = "Whether to show a popup menu when clicking the icon",
        default = False,
        )

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "paneltype", expand=True)
        row = layout.row()
        row.prop(self, "popupEnabled")

        
def RHLinkWidget_get_preferences(context):
    return context.preferences.addons[__package__].preferences

