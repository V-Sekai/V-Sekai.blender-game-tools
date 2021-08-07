import bpy
import imp

from . import modifier


class BGE_mod_set_origin(modifier.BGE_mod_default):
    label = "Set origin to pivot"
    id = 'set_origin'
    url = "http://renderhjs.net/fbxbundle/"
    type = 'MESH'
    icon = 'OBJECT_ORIGIN'
    tooltip = 'Applies the pivot of the bundle to all the meshes (changes their origin)'
    priority = 200

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    def _draw_info(self, layout):
        pass

    def process(self, bundle_info):
        objects = bundle_info['meshes']

        if not objects:
            return

        pivot = bundle_info['pivot']
        bpy.context.scene.cursor.location = pivot

        bpy.ops.object.select_all(action='DESELECT')
        for x in objects:
            x.select_set(True)

        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        pass
