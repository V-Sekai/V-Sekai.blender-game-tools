from .reg_common import BlenderTypes
from ..types.prefs import BaseAddonPreferences
from .reg_ui import DrawExtension


##########################################################################
##########################################################################
# Decorator to register UI classes.
##########################################################################

def _register_preferences(cls, base_cls) -> BaseAddonPreferences:
    from .._loader import __main_package__
    prefs_cls = type(
        cls.__name__,
        (cls, base_cls, DrawExtension),
        {
            'bl_idname': __main_package__,
        }
    )
    BlenderTypes.PREFERENCES.add_class(prefs_cls)
    return prefs_cls


##########################################################################
##########################################################################
# enum-like-class UTILITY TO REGISTER ADDON PREFS CLASSES PER SUBTYPE.
##########################################################################

class AddonPreferencesRegister:
    GENERIC = lambda cls: _register_preferences(cls, BaseAddonPreferences)
    CONFIG_BACKUP = None # TODO: class that serialize addon preferences automatically to load from previous version when updating addon.
