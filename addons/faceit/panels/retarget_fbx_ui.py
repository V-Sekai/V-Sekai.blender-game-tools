
import bpy
from bpy.props import EnumProperty, IntProperty

from . import draw_utils
from .mocap_panel import FACEIT_PT_BaseMocap
from ..core import shape_key_utils as sk_utils


class FACEIT_PT_RetargetFBX(FACEIT_PT_BaseMocap, bpy.types.Panel):
    bl_label = 'Shape Key Retargeter (FBX)'
    bl_idname = 'FACEIT_PT_RetargetFBX'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_MocapSettings'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # col = layout.column(align=True)
        box = layout.box()
        col = box.column(align=True)

        retarget_fbx_props = scene.faceit_retarget_fbx_mapping

    # box_retarget_fbx = layout.box()
    # row = box_retarget_fbx.row()
    # draw_utils.draw_panel_dropdown_expander(row, retarget_fbx_props, 'expand_ui', 'Retarget FBX')
    # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/fbx_retargeting/')

    # if retarget_fbx_props.expand_ui:
        row = col.row()
        row.label(text='Source')
        row = col.row()
        row.prop(retarget_fbx_props, 'mapping_source', expand=True)
        if retarget_fbx_props.mapping_source == 'OBJECT':
            row = col.row()
            row.prop_search(retarget_fbx_props, 'source_obj', context.scene, "objects",
                            icon="OUTLINER_OB_MESH")  # Search Bar with picker
        else:
            row = col.row()
            row.prop_search(retarget_fbx_props, 'source_action', bpy.data, "actions",
                            icon="ACTION")  # Search Bar with picker
        row = col.row()
        row.label(text='Target')
        row = col.row()
        row.prop(retarget_fbx_props, 'mapping_target', expand=True)
        if retarget_fbx_props.mapping_target == 'TARGET':
            row = col.row()
            row.prop_search(retarget_fbx_props, 'target_obj', context.scene, "objects",
                            icon="OUTLINER_OB_MESH")  # Search Bar with picker

        row = col.row()
        row.label(text='Initialize')

        row = col.row()
        row.operator('faceit.init_fbx_retargeting', icon='FILE_REFRESH')

        if retarget_fbx_props.mapping_list:

            row = col.row()
            row.operator('faceit.init_fbx_retargeting', text='Reset', icon='LOOP_BACK').empty = True

            row = col.row()
            row.label(text='Source')
            row.label(text='Target')

            if retarget_fbx_props.mapping_list:
                col.template_list('FBX_RETARGET_UL_list', '', retarget_fbx_props,
                                  'mapping_list', retarget_fbx_props, 'mapping_list_index')

            row = col.row()
            row.label(text='Retarget')
            row = col.row()
            row.operator('faceit.retarget_fbx_action', text='Retarget Action', icon='ACTION')


class FACEIT_OT_DrawFBXTargetShapesList(bpy.types.Operator):
    bl_label = "Target Shapes"
    bl_idname = 'faceit.draw_fbx_target_shapes_list'

    target_shape_edit: EnumProperty(
        items=sk_utils.get_shape_keys_from_faceit_objects_enum, name='Change target Shape',
        description='Choose a Shape Key as target for retargeting this shape. \nThe shapes listed are from the Main Object registered in Setup panel.\n'
    )

    source_shape_index: IntProperty(
        name='Index of the Shape Item',
        default=0,
    )

    @classmethod
    def poll(cls, context):
        return context.scene.faceit_retarget_fbx_mapping.mapping_list

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self)

    def draw(self, context):

        layout = self.layout

        retarget_fbx_props = context.scene.faceit_retarget_fbx_mapping
        retarget_list = retarget_fbx_props.mapping_list

        shape_item = retarget_list[self.source_shape_index]

        row = layout.row()
        row.label(text='Source Shape: {}'.format(shape_item.display_name))

        row = layout.row()
        row.template_list('FBX_TARGET_SHAPES_UL_list', '', shape_item,
                          'target_shapes', shape_item, 'target_list_index')
        row = layout.row()

        op = row.operator('faceit.edit_fbx_target_shape', text='Add Target Shape', icon='ADD')
        op.index = shape_item.index

    def execute(self, context):
        return{'FINISHED'}


class FBX_TARGET_SHAPES_UL_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.use_property_split = True
            layout.use_property_decorate = False
            row = layout.row(align=True)
            row.prop(item, 'name', text='', emboss=False)

            op = row.operator('faceit.edit_fbx_target_shape', text='', icon='DOWNARROW_HLT')
            op.operation = 'CHANGE'
            op.index = item.parent_idx
            op.target_shape_index = item.index

            op = row.operator('faceit.remove_fbx_target_shape', text='', icon='X')
            op.parent_index = item.parent_idx
            op.target_shape_index = item.index


class FBX_RETARGET_UL_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            row = layout.row(align=True)

            retarget_fbx_props = context.scene.faceit_retarget_fbx_mapping

            if item.use_animation == True:
                icon = 'CHECKBOX_HLT'
            else:
                icon = 'CHECKBOX_DEHLT'

            row.prop(item, 'use_animation', text='', expand=False, icon=icon)
            sub = row.split(factor=.5, align=True)

            target_shapes = item.target_shapes

            sub.active = expression_enabled = item.use_animation and len(target_shapes) > 0

            # if item.index == retarget_fbx_props.mapping_list_index:
            #     icon = 'RESTRICT_SELECT_OFF'
            # else:
            #     icon = 'RESTRICT_SELECT_ON'

            sub.prop(item, 'display_name', emboss=False, text='')

            display_text = '---'
            if target_shapes:
                display_text = ', '.join([t.name for t in target_shapes])
            else:
                sub.active = False

            op = sub.operator('faceit.draw_fbx_target_shapes_list', text=display_text,
                              emboss=True, icon='DOWNARROW_HLT')
            op.source_shape_index = item.index

            op = row.operator('faceit.edit_fbx_target_shape', text='', icon='ADD')
            op.index = item.index

            row.operator('faceit.clear_fbx_target_shapes', text='', icon='TRASH').source_shape_name = item.name
