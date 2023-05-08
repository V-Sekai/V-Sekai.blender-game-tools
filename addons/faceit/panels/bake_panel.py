import bpy
from bpy.props import BoolProperty
from bpy.types import Panel, UI_UL_list
from mathutils import Vector

from .ui import FACEIT_PT_Base
from ..core.retarget_list_utils import get_index_of_parent_collection_item
from ..core.faceit_utils import get_faceit_armature, using_rigify_armature
from ..panels.draw_utils import draw_text_block


class FACEIT_PT_BaseBake(FACEIT_PT_Base):
    UI_TABS = ('BAKE',)


def draw_bake_modifier_list(layout, context):
    '''Draw the bake object and modifier lists'''
    scene = context.scene
    col = layout.column(align=True)
    row = col.row()
    if scene.faceit_face_objects:
        row = col.row()
        active_item = scene.faceit_face_objects[scene.faceit_face_index]
        obj = active_item.get_object()
        found_mods = obj.modifiers
        # split = layout.split(factor=0.5)
        row.label(text="Objects")
        row.label(text="Bake Modifiers")
        row = col.row(align=True)
        split = row.split()
        split.template_list('FACE_OBJECTS_MODIFIERS_UL_list', '', scene,
                            'faceit_face_objects', scene, 'faceit_face_index')

        split.template_list('BAKE_MODIFIERS_UL_list', '', active_item,
                            'modifiers', active_item, 'active_mod_index')
        if found_mods:
            col_ul = row.column(align=True)
            col_ul.operator('faceit.move_bake_modifier', text='', icon='TRIA_UP').direction = 'UP'
            col_ul.operator('faceit.move_bake_modifier', text='', icon='TRIA_DOWN').direction = 'DOWN'


class FACEIT_PT_BakeExpressions(FACEIT_PT_BaseBake, Panel):
    bl_label = 'Bake Shape Keys'
    bl_options = set()
    bl_idname = 'FACEIT_PT_BakeExpressions'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        # row = col.row()
        # row.label(text='Bake and Finalize')
        # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/bake/')
        if context.scene.faceit_shapes_generated:
            row = col.row()
            row.label(text="Return")
            row = col.row(align=True)
            row.operator('faceit.back_to_rigging', icon='BACK')
        else:
            draw_bake_modifier_list(col, context)
            col.separator(factor=1.0)
            row = col.row(align=True)
            row.operator('faceit.generate_shapekeys', icon='USER')
        col.separator(factor=2)


class FACEIT_PT_ShapeKeyUtils(FACEIT_PT_BaseBake, Panel):
    bl_label = 'Shape Key Utils'
    bl_idname = 'FACEIT_PT_ShapeKeyUtils'
    faceit_predecessor = 'FACEIT_PT_RigUtils'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):

        layout = self.layout
        scene = context.scene
        col = layout.column()
        row = col.row(align=True)
        row.prop(context.preferences.addons["faceit"].preferences, 'dynamic_shape_key_ranges', icon='SHAPEKEY_DATA')

        if not context.preferences.addons["faceit"].preferences.dynamic_shape_key_ranges:
            row = col.row(align=True)
            row.label(text='Set Shape Key Slider Range')

            row = col.row()
            sub = row.column(align=True)
            # sk_options = scene.faceit_shape_key_options
            sub.prop(scene, 'faceit_shape_key_slider_min', text='Range Min')
            sub.prop(scene, 'faceit_shape_key_slider_max', text='Max')

            row = col.row(align=True)
            row.operator('faceit.set_shape_key_range')


