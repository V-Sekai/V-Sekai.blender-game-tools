import bpy
from bpy.types import (AddonPreferences,)
from bpy.props import *

class RH_RingArray_preferences(AddonPreferences):
    bl_idname = __package__

    count: IntProperty(
        name="Number of objects",default=6,min=1,max=1000,
        description = "Number of objects to create in the array",
        )
    radius: FloatProperty(
        name="Radius of circle",default=4,min=0.0001,
        description = "Radius of the circle to create the array on",
        )

    create_parent: BoolProperty(
        name="Create parent",default=False,
        description = "Create a parent object for the array",
        )

    auto_axis: BoolProperty(
        name="Auto axis",default=False,
        description = "Automatically determine the axis to create the array on",
        )
    delete_original: BoolProperty(
        name = "Delete Original",
        description = "Whether to delete the source object after operation",
        default = False
        )    
    merge_objects: BoolProperty(
        name = "Merge Objects",
        description = "Should array produce one object or multiple",
        default = False
        )    
    apply_transform: BoolProperty(
        name = "Apply Transform",
        description = "Whether to pre-apply transform to source",
        default = True
        )
    linked_data: BoolProperty(
        name = "Linked Data",
        description = "Whether to link data or not to allow for post adjustment",
        default = True
        )  

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "count", text = "Default Count")
        row.prop(self, "radius", text = "Default Radius")

        layout.prop(self, "apply_transform", text = "Apply Transform")
        layout.prop(self, "merge_objects", text = "Merge Objects")
        layout.prop(self, "delete_original", text = "Delete Original")
        layout.prop(self, "linked_data", text = "Linked Data")
        layout.prop(self, "create_parent", text = "Create Parent")
        layout.prop(self, "auto_axis", text = "Auto Axis")
        layout.operator("ringarray.reset_preferences", text = "Reset Preferences")



def RHRingArray_get_preferences(context):
    return context.preferences.addons[__package__].preferences

