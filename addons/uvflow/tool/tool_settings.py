import bpy

from uvflow.addon_utils import Register, Property
from uvflow.prefs import UVFLOW_Preferences

from uvflow.operators.op_pack import UVPack
from uvflow.operators.op_unwrap import UVUnwrap
from uvflow.operators.op_editor_management import ToggleUVEditor, ToggleGNEditor, get_gn_editor, get_uv_editor
from uvflow.operators.op_viewer import ActivateViewer

from bpy.types import Context, UILayout
from bl_ui.properties_data_mesh import DATA_PT_uv_texture


@Register.UI.POPOVER
class UVFlowTS_UVMapPopover:
    def draw_ui(self, context: Context, layout: UILayout) -> None:
        ''' Here draw the Unwrap options. '''
        prefs = UVFLOW_Preferences.get_prefs(context)

        class HackDataPTContext:
            def __getattribute__(self, attr: str):
                # FIX -> AttributeError: 'Context' object has no attribute 'mesh'.
                if attr == 'mesh':
                    return context.object.data
                return getattr(context, attr)

        DATA_PT_uv_texture.draw(self, HackDataPTContext())

        '''
        options_row = layout.row()
        options_row.prop(prefs, 'use_seam_layers')
        '''



@Register.UI.POPOVER
class UVFlowTS_UnwrapPopover:
    def draw_ui(self, context: Context, layout: UILayout) -> None:
        ''' Here draw the Unwrap options. '''
        prefs = UVFLOW_Preferences.get_prefs(context)
        content = layout.column()
        UVFLOW_Preferences.draw_unwrap_prefs(prefs, content)
        content.separator()
        UVUnwrap.draw_in_layout(content, label='Unwrap UVs')


@Register.UI.POPOVER
class UVFlowTS_PackPopover:
    def draw_ui(self, context: Context, layout: UILayout) -> None:
        ''' Here draw the Pack options. '''
        prefs = UVFLOW_Preferences.get_prefs(context)
        content = layout.column()
        UVFLOW_Preferences.draw_packing_prefs(prefs, content)
        content.separator()
        UVPack.draw_in_layout(content, label='Pack UVs')


@Register.UI.POPOVER
class UVFlowTS_OverlayPopover:
    def draw_ui(self, context: Context, layout: UILayout) -> None:
        ''' Here draw the Checker Texture options. '''
        prefs = UVFLOW_Preferences.get_prefs(context)
        content = layout.column()
        UVFLOW_Preferences.draw_seam_prefs(prefs, content)
        UVFLOW_Preferences.draw_texture_prefs(prefs, content)
        # UVFLOW_Preferences.draw_face_overlay_prefs(prefs, content)

        if prefs.face_highlight == 'NONE':
            return

        gn_editor = get_gn_editor(context.window)

        ToggleGNEditor.draw_in_layout(layout, label="Toggle GN Editor", depress=(gn_editor is not None))

        if gn_editor is None:
            msg_box = layout.box()
            msg_box.scale_y = 0.8
            msg_box.alert = True
            msg_box.label(text="To activate the overlays viewer")
            msg_box.label(text="you need to open a GN editor first")

        ActivateViewer.draw_in_layout(layout, label="Activate Viewer")


@Register.UI.POPOVER
class UVFlowTS_InfoPopover:
    def draw_ui(self, context: Context, layout: UILayout) -> None:
        content = layout.column()
        content.use_property_split=True
        content.use_property_decorate=False
        from uvflow import bl_info
        version = str(bl_info['version']).replace('(', '').replace(')', '').replace(',', '.').replace(' ', '')
        content.label(text=f'UV Flow {version}')
        content.operator("wm.url_open", text='Read the Docs', icon='HELP').url = 'https://cgcookie.github.io/uvflow/'
        content.operator("wm.url_open", text='Report an Issue', icon='ERROR').url = 'https://orangeturbine.com/p/contact'
        content.operator("wm.url_open", text='View on Blender Market', icon='IMPORT').url = 'https://blendermarket.com/creators/orangeturbine'

