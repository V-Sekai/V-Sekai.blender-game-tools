
import bpy
from bpy.props import StringProperty

from . import draw_utils
from .ui import FACEIT_PT_Base
from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils


class FACEIT_PT_BaseSetup(FACEIT_PT_Base):
    UI_TAB = 'SETUP'


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

            if scene.faceit_workspace.workspace != 'MOCAP':
                row = col.row(align=True)
                op = row.operator('faceit.face_object_warning_check', text='Check Geometry', icon='CHECKMARK')
                op.item_name = 'ALL'
                op.set_show_warnings = True
                op.check_main = True
                icon_hide = 'HIDE_OFF' if scene.faceit_show_warnings else 'HIDE_ON'
                row.prop(scene, 'faceit_show_warnings', icon=icon_hide)

            col_rig = col.column()

# START ####################### VERSION 2 ONLY #######################

            col_rig.separator()

            if scene.faceit_version == 2:
                row = col_rig.row(align=True)
                row.prop(scene, 'faceit_use_rigify_armature', icon='ARMATURE_DATA')

# END ######################### VERSION 2 ONLY #######################

            if futils.get_faceit_armature(force_original=True):
                col_rig.active = False

            elif scene.faceit_use_rigify_armature:
                row = col_rig.row(align=True)
                row.prop_search(scene, 'faceit_armature', bpy.data, 'objects', text='')


class FACEIT_PT_SetupVertexGroups(FACEIT_PT_BaseSetup, bpy.types.Panel):
    bl_label = 'Assign Vertex Groups'
    bl_idname = 'FACEIT_PT_SetupVertexGroups'
    bl_options = set()
    faceit_predecessor = 'FACEIT_PT_SetupRegister'
    UI_WORKSPACES = ('ALL', 'RIG')

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            return (futils.get_faceit_armature(force_original=True) or not futils.get_faceit_armature()) or not context.scene.faceit_use_rigify_armature

    def draw_assign_group_options(self, row, grp_name, grp_name_ui):
        row.operator('faceit.assign_group', text=grp_name_ui,
                     icon='GROUP_VERTEX').vertex_group = grp_name
        row.operator('faceit.remove_faceit_groups', text='',
                     icon='X').faceit_vertex_group_names = 'faceit_'+grp_name

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        col = box.column(align=True)
        # col = layout.column(align=True)

        # draw_utils.draw_web_link(
        #     row, 'https://faceit-doc.readthedocs.io/en/latest/setup/#2-assign-vertex-groups')

        col.label(text='Assign Method')
        row = col.row(align=True)
        row.prop(scene, 'faceit_vgroup_assign_method', expand=True)
        row = col.row(align=True)
        op = row.operator('faceit.remove_faceit_groups', text='Reset All', icon='TRASH')
        op.all_groups = True
        # op.faceit_vertex_group_names = 'faceit_left_eyeball, faceit_right_eyeball, faceit_left_eyes_other, faceit_right_eyes_other, faceit_upper_teeth, faceit_lower_teeth, faceit_tongue, faceit_eyelashes, faceit_rigid'
        separate_factor = .3
        # Eyes
        col.separator(factor=separate_factor)
        col.label(text='Face Main (Mandatory)')

        row = col.row(align=True)
        self.draw_assign_group_options(row, 'main', 'Main')

        col.separator(factor=separate_factor)
        col.label(text='Eyeballs (Mandatory)')

        grid = col.grid_flow(columns=2, align=False)
        row = grid.row(align=True)
        self.draw_assign_group_options(row, 'left_eyeball', 'Left Eyeball')

        row = grid.row(align=True)
        self.draw_assign_group_options(row, 'right_eyeball', 'Right Eyeball')

        # Other Eyes
        col.separator(factor=separate_factor)
        col.label(text='Cornea, Iris, Spots, Highlights')

        grid = col.grid_flow(columns=2, align=False)
        row = grid.row(align=True)
        self.draw_assign_group_options(row, 'left_eyes_other', 'Other Left')

        row = grid.row(align=True)
        self.draw_assign_group_options(row, 'right_eyes_other', 'Other Right')

        # Eyelashes
        col.separator(factor=separate_factor)
        col.label(text='Eyelashes, Eyeshells, Tearlines')

        row = col.row(align=True)
        self.draw_assign_group_options(row, 'eyelashes', 'Eyelashes (Lids)')

        # Teeth
        col.separator(factor=separate_factor)
        col.label(text='Teeth, Gum')

        row = col.row(align=True)
        self.draw_assign_group_options(row, 'upper_teeth', 'Upper Teeth')

        row = col.row(align=True)
        self.draw_assign_group_options(row, 'lower_teeth', 'Lower Teeth')

        # Tongue
        col.separator(factor=separate_factor)
        col.label(text='Tongue')

        row = col.row(align=True)
        self.draw_assign_group_options(row, 'tongue', 'Tongue')

        # Rigid
        col.separator(factor=separate_factor)
        col.label(text='Rigid, No Deform')

        row = col.row(align=True)
        self.draw_assign_group_options(row, 'rigid', 'Rigid')

        if context.object:
            if context.object.type != 'MESH':
                col.enabled = False


class FACE_OBJECTS_UL_list(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        scene = context.scene
        face_objects = scene.faceit_face_objects
        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            row = layout.row(align=True)
            row.label(text=item.name, icon='OUTLINER_OB_MESH')

            obj = futils.get_object(item.name)
            if obj:
                if vg_utils.get_faceit_vertex_grps(obj):
                    row.operator('faceit.draw_assigned_groups_list', text='', icon='GROUP_VERTEX').obj_name = item.name

            if item.warnings and scene.faceit_show_warnings:
                op = row.operator('faceit.face_object_warning', text='', icon='ERROR')
                op.warnings = item.warnings

            op = row.operator('faceit.remove_facial_part', text='', icon='X')
            op.prompt = False
            op.remove_item = item.name

        else:
            layout.alignment = 'CENTER'
            layout.label(text='',)


class FACEIT_MT_FaceitObjects(bpy.types.Menu):
    bl_label = "Faceit Register Options"

    def draw(self, context):
        scene = context.scene
        faceit_objects = scene.faceit_face_objects
        face_index = scene.faceit_face_index
        active_item = faceit_objects[face_index]
        layout = self.layout

        row = layout.row(align=True)
        op = row.operator('faceit.clear_faceit_objects', text='Clear all Registered Objects', icon='TRASH')
        row = layout.row(align=True)
        op = row.operator('faceit.remove_faceit_groups', text='Reset All Vertex Groups', icon='TRASH')
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
                    op = row.operator('faceit.remove_faceit_groups', text='', icon='X')
                    op.faceit_vertex_group_names = fgroup
                    op = row.operator('faceit.select_faceit_groups', text='', icon='EDITMODE_HLT')
                    op.faceit_vertex_group_name = fgroup
                    op.object_list_index = index
                    row.label(text=fgroup)

    def execute(self, context):
        return{'FINISHED'}