class FACEIT_PT_RigUtils(FACEIT_PT_BaseBake, Panel):
    bl_label = 'Rig Utils'
    bl_idname = 'FACEIT_PT_RigUtils'
    faceit_predecessor = 'FACEIT_PT_BakeExpressions'

    @classmethod
    def poll(cls, context):
        if super().poll(context):  # and context.scene.faceit_armature
            return not using_rigify_armature()

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        scene = context.scene
        row = col.row()
        row.prop(scene, 'faceit_armature')
        rig = get_faceit_armature(force_original=True)
        if rig:
            row = col.row(align=True)
            row.operator('faceit.unhide_rig', icon='HIDE_ON')
            row = col.row(align=True)
            row.operator('faceit.reconnect_rig', icon='LINKED')
            body_rig = scene.faceit_body_armature
            if rig is not body_rig:
                col = col.box()
                row = col.row(align=False)
                row.label(text='Join to Body Armature')
                row = col.row(align=True)
                row.prop(scene, 'faceit_body_armature', text="Body Rig")
                if body_rig:
                    if body_rig.scale != Vector((1,) * 3):
                        draw_text_block(
                            layout=col,
                            text=f"Apply the scale on {body_rig.name} before joining!",
                            heading='WARNING'
                        )
                    row = col.row(align=True)
                    row.prop_search(scene, 'faceit_body_armature_head_bone',
                                    body_rig.data, 'bones', text='Bone')
                row = col.row(align=True)
                row.operator('faceit.join_with_body_armature')


class FACEIT_PT_Other(FACEIT_PT_BaseBake, Panel):
    bl_label = 'Other Utils'
    bl_idname = 'FACEIT_PT_Other'
    faceit_predecessor = 'FACEIT_PT_ShapeKeyUtils'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        if context.object:
            row = col.row(align=True)
            row.label(text='Apply Modifiers')

            row = col.row(align=True)
            row.operator('faceit.apply_modifier_object_with_shape_keys', icon='SHAPEKEY_DATA')
            row = col.row(align=True)
            row.label(text='Apply Shape Keys')
            row = col.row(align=True)
            row.operator('faceit.apply_shape_keys_to_mesh', icon='SHAPEKEY_DATA').obj_name = context.object.name


class FACEIT_PT_Finalize(FACEIT_PT_BaseBake, Panel):
    bl_label = 'Clean Up (Destructive)'
    bl_idname = 'FACEIT_PT_Finalize'
    faceit_predecessor = 'FACEIT_PT_Other'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator('faceit.cleanup_scene', icon='TRASH')
        row = layout.row(align=True)
        row.operator('faceit.cleanup_objects', text='Clean Up Objects', icon='TRASH')


class FACE_OBJECTS_MODIFIERS_UL_list(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.label(text=item.name, icon='OUTLINER_OB_MESH')
            # row.operator("faceit.draw_bake_modifiers", text="modifiers",
            #              emboss=True, icon='DOWNARROW_HLT').obj_name = item.name
        else:
            layout.alignment = 'CENTER'
            layout.label(text='',)


class BAKE_MODIFIERS_UL_list(bpy.types.UIList):
    filter_bake_only: BoolProperty(
        name='Bake Only',
        default=False,
        description='Show only modifiers that can be baked to shape keys.'
    )

    # def __init__(self) -> None:
    #     super().__init__()
    #     self.use_filter_show = True

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            layout.use_property_split = True
            layout.use_property_decorate = False

            row = layout.row(align=True)
            row.prop(item, 'name', text='', emboss=False, icon=item.mod_icon)
            if item.can_bake is False:
                row.enabled = False

            row = layout.row(align=True)
            # if item.type in BAKE_MOD_TYPES:
            obj_item = context.scene.faceit_face_objects[get_index_of_parent_collection_item(item)]
            obj = obj_item.get_object()
            if obj:
                mod = obj.modifiers.get(item.name)
                if mod:
                    row.prop(mod, 'show_viewport', text='', icon='RESTRICT_VIEW_ON')

            if item.can_bake:
                row.prop(item, 'bake', text='', icon='CHECKBOX_HLT' if item.bake else 'CHECKBOX_DEHLT')
            else:
                row.label(text='', icon='BLANK1')

    def draw_filter(self, context, layout):
        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = True
        row = col.row(align=True)
        row.prop(self, 'filter_bake_only', text='Hide Invalid', icon='FILTER')

    def filter_mod_items(self, bitflag, items, flags=None):
        ''' Filter mods and return true for bake only'''
        if not self.filter_bake_only or not items:
            return flags or []
        if not flags:
            flags = [0] * len(items)
        for i, item in enumerate(items):
            if item.can_bake:
                flags[i] |= bitflag
        return flags

    def filter_items(self, context, data, propname):
        ''' Filter and order items in a list '''
        items = getattr(data, "modifiers")
        filtered = []
        ordered = []
        filtered = self.filter_mod_items(self.bitflag_filter_item, items)
        return filtered, ordered
