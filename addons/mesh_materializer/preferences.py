import bpy
from bpy.types import AddonPreferences
from bpy.props import FloatVectorProperty, IntProperty
import os

def addon_name():
    return os.path.basename(os.path.dirname(os.path.realpath(__file__)))

class MeshMaterializerAddonPreferences(AddonPreferences):
    """Custom preferences and associated UI for add on properties."""
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = addon_name()

    add_face_color : FloatVectorProperty(name="Add Face Color",
                                        subtype='COLOR',
                                        size=4,
                                        default=[0.4, .5, 0.9, 0.3])

    del_face_color : FloatVectorProperty(name="Delete Face Color",
                                        subtype='COLOR',
                                        size=4,
                                        default=[1.0, 0.266, 0, 0.3])

    poly_count_check : bpy.props.IntProperty(
            name="Poly Count Check",
            description="Give a warning if the target object goes above this size",
            min=0,
            default=10000
    )

    enable_legacy_version : bpy.props.BoolProperty(
            name="Enable Legacy Version",
            description="Enable the old panel for the Mesh Materializer add-on",
            default=False
    )


    def draw(self, context):
        layout = self.layout
        col = layout.column()        
        col.alignment = 'CENTER'

        col.prop(self, "enable_legacy_version")

        if self.enable_legacy_version:
            row = col.row()
            row.prop(self, "add_face_color")
            row = col.row()
            row.prop(self, "del_face_color")
            col.separator()
            row = col.row()
            row.label(text="Number of polygons to warn at: ")
            row = row.row()
            row.prop(self, "poly_count_check", text="")

