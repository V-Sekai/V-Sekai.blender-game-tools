import bpy
from bl_ui.space_view3d import VIEW3D_PT_active_tool

from dataclasses import dataclass

from uvflow.addon_utils import Register, Property
from uvflow.prefs import UVFLOW_Preferences

from uvflow.operators.op_pack import UVPack
from uvflow.operators.op_unwrap import UVUnwrap
from uvflow.operators.op_mark_seams import UVMarkSeams
from uvflow.operators.op_editor_management import ToggleUVEditor, ToggleGNEditor
from uvflow.operators.op_viewer import ActivateViewer
from uvflow.utils.editor_gn import get_gn_editor
from uvflow.utils.editor_uv import get_uv_editor
from uvflow.utils.ui_layout import draw_section_panel
from uvflow.props.temp import TempProps

from bpy.types import Context, UILayout
from bl_ui.properties_data_mesh import DATA_PT_uv_texture



@dataclass
class DummyPanel:
    layout: UILayout


@Register.UI.POPOVER
class UVFlowTS_UVMapPopover:
    label = 'UV Maps'

    def draw_ui(self, context: Context, layout: UILayout) -> None:
        ''' Here draw the Unwrap options. '''
        class HackDataPTContext:
            def __getattribute__(self, attr: str):
                # FIX -> AttributeError: 'Context' object has no attribute 'mesh'.
                if attr == 'mesh':
                    return context.object.data
                return getattr(context, attr)

        if layout is None:
            return
        DATA_PT_uv_texture.draw(DummyPanel(layout), HackDataPTContext())


@Register.UI.POPOVER
class UVFlowTS_UnwrapPopover:
    label = 'Unwrap'

    def draw_ui(self, context: Context, layout: UILayout) -> None:
        ''' Here draw the Unwrap options. '''
        if layout is None:
            return

        prefs = UVFLOW_Preferences.get_prefs(context)
        content = layout.column()
        UVFLOW_Preferences.draw_auto_unwrap_prefs(prefs, content, context)
        UVFLOW_Preferences.draw_unwrap_prefs(prefs, content, context)
        UVFLOW_Preferences.draw_split_seams_prefs(prefs, content)
        UVFLOW_Preferences.draw_split_prefs(prefs, content)
        content.separator()
        row = content.row()
        UVMarkSeams.draw_in_layout(row,  label='Mark Split', op_props={'use_seam':True})
        UVMarkSeams.draw_in_layout(row, label='Clear Split', op_props={'use_seam':False})
        UVFLOW_Preferences.draw_unwrap_apply_prefs(prefs, content)
        content.separator()
        UVUnwrap.draw_in_layout(content, label='Unwrap UVs')


@Register.UI.POPOVER
class UVFlowTS_PackPopover:
    label = 'Pack'

    def draw_ui(self, context: Context, layout: UILayout) -> None:
        ''' Here draw the Pack options. '''
        if layout is None:
            return

        prefs = UVFLOW_Preferences.get_prefs(context)
        content = layout.column()
        UVFLOW_Preferences.draw_packing_prefs(prefs, content, context)
        content.separator()
        UVPack.draw_in_layout(content, label='Pack UVs')


@Register.UI.POPOVER
class UVFlowTS_OverlayPopover:
    label = 'UV Overlays'

    def draw_ui(self, context: Context, layout: UILayout) -> None:
        ''' Here draw the Checker Texture options. '''
        if layout is None:
            return

        prefs = UVFLOW_Preferences.get_prefs(context)
        content = layout.column()
        content.use_property_split=True
        content.use_property_decorate=False
        UVFLOW_Preferences.draw_overlay_enable_prefs(prefs, content, context)
        UVFLOW_Preferences.draw_seam_prefs(prefs, content, context)
        content.separator()
        UVFLOW_Preferences.draw_texture_prefs(prefs, content, context)
        # UVFLOW_Preferences.draw_face_overlay_prefs(prefs, content, context)

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
    label = 'Info'

    def draw_ui(self, context: Context, layout: UILayout) -> None:
        if layout is None:
            return

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
        use_popover = context.region.type == 'TOOL_HEADER'
        if not use_popover:
            dummy_self = DummyPanel(layout)
        tmp_props = TempProps.get_data(context)

        prefs = UVFLOW_Preferences.get_prefs(context)
        ts_data = cls.get_data(context)

        ''' UV Editor. '''
        use_uveditor = context.scene.uvflow.uv_editor_enabled and get_uv_editor(context.window) is not None
        if use_popover:
            ToggleUVEditor.draw_in_layout(layout, label='UV Editor', icon='UV', depress=use_uveditor)
        else:
            ToggleUVEditor.draw_in_layout(layout, label='Toggle UV Editor', icon='UV', depress=use_uveditor)
            layout.separator()

        ''' Sidebar Subdiv. '''
        modifiers = [x for x in context.object.modifiers]
        if not use_popover and any(x.type =='SUBSURF' for x in modifiers):
            layout.prop(modifiers[-1], 'uv_smooth', text="Subdiv UVs")
            layout.separator()

        ''' UV MAP. '''
        act_uvmap = context.object.data.uv_layers.active
        if use_popover:
            UVFlowTS_UVMapPopover.draw_in_layout(layout, label=act_uvmap.name if act_uvmap else 'UV Maps', icon='GROUP_UVS')
        else:
            UVFlowTS_UVMapPopover.draw_ui(dummy_self, context, draw_section_panel(
                (tmp_props, 'show_uvmap_section'), layout, 'UV Maps')
            )

        ''' Unwrap. '''
        row = layout.row(align=True)
        if use_popover:
            row.prop(prefs, 'use_auto_unwrap', text="", toggle=True, icon='REC')
            UVFlowTS_UnwrapPopover.draw_in_layout(row, label="Unwrap")
            UVUnwrap.draw_in_layout(row, icon='TRIA_RIGHT', label='')
        else:
            UVFlowTS_UnwrapPopover.draw_ui(dummy_self, context, draw_section_panel(
                (tmp_props, 'show_unwrap_section'), layout, 'Unwrap'
            ))

        ''' Pack. '''
        if bpy.app.version > (3, 6, 0):
            row = layout.row(align=True)
            if use_popover:
                # row.prop(prefs, 'use_auto_pack', text="", toggle=True, icon='REC')
                UVFlowTS_PackPopover.draw_in_layout(row, label="Pack")
                UVPack.draw_in_layout(row, icon='TRIA_RIGHT', label='')
            else:
                UVFlowTS_PackPopover.draw_ui(dummy_self, context, draw_section_panel(
                    (tmp_props, 'show_pack_section'), layout, 'Pack')
                )

        ''' Overlays. '''
        row = layout.row(align=True)
        if use_popover:
            row.prop(prefs, 'use_overlays', text="", toggle=True, icon='TEXTURE')
            UVFlowTS_OverlayPopover.draw_in_layout(row, label="UV Overlays")
        else:
            UVFlowTS_OverlayPopover.draw_ui(dummy_self, context, draw_section_panel(
                (tmp_props, 'show_overlays_section'), layout, 'UV Overlays')
            )

        ''' Header Subdiv. '''
        if use_popover and any(x.type =='SUBSURF' for x in modifiers):
            layout.prop(modifiers[-1], 'uv_smooth', text='Subdiv')

        ''' Help '''
        if use_popover:
            UVFlowTS_InfoPopover.draw_in_layout(layout, label="", icon='INFO')
        else:
            UVFlowTS_InfoPopover.draw_ui(dummy_self, context, draw_section_panel(
                (tmp_props, 'show_info_section'), layout, 'Tool Info')
            )
