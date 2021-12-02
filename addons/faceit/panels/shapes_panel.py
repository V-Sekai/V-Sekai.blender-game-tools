
from ..core import shape_key_utils as sk_utils
from ..core import faceit_data as fdata
from ..panels import draw_utils
import bpy
from bpy.props import EnumProperty, IntProperty

from.ui import FACEIT_PT_Base


class FACEIT_PT_BaseArkitShapes(FACEIT_PT_Base):
    UI_TAB = 'SHAPES'


class FACEIT_PT_ArkitTargetShapes(FACEIT_PT_BaseArkitShapes, bpy.types.Panel):
    bl_label = 'ARKit Target Shapes'
    bl_options = set()
    bl_idname = 'FACEIT_PT_ArkitTargetShapes'

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            return context.scene.faceit_retarget_shapes

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        col = layout.column()

        row = col.row()
        # row.operator('faceit.set_active_target_shapes', text='', icon='CHECKBOX_DEHLT').inverse = True
        row.label(text='  Source Shape')
        row.label(text='Target Shape')

        col.template_list('SHAPE_RETARGET_UL_list', '', bpy.context.scene,
                          'faceit_retarget_shapes', scene, 'faceit_retarget_shapes_index')
        row = col.row(align=True)
        row.prop(scene, 'faceit_sync_shapes_index', icon='UV_SYNC_SELECT')
        if scene.faceit_sync_shapes_index:
            # row = col.row()
            if scene.faceit_shape_key_lock:
                pin_icon = 'PINNED'
            else:
                pin_icon = 'UNPINNED'
            row.prop(scene, 'faceit_shape_key_lock', icon=pin_icon)


class FACEIT_PT_ArkitTargetShapesSetup(FACEIT_PT_BaseArkitShapes, bpy.types.Panel):
    bl_label = 'ARKit Setup'
    bl_options = set()
    bl_idname = 'FACEIT_PT_ArkitTargetShapesSetup'
    faceit_predecessor = 'FACEIT_PT_ArkitTargetShapes'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        box = layout.box()
        col = box.column(align=True)
        # col = layout.column(align=True)

        if not scene.faceit_face_objects:
            row = col.row()
            row.alert = True
            op = row.operator('faceit.go_to_tab', text='Register Objects First...')
            op.tab = 'SETUP'
        else:

            # draw_utils.draw_web_link(
            #     row, 'https://faceit-doc.readthedocs.io/en/latest/arkit_setup/#arkit-target-shapes-retargeting-mocap')

            row = col.row(align=True)
            if scene.faceit_retarget_shapes:
                row.operator('faceit.init_retargeting', text='Smart Match', icon='FILE_REFRESH')
                row = col.row(align=True)
                row.operator('faceit.init_retargeting', text='Reset', icon='LOOP_BACK').empty = True
            else:
                row.operator_context = 'EXEC_DEFAULT'
                row.operator('faceit.init_retargeting', text='Initialize', icon='FILE_REFRESH')
                # .standart_shapes = True

            row = col.row()
            row.label(text='Presets')

            row = col.row(align=True)
            row.operator_context = 'INVOKE_DEFAULT'

            row.operator('faceit.import_retargeting_map')
            row.menu('FACEIT_MT_PresetImport', text='', icon='DOWNARROW_HLT')
            # row.operator_context = 'EXEC_DEFAULT'
            row.operator('faceit.export_retargeting_map')

            if scene.faceit_retarget_shapes:
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


class FACEIT_OT_DrawTargetShapesList(bpy.types.Operator):
    bl_label = "Target Shapes"
    bl_idname = 'faceit.draw_target_shapes_list'

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
        return context.scene.faceit_retarget_shapes

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self)
        # return wm.invoke_popup(self)
        # invoke_popup

    def draw(self, context):

        layout = self.layout

        shape_item = context.scene.faceit_retarget_shapes[self.source_shape_index]

        row = layout.row()
        row.label(text='Source Shape: {}'.format(shape_item.display_name))

        row = layout.row()
        row.template_list('TARGET_SHAPES_UL_list', '', shape_item,
                          'target_shapes', shape_item, 'target_list_index')
        row = layout.row()

        op = row.operator('faceit.edit_target_shape', text='Add Target Shape', icon='ADD')
        op.index = shape_item.index

    def execute(self, context):
        return{'FINISHED'}


class TARGET_SHAPES_UL_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            layout.use_property_split = True
            layout.use_property_decorate = False

            row = layout.row(align=True)
            row.prop(item, 'name', text='', emboss=False)

            op = row.operator('faceit.edit_target_shape', text='', icon='DOWNARROW_HLT')
            op.operation = 'CHANGE'
            op.index = item.parent_idx
            op.target_shape_index = item.index

            op = row.operator('faceit.remove_target_shape', text='', icon='X')
            op.parent_index = item.parent_idx
            op.target_shape_index = item.index


