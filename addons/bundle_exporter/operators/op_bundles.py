import bpy

from .. import bundles
from .. import modifiers


class BGE_OT_select(bpy.types.Operator):
    """Select the objects of the bundle"""
    bl_idname = "bge.select"
    bl_label = "Select Bundle"

    index: bpy.props.IntProperty(name="index")

    @classmethod
    def description(cls, context, properties):
        ans = ''
        bundle = bpy.context.scene.BGE_Settings.bundles[properties.index]
        for x in bundle.objects:
            ans += x.name + '\n'
        return ans

    def invoke(self, context, event):
        if event.ctrl or event.shift:
            bpy.context.scene.BGE_Settings.bundles[self.index].select(alone=False)
        else:
            bpy.context.scene.BGE_Settings.bundles[self.index].select()
        return {'FINISHED'}


class BGE_OT_create_bundle(bpy.types.Operator):
    """Create new bundle"""
    bl_idname = "bge.create_bundle"
    bl_label = "Create Bundle"

    def execute(self, context):
        bundles.create_bundles_from_selection()
        return {'FINISHED'}

    @classmethod
    def poll(self, context):
        return len(bpy.context.selected_objects) > 0

    @classmethod
    def description(cls, context, properties):
        if len(bpy.context.selected_objects) > 0:
            return "Create new bundle(s) from selected objects"
        else:
            return "Select objects to create a bundle"


mesh_modifiers = [(x.id, x.label, "add " + x.label, x.icon, x.unique_num) for x in modifiers.modifier_classes if x.type == 'MESH']
general_modifiers = [(x.id, x.label, "add " + x.label, x.icon, x.unique_num) for x in modifiers.modifier_classes if x.type == 'GENERAL']
helper_modifiers = [(x.id, x.label, "add " + x.label, x.icon, x.unique_num) for x in modifiers.modifier_classes if x.type == 'HELPER']
armature_modifiers = [(x.id, x.label, "add " + x.label, x.icon, x.unique_num) for x in modifiers.modifier_classes if x.type == 'ARMATURE']
modifier_enum = [("", "General", "description", "MODIFIER", 0)] + general_modifiers + [("", "Mesh", "description", "OUTLINER_OB_MESH", 0)] + mesh_modifiers + [("", "Empty", "description", "OUTLINER_OB_EMPTY", 0)] + helper_modifiers + [("", "Armature", "description", "OUTLINER_OB_ARMATURE", 0)] + armature_modifiers


class BGE_OT_override_bundle_modifier(bpy.types.Operator):
    """Add a modifier to the selected bundle, if the same modifier is already activated in the scene modifiers this will override it"""
    bl_idname = "bge.override_bundle_modifier"
    bl_label = "Add Override Modifier"

    option: bpy.props.EnumProperty(items=modifier_enum)

    @classmethod
    def description(cls, context, properties):
        mods = modifiers.get_modifiers(bpy.context.scene.BGE_Settings.bundles[bpy.context.scene.BGE_Settings.bundle_index].override_modifiers)
        for x in mods:
            if x.id == properties.option:
                return x.tooltip

        return "not implemented"

    def execute(self, context):
        mods = modifiers.get_modifiers(bpy.context.scene.BGE_Settings.bundles[bpy.context.scene.BGE_Settings.bundle_index].override_modifiers)
        for x in mods:
            if x.id == self.option:
                x.active = True
                x.show_info = True

        return {'FINISHED'}


class BGE_OT_add_bundle_modifier(bpy.types.Operator):
    """Add a modifier to the scene modifiers stack, these modifiers will be applied to the bundles when exported"""
    bl_idname = "bge.add_bundle_modifier"
    bl_label = "Add Export Modifier"

    option: bpy.props.EnumProperty(items=modifier_enum)

    @classmethod
    def description(cls, context, properties):
        mods = modifiers.get_modifiers(bpy.context.scene.BGE_Settings.bundles[bpy.context.scene.BGE_Settings.bundle_index].override_modifiers)
        for x in mods:
            if x.id == properties.option:
                return x.tooltip

        return "not implemented"

    def execute(self, context):
        mods = modifiers.get_modifiers(bpy.context.scene.BGE_Settings.scene_modifiers)
        for x in mods:
            if x.id == self.option:
                x.active = True
                x.show_info = True

        return {'FINISHED'}


class BGE_OT_remove(bpy.types.Operator):
    """Remove the bundle"""
    bl_idname = "bge.remove"
    bl_label = "Remove Bundle"

    index: bpy.props.IntProperty(name="index")

    def execute(self, context):
        bpy.context.scene.BGE_Settings.bundles.remove(self.index)
        return {'FINISHED'}
