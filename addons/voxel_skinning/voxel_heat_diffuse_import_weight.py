import bpy


def read_weight_data(context, filepath, voxel_protect):
    arm = None
    objs = []
    permulation = []
    selected_indices = []
    selected_group_index_weights = []

    # get armature and mesh
    for ob in bpy.context.selected_objects:
        if 'ARMATURE' == ob.type:
            arm = ob
        if 'MESH' == ob.type:
            objs.append(ob)

    # sort meshes by name
    objs.sort(key=lambda obj:obj.name);

    # make permulation for all vertices
    vertex_offset = 0;
    for obj in objs:
        for index in range(len(obj.data.vertices)):
            permulation.append((vertex_offset + index, index, obj))
        vertex_offset += len(obj.data.vertices)

    if voxel_protect:
        for index in range(len(objs)):
            obj = objs[index]
            # get selected vertex indices
            selected_indices.append([i.index for i in obj.data.vertices if i.select])
            selected_group_index_weights.append([])

            # push protected vertices weight
            for vert_ind in selected_indices[index]:
                for g in obj.data.vertices[vert_ind].groups:
                    selected_group_index_weights[index].append((obj.vertex_groups[g.group].name, vert_ind, g.weight))

    f = open(filepath, 'r', encoding='utf-8')

    bones = []
    for line in f:
        if len(line) == 0:
            continue
        tokens = line.strip("\r\n").split(",")
        if tokens[0] == "b":
            group_name = tokens[1].replace("\\;", ",")
            bones.append(group_name)
            for obj in objs:
                #check for existing group with the same name
                if None != obj.vertex_groups.get(group_name):
                    group = obj.vertex_groups[group_name]
                    obj.vertex_groups.remove(group)
                obj.vertex_groups.new(name = group_name)
        if tokens[0] == "w":
            group_name = bones[int(tokens[2])]
            index = int(tokens[1])
            vert_ind = permulation[index][1]
            weight = float(tokens[3])
            obj = permulation[index][2]
            # protect vertices weight
            if voxel_protect and vert_ind in selected_indices[objs.index(obj)]:
                continue
            obj.vertex_groups[group_name].add([vert_ind], weight, 'REPLACE')

    f.close()

    if voxel_protect:
        for index in range(len(objs)):
            obj = objs[index]
            # pop protected vertices weight
            for (group_name, vert_ind, weight) in selected_group_index_weights[index]:
                obj.vertex_groups[group_name].add([vert_ind], weight, 'REPLACE')

    # we must focus on the armature before we can bind meshes to the armature
    bpy.context.view_layer.objects.active = arm
    # synchronize data
    bpy.ops.object.mode_set(mode='OBJECT')
    # bind meshes to the armature
    bpy.ops.object.parent_set(type='ARMATURE')

    return {'FINISHED'}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ImportVoxelWeight(Operator, ImportHelper):
    """Import voxel weight"""
    bl_idname = "import_voxel.weight"
    bl_label = "Import Voxel Weight"
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
        return (context.mode == 'OBJECT' and arm_count == 1 and obj_count >= 1)


    # ImportHelper mixin class uses this
    filename_ext = ".txt"

    filter_glob: StringProperty(
            default="*.txt",
            options={'HIDDEN'},
            maxlen=255,  # Max internal buffer length, longer would be clamped.
            )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    voxel_protect: BoolProperty(
            name="Protect Selected Vertex Weight",
            description="Protect selected vertex weight",
            default=False,
            )

    def execute(self, context):
        return read_weight_data(context, self.filepath, self.voxel_protect)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportVoxelWeight.bl_idname, text="Voxel Weight (.txt)")


def register_voxel_heat_diffuse_import_weight():
    bpy.utils.register_class(ImportVoxelWeight)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister_voxel_heat_diffuse_import_weight():
    bpy.utils.unregister_class(ImportVoxelWeight)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register_voxel_heat_diffuse_import_weight()

    # test call
    bpy.ops.import_voxel.weight('INVOKE_DEFAULT')
