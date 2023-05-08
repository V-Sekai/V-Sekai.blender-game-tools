
import bpy

from .ui import FACEIT_PT_BaseSub

from ..core.retarget_list_base import (DrawTargetShapesListBase,
                                       TargetShapesListBase)
from ..core.retarget_list_utils import get_index_of_collection_item


class FACEIT_PT_RetargetFBX(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Shape Key Retargeter (FBX)'
    bl_idname = 'FACEIT_PT_RetargetFBX'
    bl_parent_id = 'FACEIT_PT_MocapUtils'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_MocapMotionTargets'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)

        retarget_fbx_props = scene.faceit_retarget_fbx_mapping

    # box_retarget_fbx = layout.box()
    # row = box_retarget_fbx.row()
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

        row = col.row(align=True)
        row.operator('faceit.init_fbx_retargeting', icon='FILE_REFRESH')

        if retarget_fbx_props.mapping_list:

            row.operator('faceit.init_fbx_retargeting', text='Reset', icon='LOOP_BACK').empty = True

            row = col.row()
            row.label(text='Retarget')
            row = col.row()
            row.operator('faceit.retarget_fbx_action', text='Retarget Action', icon='ACTION')

            # col.separator()
            row = col.row()
            row.label(text='Source')
            row.label(text='Target')
            if retarget_fbx_props.mapping_list:
                col.template_list('FACEIT_UL_FBXRetargetList', '', retarget_fbx_props,
                                  'mapping_list', retarget_fbx_props, 'mapping_list_index')


class FACEIT_UL_FbxTargetShapesList(TargetShapesListBase, bpy.types.UIList):

    # the edit target shapes operator
    edit_target_shapes_operator = 'faceit.edit_fbx_target_shape'
    # the edit target shapes operator
    remove_target_shapes_operator = 'faceit.remove_fbx_target_shape'


class FACEIT_OT_DrawFBXTargetShapesList(DrawTargetShapesListBase, bpy.types.Operator):
    bl_idname = 'faceit.draw_fbx_target_shapes_list'

    @classmethod
    def poll(cls, context):
        return super().poll(context) and context.scene.faceit_retarget_fbx_mapping.mapping_list

    edit_target_shapes_operator = 'faceit.edit_fbx_target_shape'
    target_shapes_list = 'FACEIT_UL_FbxTargetShapesList'
    use_display_name = False

    @staticmethod
    def get_retarget_shapes():
        return bpy.context.scene.faceit_retarget_fbx_mapping.mapping_list


class FACEIT_UL_FBXRetargetList(bpy.types.UIList):
    show_use_animation = True
    # the edit target shapes operator
    edit_target_shapes_operator = 'faceit.edit_fbx_target_shape'
    # the clear target shapes operator
    clear_target_shapes_operator = 'faceit.clear_fbx_target_shapes'

    draw_target_shapes_operator = 'faceit.draw_fbx_target_shapes_list'

    def draw_alert(self, item):
        ''' if return statement is true the row is red. '''
        return False
        # sk_names = get_shape_key_names_from_objects()
        # return any([item.name not in sk_names for item in item.target_shapes])

    def draw_active(self, item):
        ''' If the return statement is false the row is drawn deactivated '''
        return bool(item.use_animation and item.target_shapes)

    def get_display_text_target_shapes(self, item):
        display_text = '---'
        if item.target_shapes:
            display_text = ', '.join([t.name for t in item.target_shapes])
        return display_text

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        self.use_filter_show = True

        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            row = layout.row(align=True)

            first_col = row.row(align=True)

            if self.show_use_animation:

                if item.use_animation is True:
                    icon = 'CHECKBOX_HLT'
                else:
                    icon = 'CHECKBOX_DEHLT'

                first_col.prop(item, 'use_animation', text='', expand=False, icon=icon)

            second_col = row.row(align=True)

            second_col.alert = self.draw_alert(item)
            second_col.enabled = self.draw_active(item)

            second_col.prop(item, 'name', emboss=False, text='')

            op = second_col.operator(self.draw_target_shapes_operator, text=self.get_display_text_target_shapes(item),
                                     emboss=True, icon='DOWNARROW_HLT')
            op.source_shape = item.name

            third_col = row.row(align=True)

            op = third_col.operator(self.edit_target_shapes_operator, text='', icon='ADD')
            op.source_shape_index = get_index_of_collection_item(item)

            third_col.operator(self.clear_target_shapes_operator, text='', icon='TRASH').source_shape_name = item.name