class SHAPE_RETARGET_UL_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            row = layout.row(align=True)

            target_shapes = item.target_shapes

            row.active = item.use_animation and len(target_shapes) > 0

            if item.index == context.scene.faceit_retarget_shapes_index:
                icon = 'RESTRICT_SELECT_OFF'
            else:
                icon = 'RESTRICT_SELECT_ON'

            row.prop(item, 'display_name', emboss=False, text='')

            sk_names = sk_utils.get_shape_key_names_from_objects()
            if any([item.name not in sk_names for item in item.target_shapes]):
                row.alert = True

            display_text = '---'
            if target_shapes:
                display_text = ', '.join([t.name for t in target_shapes])
            else:
                row.active = False

            op = row.operator('faceit.draw_target_shapes_list', text=display_text,
                              emboss=True, icon='DOWNARROW_HLT')
            op.source_shape_index = item.index

            op = row.operator('faceit.edit_target_shape', text='', icon='ADD')
            op.index = item.index

            row.operator('faceit.clear_target_shapes', text='', icon='TRASH').arkit_shape_name = item.name


class FACEIT_MT_PresetImport(bpy.types.Menu):
    bl_label = 'Import Retargeting Preset'

    file_path = fdata.get_retargeting_presets()

    def draw(self, _context):
        layout = self.layout
        row = layout.row()
        row.operator_context = 'EXEC_DEFAULT'
        row.operator('faceit.import_retargeting_map', text='CC3').filepath = self.file_path+'cc3.json'
        row = layout.row()
        row.operator('faceit.import_retargeting_map', text='CC3+').filepath = self.file_path+'cc3+.json'


def draw(context, layout):
    scene = context.scene

    col_retarget = layout.column()

    row = col_retarget.row()
    row.label(text='ARKit Target Shapes')

    box = col_retarget.box()
    col = box.column(align=False)

    if scene.faceit_retarget_shapes:
        row = col.row()
        # row.operator('faceit.set_active_target_shapes', text='', icon='CHECKBOX_DEHLT').inverse = True
        row.label(text='  Source Shape')
        row.label(text='Target Shape')

        col.template_list('SHAPE_RETARGET_UL_list', '', bpy.context.scene,
                          'faceit_retarget_shapes', scene, 'faceit_retarget_shapes_index')
        row = col.row(align=True)
        row.prop(scene, 'faceit_sync_shapes_index', icon='UV_SYNC_SELECT')
        if scene.faceit_sync_shapes_index:
            # row = col.row()
            if scene.faceit_shape_key_lock:
                pin_icon = 'PINNED'
            else:
                pin_icon = 'UNPINNED'
            row.prop(scene, 'faceit_shape_key_lock', icon=pin_icon)

        # row = col.row(align=True)
        # row.operator('faceit.set_amplify_values', text='Amplify All Expressions', icon='INDIRECT_ONLY_ON')

    if not scene.faceit_face_objects:
        row = box.row()
        row.alert = True
        op = row.operator('faceit.go_to_tab', text='Complete Setup First...')
        op.tab = 'SETUP'
    else:

        box = col.box()
    # row = box.row()
        col_init = box.column(align=True)

        row = col_init.row()
        draw_utils.draw_panel_dropdown_expander(
            row, scene, 'faceit_shape_key_utils_expand_ui', 'Setup')

        draw_utils.draw_web_link(
            row, 'https://faceit-doc.readthedocs.io/en/latest/arkit_setup/#arkit-target-shapes-retargeting-mocap')

        if scene.faceit_shape_key_utils_expand_ui:
            # row.label(text='Initialize')

            row = col_init.row(align=True)
            if scene.faceit_retarget_shapes:
                row.operator('faceit.init_retargeting', text='Smart Match', icon='FILE_REFRESH')
                row = col_init.row(align=True)
                row.operator('faceit.init_retargeting', text='Reset', icon='LOOP_BACK').empty = True
            else:
                row.operator_context = 'EXEC_DEFAULT'
                row.operator('faceit.init_retargeting', text='Initialize', icon='FILE_REFRESH')
                # .standart_shapes = True

            row = col_init.row()
            row.label(text='Presets')

            row = col_init.row(align=True)
            row.operator_context = 'INVOKE_DEFAULT'

            row.operator('faceit.import_retargeting_map')
            row.menu('FACEIT_MT_PresetImport', text='', icon='DOWNARROW_HLT')
            # row.operator_context = 'EXEC_DEFAULT'
            row.operator('faceit.export_retargeting_map')

            if scene.faceit_retarget_shapes:
                row = col_init.row()
                row.label(text='Names and Indices')
                row = col_init.row()
                row.prop(scene, 'faceit_retargeting_naming_scheme', text='Name Scheme', expand=True)

                row = col_init.row()
                row.operator('faceit.retarget_names', icon='FILE_FONT')
                row = col_init.row()
                row.operator_context = 'EXEC_DEFAULT'
                row.operator('faceit.reorder_keys', icon='FILE_FONT').order = scene.faceit_retargeting_naming_scheme
                row.operator_context = 'INVOKE_DEFAULT'
