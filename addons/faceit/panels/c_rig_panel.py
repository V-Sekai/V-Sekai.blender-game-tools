import bpy


from bpy.props import EnumProperty, StringProperty

from .ui import FACEIT_PT_Base, FACEIT_PT_BaseSub
from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..retargeting import retarget_list_utils as rutils


class FACEIT_PT_BaseCtrl(FACEIT_PT_Base):
    UI_TAB = 'CONTROL'


class FACEIT_PT_ControlRig(FACEIT_PT_BaseCtrl, bpy.types.Panel):
    bl_label = 'Control Rig'
    bl_idname = 'FACEIT_PT_ControlRig'
    bl_options = set()

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        # draw_utils.draw_panel_dropdown_expander(row, scene, 'faceit_control_rig_expand_ui', 'Control Rig')
        # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/control_rig/')

        # if scene.faceit_control_rig_expand_ui:

        row = col.row(align=True)
        row.label(text='Generate')

        row = col.row(align=True)
        row.prop(scene, 'faceit_control_armature', text='', icon='OBJECT_DATA')

        row = col.row(align=True)
        row.operator('faceit.generate_control_rig', icon='CON_ARMATURE')

        row = col.row(align=True)
        row.label(text='Drivers')

        row = col.row(align=True)
        row.operator('faceit.setup_control_drivers', text='Connect', icon='LINKED')
        row.operator('faceit.remove_control_drivers', text='Disconnect', icon='UNLINKED')

        row = col.row(align=True)
        row.label(text='Bake Action')

        row = col.row(align=True)
        row.operator('faceit.bake_shape_keys_to_control_rig', text='Shape Keys to Control Rig', icon='ACTION')

        row = col.row(align=True)
        row.operator('faceit.bake_control_rig_to_shape_keys', text='Control Rig to Shape Keys', icon='ACTION')


