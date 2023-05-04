import bpy
from bpy.types import (AddonPreferences,PropertyGroup,)
from bpy.props import (EnumProperty,)

class QOL_CamBM_preferences(AddonPreferences):
    bl_idname = __package__

    paneltype: EnumProperty(
        name = "Panel Type",
        items = [('properties',"Properties Panel",""),
        ('npanel',"NPanel",""),],
        description = "Whether to be an NPanel or Properties Panel",)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        row = box.row()
        row.label(text="Note: 'Panel Type' won't apply until next Blender restart")
        row = box.row()
        row.prop(self, "paneltype")

