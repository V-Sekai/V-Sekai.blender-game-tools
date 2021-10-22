import bpy
import bmesh
import imp

from . import modifier


class BGE_mod_custom_pivot(modifier.BGE_mod_default):
    label = "Custom Pivot"
    id = 'custom_pivot'
    url = "http://renderhjs.net/fbxbundle/"
    type = 'MESH'
    icon = 'EMPTY_ARROWS'
    priority = -999
    tooltip = 'Assign a custom pivot by choosing a source object'

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    source: bpy.props.StringProperty()

    def _warning(self):
        return self.source not in bpy.context.scene.objects

    def _draw_info(self, layout):
        layout.prop_search(self, "source", bpy.context.scene, "objects", text="Source")

    def process(self, bundle_info):
        source = self.get_object_from_name(self.source)
        if source:
            bundle_info['pivot'] = source.location
