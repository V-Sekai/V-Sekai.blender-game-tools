import bpy

from ..ctrl_rig.control_rig_data import CNTRL_RIG_VERSION
from ..core.faceit_data import get_arkit_shape_data
from ..core.retarget_list_base import (DrawRegionsFilterBase,
                                       DrawTargetShapesListBase,
                                       ResetRegionsOperatorBase,
                                       RetargetShapesListBase,
                                       TargetShapesListBase)
from ..core.retarget_list_utils import get_index_of_collection_item
from .ui import FACEIT_PT_Base, FACEIT_PT_BaseSub


class FACEIT_PT_BaseCtrl(FACEIT_PT_Base):
    UI_TABS = ('CONTROL',)
    weblink = "https://faceit-doc.readthedocs.io/en/latest/control_rig/"


class FACEIT_PT_ControlRig(FACEIT_PT_BaseCtrl, bpy.types.Panel):
    bl_label = 'ARKit Control Rig'
    bl_idname = 'FACEIT_PT_ControlRig'
    bl_options = set()

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/control_rig/')
        found_old_c_rigs = False
        for obj in bpy.data.objects:
            if obj.users == 0:
                if obj.name not in context.scene.objects:
                    if 'ctrl_rig_id' in obj:
                        found_old_c_rigs = True
                        break
                    else:
                        if 'FaceitControlRig' in obj.name:
                            found_old_c_rigs = True
                            break
        if found_old_c_rigs:
            row = col.row(align=True)
            row.label(text='Cleanup')
            row = col.row(align=True)
            row.operator('faceit.clear_old_ctrl_rig_data', icon='TRASH')
        row = col.row(align=True)
        row.label(text='Generate')
        row = col.row(align=True)
        row.prop(scene, 'faceit_control_armature', text='', icon='OBJECT_DATA')
        row = col.row(align=True)
        row.operator('faceit.generate_control_rig', icon='CON_ARMATURE')
        ctrl_rig = context.scene.faceit_control_armature
        if ctrl_rig:
            if ctrl_rig.get('ctrl_rig_version', 1.0) != CNTRL_RIG_VERSION:
                # TODO: Make sure that this operator is not shown when
                # the control rig is linked form another scene
                col.separator()
                box = col.box()
                row = box.row()
                row.label(text='Control Rig Update Available!')
                row = box.row()
                row.operator('faceit.update_control_rig', icon='FILE_REFRESH')
            elif bpy.app.version >= (4, 0, 0):
                if any("Layer" in coll.name for coll in ctrl_rig.data.collections):
                    col.separator()
                    box = col.box()
                    row = box.row()
                    row.label(text='Control Rig Update Available!')
                    row = box.row()
                    row.operator('faceit.update_bone_collections',
                                 icon='FILE_REFRESH')

            row = col.row(align=True)
            row.label(text='Drivers')

            row = col.row(align=True)
            row.operator('faceit.setup_control_drivers',
                         text='Connect', icon='LINKED')
            # text = "Disconnect" if scene.faceit_control_armature else "Clear Drivers"
            row.operator('faceit.remove_control_drivers',
                         text="Disconnect", icon='UNLINKED')


class FACEIT_PT_ControlRigAnimation(FACEIT_PT_BaseCtrl, bpy.types.Panel):
    bl_label = 'Animation & Baking'
    bl_idname = 'FACEIT_PT_ControlRigAnimation'
    bl_options = set()
    faceit_predecessor = 'FACEIT_PT_ControlRig'
    weblink = "https://faceit-doc.readthedocs.io/en/latest/control_rig/#bake-animations"

    @classmethod
    def poll(cls, context):
        if context.scene.faceit_control_armature:
            return super().poll(context)

    def draw(self, context):
        col = self.layout.column(align=True)
        row = col.row()
        ctrl_rig = context.scene.faceit_control_armature
        row = col.row(align=True)
        row.label(text='Active Action')
        row = col.row(align=True)
        if ctrl_rig.animation_data:
            row.prop(ctrl_rig.animation_data, 'action', text='')
            mocap_action = ctrl_rig.animation_data.action
            if mocap_action:
                row.prop(mocap_action, "use_fake_user",
                         text="", icon='FAKE_USER_OFF')
            row.operator('faceit.new_ctrl_rig_action',
                         text="New Ctrl Rig Action", icon='ADD')
        else:
            row.operator('faceit.new_ctrl_rig_action',
                         text="Create Ctrl Rig Action", icon='ADD')

        row = col.row(align=True)
        row.label(text='Bake Action')

        row = col.row(align=True)
        row.operator('faceit.bake_shape_keys_to_control_rig',
                     text='Shape Keys to Control Rig', icon='ACTION')

        row = col.row(align=True)
        row.operator('faceit.bake_control_rig_to_shape_keys',
                     text='Control Rig to Shape Keys', icon='ACTION')