class FACEIT_PT_ControlRigUtils(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Control Rig Setup and Utils'
    bl_idname = 'FACEIT_PT_ControlRigUtils'
    bl_parent_id = 'FACEIT_PT_ControlRig'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_ControlRigSettings'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)


# class FACEIT_PT_ControlRigSetup(FACEIT_PT_BaseSub, bpy.types.Panel):
#     bl_label = 'Setup'
#     bl_idname = 'FACEIT_PT_ControlRigSetup'
#     bl_parent_id = 'FACEIT_PT_ControlRig'
#     bl_options = set()

#     @classmethod
#     def poll(cls, context):
#         return super().poll(context)

#     def draw(self, context):
#         layout = self.layout
#         scene = context.scene
#         col = layout.column()

class FACEIT_PT_ControlRigControllers(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Controllers'
    bl_idname = 'FACEIT_PT_ControlRigControllers'
    bl_parent_id = 'FACEIT_PT_ControlRigUtils'
    # bl_options = set()

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.column()

        row = col.row(align=True)
        row.operator('faceit.setup_custom_controller', icon='BONE_DATA')
        row.operator('faceit.remove_custom_controller', icon='TRASH')

        row = col.row()
        row.operator('faceit.update_control_rig', icon='FILE_REFRESH')
        row = col.row()
        row.operator('faceit.control_rig_set_slider_ranges', text='Change Slider Ranges', icon='CON_DISTLIMIT')

        # row = col.row(align=True)
        # row.label(text='Other (Experimental)')


class FACEIT_PT_ControlRigExperimental(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Experimental'
    bl_idname = 'FACEIT_PT_ControlRigExperimental'
    bl_parent_id = 'FACEIT_PT_ControlRigUtils'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_ControlRigUtils'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.column()

        row = col.row()
        row.operator('faceit.constrain_to_body_rig', icon='CONSTRAINT_BONE')

        row = col.row(align=True)
        row.operator('faceit.draw_c_ranges', icon='GREASEPENCIL')
        row.operator('faceit.remove_draw_c_ranges', icon='TRASH')


class FACEIT_PT_ControlRigTargetShapes(FACEIT_PT_BaseCtrl, bpy.types.Panel):
    bl_label = 'Target Shapes'
    bl_idname = 'FACEIT_PT_ControlRigTargetShapes'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_ControlRigUtils'

    @classmethod
    def poll(cls, context):

        c_rig = context.scene.faceit_control_armature
        if c_rig:
            return super().poll(context) and c_rig.faceit_crig_targets

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        c_rig = scene.faceit_control_armature

        # box = layout.box()
        # row = box.row()
        # draw_utils.draw_panel_dropdown_expander(
        #     row, scene, 'faceit_crig_target_settings_expand_ui', 'Control Rig Settings')
        # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/control_rig/')

        # if scene.faceit_crig_target_settings_expand_ui:

        ctrl_rig_version = c_rig.get('ctrl_rig_version', 1.0)
        if ctrl_rig_version < 1.2:
            row = col.row(align=True)
            row.operator('faceit.update_control_rig', icon='FILE_REFRESH')
        else:

            row = col.row(align=True)
            row.operator('faceit.load_crig_settings_from_scene', icon='SORT_ASC')
            row.operator('faceit.load_faceit_settings_from_crig', icon='SORT_DESC')

            col.separator()

            # box = col.box()
            # row = box.row()
            # draw_utils.draw_panel_dropdown_expander(
            #     row, scene, 'faceit_crig_target_shapes_expand_ui', 'Target Shapes')
            # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/control_rig/')
            col_retarget = col.column()
            col_retarget.use_property_decorate = True
            row.use_property_split = True

            if scene.faceit_crig_target_shapes_expand_ui:
                if c_rig.faceit_crig_targets:
                    row = col_retarget.row()
                    col_retarget.template_list('SHAPE_AMPLIFY_CRIG_UL_list', '', c_rig,
                                               'faceit_crig_targets', c_rig, 'faceit_crig_targets_index')

            # box = col.box()
            # row = box.row()
            # draw_utils.draw_panel_dropdown_expander(
            #     row, scene, 'faceit_crig_target_objects_expand_ui', 'Target Objects')
            # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/control_rig/')


class FACEIT_PT_ControlRigTargetObjects(FACEIT_PT_BaseCtrl, bpy.types.Panel):
    bl_label = 'Target Objects'
    bl_idname = 'FACEIT_PT_ControlRigTargetObjects'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_ControlRigTargetShapes'

    @classmethod
    def poll(cls, context):

        c_rig = context.scene.faceit_control_armature
        if c_rig:
            return super().poll(context) and c_rig.faceit_crig_objects

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        scene = context.scene
        c_rig = scene.faceit_control_armature

        ctrl_rig_version = c_rig.get('ctrl_rig_version', 1.0)
        if ctrl_rig_version < 1.2:
            row = col.row(align=True)
            row.operator('faceit.update_control_rig', icon='FILE_REFRESH')
        else:
            row = col.row()
            row.template_list('CRIG_TARGET_OBJECTS_UL_list', '', c_rig,
                              'faceit_crig_objects', c_rig, 'faceit_crig_objects_index')
            col = row.column(align=True)

            row = col.row(align=True)
            op = row.operator('faceit.add_crig_target_object', text='', icon='ADD')

            row = col.row(align=True)
            op = row.operator('faceit.remove_crig_target_object', text='', icon='REMOVE')
            op.prompt = False


class FACEIT_OT_DrawCrigRegionsFilter(bpy.types.Operator):
    bl_label = "Filter Regions"
    bl_idname = 'faceit.draw_crig_regions_filter'

    @classmethod
    def poll(cls, context):
        return context.scene.faceit_retarget_shapes

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self)

    def draw(self, context):

        layout = self.layout
        face_regions = context.scene.faceit_face_regions
        col = layout.column(align=True)
        row = col.row(align=True)
        icon_value = 'HIDE_OFF' if face_regions.brows else 'HIDE_ON'
        row.prop(face_regions, 'brows', icon=icon_value)
        icon_value = 'HIDE_OFF' if face_regions.eyes else 'HIDE_ON'
        row.prop(face_regions, 'eyes', icon=icon_value)
        row = col.row(align=True)
        icon_value = 'HIDE_OFF' if face_regions.cheeks else 'HIDE_ON'
        row.prop(face_regions, 'cheeks', icon=icon_value)
        icon_value = 'HIDE_OFF' if face_regions.nose else 'HIDE_ON'
        row.prop(face_regions, 'nose', icon=icon_value)
        row = col.row(align=True)
        icon_value = 'HIDE_OFF' if face_regions.mouth else 'HIDE_ON'
        row.prop(face_regions, 'mouth', icon=icon_value)
        icon_value = 'HIDE_OFF' if face_regions.tongue else 'HIDE_ON'
        row.prop(face_regions, 'tongue', icon=icon_value)
        row = col.row(align=True)
        icon_value = 'HIDE_OFF' if face_regions.other else 'HIDE_ON'
        row.prop(face_regions, 'other', icon=icon_value)

    def execute(self, context):
        return{'FINISHED'}


class FACEIT_OT_DrawCrigTargetShapesList(bpy.types.Operator):
    ''' Edit the target shapes for this expression/slider '''
    bl_label = "Target Shapes"
    bl_idname = 'faceit.draw_crig_target_shapes_list'

    target_shape_edit: EnumProperty(
        items=sk_utils.get_shape_keys_from_faceit_objects_enum, name='Change target Shape',
        description='Choose a Shape Key as target for retargeting this shape. \nThe shapes listed are from the Main Object registered in Setup panel.\n'
    )

    source_shape: StringProperty(
        name='Name of the Shape Item',
        default='',
    )

    @classmethod
    def poll(cls, context):
        return context.scene.faceit_retarget_shapes

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self)

    def draw(self, context):

        layout = self.layout

        ctrl_rig = futils.get_faceit_control_armature()

        crig_targets = ctrl_rig.faceit_crig_targets
        shape_item = crig_targets[self.source_shape]
        shape_item_index = crig_targets.find(self.source_shape)

        row = layout.row()
        row.label(text='Source Shape: {}'.format(shape_item.name))

        row = layout.row()
        row.template_list('CRIG_TARGET_SHAPES_UL_list', '', shape_item,
                          'target_shapes', shape_item, 'target_list_index')
        row = layout.row()

        op = row.operator('faceit.edit_crig_target_shape', text='Add Target Shape', icon='ADD')
        op.source_shape_index = shape_item_index

    def execute(self, context):
        return{'FINISHED'}


class CRIG_TARGET_SHAPES_UL_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            layout.use_property_split = True
            layout.use_property_decorate = False

            row = layout.row(align=True)
            row.prop(item, 'name', text='', emboss=False)

            op = row.operator('faceit.edit_crig_target_shape', text='', icon='DOWNARROW_HLT')
            op.operation = 'CHANGE'

            # Parent index
            source_shape_index = rutils.get_index_of_parent_collection_from_target_shape(item)
            op.source_shape_index = source_shape_index
            op.target_shape = item.name

            op = row.operator('faceit.remove_crig_target_shape', text='', icon='X')
            op.source_shape_index = source_shape_index
            op.target_shape = item.name


class CRIG_TARGET_OBJECTS_UL_list(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        scene = context.scene
        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            row = layout.row(align=True)
            row.label(text=item.name, icon='OUTLINER_OB_MESH')

            op = row.operator('faceit.remove_crig_target_object', text='', icon='X')
            op.prompt = False
            op.remove_item = item.name

        else:
            layout.alignment = 'CENTER'
            layout.label(text='',)


class SHAPE_AMPLIFY_CRIG_UL_list(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        self.use_filter_show = True
        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            row = layout.row(align=True)

            sub = row.split(factor=1, align=True)
            sub.use_property_decorate = True
            sub.use_property_split = True

            sub.prop(item, 'amplify', emboss=True, text=item.name)

            target_shapes = item.target_shapes

            display_text = ''
            if target_shapes:
                if context.scene.faceit_show_crig_target_shapes:
                    display_text = ', '.join([t.name for t in target_shapes])
                # else:
                #     display_text = ''
            else:
                if not item.custom_slider:
                    row.active = False
            op = row.operator('faceit.draw_crig_target_shapes_list', text=display_text, icon='DOWNARROW_HLT')
            op.source_shape = item.name

            if context.scene.faceit_show_crig_regions:
                row.separator(factor=.1)
                row.prop(item, 'region', text='')
            op = row.operator('faceit.select_bone_from_source_shape', text='', icon='BONE_DATA')
            op.expression = item.name

    def draw_filter(self, context, layout):

        col = layout.column(align=True)

        scene = context.scene
        row = col.row(align=True)
        # Draw pressed in if filter is changed
        depress = any([x == False for x in scene.faceit_face_regions.values()])
        row.operator('faceit.draw_crig_regions_filter', depress=depress, icon='COLLAPSEMENU')
        row.operator('faceit.reset_regions', text='', icon='LOOP_BACK')

        row = col.row(align=True)
        if scene.faceit_show_crig_target_shapes:
            icon = 'HIDE_OFF'
        else:
            icon = 'HIDE_ON'
        row.prop(scene, 'faceit_show_crig_target_shapes', icon=icon)
        if scene.faceit_show_crig_regions:
            icon = 'HIDE_OFF'
        else:
            icon = 'HIDE_ON'
        row.prop(scene, 'faceit_show_crig_regions', text='Change Regions', icon=icon)

    def filter_items_in_active_regions(self, context, shape_items):
        ''' Filter all shape items and return a list where all hidden region items are marked True and all visible are marked False'''
        ret = [True, ]*len(shape_items)  # [True for i in shape_items]
        active_region_dict = context.scene.faceit_face_regions.get_active_regions()
        for i, item in enumerate(shape_items):
            if active_region_dict.get(item.region.lower(), False):
                ret[i] = False
        return ret

    def filter_items(self, context, data, propname):
        ''' Filter and order items in a list '''
        # This function gets the collection property (as the usual tuple (data, propname)), and must return two lists:
        # * The first one is for filtering, it must contain 32bit integers were self.bitflag_filter_item marks the
        #   matching item as filtered (i.e. to be shown), and 31 other bits are free for custom needs. Here we use the
        #   first one to mark VGROUP_EMPTY.
        # * The second one is for reordering, it must return a list containing the new indices of the items (which
        #   gives us a mapping org_idx -> new_idx).
        # Please note that the default UI_UL_list defines helper functions for common tasks (see its doc for more info).
        # If you do not make filtering and/or ordering, return empty list(s) (this will be more efficient than
        # returning full lists doing nothing!).

        items = getattr(data, propname)

        filtered = []
        ordered = []

        hidden_shape_items = self.filter_items_in_active_regions(context, items)
        # Initialize with all items visible
        filtered = [self.bitflag_filter_item] * len(items)

        for i, item in enumerate(items):
            if hidden_shape_items[i]:
                # filtered[i] |= self.ITEM_HIDDEN
                filtered[i] &= ~self.bitflag_filter_item

        return filtered, ordered
