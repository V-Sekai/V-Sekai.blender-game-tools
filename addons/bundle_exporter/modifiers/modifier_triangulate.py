import bpy
import imp

from . import modifier

bl_rna_properties = {x.identifier: {y.identifier: getattr(x, y.identifier) for y in x.bl_rna.properties} for x in bpy.types.TriangulateModifier.bl_rna.properties}

class BGE_mod_triangulate(modifier.BGE_mod_default):
    label = "Triangulate"
    id = 'triangulate'
    url = "http://renderhjs.net/fbxbundle/"
    type = 'MESH'
    icon = 'MOD_TRIANGULATE'
    tooltip = 'Applies the triangulate modifier (keeping normals)'
    priority = -1  # before the merge modifier

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    quad_method: bpy.props.EnumProperty(
        name=bl_rna_properties['quad_method']['name'],
        items=[(x.identifier, x.name, x.description) for x in bl_rna_properties['quad_method']['enum_items']],
        default=bl_rna_properties['quad_method']['default'],
        description=bl_rna_properties['quad_method']['description'],
    )

    ngon_method: bpy.props.EnumProperty(
        name=bl_rna_properties['ngon_method']['name'],
        items=[(x.identifier, x.name, x.description) for x in bl_rna_properties['ngon_method']['enum_items']],
        default=bl_rna_properties['ngon_method']['default'],
        description=bl_rna_properties['ngon_method']['description'],
    )

    min_vertices: bpy.props.IntProperty(
        name=bl_rna_properties['min_vertices']['name'],
        default=bl_rna_properties['min_vertices']['default'],
        description=bl_rna_properties['min_vertices']['description'],
        min=bl_rna_properties['min_vertices']['hard_min'],
        max=bl_rna_properties['min_vertices']['hard_max'],
    )

    keep_custom_normals: bpy.props.BoolProperty(
        name=bl_rna_properties['keep_custom_normals']['name'],
        default=bl_rna_properties['keep_custom_normals']['default'],
        description=bl_rna_properties['keep_custom_normals']['description'],
    )

    def _draw_info(self, layout):
        col = layout.column(align=False)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(self, "quad_method")
        col.prop(self, "ngon_method")
        col.prop(self, "min_vertices")
        col.prop(self, "keep_custom_normals")

    def process(self, bundle_info):
        meshes = bundle_info['meshes']

        if not meshes:
            return

        for mesh in meshes:
            mod = mesh.modifiers.new('export_triangulate', type='TRIANGULATE')

            mod.quad_method = self.quad_method
            mod.ngon_method = self.ngon_method
            mod.min_vertices = self.min_vertices
            mod.keep_custom_normals = self.keep_custom_normals
