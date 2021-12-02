import bpy
from bpy.props import BoolProperty
from bpy.types import Panel
from . import draw_utils
from .ui import FACEIT_PT_Base


class FACEIT_PT_BaseBake(FACEIT_PT_Base):
    UI_TAB = 'BAKE'


class FACEIT_PT_ShapeKeyUtils(FACEIT_PT_BaseBake, Panel):
    bl_label = 'Shape Key Utils'
    bl_idname = 'FACEIT_PT_ShapeKeyUtils'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):

        layout = self.layout
        scene = context.scene

        col = layout.column()

        if not scene.faceit_face_objects:
            row = col.row()
            row.alert = True
            op = row.operator('faceit.go_to_tab', text='Complete Setup First...')
            op.tab = 'SETUP'
            col.enabled = False
        else:
            col.enabled = True

        col.separator()

        row = col.row(align=True)
        row.label(text='Set Shape Key Slider Range')

        row = col.row()
        sub = row.column(align=True)
        # sk_options = scene.faceit_shape_key_options
        sub.prop(scene, 'faceit_shape_key_slider_min', text='Range Min')
        sub.prop(scene, 'faceit_shape_key_slider_max', text='Max')

        row = col.row(align=True)
        row.operator('faceit.set_shape_key_range')

        row = col.row(align=True)
        row.label(text='Indices')
        row = col.row(align=True)
        row.operator('faceit.reorder_keys', icon='SHAPEKEY_DATA')

        row = col.row(align=True)
        row.label(text='Testing')
        row = col.row(align=True)
        row.operator('faceit.test_action', icon='ACTION')


class FACEIT_PT_Finalize(FACEIT_PT_BaseBake, Panel):
    bl_label = 'Finalize'
    bl_idname = 'FACEIT_PT_Finalize'
    faceit_predecessor = 'FACEIT_PT_ShapeKeyUtils'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator('faceit.cleanup_objects', icon='TRASH')
        row = layout.row(align=True)
        row.operator('faceit.cleanup_scene', icon='TRASH')
        row = layout.row(align=True)
        row.operator('faceit.clear_all_corrective_shapes', icon='SHAPEKEY_DATA').expression = 'ALL'


class FACEIT_PT_RigUtils(FACEIT_PT_BaseBake, Panel):
    bl_label = 'Rig Utils'
    bl_idname = 'FACEIT_PT_RigUtils'
    faceit_predecessor = 'FACEIT_PT_Finalize'

    @classmethod
    def poll(cls, context):
        return super().poll(context)  # and context.scene.faceit_armature

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        scene = context.scene
        row = col.row()
        row.prop(scene, 'faceit_armature')

        rig = scene.faceit_armature
        if rig:
            if rig != scene.faceit_body_armature:
                col = col.box()
                row = col.row(align=False)
                row.label(text='Join to Body Armature')

                row = col.row(align=True)
                row.prop(scene, 'faceit_body_armature')
                if scene.faceit_body_armature:
                    row = col.row(align=True)
                    row.prop_search(scene, 'faceit_body_armature_head_bone',
                                    scene.faceit_body_armature.data, 'bones', text='Bone')
                row = col.row(align=True)
                row.operator('faceit.join_with_body_armature')


class FACEIT_PT_Other(FACEIT_PT_BaseBake, Panel):
    bl_label = 'Other Utils'
    bl_idname = 'FACEIT_PT_Other'
    faceit_predecessor = 'FACEIT_PT_RigUtils'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        # box = layout.box()
        col = layout.column()

        # row = col.row(align=True)
        # row.label(text='Fixes')
        row = col.row(align=True)
        row.label(text='Apply Modifiers')

        row = col.row(align=True)
        row.operator('faceit.apply_modifier_object_with_shape_keys', icon='SHAPEKEY_DATA')

        row = col.row(align=True)
        row.label(text='Set Theme Vertex Size')
        row = col.row(align=True)

        sub = row.split(factor=.9, align=True)
        # bpy.context.preferences.themes[0].view_3d.vertex_size
        sub.prop(bpy.context.preferences.themes[0].view_3d, 'vertex_size')
        sub.operator('faceit.set_theme_vertex_size', text='3').vertex_size = 3
        sub.operator('faceit.set_theme_vertex_size', text='8').vertex_size = 8


def draw(context, layout, rig):

    scene = context.scene

    col = layout.column(align=True)

    col.use_property_split = True
    col.use_property_decorate = False

    row = col.row()
    row.label(text='Bake and Finalize')

    draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/bake/')

    col.separator()

    if context.scene.faceit_shapes_generated:
        row = col.row(align=True)
        row.operator('faceit.reset_to_rig', icon='BACK')

    row = col.row(align=True)
    row.operator('faceit.generate_shapekeys', icon='USER')

    col.separator(factor=1)
    row = col.row(align=True)
    row.alert = True

    # if not scene.faceit_face_objects:
    #     op = row.operator('faceit.go_to_tab', text='Complete Setup First...')
    #     op.tab = 'SETUP'

    # elif not rig:
    #     op = row.operator('faceit.go_to_tab', text='Generate Rig First...')
    #     op.tab = 'CREATE'

    # elif rig and not scene.faceit_shapes_generated:
    #     if not futils.get_faceit_armature_modifier(futils.get_main_faceit_object()):
    #         op = row.operator('faceit.go_to_tab', text='Bind Rig First...')
    #         op.tab = 'CREATE'
