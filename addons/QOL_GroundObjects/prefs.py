import bpy
from bpy.types import (
    AddonPreferences,
    PropertyGroup,
    )
from bpy.props import (
    StringProperty,
    BoolProperty,
    EnumProperty,
    IntProperty,
    FloatProperty
    )

class QOL_GroundObjects_preferences(AddonPreferences):
    bl_idname = __package__

    MoveType: EnumProperty(
    name = 'As',
    items = [('group',"All as one group",""),
            ('individual',"All individually",""),],
    description = 'How to sit things',)
    WhereTo: EnumProperty(
    name = 'How to sit',
    items = [('worldzero',"At world zero",""),
            ('straightdn',"Straight down",""),],
    description = 'How to sit things',)
    SitOrSwim: EnumProperty(
    name = 'Sit or Swim',
    items = [('sit',"Sit on floor",""),
            ('swim',"Swim on surface",""),],
    description = 'How to sit things',)
    PivotPlace: EnumProperty(
    name = 'Pivot Placement',
    items = [('untouched',"Leave alone",""),
            ('worldzero',"At world origin",""),
            ('base',"At Base",""),
            ('center',"At Center",""),],
    description = 'Where to place pivot after',)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "MoveType")
        row = layout.row()
        row.prop(self, "WhereTo")
        row = layout.row()
        row.prop(self, "SitOrSwim")
        row = layout.row()
        row.prop(self, "PivotPlace")


def QOLGroundObjects_get_preferences(context):
    return context.preferences.addons[__package__].preferences


bpy.utils.register_class(QOL_GroundObjects_preferences)