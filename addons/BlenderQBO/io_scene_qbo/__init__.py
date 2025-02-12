# SPDX-FileCopyrightText: 2011-2022 Blender Foundation
#
# SPDX-License-Identifier: GPL-2.0-or-later

bl_info = {
    "name": "Quaternion-BVH-OBJ (QBO) format",
    "author": "Pierce Brooks",
    "version": (1, 0, 0),
    "blender": (2, 81, 6),
    "location": "File > Import-Export",
    "description": "Import-Export QBO from scenes",
    "warning": "",
    "doc_url": "{BLENDER_MANUAL_URL}/addons/import_export/scene_qbo.html",
    "support": 'OFFICIAL',
    "category": "Import-Export",
}

if "bpy" in locals():
    import importlib
    if "import_qbo" in locals():
        importlib.reload(import_qbo)
    if "export_qbo" in locals():
        importlib.reload(export_qbo)

import bpy
from bpy.props import (
    StringProperty,
    FloatProperty,
    IntProperty,
    BoolProperty,
    EnumProperty,
)
from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper,
)


class ImportQBO(bpy.types.Operator, ImportHelper):
    """Load a QBO file"""
    bl_idname = "import_scene.qbo"
    bl_label = "Import QBO"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".qbo"
    filter_glob: StringProperty(default="*.qbo", options={'HIDDEN'})

    frame_start: IntProperty(
        name="Start Frame",
        description="Starting frame for the animation",
        default=1,
    )
    use_fps_scale: BoolProperty(
        name="Scale FPS",
        description=(
            "Scale the framerate from the QBO to the current scenes, "
            "otherwise each QBO frame maps directly to a Blender frame"
        ),
        default=False,
    )
    update_scene_fps: BoolProperty(
        name="Update Scene FPS",
        description=(
            "Set the scene framerate to that of the QBO file (note that this "
            "nullifies the 'Scale FPS' option, as the scale will be 1:1)"
        ),
        default=False,
    )
    update_scene_duration: BoolProperty(
        name="Update Scene Duration",
        description="Extend the scene's duration to the QBO duration (never shortens the scene)",
        default=False,
    )
    use_cyclic: BoolProperty(
        name="Loop",
        description="Loop the animation playback",
        default=False,
    )

    def execute(self, context):
        keywords = self.as_keywords(
            ignore=(
                "filter_glob",
            )
        )

        from . import import_qbo
        return import_qbo.load(context, report=self.report, **keywords)

    def draw(self, context):
        pass


class QBO_PT_import_main(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = ""
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'HIDE_HEADER'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "IMPORT_SCENE_OT_qbo"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "target")


class QBO_PT_import_transform(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Transform"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "IMPORT_SCENE_OT_qbo"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        #layout.prop(operator, "global_scale")
        #layout.prop(operator, "axis_forward")
        #layout.prop(operator, "axis_up")


class QBO_PT_import_animation(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Animation"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "IMPORT_SCENE_OT_qbo"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "frame_start")
        layout.prop(operator, "use_fps_scale")
        layout.prop(operator, "use_cyclic")

        layout.prop(operator, "update_scene_fps")
        layout.prop(operator, "update_scene_duration")


class ExportQBO(bpy.types.Operator, ExportHelper):
    """Save a QBO file from an armature"""
    bl_idname = "export_scene.qbo"
    bl_label = "Export QBO"

    filename_ext = ".qbo"
    filter_glob: StringProperty(
        default="*.qbo",
        options={'HIDDEN'},
    )

    frame_start: IntProperty(
        name="Start Frame",
        description="Starting frame to export",
        default=0,
    )
    frame_end: IntProperty(
        name="End Frame",
        description="End frame to export",
        default=0,
    )
    root_transform_only: BoolProperty(
        name="Root Translation Only",
        description="Only write out translation channels for the root bone",
        default=False,
    )
    sort_child_names: BoolProperty(
        name="Sort Child Names",
        description="Sort the name ordering of children for each bone alphabetically",
        default=True,
    )
    bone_weight_limit: IntProperty(
        name="Bone Weight Limit",
        description="The maximum number of weights any vertex can have for its influencing bones (negative for no limiting)",
        default=4,
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'ARMATURE'

    def invoke(self, context, event):
        self.frame_start = context.scene.frame_start
        self.frame_end = context.scene.frame_end

        return super().invoke(context, event)

    def execute(self, context):
        if self.frame_start == 0 and self.frame_end == 0:
            self.frame_start = context.scene.frame_start
            self.frame_end = context.scene.frame_end

        keywords = self.as_keywords(
            ignore=(
                "check_existing",
                "filter_glob",
            )
        )

        from . import export_qbo
        return export_qbo.save(context, **keywords)

    def draw(self, context):
        pass


class QBO_PT_export_transform(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Transform"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_qbo"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        #layout.prop(operator, "global_scale")
        #layout.prop(operator, "axis_forward")
        #layout.prop(operator, "axis_up")
        layout.prop(operator, "root_transform_only")
        layout.prop(operator, "sort_child_names")
        layout.prop(operator, "bone_weight_limit")


class QBO_PT_export_animation(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Animation"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_qbo"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        col = layout.column(align=True)
        col.prop(operator, "frame_start", text="Frame Start")
        col.prop(operator, "frame_end", text="End")


def menu_func_import(self, context):
    self.layout.operator(ImportQBO.bl_idname, text="Qbo (.qbo)")
    pass


def menu_func_export(self, context):
    self.layout.operator(ExportQBO.bl_idname, text="Qbo (.qbo)")


classes = (
    ImportQBO,
    QBO_PT_import_main,
    QBO_PT_import_transform,
    QBO_PT_import_animation,
    ExportQBO,
    QBO_PT_export_transform,
    QBO_PT_export_animation,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
