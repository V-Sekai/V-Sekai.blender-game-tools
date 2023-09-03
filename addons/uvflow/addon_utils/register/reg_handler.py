from enum import Enum, auto
from collections import defaultdict

import bpy
from bpy.app import handlers



to_register_handlers: dict[str, list] = defaultdict(list)
registered_handlers: dict[str, list] = defaultdict(list)


class Handlers(Enum):
    LOAD_PRE = auto()
    LOAD_POST = auto()
    ANNOTATION_PRE = auto()
    ANNOTATION_POST = auto()
    COMPOSITE_PRE = auto()
    COMPOSITE_POST = auto()
    COMPOSITE_CANCEL = auto()
    DEPSGRAPH_UPDATE_PRE = auto()
    DEPSGRAPH_UPDATE_POST = auto()
    FRAME_CHANGE_PRE = auto()
    FRAME_CHANGE_POST = auto()
    LOAD_FACTORY_PREFERENCES_PRE = auto()
    LOAD_FACTORY_PREFERENCES_POST = auto()
    OBJECT_BAKE_PRE = auto()
    OBJECT_BAKE_COMPLETE = auto()
    OBJECT_BAKE_CANCEL = auto()
    REDO_PRE = auto()
    REDO_POST = auto()
    RENDER_PRE = auto()
    RENDER_POST = auto()
    RENDER_INIT = auto()
    RENDER_COMPLETE = auto()
    RENDER_CANCEL = auto()
    RENDER_STATS = auto()
    RENDER_WRITE = auto()
    UNDO_PRE = auto()
    UNDO_POST = auto()
    VERSION_UPDATE = auto()
    XR_SESSION_START_PRE = auto()

    SAVE_PRE = auto()
    SAVE_POST = auto()

    def __call__(self, persistent: bool = False):
        ''' Use as a decorator. Only 1 parameter is required in target function, which is context. '''
        print(f"[UVFLOW] Registering... {self.name} Handler!")
        def decorator(deco_fun):

            def callback_deco(_deco_fun):
                def wrapper(*args, **kwargs):
                    # print(f"{self.name} Handler was called!") # _deco_fun.handler_type
                    _deco_fun(bpy.context, *args)
                    return None
                return wrapper

            deco_fun = callback_deco(deco_fun)
            # setattr(deco_fun, 'handler_type', self.name)
            if persistent:
                deco_fun = handlers.persistent(deco_fun)
            # getattr(handlers, self.name.lower()).append(deco_fun)
            to_register_handlers[self.name].append(deco_fun)
            return deco_fun
        return decorator

    def unregister_all(self):
        if self.name not in registered_handlers:
            return
        handler_type = getattr(handlers, self.name.lower())
        for handler in registered_handlers[self.name]:
            if handler in handler_type:
                handler_type.remove(handler)
        del registered_handlers[self.name]


def register():
    for handler_type, handler_funcs in to_register_handlers.items():
        handler_list = getattr(handlers, handler_type.lower())
        for handler_fun in handler_funcs:
            handler_list.append(handler_fun)
            registered_handlers[handler_type].append(handler_fun)

def unregister():
    for handler_type in Handlers:
        handler_type.unregister_all()
