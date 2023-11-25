from bpy.types import Context

from uvflow.addon_utils import Register
from uvflow.prefs import UVFLOW_Preferences
from uvflow.utils.tool import get_tool_label_from_context


save__use_uvflow_overlays = False


@Register.HANDLER.SAVE_PRE(persistent=True)
def on_save_pre(context: Context, *any_dummy_args):
    ''' Disable UVFlow overlays. '''
    prefs = UVFLOW_Preferences.get_prefs(context)
    global save__use_uvflow_overlays
    save__use_uvflow_overlays = prefs.use_overlays and get_tool_label_from_context(context) in {'Cut UV'}
    if save__use_uvflow_overlays:
        prefs.use_overlays = False


@Register.HANDLER.SAVE_POST(persistent=True)
def on_save_post(context: Context, *any_dummy_args):
    ''' Enable UVFlow overlays. '''
    global save__use_uvflow_overlays
    if save__use_uvflow_overlays:
        prefs = UVFLOW_Preferences.get_prefs(context)
        prefs.use_overlays = True
