
import bpy
from . import draw_utils
from .ui import FACEIT_PT_Base
from ..core.faceit_utils import get_faceit_armature


class FACEIT_PT_BaseExpressions(FACEIT_PT_Base):
    UI_TAB = 'EXPRESSIONS'

    @classmethod
    def poll(cls, context):
        if not super().poll(context):
            return False
        return bool(get_faceit_armature())


class FACEIT_PT_Expressions(FACEIT_PT_BaseExpressions, bpy.types.Panel):
    bl_label = 'Expressions'
    bl_options = set()
    bl_idname = 'FACEIT_PT_Expressions'

    @classmethod
    def poll(cls, context):
        if not super().poll(context):
            return False
        rig = get_faceit_armature()
        return rig.name in context.scene.objects

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        rig = get_faceit_armature()

        actions_disabled = rig.hide_viewport == True or scene.faceit_shapes_generated

        col = layout.column(align=True)

        # row = col.row()
        # row.label(text='Expressions')
        # if scene.faceit_version == 2:
        #     draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/expressions-2-0/')
        # else:
        #     draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/expressions/')

        # col.separator()

# START ####################### VERSION 2 ONLY #######################

        if not actions_disabled and scene.faceit_version == 2:

            box = col.box()
            row = box.row()
            draw_utils.draw_panel_dropdown_expander(row, scene, 'faceit_expression_init_expand_ui', 'Create      ')
            if scene.faceit_expression_init_expand_ui:
                col_above_list = box.column(align=True)

                if actions_disabled:
                    col_above_list.enabled = False

                row = col_above_list.row(align=True)
                row.operator('faceit.append_action_to_faceit_rig', text='Load Faceit Expressions', icon='ACTION')

                row = col_above_list.row(align=True)
                op = row.operator('faceit.append_action_to_faceit_rig',
                                  text='Load Custom Expressions', icon='IMPORT')
                op.load_custom_path = True

                row.operator('faceit.export_expressions', text='Export Custom Expressions',  icon='EXPORT')

                row = col_above_list.row(align=True)
                op = row.operator('faceit.add_expression_item', text='Add Custom Expression', icon='ADD')
                op.custom_shape = True

# END ######################### VERSION 2 ONLY #######################

        if actions_disabled:
            row = col.row()
            row.template_list('FACEIT_UL_ExpressionsBaked', '', bpy.context.scene,
                              'faceit_expression_list', scene, 'faceit_expression_list_index')
            row = col.row(align=True)
            row.prop(scene, 'faceit_sync_shapes_index', icon='UV_SYNC_SELECT')
            if scene.faceit_sync_shapes_index:
                # row = col.row()
                if scene.faceit_shape_key_lock:
                    pin_icon = 'PINNED'
                else:
                    pin_icon = 'UNPINNED'
                row.prop(scene, 'faceit_shape_key_lock', icon=pin_icon)

        elif 'faceit_shape_action' in bpy.data.actions and scene.faceit_expression_list:

            col.separator()

            row = col.row()
            row.template_list('FACEIT_UL_Expressions', '', bpy.context.scene,
                              'faceit_expression_list', scene, 'faceit_expression_list_index')

            col_ul = row.column(align=True)

# START ####################### VERSION 2 ONLY #######################

            if scene.faceit_version == 2:

                row = col_ul.row(align=True)
                op = row.operator('faceit.add_expression_item', text='', icon='ADD')
                op.custom_shape = True

                row = col_ul.row(align=True)
                op = row.operator('faceit.remove_expression_item', text='', icon='REMOVE')
                # op.prompt = False

# END ######################### VERSION 2 ONLY #######################

            col_ul.separator()
            col_ul.row().menu('FACEIT_MT_ExpressionList', text='', icon='DOWNARROW_HLT')
            col_ul.separator()

            # Move the indices
            row = col_ul.row(align=True)
            op = row.operator('faceit.move_expression_item', text='', icon='TRIA_UP')
            op.direction = 'UP'

            row = col_ul.row(align=True)
            op = row.operator('faceit.move_expression_item', text='', icon='TRIA_DOWN')
            op.direction = 'DOWN'

            # col.separator()
            # box_options = col.box()


