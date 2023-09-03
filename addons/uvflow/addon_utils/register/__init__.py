from .reg_operator import OperatorRegister
from .reg_ui import UIRegister
from .reg_property import PropertyRegister, BatchPropertyRegister
from .reg_property_group import PropertyGroupRegister
from .reg_shortcut import ShortcutRegister
from .reg_prefs import AddonPreferencesRegister
from .reg_tool import ToolsRegister

from .reg_handler import Handlers
from .reg_rna_sub import subscribe_to_rna_change, subscribe_to_rna_change_based_on_context # RNASubscription
from .reg_timer import new_timer_as_decorator


class Register:
    PREFS = AddonPreferencesRegister
    OPS = OperatorRegister
    UI = UIRegister
    PROP_GROUP = PropertyGroupRegister
    PROP = PropertyRegister
    PROP_BATCH = BatchPropertyRegister
    SHORTCUT = ShortcutRegister
    TOOLS = ToolsRegister
    RNA_SUB = subscribe_to_rna_change
    RNA_SUB_CONTEXT = subscribe_to_rna_change_based_on_context
    TIMER = new_timer_as_decorator
    HANDLER = Handlers
