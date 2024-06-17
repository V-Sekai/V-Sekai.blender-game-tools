import bpy


def write_bone_data(context, filepath):
    f = open(filepath, 'w', encoding='utf-8')

    f.write("# voxel heat diffuse bone export.\n")

    obj = bpy.context.object
    amt = obj.data
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in amt.edit_bones:
        if bone.use_deform:
            # ignore unselected bones
            if bpy.context.scene.voxel_use_selected_bones and not bone.select:
                continue
            world_bone_head = obj.matrix_world @ bone.head
            world_bone_tail = obj.matrix_world @ bone.tail
            f.write("b,{},{},{},{},{},{},{}\n".format(
            bone.name.replace(",", "\\;"), world_bone_head[0], world_bone_head[1], world_bone_head[2],
            world_bone_tail[0], world_bone_tail[1], world_bone_tail[2]))
    bpy.ops.object.mode_set(mode='OBJECT')

    f.close()

    return {'FINISHED'}


# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ExportVoxelBone(Operator, ExportHelper):
    """Export voxel bone"""
    bl_idname = "export_voxel.bone"
    bl_label = "Export Voxel Bone"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        arm_count = 0
        obj_count = 0
        for ob in bpy.context.selected_objects:
            if 'ARMATURE' == ob.type:
                arm_count += 1
            if 'MESH' == ob.type:
                obj_count += 1
        return (context.mode == 'OBJECT' and arm_count == 1 and obj_count == 0)


    # ExportHelper mixin class uses this
    filename_ext = ".txt"

    filter_glob: StringProperty(
            default="*.txt",
            options={'HIDDEN'},
            maxlen=255,  # Max internal buffer length, longer would be clamped.
            )

    def execute(self, context):
        return write_bone_data(context, self.filepath)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportVoxelBone.bl_idname, text="Voxel Bone (.txt)")


def register_voxel_heat_diffuse_export_bone():
    bpy.utils.register_class(ExportVoxelBone)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister_voxel_heat_diffuse_export_bone():
    bpy.utils.unregister_class(ExportVoxelBone)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register_voxel_heat_diffuse_export_bone()

    # test call
    bpy.ops.export_voxel.bone('INVOKE_DEFAULT')
