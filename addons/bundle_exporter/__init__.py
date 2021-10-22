import bpy
import bpy.utils.previews

from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    PointerProperty,
)

from . import modifiers
from . import operators
from . import settings
from .settings import mode_bundle_types, mode_pivot_types
from . import addon_updater_ops

bl_info = {
    "name": "Bundle Exporter",
    "description": "Export objects in bundles",
    "author": "AquaticNightmare",
    "blender": (2, 82, 0),
    "version": (2, 3, 2),
    "category": "3D View",
    "location": "3D View > Tools Panel > Bundle Exporter",
    "warning": "",
    "wiki_url": "https://gitlab.com/AquaticNightmare/bundle_exporter",
    "doc_url": "https://gitlab.com/AquaticNightmare/bundle_exporter",
    "tracker_url": "https://gitlab.com/AquaticNightmare/bundle_exporter/-/issues",
}


# https://blender.stackexchange.com/questions/118118/blender-2-8-field-property-declaration-and-dynamic-class-creation
def export_presets_getter(self, context):
    items = settings.get_presets_enum(bpy.context.preferences.addons[__name__.split('.')[0]].preferences.export_format)
    return items


def update_scene_export_preset(self, context):
    context.scene.BGE_Settings.export_preset = self.export_preset


class BGE_preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    mode_bundle: bpy.props.EnumProperty(items=mode_bundle_types, name="Bundle Mode", default='COLLECTION')
    mode_pivot: bpy.props.EnumProperty(items=mode_pivot_types, name="Pivot From", default='OBJECT_FIRST')

    export_format: bpy.props.EnumProperty(items=settings.export_formats)
    export_preset: bpy.props.EnumProperty(items=export_presets_getter, update=update_scene_export_preset)
    # addon updater preferences

    auto_check_update: bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=True,
    )
    updater_intrval_months: bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0
    )
    updater_intrval_days: bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31
    )
    updater_intrval_hours: bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23
    )
    updater_intrval_minutes: bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59
    )

    def draw(self, context):
        layout = self.layout

        addon_updater_ops.update_settings_ui(self, context)

        box = layout.box()
        row = box.row(align=True)
        row.label(text='Default Settings (manually save preferences after changing values please)', icon='PREFERENCES')

        col = box.column(align=True)
        col.prop(self, 'export_format', text="Export Format")
        col.prop(self, 'export_preset', text="Export Preset")
        col.prop(self, "mode_bundle", text="Bundle by")
        col.prop(self, "mode_pivot", text="Bundle by", icon='OUTLINER_DATA_EMPTY')

        col.operator('bge.save_preferences', text='Save User Preferences', icon='FILE_TICK')


def register():
    print('--> REGISTER INIT')
    from bpy.utils import register_class

    addon_updater_ops.register(bl_info)

    register_class(BGE_preferences)

    modifiers.register()

    operators.register()

    # we need to load core after the addon preferences have been registered, because classes in this module reference them
    from . import core
    import imp
    imp.reload(core)

    core.register()


def unregister():
    print('### UNREGISTER INIT')
    from bpy.utils import unregister_class

    from . import core

    core.unregister()

    modifiers.unregister()

    operators.unregister()

    unregister_class(BGE_preferences)

    addon_updater_ops.unregister()
