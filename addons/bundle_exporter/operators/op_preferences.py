import bpy
import imp


class BGE_OT_save_preferences(bpy.types.Operator):
    bl_idname = "bge.save_preferences"
    bl_label = "Save Preferences"

    def execute(self, context):
        from .. import core
        from .. import modifiers

        bpy.ops.wm.save_userpref()

        modifiers.unregister_locals()
        modifiers.register_locals()

        core.unregister()
        imp.reload(core)
        core.register()

        return {'FINISHED'}


class BGE_OT_load_preferences(bpy.types.Operator):
    """Reload the addon preferences"""
    bl_idname = "bge.load_preferences"
    bl_label = "Load Preferences"

    def execute(self, context):
        print('TODO: LOAD PREFERENCES')
        return {'FINISHED'}
