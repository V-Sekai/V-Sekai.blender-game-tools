import bpy


def write_mesh_data(context, filepath):
    f = open(filepath, 'w', encoding='utf-8')

    f.write("# voxel heat diffuse mesh export.\n")

    objs = []

    # get armature and mesh
    for ob in bpy.context.selected_objects:
        if 'MESH' == ob.type:
            objs.append(ob)

    # sort meshes by name
    objs.sort(key=lambda obj:obj.name);

    vertex_offset = 0
    for obj in objs:
        for v in obj.data.vertices:
            world_v_co = obj.matrix_world @ v.co
            f.write("v,{},{},{}\n".format(world_v_co[0], world_v_co[1], world_v_co[2]))

        for poly in obj.data.polygons:
            f.write("f");
            for loop_ind in poly.loop_indices:
                vert_ind = obj.data.loops[loop_ind].vertex_index
                f.write(",{}".format(vertex_offset + vert_ind))
            f.write("\n")

        vertex_offset += len(obj.data.vertices)

    f.close()

    return {'FINISHED'}


# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ExportVoxelMesh(Operator, ExportHelper):
    """Export voxel mesh"""
    bl_idname = "export_voxel.mesh"
    bl_label = "Export Voxel Mesh"
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
        return (context.mode == 'OBJECT' and arm_count == 0 and obj_count >= 1)


    # ExportHelper mixin class uses this
    filename_ext = ".txt"

    filter_glob: StringProperty(
            default="*.txt",
            options={'HIDDEN'},
            maxlen=255,  # Max internal buffer length, longer would be clamped.
            )

    def execute(self, context):
        return write_mesh_data(context, self.filepath)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportVoxelMesh.bl_idname, text="Voxel Mesh (.txt)")


def register_voxel_heat_diffuse_export_mesh():
    bpy.utils.register_class(ExportVoxelMesh)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister_voxel_heat_diffuse_export_mesh():
    bpy.utils.unregister_class(ExportVoxelMesh)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register_voxel_heat_diffuse_export_mesh()

    # test call
    bpy.ops.export_voxel.mesh('INVOKE_DEFAULT')
