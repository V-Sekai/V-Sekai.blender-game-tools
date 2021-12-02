import bpy
# from bpy.types import Panel

from . import draw_utils
from . import bake_panel
# from . import setup_panel
# from . import mocap_panel
# from . import c_rig_panel
# from . import shapes_panel
# from . import rigging_panel
# from . import expresssions_panel
from ..core import faceit_utils as futils


class FACEIT_PT_Base():
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FACEIT'
    bl_label = 'Base'
    bl_options = {'DEFAULT_CLOSED'}
    # bl_parent_id = 'FACEIT_PT_MainPanel'
    # faceit_predecessor = ''

    faceit_predecessor = 'FACEIT_PT_MainPanel'
    UI_TAB = 'SETUP'
    UI_WORKSPACES = ('ALL', 'RIG', 'MOCAP')

    @classmethod
    def poll(cls, context):
        workspace = context.scene.faceit_workspace
        if workspace.workspace in cls.UI_WORKSPACES:
            pin_panel = bpy.context.scene.faceit_pin_panels
            return workspace.active_tab == cls.UI_TAB or pin_panel.get_pin(
                cls.bl_idname)

    def draw_header_preset(self, context):
        row = self.layout.row()

        pin_panel = bpy.context.scene.faceit_pin_panels
        if pin_panel.get_pin(self.bl_idname):
            if context.scene.faceit_workspace.active_tab != self.UI_TAB:
                row.label(text=self.UI_TAB)
            icon = 'PINNED'
        else:
            icon = 'UNPINNED'
        row.prop(pin_panel, self.bl_idname, text='', emboss=False, icon=icon)

    def draw(self, context):
        layout = self.layout


class FACEIT_PT_BaseSub():
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FACEIT'
    bl_label = 'Base Sub'
    bl_options = {'DEFAULT_CLOSED'}

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

        # current_version = fdata.get_faceit_current_version()

        scene = context.scene

        layout = self.layout

        box = layout.box()
        row = box.row()
        faceit_workspace = scene.faceit_workspace

        draw_utils.draw_panel_dropdown_expander(row, faceit_workspace, 'expand_ui', 'Choose Workspace')

        if faceit_workspace.expand_ui:
            box.row().prop(faceit_workspace, 'workspace', expand=True, icon='CUBE')

        active_tab = faceit_workspace.active_tab
        layout.row().prop(faceit_workspace, 'active_tab', expand=True)

        layout.separator()

        rig = futils.get_faceit_armature()
        # if scene.faceit_use_rigify_armature:
        #     rig = futils.get_faceit_armature()
        # else:
        #     rig = futils.get_faceit_armature(force_original=True)

        c_rig = futils.get_faceit_control_armature()

        ############ SETUP ################
        # if active_tab == 'SETUP':

        #     setup_panel.draw(context, layout)

        ############ RIGGING ################

        if active_tab == 'CREATE':
            if not scene.faceit_face_objects:
                col = layout.column()
                row = col.row()
                row.alert = True
                op = row.operator('faceit.go_to_tab', text='Complete Setup first...')
                op.tab = 'SETUP'
                return
            # rigging_panel.draw(context, layout, landmarks_obj, rig)

        ############ ADAPTION ################

        # rig = get_faceit_armature()

        if active_tab == 'EXPRESSIONS':
            if not rig:
                col = layout.column()
                row = col.row()
                row.alert = True
                op = row.operator('faceit.go_to_tab', text='Generate Rig First...')
                op.tab = 'CREATE'
        #     expresssions_panel.draw(context, layout, landmarks_obj, rig)

        ############ BAKING ################

        if active_tab == 'BAKE':
            bake_panel.draw(context, layout, rig)

        ############ MOCAP ################

        # if active_tab == 'MOCAP':
        #     mocap_panel.draw(context, layout)

        ############ SHAPES ################

        # if active_tab == 'SHAPES':
        #     shapes_panel.draw(context, layout)

        ############ CONTROL RIG ################

        # if active_tab == 'CONTROL':
        #     c_rig_panel.draw(context, layout, c_rig, landmarks_obj)
