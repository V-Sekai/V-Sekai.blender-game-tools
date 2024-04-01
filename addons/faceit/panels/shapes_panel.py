
import os

import bpy


from .draw_utils import draw_text_block
from ..ctrl_rig.control_rig_utils import is_control_rig_connected

from ..core import faceit_data as fdata
from ..core.retarget_list_base import (DrawRegionsFilterBase,
                                       DrawTargetShapesListBase,
                                       ResetRegionsOperatorBase,
                                       RetargetShapesListBase,
                                       TargetShapesListBase)
from ..retargeting.retarget_list_operators import get_active_retarget_list

from .ui import FACEIT_PT_Base, FACEIT_PT_BaseSub


class FACEIT_PT_BaseRetargetShapes(FACEIT_PT_Base):
    UI_TABS = ('SHAPES',)
    weblink = "https://faceit-doc.readthedocs.io/en/latest/target_shapes/"


class FACEIT_PT_TargetShapeLists(FACEIT_PT_BaseRetargetShapes, bpy.types.Panel):
    bl_label = 'Target Shapes'
    bl_options = set()
    bl_idname = 'FACEIT_PT_TargetShapeLists'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout

        scene = context.scene
        ctrl_rig_connected = False
        ctrl_rig = scene.faceit_control_armature
        if ctrl_rig is not None:
            ctrl_rig_connected = is_control_rig_connected(ctrl_rig)

        col = layout.column(align=True)

        box = col.box()
        row = box.row()
        row.label(text='Display Expressions')
        row = box.row()
        row.prop(scene, 'faceit_display_retarget_list', expand=True)

        col.separator()

        if scene.faceit_display_retarget_list == 'ARKIT':
            # ARKIT
            col_arkit = col.column(align=True)
            if scene.faceit_arkit_retarget_shapes:
                row = col_arkit.row()
                row.label(text='  Source Shape')
                row.label(text='Target Shape')
                col_arkit.template_list('FACEIT_UL_ShapeRetargetList', '', bpy.context.scene,
                                        'faceit_arkit_retarget_shapes', scene, 'faceit_arkit_retarget_shapes_index')
                row = col_arkit.row(align=True)
                row.operator('faceit.reset_expression_values', icon='LOOP_BACK')
                if ctrl_rig_connected:
                    col_arkit.enabled = False
            else:
                row = col_arkit.row(align=True)
                row.operator_context = 'EXEC_DEFAULT'
                op = row.operator('faceit.init_retargeting', text='Find ARKit Shapes', icon='LONGDISPLAY')
                op.expression_sets = 'ARKIT'
                row = col_arkit.row()
                row.label(text='Capture Profiles')

                row = col_arkit.row(align=True)
                row.operator_context = 'INVOKE_DEFAULT'

                row.operator('faceit.import_retargeting_map', text='Load Profile').expression_sets = 'ARKIT'
                row.menu('FACEIT_MT_PresetImport', text='', icon='DOWNARROW_HLT')
                row.operator('faceit.export_retargeting_map', text='Save Profile').expression_sets = 'ARKIT'
            if ctrl_rig_connected:
                draw_text_block(
                    context,
                    col,
                    text="Can't edit ARKit target shapes while the control rig is connected. See CONTROL tab.",
                    heading="WARNING")
                # Disable Panel if the control rig is connected.
                # .... Or disable each expression individually if they are connected to drivers..
                # ctrl_rig = scene.faceit_control_armature
                # if ctrl_rig is not None:
                #     if is_control_rig_connected(ctrl_rig):
                #         col_arkit.enabled = False
        elif scene.faceit_display_retarget_list == 'A2F':
            # A2F
            a2f_col = col.column(align=True)
            if scene.faceit_a2f_retarget_shapes:
                row = a2f_col.row()
                row.label(text='  Source Shape')
                row.label(text='Target Shape')
                a2f_col.template_list('FACEIT_UL_ShapeRetargetList', '', bpy.context.scene,
                                      'faceit_a2f_retarget_shapes', scene, 'faceit_a2f_retarget_shapes_index')
                row = a2f_col.row(align=True)
                row.operator('faceit.reset_expression_values', icon='LOOP_BACK')
            else:
                row = a2f_col.row(align=True)
                row.operator_context = 'EXEC_DEFAULT'
                op = row.operator('faceit.init_retargeting', text='Find A2F Shapes', icon='LONGDISPLAY')
                op.expression_sets = 'A2F'
                row = a2f_col.row()
                row.label(text='Capture Profiles')

                row = a2f_col.row(align=True)
                row.operator_context = 'INVOKE_DEFAULT'
                row.operator('faceit.import_retargeting_map', text='Load Profile').expression_sets = 'A2F'
                # row.menu('FACEIT_MT_PresetImport', text='', icon='DOWNARROW_HLT')
                row.operator('faceit.export_retargeting_map', text='Save Profile').expression_sets = 'A2F'


