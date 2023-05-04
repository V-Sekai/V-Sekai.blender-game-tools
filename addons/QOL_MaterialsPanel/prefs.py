import bpy
from bpy.types import AddonPreferences
from bpy.props import (BoolProperty,EnumProperty,)

class RH_Materials_Panel_preferences(AddonPreferences):
    bl_idname = __package__

    paneltype: EnumProperty(
        name = "Panel Type",
        items = [('npanel',"NPanel",""),
        ('properties',"Properties Panel",""),],
        description = "Whether to be an NPanel or Properties Panel",       
        )
    show_swatch: BoolProperty(
        name = "Show Swatch",
        description = "Show the swatch in the panel",
        default = True,
        )
    show_delete: BoolProperty(
        name = "Show Delete",
        description = "Whether to show the delete button on the panel",
        default = False
        )    
    show_fakeuser: BoolProperty(
        name = "Show Fake User",
        description = "Whether to show the fake_user button on the panel",
        default = True
        )    
    show_grab: BoolProperty(
        name = "Show Grab",
        description = "Whether to show the grab button on the panel",
        default = True
        )    

    def draw(self, context):
        layout = self.layout
        # layout.use_property_split = True
        row = layout.row()
        row.prop(self, "show_swatch")
        row.prop(self, "show_delete", icon = "TRASH")
        # row = layout.row()
        row.prop(self, "show_fakeuser", icon = "FAKE_USER_ON")
        # row = layout.row()
        box = layout.box()
        row.prop(self, "show_grab", icon = "VIEW_PAN")
        row = box.row()
        row.label(text="Note: 'Panel Type' won't apply until next Blender restart")
        row = box.row()
        row.prop(self, "paneltype")
        
def RHMatPanel_get_preferences(context):
    return context.preferences.addons[__package__].preferences