class FACEIT_PT_ExpressionOptions(FACEIT_PT_BaseExpressions, bpy.types.Panel):
    bl_label = 'Options'
    bl_idname = 'FACEIT_PT_ExpressionOptions'
    bl_options = set()
    faceit_predecessor = 'FACEIT_PT_Expressions'

    @classmethod
    def poll(cls, context):
        if not super().poll(context):
            return False
        scene = context.scene
        rig = scene.faceit_armature
        if rig.hide_viewport == True or scene.faceit_shapes_generated:
            return False
        return 'faceit_shape_action' in bpy.data.actions and scene.faceit_expression_list

    def draw(self, context):
        layout = self.layout

        scene = context.scene
        # row = box_options.row()
        # draw_utils.draw_panel_dropdown_expander(
        #     row, scene, 'faceit_expression_options_expand_ui', 'Options      ')
        # if scene.faceit_expression_options_expand_ui:

        col = layout.column(align=True)

        row = col.row(align=True)
        row.prop(scene, 'faceit_use_corrective_shapes', icon='SCULPTMODE_HLT')
        if scene.faceit_use_corrective_shapes:
            row = col.row(align=True)
            row.prop(scene, 'faceit_try_mirror_corrective_shapes', expand=True, icon='MOD_MIRROR')

            if scene.faceit_try_mirror_corrective_shapes:
                row.prop(scene, 'faceit_shape_key_mirror_use_topology', expand=True, icon='UV_VERTEXSEL')
        col.separator()

        row = col.row(align=True)
        row.prop(scene, 'faceit_use_auto_mirror_x',
                 text='Auto Mirror X', icon='MOD_MIRROR')
        row = col.row(align=True)
        row.prop(scene.tool_settings, 'use_keyframe_insert_auto', icon='RADIOBUT_ON')


