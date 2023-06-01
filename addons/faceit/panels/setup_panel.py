
import bpy
from bpy.props import StringProperty

from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils
from . import draw_utils
from .ui import FACEIT_PT_Base, FACEIT_PT_BaseSub

from ..setup.assign_groups_operators import is_picker_running


class FACEIT_PT_BaseSetup(FACEIT_PT_Base):
    UI_TABS = ('SETUP',)


class FACEIT_PT_SetupRegister(FACEIT_PT_BaseSetup, bpy.types.Panel):
    bl_label = 'Register Objects'
    bl_idname = 'FACEIT_PT_SetupRegister'
    bl_options = set()

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)

        # row = col.row(align=True)
        # row.label(text='Registration')

        # draw_utils.draw_web_link(row, 'https://faceit-doc.readthedocs.io/en/latest/setup/')

        if not scene.faceit_face_objects:
            row = col.row(align=True)
            op = row.operator('faceit.add_facial_part', text='Register Face Objects', icon='ADD')
            op.facial_part = 'main'
        else:
            col.separator(factor=1.0)
            row = col.row()
            row.template_list('FACE_OBJECTS_UL_list', '', scene, 'faceit_face_objects', scene, 'faceit_face_index')
            col_ul = row.column(align=True)
            # row.prop(scene, 'faceit_show_warnings', text='', icon='ERROR')
            row = col_ul.row(align=True)
            op = row.operator('faceit.add_facial_part', text='', icon='ADD')
            row = col_ul.row(align=True)
            op = row.operator('faceit.remove_facial_part', text='', icon='REMOVE')
            op.prompt = False
            col_ul.separator()
            row = col_ul.row()
            row.menu('FACEIT_MT_FaceitObjects', text='', icon='DOWNARROW_HLT')
            col_ul.separator()
            row = col_ul.row(align=True)
            op = row.operator('faceit.move_face_object', text='', icon='TRIA_UP')
            op.direction = 'UP'
            row = col_ul.row(align=True)
            op = row.operator('faceit.move_face_object', text='', icon='TRIA_DOWN')
            op.direction = 'DOWN'
            row = col.row(align=True)
            op = row.operator('faceit.add_facial_part', icon='ADD')
            row = col.row(align=True)
            if scene.faceit_workspace.workspace != 'MOCAP' and not scene.faceit_use_rigify_armature:
                row = col.row(align=True)
                op = row.operator('faceit.face_object_warning_check', text='Check Geometry', icon='CHECKMARK')
                op.item_name = 'ALL'
                op.set_show_warnings = True
                op.check_main = True
                icon_hide = 'HIDE_OFF' if scene.faceit_show_warnings else 'HIDE_ON'
                row.prop(scene, 'faceit_show_warnings', icon=icon_hide)
            row = col.row(align=True)
            row.label(text="Existing Rig")
            row = col.row(align=True)
            row.prop(scene, "faceit_body_armature", text="", icon='ARMATURE_DATA')
            if scene.faceit_use_rigify_armature:  # or scene.faceit_eye_pivot_options == 'BONE_PIVOT'
                row.enabled = False


class FACEIT_PT_BodyRigSetup(FACEIT_PT_BaseSub, bpy.types.Panel):
    bl_label = 'Existing Rig Settings'
    bl_idname = 'FACEIT_PT_BodyRigSetup'
    faceit_predecessor = 'FACEIT_PT_SetupRegister'
    bl_parent_id = 'FACEIT_PT_SetupRegister'
    bl_options = set()

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            return context.scene.faceit_face_objects and context.scene.faceit_body_armature

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.column(align=True)
        row = col.row(align=True)
        if scene.faceit_body_armature:
            row = col.row(align=True)
            row.prop(scene.faceit_body_armature.data, "pose_position", expand=True)
            if scene.faceit_workspace.workspace != 'MOCAP':
                col.separator()
                if context.scene.faceit_is_rigify_armature:
                    row = col.row(align=True)
                    row.prop(scene, 'faceit_use_rigify_armature', icon='ARMATURE_DATA')
                if not scene.faceit_use_rigify_armature:
                    draw_utils.draw_anime_style_eyes(col, scene)


