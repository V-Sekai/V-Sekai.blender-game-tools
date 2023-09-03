from uvflow.addon_utils import Register, Property
import bpy


@Register.PROP_GROUP.ROOT.TEMPORAL('uvflow')
class TempProps:
    @staticmethod
    def get_data(context) -> 'TempProps':
        return context.window_manager.uvflow
