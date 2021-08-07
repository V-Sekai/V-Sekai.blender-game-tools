import bpy
import math
import imp

from . import modifier


def get_quality(index, count, max_quality):
    return 1 - (index) / (count - 1) * (1 - max_quality)


class BGE_mod_lod(modifier.BGE_mod_default):
    label = "LOD"
    id = 'lod'
    url = "http://renderhjs.net/fbxbundle/#modifier_lod"
    type = 'MESH'
    icon = 'MOD_DECIM'
    priority = 999  # just after rename
    tooltip = 'Creates automatic LODs for all export meshes'

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    levels: bpy.props.IntProperty(
        default=3,
        min=2,
        max=6,
        subtype='FACTOR'
    )
    quality: bpy.props.FloatProperty(
        default=0.05,
        min=0.01,
        max=1,
        description="Maximum quality ratio.",
        subtype='FACTOR'
    )

    def _draw_info(self, layout):
        row = layout.row(align=True)
        row.prop(self, "levels", text="Steps", icon='AUTOMERGE_ON')
        row.prop(self, "quality", text="Quality", icon='AUTOMERGE_ON')

        col = layout.column(align=True)
        for i in range(0, self.levels):
            r = col.row()
            r.enabled = False
            icon = 'MESH_UVSPHERE' if i == 0 else 'MESH_ICOSPHERE'
            r.label(text="LOD{}".format(i), icon=icon)
            r = r.row()
            r.enabled = False
            r.alignment = 'RIGHT'
            r.label(text="{}%".format(math.ceil(get_quality(i, self.levels, self.quality) * 100)))
        # row_freeze = row.row()
        # row_freeze.enabled = self.merge_active
        # row_freeze.prop( self , "merge_distance")

    def process(self, bundle_info):
        # UNITY 	https://docs.unity3d.com/Manual/LevelOfDetail.html
        # UNREAL 	https://docs.unrealengine.com/en-us/Engine/Content/Types/StaticMeshes/HowTo/LODs
        # 			https://answers.unrealengine.com/questions/416995/how-to-import-lods-as-one-fbx-blender.html
        objects = bundle_info['meshes']

        if not objects:
            return

        for obj in objects:
            prefix = obj.name

            obj.name = "{}_LOD{}".format(prefix, 0)

            for i in range(1, self.levels):

                # Select
                bpy.ops.object.select_all(action="DESELECT")
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj

                # Copy & Decimate modifier
                bpy.ops.object.duplicate()
                bpy.context.object.name = "{}_LOD{}".format(prefix, i)
                bpy.ops.object.modifier_add(type='DECIMATE')
                bpy.context.object.modifiers["Decimate"].ratio = get_quality(i, self.levels, self.quality)

                # add them to "extras" so other modifiers won't process them
                bundle_info['extras'].append(bpy.context.object)
