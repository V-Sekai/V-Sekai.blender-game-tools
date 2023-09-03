from typing import Union, Type, Callable, List, Tuple

from bpy.types import Menu, Panel

from .reg_common import BlenderTypes
from ..types.ui import UI_TYPES, MenuUI, PanelUI, DrawExtension


BL_UI_TYPES = Union[Menu, Panel]

ui_appends: List[Tuple[BL_UI_TYPES, Callable, bool]] = []


##########################################################################
##########################################################################
# Decorator to register UI classes.
##########################################################################


def _register_ui(cls, base_cls, suffix: str = 'PT', **bl_kwargs: dict) -> UI_TYPES:
    # Create new dynamic type.
    ui_cls: UI_TYPES = type(
        cls.__name__,
        (cls, *base_cls),
        {
            'bl_idname': 'UVFLOW_' + suffix + '_' + cls.__name__.lower(),
            'bl_label': cls.label if hasattr(cls, 'label') else cls.__name__,
            **bl_kwargs
        }
    )

    # Add new class for the registering.
    BlenderTypes.INTERFACE.add_class(ui_cls)
    return ui_cls


def _register_ui__append(bl_ui_class: BL_UI_TYPES, prepend: bool = False) -> Callable:
    def _decorator(func: Callable) -> Callable:
        ui_appends.append((bl_ui_class, lambda ui, ctx: func(ctx, ui.layout), prepend))
        return func
    return _decorator


##########################################################################
##########################################################################
# enum-like-class UTILITY TO REGISTER UI CLASSES PER SUBTYPE.
##########################################################################

class UIRegister:
    MENU = lambda cls: _register_ui(cls, (MenuUI, Menu), 'MT')
    
    class PANEL:
        def new(cls, space_type: str = '', region_type: str = '', **kwargs) -> Union[DrawExtension, PanelUI, Panel]:
            return _register_ui(cls, (PanelUI, DrawExtension, Panel), 'PT', **{
                'bl_space_type': space_type, 'bl_region_type': region_type, 'bl_category': getattr(cls, 'tab', 'UVFlow'), **kwargs})

        VIEW3D = lambda cls: UIRegister.PANEL.new(cls, 'VIEW_3D', 'UI')
        IMAGE_EDITOR = lambda cls: UIRegister.PANEL.new(cls, 'IMAGE_EDITOR', 'UI')

    
    POPOVER = lambda cls: UIRegister.PANEL.new(cls, 'TOPBAR', 'HEADER', bl_options={"INSTANCED"})

    APPEND = _register_ui__append



##############################################

def register():
    for ui_append in ui_appends:
        bl_ui_type, draw_ext, prepend = ui_append
        if prepend:
            bl_ui_type.prepend(draw_ext)
        else:
            bl_ui_type.append(draw_ext)

def unregister():
    for ui_append in ui_appends:
        bl_ui_type, draw_ext, _prepend = ui_append
        bl_ui_type.remove(draw_ext)
    # ui_appends.clear()