def draw_assign_group_options(row, grp_name, grp_name_ui, can_pick=False):
    vgroup_props = bpy.context.scene.faceit_vertex_groups
    grp_prop = vgroup_props.get('faceit_' + grp_name)
    is_assigned = grp_prop.is_assigned
    is_masked = grp_prop.is_masked
    mask_inverted = grp_prop.mask_inverted
    is_drawn = grp_prop.is_drawn
    if can_pick:
        row.operator('faceit.assign_main', text=grp_name_ui, icon='GROUP_VERTEX')
        picker_running = is_picker_running()
        row.operator('faceit.assign_main_modal', text='', icon='EYEDROPPER', depress=picker_running)
    else:
        row.operator('faceit.assign_group', text=grp_name_ui,
                     icon='GROUP_VERTEX').vertex_group = grp_name
    sub = row.row(align=True)
    sub.enabled = is_assigned
    op = sub.operator('faceit.draw_faceit_vertex_group', text='',
                      icon='HIDE_OFF', depress=is_drawn)
    op.faceit_vertex_group_name = 'faceit_' + grp_name
    op = sub.operator('faceit.mask_group', text='', icon='MOD_MASK',
                      depress=is_masked)
    op.vgroup_name = 'faceit_' + grp_name
    op.operation = 'REMOVE' if is_masked else 'ADD'
    if is_masked:
        op = sub.operator('faceit.mask_group', text='', icon='ARROW_LEFTRIGHT',
                          depress=mask_inverted)
        op.vgroup_name = 'faceit_' + grp_name
        op.operation = 'INVERT'
    sub.operator('faceit.remove_faceit_groups', text='',
                 icon='X').vgroup_name = 'faceit_' + grp_name


class FACEIT_PT_SetupVertexGroups(FACEIT_PT_BaseSetup, bpy.types.Panel):
    bl_label = 'Assign Vertex Groups'
    bl_idname = 'FACEIT_PT_SetupVertexGroups'
    bl_options = set()
    faceit_predecessor = 'FACEIT_PT_SetupRegister'
    UI_WORKSPACES = ('ALL', 'RIG')

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            if context.scene.faceit_face_objects:
                return not context.scene.faceit_use_rigify_armature

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        col_main = box.column(align=True)
        row = col_main.row(align=True)
        row.label(text='Face Main (Mandatory)')
        row = col_main.row(align=True)

        draw_assign_group_options(row, 'main', 'Main', can_pick=True)
        box = layout.box()
        col = box.column(align=True)
        separate_factor = .3

        if context.scene.faceit_use_eye_pivots:
            col.separator(factor=separate_factor)
            col.label(text='Eyes (Eyeballs, Cornea, Iris, Spots, Highlights)')

            grid = col.grid_flow(columns=2, align=False)
            row = grid.row(align=True)
            draw_assign_group_options(row, 'right_eyeball', 'Right Eye')

            row = grid.row(align=True)
            draw_assign_group_options(row, 'left_eyeball', 'Left Eye')
        else:
            col.separator(factor=separate_factor)
            col.label(text='Eyeballs')

            grid = col.grid_flow(columns=2, align=False)
            row = grid.row(align=True)
            draw_assign_group_options(row, 'right_eyeball', 'Right Eyeball')

            row = grid.row(align=True)
            draw_assign_group_options(row, 'left_eyeball', 'Left Eyeball')

            # Other Eyes
            col.separator(factor=separate_factor)
            col.label(text='Cornea, Iris, Spots, Highlights')

            grid = col.grid_flow(columns=2, align=False)
            row = grid.row(align=True)
            draw_assign_group_options(row, 'right_eyes_other', 'Other Right')

            row = grid.row(align=True)
            draw_assign_group_options(row, 'left_eyes_other', 'Other Left')

        col.separator(factor=separate_factor)
        col.label(text='Teeth, Gum')

        row = col.row(align=True)
        draw_assign_group_options(row, 'upper_teeth', 'Upper Teeth')

        row = col.row(align=True)
        draw_assign_group_options(row, 'lower_teeth', 'Lower Teeth')

        # Tongue
        col.separator(factor=separate_factor)
        col.label(text='Tongue')

        row = col.row(align=True)
        draw_assign_group_options(row, 'tongue', 'Tongue')

        # Eyelashes
        col.separator(factor=separate_factor)
        col.label(text='Eyelashes, Eyeshells, Tearlines')

        row = col.row(align=True)
        draw_assign_group_options(row, 'eyelashes', 'Eyelashes')

        # Facial Hair
        col.separator(factor=separate_factor)
        col.label(text='Eyebrows, Beards, Facial Hair etc.')

        row = col.row(align=True)
        draw_assign_group_options(row, 'facial_hair', 'Facial Hair')

        # Rigid
        col.separator(factor=separate_factor)
        col.label(text='Rigid, No Deform')

        row = col.row(align=True)
        draw_assign_group_options(row, 'rigid', 'Rigid')

        if context.object:
            if context.object.mode != 'OBJECT':
                if context.object.type != 'MESH':
                    layout.enabled = False

        box = layout.box()
        col_utils = box.column(align=True)
        row = col_utils.row(align=True)
        row.label(text='Utilities')
        row = col_utils.row(align=True)
        vgroup_props = bpy.context.scene.faceit_vertex_groups
        grp_prop = vgroup_props.get('UNASSIGNED')
        is_drawn = grp_prop.is_drawn
        row.operator('faceit.draw_faceit_vertex_group', text='Show Unassigned',
                     icon='HIDE_OFF', depress=is_drawn).faceit_vertex_group_name = 'UNASSIGNED'
        col_utils.separator()
        row = col_utils.row(align=True)
        row.operator('faceit.remove_all_faceit_groups', text='Reset All', icon='TRASH')


