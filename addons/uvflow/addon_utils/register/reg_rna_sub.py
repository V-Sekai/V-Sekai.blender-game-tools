import bpy
from .reg_timer import new_timer_as_decorator

from collections import defaultdict


owners = []

rna_listeners: dict[object, dict] = {}
ctx_rna_listeners: dict[object, dict] = {}


def subscribe_to_rna_change(bpy_rna_type: type, attr_name: str, data_path: str | None = None, persistent: bool = False):
    def decorator(decorated_func):
        def rna_callback_decorator(decorated_func):
            def wrapper(*args, **kwargs):
                # print(f"RNA change {bpy_rna_type.__name__}.{attr_name}")
                ctx = bpy.context
                if data_path is not None:
                    data = ctx.path_resolve(data_path)
                else:
                    data = getattr(ctx, bpy_rna_type.__name__.lower(), None)
                decorated_func(ctx, data, getattr(data, attr_name) if data is not None else None)
            return wrapper

        owner = object()
        options = set()
        if persistent:
            options.add('PERSISTENT')
        rna_listeners[owner] = {
            'key': (bpy_rna_type, attr_name),
            'owner': owner,
            'args': (),
            'notify': rna_callback_decorator(decorated_func),
            'options': options
        }
    return decorator


def subscribe_to_rna_change_based_on_context(data_path: str, attr_name: str, persistent: bool,):
    def decorator(decorated_func):
        def rna_callback_decorator(_decorated_func):
            def wrapper(*args, **kwargs):
                # print(f"RNA change {bpy_rna_type.__name__}.{attr_name}")
                ctx = bpy.context
                data = ctx.path_resolve(data_path)
                _decorated_func(ctx, data, getattr(data, attr_name))
            return wrapper

        owner = object()
        options = set()
        if persistent:
            options.add('PERSISTENT')
        ctx = bpy.context
        ctx_rna_listeners[owner] = {
            'key': data_path + '.' + attr_name,
            'owner': owner,
            'args': (),
            'notify': rna_callback_decorator(decorated_func),
            'options': options
        }
    return decorator


def register():
    if not rna_listeners:
        return
    
    print("\n-----------------------\nRNA Subscriptions:")
    for owner, data in rna_listeners.items():
        bpy_data, data_attr = data['key']
        print(f"\t> {bpy_data.__name__} . {data_attr}")
        bpy.msgbus.subscribe_rna(**data)
        owners.append(owner)
    print("-----------------------")


def unregister():
    for owner in owners:
        bpy.msgbus.clear_by_owner(owner)
    owners.clear()


@new_timer_as_decorator(first_interval=0.1, one_time_only=True, persistent=True)
def register_rna_sub_powered_by_context(*args):
    print("\n-----------------------\nRNA Subscriptions (context-based):")
    context = bpy.context
    for owner, data in ctx_rna_listeners.items():
        print(f"\t> {'Context'} . {data['key']}")
        data['key'] = context.path_resolve(data['key'], False)
        bpy.msgbus.subscribe_rna(**data)
        owners.append(owner)
    print("-----------------------")
