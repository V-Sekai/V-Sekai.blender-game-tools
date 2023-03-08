bl_info = {
    "name": "Import Obj Sequence",
    "author": "MarcusZ",
    "version": (1, 0, 2),
    "blender": (2, 80, 0),
    "location": "File > Import/Export",
    "description": "Import Obj Sequence",
    "doc_url": "",
    "support": "COMMUNITY",
    "category": "Import-Export",
}


import bpy
from pathlib import Path
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    StringProperty,
)
from bpy_extras.io_utils import ImportHelper


class ImportObjSeq(bpy.types.Operator, ImportHelper):
    """Load an OBJ Sequence as absolute shape keys"""

    bl_idname = "import_scene.objseq"
    bl_label = "Import OBJ Seq"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".obj"
    filter_glob: StringProperty(default="*.obj", options={"HIDDEN"})

    files: CollectionProperty(
        name="File Path",
        description="File path used for importing the OBJ sequence",
        type=bpy.types.OperatorFileListElement,
    )
    directory: StringProperty()

    relative_shapekey: BoolProperty(
        name="Relative ShapeKey",
        description="Import shapes as relative shapekeys. Uncheck to import absolute shapekeys.",
        default=True,
    )

    def execute(self, context):
        filepaths = [Path(self.directory, n.name) for n in self.files]
        if not filepaths:
            filepaths.append(self.filepath)

        self.create_shapekeys(filepaths)

        return {"FINISHED"}

    def create_shapekeys(self, filepaths):
        from contextlib import redirect_stdout

        def import_obj(filepath):
            with redirect_stdout(None):
                bpy.ops.import_scene.obj(filepath=filepath, filter_glob='*.obj;*.mtl', use_edges=True, use_smooth_groups=True, use_split_objects=False, use_split_groups=False, use_groups_as_vgroups=False, use_image_search=True, split_mode='ON', global_clamp_size=0.0, axis_forward='-Z', axis_up='Y')

        # import first obj
        import_obj(str(filepaths[0]))
        main_obj = bpy.context.selected_objects[-1]
        main_obj.location = [0, 0, 0]
        main_obj.rotation_euler = [0, 0, 0]
        main_obj.shape_key_add(name=main_obj.name)
        for face in main_obj.data.polygons:
            face.use_smooth = True
        main_key = main_obj.data.shape_keys
        bpy.context.view_layer.objects.active = main_obj
        seq_len = len(filepaths)

        # import the rest
        for i, filepath in enumerate(filepaths[1:]):
            import_obj(str(filepath))
            current_obj = bpy.context.selected_objects[-1]
            current_obj.location = [0, 0, 0]
            current_obj.rotation_euler = [0, 0, 0]

            # join as shapes
            bpy.ops.object.join_shapes()
            print(f"{i}/{seq_len}", end="\r")

            # remove meshes
            current_mesh = current_obj.data
            current_mat = current_obj.material_slots[0].material
            bpy.data.objects.remove(current_obj, do_unlink=True)
            bpy.data.meshes.remove(current_mesh, do_unlink=True)
            bpy.data.materials.remove(current_mat, do_unlink=True)

        if self.relative_shapekey:
            # set keyframes
            main_key.use_relative = True
            for i, key_block in enumerate(main_key.key_blocks[1:]):
                key_block.value = 0.0
                key_block.keyframe_insert("value", frame=i)
                key_block.value = 1.0
                key_block.keyframe_insert("value", frame=i+1)
                key_block.value = 0.0
                key_block.keyframe_insert("value", frame=i+2)

        else:
            # set driver
            main_key.use_relative = False
            fcurve = main_key.driver_add("eval_time")
            fcurve.driver.expression = "frame*10"

        # set start/end time
        bpy.context.scene.frame_start = 0
        bpy.context.scene.frame_end = seq_len - 1


def menu_func_import(self, context):
    self.layout.operator(ImportObjSeq.bl_idname, text="Obj Seq As Shapekey(.obj)")


def register():
    bpy.utils.register_class(ImportObjSeq)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportObjSeq)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
