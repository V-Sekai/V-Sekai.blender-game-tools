import bpy

from ..core import faceit_utils as futils
from . import draw_utils


class FACEIT_PT_Base():
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FACEIT'
    bl_label = 'Base'
    bl_options = {'DEFAULT_CLOSED'}
    # bl_parent_id = 'FACEIT_PT_MainPanel'
    # faceit_predecessor = ''

    faceit_predecessor = 'FACEIT_PT_MainPanel'
    UI_TABS = ('SETUP',)
    UI_WORKSPACES = ('ALL', 'RIG', 'MOCAP')

    @classmethod
    def poll(cls, context):
        workspace = context.scene.faceit_workspace
        if workspace.workspace in cls.UI_WORKSPACES:
            pin_panel = bpy.context.scene.faceit_pin_panels
            return workspace.active_tab in cls.UI_TABS or pin_panel.get_pin(
                cls.bl_idname)

    def draw_header_preset(self, context):
        row = self.layout.row()

        pin_panel = bpy.context.scene.faceit_pin_panels
        if pin_panel.get_pin(self.bl_idname):
            if context.scene.faceit_workspace.active_tab not in self.UI_TABS:
                row.label(text=self.UI_TABS[0])
            icon = 'PINNED'
        else:
            icon = 'UNPINNED'
        row.prop(pin_panel, self.bl_idname, text='', emboss=False, icon=icon)

    def draw(self, context):
        pass


class FACEIT_PT_BaseSub():
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FACEIT'
    bl_label = 'Base Sub'
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = ''
    faceit_predecessor = ''

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout


class FACEIT_PT_MainPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FACEIT'
    bl_label = 'FaceIt'
    bl_idname = 'FACEIT_PT_MainPanel'
    # bl_options = {'HIDE_HEADER'}
    bl_order = 0

    def draw(self, context):

        scene = context.scene

        layout = self.layout

        box = layout.box()
        row = box.row()
        faceit_workspace = scene.faceit_workspace

        if faceit_workspace.expand_ui:
            icon = 'TRIA_DOWN'
        else:
            icon = 'TRIA_RIGHT'
        row.prop(faceit_workspace, 'expand_ui', text='Choose Workspace',
                 icon=icon, icon_only=True, emboss=False)

        if faceit_workspace.expand_ui:
            box.row().prop(faceit_workspace, 'workspace', expand=True, icon='CUBE')

        active_tab = faceit_workspace.active_tab
        layout.row().prop(faceit_workspace, 'active_tab', expand=True)

        layout.separator()

        rig = context.scene.faceit_armature
        if active_tab != 'SETUP':
            if not scene.faceit_face_objects and not scene.faceit_control_armature:
                col = layout.column()
                row = col.row()
                row.alert = True
                op = row.operator('faceit.go_to_tab', text='Complete Setup First...')
                op.tab = 'SETUP'
                return

        if active_tab in ('CONTROL', 'MOCAP'):
            if not scene.faceit_arkit_retarget_shapes and not scene.faceit_arkit_retarget_shapes and not scene.faceit_control_armature:
                col = layout.column()
                row = col.row()
                row.alert = True
                op = row.operator('faceit.go_to_tab', text='No Targets Shapes found...')
                op.tab = 'SHAPES'
                return

        elif active_tab in ('EXPRESSIONS', 'BAKE', 'CREATE'):
            if rig is None:
                if scene.faceit_armature_missing:
                    col = layout.column()
                    row = col.row()
                    row.alert = True
                    row.label(text="Warning: The Faceit Rig has been deleted.")
                if active_tab != 'CREATE':
                    col = layout.column()
                    row = col.row()
                    row.alert = True
                    op = row.operator('faceit.go_to_tab', text='Generate Rig First...')
                    op.tab = 'CREATE'
            elif active_tab == 'BAKE':
                if 'overwrite_shape_action' not in bpy.data.actions or not scene.faceit_expression_list:
                    col = layout.column()
                    row = col.row()
                    row.alert = True
                    op = row.operator('faceit.go_to_tab', text='Generate Expressions First...')
                    op.tab = 'EXPRESSIONS'

        if futils.get_any_view_locked():
            row = layout.row()
            row.operator("faceit.unlock_3d_view", icon='LOCKED', depress=True)
