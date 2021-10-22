import bpy
import bmesh
import imp

from . import modifier

from ..settings import prefix_copy
from bl_ui.properties_data_modifier import DATA_PT_modifiers


class BGE_mod_copy_modifiers(modifier.BGE_mod_default):
    label = "Copy Modifiers"
    id = 'copy_modifiers'
    url = "http://renderhjs.net/fbxbundle/#modifier_modifiers"
    type = 'MESH'
    icon = 'MODIFIER_DATA'
    tooltip = 'Copies all the modifiers from the selected source object to all the export meshes'

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    source: bpy.props.StringProperty()

    replace_references: bpy.props.BoolProperty(default=True)

    def _draw_info(self, layout):
        row = layout.row(align=True)
        row.prop_search(self, "source", bpy.context.scene, "objects", text="Source")

        if self.source in bpy.data.objects:
            mp = DATA_PT_modifiers(bpy.context)
            row = layout.row()
            row.enabled = False

            modifiers = bpy.data.objects[self.source].modifiers
            count = len(modifiers)
            row.label(text="copies {}x modifiers".format(count))

            for x in modifiers:
                box = layout.template_modifier(x)
                #box = layout.box()
                if box:
                    getattr(mp, x.type)(box, bpy.data.objects[self.source], x)

    def process(self, bundle_info):
        objects = bundle_info['meshes']
        if not objects:
            return

        source = self.get_object_from_name(self.source)

        if source:
            bpy.ops.object.select_all(action="DESELECT")

            for obj in objects:
                obj.select_set(True)

            source.select_set(True)
            bpy.context.view_layer.objects.active = source

            bpy.ops.object.make_links_data(type='MODIFIERS')

            if self.replace_references:
                for obj in objects:
                    for mod in obj.modifiers:
                        if hasattr(mod, 'object'):
                            if mod.object.name.startswith(prefix_copy):
                                if mod.object['__orig_name__'] in bpy.data.objects.keys():
                                    mod.object = bpy.data.objects[mod.object['__orig_name__']]

            source.select_set(False)
        else:
            print('MODIFIER_COPY_MODIFIERS source not found')