class FACE_OBJECTS_UL_list(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        scene = context.scene
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            obj = futils.get_object(item.name)
            row = layout.row(align=True)
            sub = row.row(align=True)
            sub.label(text=item.name, icon='OUTLINER_OB_MESH')
            if obj:
                if vg_utils.get_faceit_vertex_grps(obj):
                    row.operator('faceit.draw_assigned_groups_list', text='', icon='GROUP_VERTEX').obj_name = item.name
                if futils.get_hide_obj(obj):
                    sub.enabled = False
            if item.warnings and scene.faceit_show_warnings:
                op = row.operator('faceit.face_object_warning', text='', icon='ERROR')
                op.item_name = item.name
            op = row.operator('faceit.remove_facial_part', text='', icon='X')
            op.prompt = False
            op.remove_item = item.name
        else:
            layout.alignment = 'CENTER'
            layout.label(text='',)


class FACEIT_MT_FaceitObjects(bpy.types.Menu):
    bl_label = "Faceit Register Options"

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        op = row.operator('faceit.clear_faceit_objects', text='Clear all Registered Objects', icon='TRASH')
        row = layout.row(align=True)
        row.operator('faceit.remove_all_faceit_groups', text='Reset All Vertex Groups', icon='TRASH')
        # op = row.operator('faceit.remove_faceit_groups', text='Reset All Vertex Groups', icon='TRASH')
        op.all_groups = True


class FACEIT_OT_DrawAssignedGroupsList(bpy.types.Operator):
    bl_label = "Assigned Groups"
    bl_idname = 'faceit.draw_assigned_groups_list'

    obj_name: StringProperty()

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self)

    def draw(self, context):

        layout = self.layout
        obj = futils.get_object(self.obj_name)
        if obj:
            faceit_groups = vg_utils.get_faceit_vertex_grps(obj)
            if faceit_groups:
                layout.label(text='Faceit Vertex Groups')

                box = layout.box()
                col = box.column()

                index = context.scene.faceit_face_objects.find(self.obj_name)
                for fgroup in faceit_groups:

                    row = col.row(align=True)
                    op = row.operator('faceit.remove_faceit_group_list', text='', icon='X')
                    op.vgroup_name = fgroup
                    op.object_list_index = index
                    op = row.operator('faceit.select_faceit_groups', text='', icon='EDITMODE_HLT')
                    op.faceit_vertex_group_name = fgroup
                    op.object_list_index = index
                    row.label(text=fgroup)

    def execute(self, context):
        return {'FINISHED'}
