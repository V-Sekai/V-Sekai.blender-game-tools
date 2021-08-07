import bpy
import mathutils
import imp

from . import modifier


class BGE_mod_transform_helpers(modifier.BGE_mod_default):
    label = "Scale Empties"
    id = 'transform_helpers'
    url = "http://renderhjs.net/fbxbundle/"
    type = 'HELPER'
    icon = 'EMPTY_ARROWS'
    tooltip = 'Applies the desired scale to all exported empties'

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    scale: bpy.props.FloatVectorProperty(default=(0.01, 0.01, 0.01), subtype='XYZ', size=3)
    rotation: bpy.props.FloatVectorProperty(default=(90.0, 0.0, 0.0), subtype='XYZ', size=3)

    def _draw_info(self, layout):
        row = layout.row(align=True)
        row.prop(self, "scale", text="Scale")

    def process(self, bundle_info):
        helpers = bundle_info['empties']

        if not helpers:
            return

        for x in helpers:
            new_scale = mathutils.Vector((x.scale.x * self.scale.x, x.scale.y * self.scale.y, x.scale.z * self.scale.z))
            x.scale = new_scale