class FACEIT_PT_ControlRigUtils(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Control Rig Setup and Utils'
    bl_idname = 'FACEIT_PT_ControlRigUtils'
    bl_parent_id = 'FACEIT_PT_ControlRig'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_ControlRigSettings'
    weblink = "https://faceit-doc.readthedocs.io/en/latest/control_rig/#set-child-of"

    @classmethod
    def poll(cls, context):
        if context.scene.faceit_control_armature:
            return super().poll(context)

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        row = col.row()
        row.operator('faceit.constrain_to_body_rig', icon='CONSTRAINT_BONE')


class FACEIT_PT_ControlRigControllers(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Controllers'
    bl_idname = 'FACEIT_PT_ControlRigControllers'
    bl_parent_id = 'FACEIT_PT_ControlRigUtils'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_ControlRigActiveAction'
    weblink = "https://faceit-doc.readthedocs.io/en/latest/control_rig/#custom-controllers"

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        row = col.row(align=True)
        row.operator('faceit.setup_custom_controller', icon='BONE_DATA')
        row.operator('faceit.remove_custom_controller', icon='TRASH')
        row = col.row(align=True)
        c_rig = context.scene.faceit_control_armature
        row.prop(c_rig, 'faceit_crig_rows')
        row.operator('faceit.rearrange_custom_controllers',
                     text='Rearrange', icon='SORTSIZE')
        row = col.row(align=True)
        row.operator('faceit.save_control_rig_template', icon='FILE_TICK')
        row.operator('faceit.load_control_rig_template', icon='FILE_FOLDER')

        row = col.row()
        row.operator('faceit.control_rig_set_slider_ranges',
                     text='Change Slider Ranges', icon='CON_DISTLIMIT')
        if bpy.app.version < (4, 0, 0):
            box = col.box()
            col = box.column(align=True)
            col.alignment = 'RIGHT'
            row = col.row()
            row.label(text='Slider Colors (Bone Groups)')
            bone_groups = c_rig.pose.bone_groups
            # row = box.row(align=False)
            left_grp = bone_groups.get('Left')
            row = col.row(align=True)
            sub = row.split(align=True)
            sub.alignment = 'RIGHT'
            sub.label(text="Left")
            sub.prop(left_grp.colors, "normal", text="")
            sub.prop(left_grp.colors, "select", text="")
            sub.prop(left_grp.colors, "active", text="")
            right_grp = bone_groups.get('Right')
            row = col.row(align=True)
            sub = row.split(align=True)
            sub.alignment = 'RIGHT'
            sub.label(text="Right")
            sub.prop(right_grp.colors, "normal", text="")
            sub.prop(right_grp.colors, "select", text="")
            sub.prop(right_grp.colors, "active", text="")
            special_grp = bone_groups.get('Special')
            row = col.row(align=True)
            sub = row.split(align=True)
            sub.alignment = 'RIGHT'
            sub.label(text="Special")
            sub.prop(special_grp.colors, "normal", text="")
            sub.prop(special_grp.colors, "select", text="")
            sub.prop(special_grp.colors, "active", text="")


class FACEIT_PT_ControlRigTargetShapes(FACEIT_PT_BaseCtrl, bpy.types.Panel):
    bl_label = 'Target Shapes'
    bl_idname = 'FACEIT_PT_ControlRigTargetShapes'
    faceit_predecessor = 'FACEIT_PT_ControlRigUtils'
    weblink = "https://faceit-doc.readthedocs.io/en/latest/control_rig/#control-rig-settings"

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
        # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/control_rig/')
        ctrl_rig_version = c_rig.get('ctrl_rig_version', 1.0)
        if ctrl_rig_version < 1.2:
            row = col.row(align=True)
            row.operator('faceit.update_control_rig', icon='FILE_REFRESH')
        else:
            row = col.row(align=True)
            row.operator('faceit.load_crig_settings_from_scene',
                         icon='SORT_ASC')
            row.operator('faceit.load_faceit_settings_from_crig',
                         icon='SORT_DESC')
            col.separator()
            col_retarget = col.column()
            col_retarget.use_property_decorate = True
            row.use_property_split = True
            row = col_retarget.row(align=True)
            row.template_list('FACEIT_UL_RetargetControlRigList', '', c_rig,
                              'faceit_crig_targets', c_rig, 'faceit_crig_targets_index')

            col_ul = row.column(align=False)
            row = col_ul.row(align=True)
            row.operator('faceit.setup_custom_controller', text='', icon='ADD')
            row = col_ul.row(align=True)
            row.operator_context = 'EXEC_DEFAULT'
            active_target = c_rig.faceit_crig_targets[c_rig.faceit_crig_targets_index]
            is_valid = active_target.name not in get_arkit_shape_data()
            row.enabled = is_valid
            op = row.operator('faceit.remove_custom_controller',
                              text='', icon='REMOVE')
            op.custom_only = False
            if is_valid:
                op.custom_slider = active_target.name

            col_ul.separator()
            row = col_ul.row(align=True)
            col_ul.operator('faceit.move_target_shape_item',
                            icon='TRIA_UP', text='').direction = 'UP'
            row = col_ul.row(align=False)
            col_ul.operator('faceit.move_target_shape_item',
                            icon='TRIA_DOWN', text='').direction = 'DOWN'


class FACEIT_PT_ControlRigTargetObjects(FACEIT_PT_BaseCtrl, bpy.types.Panel):
    bl_label = 'Target Objects'
    bl_idname = 'FACEIT_PT_ControlRigTargetObjects'
    # bl_options = set()
    faceit_predecessor = 'FACEIT_PT_ControlRigTargetShapes'
    weblink = "https://faceit-doc.readthedocs.io/en/latest/control_rig/#control-rig-settings"

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
            op = row.operator('faceit.add_crig_target_object',
                              text='', icon='ADD')

            row = col.row(align=True)
            op = row.operator(
                'faceit.remove_crig_target_object', text='', icon='REMOVE')
            op.prompt = False


class CRIG_TARGET_OBJECTS_UL_list(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        scene = context.scene
        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            row = layout.row(align=True)
            row.label(text=item.name, icon='OUTLINER_OB_MESH')

            op = row.operator(
                'faceit.remove_crig_target_object', text='', icon='X')
            op.prompt = False
            op.remove_item = item.name

        else:
            layout.alignment = 'CENTER'
            layout.label(text='',)


class FACEIT_UL_ControlRigTargetShapesList(TargetShapesListBase, bpy.types.UIList):
    # the edit target shapes operator
    edit_target_shapes_operator = 'faceit.edit_crig_target_shape'
    # the edit target shapes operator
    remove_target_shapes_operator = 'faceit.remove_crig_target_shape'


class FACEIT_OT_DrawCrigTargetShapesList(DrawTargetShapesListBase, bpy.types.Operator):
    ''' Edit the target shapes for this expression/slider '''
    bl_idname = 'faceit.draw_crig_target_shapes_list'

    edit_target_shapes_operator = 'faceit.edit_crig_target_shape'
    target_shapes_list = FACEIT_UL_ControlRigTargetShapesList.__name__
    use_display_name = False

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    @staticmethod
    def get_retarget_shapes():
        ''' Get the retarget_list property group '''
        ctrl_rig = bpy.context.scene.faceit_control_armature
        if ctrl_rig:
            return ctrl_rig.faceit_crig_targets


class FACEIT_UL_RetargetControlRigList(RetargetShapesListBase, bpy.types.UIList):

    draw_region_filter_operator = 'faceit.draw_crig_regions_filter'
    reset_regions_filter_operator = 'faceit.reset_crig_regions_filter'
    reset_regions_filter_operator = 'faceit.reset_crig_regions_filter'

    @staticmethod
    def get_face_regions(context):
        ctrl_rig = bpy.context.scene.faceit_control_armature
        if ctrl_rig:
            return ctrl_rig.faceit_crig_face_regions

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            self.use_filter_show = True

            row = layout.row(align=True)
            row.use_property_decorate = True
            row.use_property_split = True

            first_col = row.row(align=True)
            first_col.enabled = self.draw_active(item)

            first_col.prop(item, 'amplify', emboss=True, text=item.name)

            second_col = row.row(align=True)

            display_text = ''

            if item.target_shapes:
                if self.show_assigned_regions:
                    display_text = ', '.join(
                        [t.name for t in item.target_shapes])

                op = second_col.operator(
                    'faceit.draw_crig_target_shapes_list', text=display_text, icon='DOWNARROW_HLT')
                op.source_shape = item.name
            else:
                if self.show_assigned_regions:
                    display_text = '---'

                op = second_col.operator(
                    'faceit.edit_crig_target_shape', text=display_text, icon='ADD')
                op.source_shape_index = get_index_of_collection_item(item)

            if self.show_assigned_regions:
                second_col.prop(item, 'region', text='')

            op = second_col.operator(
                'faceit.select_bone_from_source_shape', text='', icon='BONE_DATA')
            op.expression = item.name


class FACEIT_OT_DrawCrigRegionsFilter(DrawRegionsFilterBase, bpy.types.Operator):
    ''' Filter the displayed expressions by face regions. '''
    bl_idname = 'faceit.draw_crig_regions_filter'

    @staticmethod
    def get_face_regions(context):
        ctrl_rig = context.scene.faceit_control_armature
        if ctrl_rig:
            return ctrl_rig.faceit_crig_face_regions

    @classmethod
    def poll(cls, context):
        return super().poll(context)


class FACEIT_OT_ResetCrigRegionsFilter(ResetRegionsOperatorBase, bpy.types.Operator):
    ''' Reset the regions filter to default settings'''
    bl_idname = 'faceit.reset_crig_regions_filter'

    @staticmethod
    def get_face_regions(context):
        ctrl_rig = context.scene.faceit_control_armature
        if ctrl_rig:
            return ctrl_rig.faceit_crig_face_regions

    @classmethod
    def poll(cls, context):
        return super().poll(context)