class FACEIT_UL_Expressions(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            scene = context.scene
            # if not bpy.context.scene.faceit_shapes_generated:
            row = layout.row(align=True)
            row.prop(item, 'name', text='', emboss=False, icon='KEYFRAME')

            if item.mirror_name:
                op = row.operator('faceit.mirror_overwrite', text='', icon='MOD_MIRROR')
                op.expression_to_mirror = item.name
            elif scene.faceit_use_auto_mirror_x:
                row.label(text='', icon='MOD_MIRROR')

            op = row.operator('faceit.pose_amplify', text='', icon='ARROW_LEFTRIGHT')
            op.expression_index = scene.faceit_expression_list.find(item.name)
            op = row.operator('faceit.reset_expression', text='', icon='LOOP_BACK')
            op.expression_to_reset = item.name
            if scene.faceit_use_corrective_shapes:
                op = row.operator('faceit.add_corrective_shape_key_to_expression', text='', icon='SCULPTMODE_HLT')
                op.expression = item.name
                _emboss = False
                if item.corr_shape_key:
                    _emboss = True
                    op = row.operator('faceit.remove_corrective_shape_key', text='', emboss=_emboss, icon='X')
                    op.expression = item.name
                else:
                    op = row.operator('faceit.remove_corrective_shape_key',
                                      text='', emboss=_emboss, icon='RADIOBUT_OFF')
                    op.expression = item.name
                    # row.label(text='', emboss=_emboss, icon='RADIOBUT_OFF')
                    # row.separator_spacer()


class FACEIT_UL_ExpressionsBaked(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            scene = context.scene
            # if not bpy.context.scene.faceit_shapes_generated:
            row = layout.row(align=True)
            row.prop(item, 'name', text='', emboss=False, icon='KEYFRAME')


class FACEIT_MT_ExpressionList(bpy.types.Menu):
    bl_label = 'Expression List Menu'

    def draw(self, context):

        layout = self.layout

        scene = context.scene

# START ####################### VERSION 2 ONLY #######################

        if scene.faceit_version == 2:
            row = layout.row()
            row.operator('faceit.clear_faceit_expressions', icon='TRASH')

# END ######################### VERSION 2 ONLY #######################

        row = layout.row(align=True)
        op = row.operator('faceit.pose_amplify', text='Amplify All Expressions', icon='ARROW_LEFTRIGHT')

        row = layout.row(align=True)
        op = row.operator('faceit.reset_expression', text='Reset All Expressions', icon='LOOP_BACK')
        op.expression_to_reset = 'ALL'

        row = layout.row(align=True)
        row.operator('faceit.set_timeline', text='Timeline to Pose', icon='TIME')

        row = layout.row(align=True)
        op = row.operator('faceit.force_zero_frames', icon='KEYFRAME')


# def draw(context, layout, landmarks_obj, rig):

#     scene = context.scene

#     if not rig:
#         col = layout.column()
#         row = col.row()
#         row.alert = True
#         op = row.operator('faceit.go_to_tab', text='Generate Rig First...')
#         op.tab = 'CREATE'

#     else:
#         actions_disabled = rig.hide_viewport == True or scene.faceit_shapes_generated

#         col = layout.column(align=True)

#         row = col.row()
#         row.label(text='Expressions')
#         if scene.faceit_version == 2:
#             draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/expressions-2-0/')
#         else:
#             draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/expressions/')

#         col.separator()

# # START ####################### VERSION 2 ONLY #######################

#         if not actions_disabled and scene.faceit_version == 2:

#             box = col.box()
#             row = box.row()
#             draw_utils.draw_panel_dropdown_expander(row, scene, 'faceit_expression_init_expand_ui', 'Create      ')
#             if scene.faceit_expression_init_expand_ui:
#                 col_above_list = box.column(align=True)

#                 if actions_disabled:
#                     col_above_list.enabled = False

#                 row = col_above_list.row(align=True)
#                 row.operator('faceit.append_action_to_faceit_rig', text='Load Faceit Expressions', icon='ACTION')

#                 row = col_above_list.row(align=True)
#                 op = row.operator('faceit.append_action_to_faceit_rig',
#                                   text='Load Custom Expressions', icon='IMPORT')
#                 op.load_custom_path = True

#                 row.operator('faceit.export_expressions', text='Export Custom Expressions',  icon='EXPORT')

#                 row = col_above_list.row(align=True)
#                 op = row.operator('faceit.add_expression_item', text='Add Custom Expression', icon='ADD')
#                 op.custom_shape = True

# # END ######################### VERSION 2 ONLY #######################

#         if actions_disabled:
#             row = col.row()
#             row.template_list('FACEIT_UL_ExpressionsBaked', '', bpy.context.scene,
#                               'faceit_expression_list', scene, 'faceit_expression_list_index')
#             row = col.row(align=True)
#             row.prop(scene, 'faceit_sync_shapes_index', icon='UV_SYNC_SELECT')
#             if scene.faceit_sync_shapes_index:
#                 # row = col.row()
#                 if scene.faceit_shape_key_lock:
#                     pin_icon = 'PINNED'
#                 else:
#                     pin_icon = 'UNPINNED'
#                 row.prop(scene, 'faceit_shape_key_lock', icon=pin_icon)

#         elif 'faceit_shape_action' in bpy.data.actions and scene.faceit_expression_list:

#             col.separator()

#             row = col.row()
#             row.template_list('FACEIT_UL_Expressions', '', bpy.context.scene,
#                               'faceit_expression_list', scene, 'faceit_expression_list_index')

#             col_ul = row.column(align=True)

# # START ####################### VERSION 2 ONLY #######################

#             if scene.faceit_version == 2:

#                 row = col_ul.row(align=True)
#                 op = row.operator('faceit.add_expression_item', text='', icon='ADD')
#                 op.custom_shape = True

#                 row = col_ul.row(align=True)
#                 op = row.operator('faceit.remove_expression_item', text='', icon='REMOVE')
#                 # op.prompt = False

# # END ######################### VERSION 2 ONLY #######################

#             col_ul.separator()
#             col_ul.row().menu('FACEIT_MT_ExpressionList', text='', icon='DOWNARROW_HLT')
#             col_ul.separator()

#             # Move the indices
#             row = col_ul.row(align=True)
#             op = row.operator('faceit.move_expression_item', text='', icon='TRIA_UP')
#             op.direction = 'UP'

#             row = col_ul.row(align=True)
#             op = row.operator('faceit.move_expression_item', text='', icon='TRIA_DOWN')
#             op.direction = 'DOWN'

#             col.separator()
#             box_options = col.box()

#             row = box_options.row()
#             draw_utils.draw_panel_dropdown_expander(row, scene, 'faceit_expression_options_expand_ui', 'Options      ')
#             if scene.faceit_expression_options_expand_ui:

#                 col_opt = box_options.column(align=True)

#                 row = col_opt.row(align=True)
#                 row.prop(scene, 'faceit_use_corrective_shapes', icon='SCULPTMODE_HLT')
#                 if scene.faceit_use_corrective_shapes:
#                     row = col_opt.row(align=True)
#                     row.prop(scene, 'faceit_try_mirror_corrective_shapes', expand=True, icon='MOD_MIRROR')

#                     if scene.faceit_try_mirror_corrective_shapes:
#                         row.prop(scene, 'faceit_shape_key_mirror_use_topology', expand=True, icon='UV_VERTEXSEL')
#                 col_opt.separator()

#                 row = col_opt.row(align=True)
#                 row.prop(scene, 'faceit_use_auto_mirror_x',
#                          text='Auto Mirror X', icon='MOD_MIRROR')
#                 row = col_opt.row(align=True)
#                 row.prop(scene.tool_settings, 'use_keyframe_insert_auto', icon='RADIOBUT_ON')