#####################################################################


@Register.PROP_GROUP.ROOT.SCENE('uvflow_tool_settings')
class UVFlowToolSettings:
    '''Add tool specific settings here if they don't belong in preferences'''

    #TODO: The smoothing property of the last subdiv in the stack is now set directly,
    # but it would be nice to set it for all subdiv modifiers on all objects in edit mode
    '''
    subdiv: Property.ENUM(
        name="Subdiv Smoothing",
        items=(
            ("DEFAULT", "Default", "Does not change the Subdiv Modifier"),
            ("NONE", "None", "UVs are not smoothed"),
            ("PRESERVE_CORNERS", "Keep Corners",
                "Only corners on discontinuous boundaries are kept sharp"),
            ("PRESERVE_CORNERS_AND_JUNCTIONS", "Keep Corners, Junctions",
                "Corners on discontinuous boundaries and junctions of 3 or more regions are kept sharp"),
            ("PRESERVE_CORNERS_JUNCTIONS_AND_CONCAVE", "Keep Corners, Junctions, Concave",
                "Corners on discontinuous boundaries, junctions of 3 or more regions, darts, and concave corners are kept sharp"),
            ("PRESERVE_BOUNDARIES", "Keep Boundaries", "All boundaries of the UV islands are kept sharp"),
            ("SMOOTH_ALL", "All", "All UV points are smoothed")
        ),
        default="DEFAULT",
        description="Sets the UV Smooth property of any Subdiv modifier in the modifier stack",
        update=lambda self, ctx: update_subdiv(ctx)
    )
    '''

    @staticmethod
    def get_data(context: Context) -> 'UVFlowToolSettings':
        return context.scene.uvflow_tool_settings

    @classmethod
    def draw(cls, context: Context, layout: UILayout):
        prefs = UVFLOW_Preferences.get_prefs(context)
        ts_data = cls.get_data(context)

        ''' UV Editor. '''
        use_uveditor = context.scene.uvflow.uv_editor_enabled and get_uv_editor(context.window) is not None
        ToggleUVEditor.draw_in_layout(layout, label='UV Editor', icon='UV', depress=use_uveditor)

        ''' UV MAP. '''
        icon = 'GROUP_UVS'
        act_uvmap = context.object.data.uv_layers.active
        UVFlowTS_UVMapPopover.draw_in_layout(layout, label=act_uvmap.name if act_uvmap else 'UV Map', icon='GROUP_UVS')

        ''' Unwrap. '''
        row = layout.row(align=True)
        icon = 'REC'
        row.prop(prefs, 'use_auto_unwrap', text="", toggle=True, icon=icon)
        UVFlowTS_UnwrapPopover.draw_in_layout(row, label="Unwrap")
        UVUnwrap.draw_in_layout(row, icon='TRIA_RIGHT', label='')

        ''' Pack. '''
        if bpy.app.version > (3, 6, 0):
            row = layout.row(align=True)
            icon = 'REC'
            row.prop(prefs, 'use_auto_pack', text="", toggle=True, icon=icon)
            UVFlowTS_PackPopover.draw_in_layout(row, label="Pack")
            UVPack.draw_in_layout(row, icon='TRIA_RIGHT', label='')

        ''' Overlays. '''
        row = layout.row(align=True)
        icon = 'TEXTURE'
        row.prop(prefs, 'use_overlays', text="", toggle=True, icon=icon)
        UVFlowTS_OverlayPopover.draw_in_layout(row, label="UV Overlays")

        ''' Subdiv. '''
        modifiers = [x for x in context.object.modifiers]
        if any(x.type =='SUBSURF' for x in modifiers):
            row = layout.row(align=True)
            icon = 'MOD_SUBSURF'
            row.prop(modifiers[-1], 'uv_smooth')

        ''' Help '''
        UVFlowTS_InfoPopover.draw_in_layout(layout, label="", icon='INFO')