class FACEIT_PT_RetargetShapesSetup(FACEIT_PT_BaseRetargetShapes, bpy.types.Panel):
    bl_label = 'Target Shapes Setup'
    bl_options = set()
    bl_idname = 'FACEIT_PT_RetargetShapesSetup'
    faceit_predecessor = 'FACEIT_PT_TargetShapeLists'

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            scene = context.scene
            if scene.faceit_display_retarget_list == 'ARKIT' and scene.faceit_arkit_retarget_shapes:
                ctrl_rig = scene.faceit_control_armature
                if ctrl_rig is not None:
                    if is_control_rig_connected(ctrl_rig):
                        return False
                return True
            if scene.faceit_display_retarget_list == 'A2F' and scene.faceit_a2f_retarget_shapes:
                return True

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        box = layout.box()
        col = box.column(align=True)

        if not scene.faceit_face_objects:
            row = col.row()
            row.alert = True
            op = row.operator('faceit.go_to_tab', text='Register Objects First...')
            op.tab = 'SETUP'
        else:
            # row = col.row()
            # row.label(text='Setup')

            row = col.row(align=True)
            op = row.operator('faceit.init_retargeting', text='Find Target Shapes', icon='FILE_REFRESH')
            op.expression_sets = scene.faceit_display_retarget_list
            row = col.row(align=True)
            op = row.operator('faceit.reset_retarget_shapes', text='Reset', icon='TRASH')
            op.expression_sets = scene.faceit_display_retarget_list
            col.separator(factor=.5)
            row = col.row(align=True)
            row.operator('faceit.set_default_regions', text='Reset Regions', icon='LOOP_BACK')
            row.operator('faceit.set_default_amplify_values', text='Reset Amplify', icon='LOOP_BACK')

            row = col.row()
            row.label(text='Capture Profiles')
            row = col.row(align=True)

            row.operator_context = 'INVOKE_DEFAULT'
            op = row.operator('faceit.import_retargeting_map', text='Load Profile')
            op.expression_sets = scene.faceit_display_retarget_list
            if scene.faceit_display_retarget_list == 'ARKIT':
                row.menu('FACEIT_MT_PresetImport', text='', icon='DOWNARROW_HLT')

            op = row.operator('faceit.export_retargeting_map', text='Save Profile')
            op.expression_sets = scene.faceit_display_retarget_list


class FACEIT_PT_RenameTargetShapes(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'ARKit Name Scheme'
    bl_idname = 'FACEIT_PT_RenameTargetShapes'
    bl_parent_id = 'FACEIT_PT_RetargetShapesSetup'

    @classmethod
    def poll(cls, context):
        scene = context.scene
        return scene.faceit_display_retarget_list == 'ARKIT' and scene.faceit_arkit_retarget_shapes

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        scene = context.scene
        row = col.row()
        row.label(text='Names and Indices')
        row = col.row()
        row.prop(scene, 'faceit_retargeting_naming_scheme', text='Name Scheme', expand=True)

        row = col.row()
        row.operator('faceit.retarget_names', icon='FILE_FONT')
        row = col.row()
        row.operator_context = 'EXEC_DEFAULT'
        row.operator('faceit.reorder_keys', icon='FILE_FONT').order = scene.faceit_retargeting_naming_scheme
        row.operator_context = 'INVOKE_DEFAULT'


class FACEIT_UL_TargetShapes(TargetShapesListBase, bpy.types.UIList):
    # the edit target shapes operator
    edit_target_shapes_operator = 'faceit.edit_target_shape'
    # the edit target shapes operator
    remove_target_shapes_operator = 'faceit.remove_target_shape'


class FACEIT_OT_DrawTargetShapesList(DrawTargetShapesListBase, bpy.types.Operator):
    bl_label = "Target Shapes"
    bl_idname = 'faceit.draw_target_shapes_list'

    edit_target_shapes_operator = 'faceit.edit_target_shape'
    target_shapes_list = 'FACEIT_UL_TargetShapes'
    use_display_name = True

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    @staticmethod
    def get_retarget_shapes():
        ''' Get the retarget_list property group '''
        return get_active_retarget_list()
        # return bpy.context.scene.faceit_arkit_retarget_shapes

# --------------- Expression Retarget Listen  --------------------
# | - ARKit retarget shapes
# | - A2F retarget shapes
# ----------------------------------------------


class FACEIT_UL_ShapeRetargetList(RetargetShapesListBase, bpy.types.UIList):
    # the edit target shapes operator
    edit_target_shapes_operator = 'faceit.edit_target_shape'
    # the remove target shapes operator
    remove_target_shapes_operator = 'faceit.remove_target_shape'
    # the clear target shapes operator
    clear_target_shapes_operator = 'faceit.clear_target_shapes'

    draw_target_shapes_operator = 'faceit.draw_target_shapes_list'

    draw_region_filter_operator = 'faceit.draw_regions_filter'
    reset_regions_filter_operator = 'faceit.reset_regions_filter'

    property_name = 'display_name'


class FACEIT_MT_PresetImport(bpy.types.Menu):
    bl_label = 'Import Retargeting Preset'

    file_path = fdata.get_retargeting_presets()

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = 'EXEC_DEFAULT'
        row = layout.row()
        row.operator('faceit.import_retargeting_map', text='CC4').filepath = os.path.join(self.file_path, 'cc4.json')
        row = layout.row()
        row.operator('faceit.import_retargeting_map', text='CC3+').filepath = os.path.join(self.file_path, 'cc3+.json')
        row = layout.row()
        row.operator('faceit.import_retargeting_map', text='CC3').filepath = os.path.join(self.file_path, 'cc3.json')
        row = layout.row()
        row.operator(
            'faceit.import_retargeting_map', text='DazGen8').filepath = os.path.join(
            self.file_path, 'daz_gen8.json')


class FACEIT_OT_DrawRegionsFilter(DrawRegionsFilterBase, bpy.types.Operator):
    ''' Filter the displayed expressions by face regions'''

    bl_label = "Filter Regions"
    bl_idname = 'faceit.draw_regions_filter'

    @classmethod
    def poll(cls, context):
        return super().poll(context)


class FACEIT_OT_ResetRegionsFilter(ResetRegionsOperatorBase, bpy.types.Operator):
    ''' Reset the regions filter to default settings'''
    bl_idname = 'faceit.reset_regions_filter'

    @staticmethod
    def get_face_regions(context):
        # return get_active_retarget_list()
        return context.scene.faceit_face_regions
