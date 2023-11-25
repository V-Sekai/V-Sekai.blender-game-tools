from uvflow.addon_utils import Register, Property
import bpy
from bpy.props import BoolProperty


@Register.PROP_GROUP.ROOT.TEMPORAL('uvflow')
class TempProps:
    show_uvmap_section: BoolProperty(name="Show UV Map Options", default=True)
    show_unwrap_section: BoolProperty(name="Show Unwrap Options", default=False)
    show_pack_section: BoolProperty(name="Show Pack Options", default=False)
    show_overlays_section: BoolProperty(name="Show Overlays Options", default=False)
    show_info_section: BoolProperty(name="Show Info Options", default=False)

    @staticmethod
    def get_data(context) -> 'TempProps':
        return context.window_manager.uvflow
