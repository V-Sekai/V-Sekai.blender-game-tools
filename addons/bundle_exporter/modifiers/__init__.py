import bpy
import os
import importlib

# ---------------------------------------------------------------------------- #
#                            AUTO LOAD ALL MODIFIERS                           #
# ---------------------------------------------------------------------------- #
tree = [x[:-3] for x in os.listdir(os.path.dirname(__file__)) if x.endswith('.py') and x != '__init__.py']

for i in tree:
    importlib.import_module('.' + i, package=__package__)

__globals = globals().copy()

modifier_classes = []
created_classes = []

num_id = 1
for x in [x for x in __globals if x.startswith('modifier_')]:
    for y in [item for item in dir(__globals[x]) if item.startswith('BGE_mod_')]:
        mod = getattr(__globals[x], y)
        mod.unique_num = num_id
        modifier_classes.append(mod)
        num_id += 1

modifier_annotations = {}
for modifier_class in modifier_classes:
    created_type = type(modifier_class.__name__, (modifier_class,), modifier_class.__dict__.copy())
    created_classes.append(created_type)
    modifier_annotations[modifier_class.settings_name()] = (bpy.props.PointerProperty, {'type': created_type})
BGE_modifiers = type("BGE_modifiers", (bpy.types.PropertyGroup,), {'__annotations__': modifier_annotations, 'bl_idname':'BGE_modifiers'})
print(modifier_annotations)

# ---------------------------------------------------------------------------- #
#                              REGISTER/UNREGISTER                             #
# ---------------------------------------------------------------------------- #

# registers the modifiers used by the scene and bundles (they are registered after the addon preferences because they need to reference it)
def register():
    from bpy.utils import register_class

    modifier_annotations = {}
    for modifier_class in created_classes:
        modifier_class.register_dependants()
        register_class(modifier_class)
    register_class(BGE_modifiers)

def unregister():
    from bpy.utils import unregister_class

    unregister_class(BGE_modifiers)

    for x in created_classes:
        unregister_class(x)
        x.unregister_dependants()

# ---------------------------------------------------------------------------- #
#                                   UTILITIES                                  #
# ---------------------------------------------------------------------------- #

def get_modifiers_iter(modifier_group):
    for x in modifier_group.keys():
        if x.startswith('BGE_modifier_'):
            try:
                attr = getattr(modifier_group, x)
                yield attr
            except AttributeError:
                pass


def get_modifiers(modifier_group):
    return [x for x in get_modifiers_iter(modifier_group)]


def draw(layout, context, modifier_group, draw_only_active=False, types={'GENERAL', 'MESH', 'HELPER', 'ARMATURE'}):
    col = layout.column()

    modifiers_to_draw = []
    for x in created_classes:
        modifier = getattr(modifier_group, x.settings_name())
        if modifier.type in types:
            if not draw_only_active or modifier.active:
                modifiers_to_draw.append(modifier)
    modifiers_to_draw = sorted(modifiers_to_draw)
    for x in modifiers_to_draw:
        box = col.box()
        x.draw(box, active_as_x=draw_only_active)
