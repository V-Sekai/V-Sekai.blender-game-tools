import bpy
import sys
import os
import time
import platform
from subprocess import PIPE, Popen
from threading  import Thread
from bpy.props import *
from queue import Queue, Empty

class VXL_OT_ModalTimerOperator(bpy.types.Operator):
    """Operator which runs its self from a timer"""
    bl_idname = "wm.voxel_heat_diffuse"
    bl_label = "Voxel Heat Diffuse Skinning"
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None
    _pid = None
    _queue = None

    _objs = []
    _permulation = []
    _selected_indices = []
    _selected_group_index_weights = []

    _start_time = None

    def write_bone_data(self, obj, filepath):
        f = open(filepath, 'w', encoding='utf-8')

        f.write("# voxel heat diffuse bone export.\n")

        amt = obj.data
        bpy.ops.object.mode_set(mode='EDIT')
        at_least_one_bone = False
        for bone in amt.edit_bones:
            if bone.use_deform:
                # ignore unselected bones
                if bpy.context.scene.voxel_use_selected_bones and not bone.select:
                    continue
                at_least_one_bone = True
                world_bone_head = obj.matrix_world @ bone.head
                world_bone_tail = obj.matrix_world @ bone.tail
                f.write("b,{},{},{},{},{},{},{}\n".format(
                bone.name.replace(",", "\\;"), world_bone_head[0], world_bone_head[1], world_bone_head[2],
                world_bone_tail[0], world_bone_tail[1], world_bone_tail[2]))
        bpy.ops.object.mode_set(mode='OBJECT')

        f.close()

        return at_least_one_bone

    def write_mesh_data(self, objs, filepath):
        f = open(filepath, 'w', encoding='utf-8')

        f.write("# voxel heat diffuse mesh export.\n")

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

    def read_weight_data(self, objs, filepath):
        # make permulation for all vertices
        vertex_offset = 0;
        for obj in objs:
            for index in range(len(obj.data.vertices)):
                self._permulation.append((vertex_offset + index, index, obj))
            vertex_offset += len(obj.data.vertices)

        if bpy.context.scene.voxel_protect:
            for index in range(len(objs)):
                obj = objs[index]
                # get selected vertex indices
                self._selected_indices.append([i.index for i in obj.data.vertices if i.select])
                self._selected_group_index_weights.append([])

                # push protected vertices weight
                for vert_ind in self._selected_indices[index]:
                    for g in obj.data.vertices[vert_ind].groups:
                        self._selected_group_index_weights[index].append((obj.vertex_groups[g.group].name, vert_ind, g.weight))

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
                vert_ind = self._permulation[index][1]
                weight = float(tokens[3])
                obj = self._permulation[index][2]
                # protect vertices weight
                if bpy.context.scene.voxel_protect and vert_ind in self._selected_indices[objs.index(obj)]:
                    continue
                obj.vertex_groups[group_name].add([vert_ind], weight, 'REPLACE')

        f.close()

        if bpy.context.scene.voxel_protect:
            for index in range(len(objs)):
                obj = objs[index]
                # pop protected vertices weight
                for (group_name, vert_ind, weight) in self._selected_group_index_weights[index]:
                    obj.vertex_groups[group_name].add([vert_ind], weight, 'REPLACE')

    def modal(self, context, event):
        if event.type == 'ESC':
            self._pid.terminate()
            return self.cancel(context)

        if event.type == 'TIMER':
            # background task is still running
            if self._pid.poll() == None:
                # read line without blocking
                try:
                    rawline = self._queue.get_nowait()
                except Empty:
                    pass
                else:
                    line = rawline.decode().strip("\r\n")
                    self.report({'INFO'}, line)
            else:
                # background task finished running
                try:
                    self.read_weight_data(self._objs, os.path.join(os.path.dirname(__file__), "data", "untitled-weight.txt"))
                except:
                    pass
                running_time = time.time() - self._start_time
                self.report({'INFO'}, "".join(("Complete, ", "running time: ", \
                str(int(running_time / 60))," minutes ", str(int(running_time % 60)), " seconds")))
                # bind meshes to the armature
                bpy.ops.object.parent_set(type='ARMATURE')
                return self.cancel(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        arm_count = 0
        obj_count = 0
        for ob in bpy.context.selected_objects:
            if 'ARMATURE' == ob.type:
                arm_count += 1
            if 'MESH' == ob.type:
                obj_count += 1
        if not (context.mode == 'OBJECT' and arm_count == 1 and obj_count >= 1):
            self.report({'ERROR'}, "Please select one armature and at least one mesh in 'OBJECT' mode, then try again.")
            return {'CANCELLED'}

        self._objs = []
        self._permulation = []
        self._selected_indices = []
        self._selected_group_index_weights = []

        arm = None
        objs = []

        # get armature and mesh
        for ob in bpy.context.selected_objects:
            if 'ARMATURE' == ob.type:
                arm = ob
            if 'MESH' == ob.type:
                objs.append(ob)

        # sort meshes by name
        objs.sort(key=lambda obj:obj.name);
        # save the reference for later use
        self._objs = objs

        for obj in objs:
            # focus on the mesh
            bpy.context.view_layer.objects.active = obj
            # synchronize data
            bpy.ops.object.mode_set(mode='OBJECT')

        # write mesh data
        self.write_mesh_data(objs, os.path.join(os.path.dirname(__file__), "data", "untitled-mesh.txt"))

        # we must focus on the armature before we can write bone data
        bpy.context.view_layer.objects.active = arm
        # synchronize data
        bpy.ops.object.mode_set(mode='OBJECT')

        # write bone data
        if not self.write_bone_data(arm, os.path.join(os.path.dirname(__file__), "data", "untitled-bone.txt")):
            if bpy.context.scene.voxel_use_selected_bones:
                self.report({'ERROR'}, "Please select at least one deform bone, then try again.")
            else:
                self.report({'ERROR'}, "Please setup at least one deform bone, then try again.")
            return {'CANCELLED'}

        def enqueue_output(out, queue):
            for line in iter(out.readline, b''):
                queue.put(line)
            out.close()

        executable_path = None
        if platform.system() == 'Windows':
            if platform.machine().lower().endswith('amd64') or platform.machine().lower().endswith('x86_64'):
                executable_path = os.path.join(os.path.dirname(__file__), "bin", platform.system(), "x64", "vhd")
            elif platform.machine().lower().endswith('arm64') or platform.machine().lower().endswith('aarch64'):
                executable_path = os.path.join(os.path.dirname(__file__), "bin", platform.system(), "arm64", "vhd")
            else:
                executable_path = os.path.join(os.path.dirname(__file__), "bin", platform.system(), "x86", "vhd")
        else:
            if platform.system() == 'Linux':
                if platform.machine().lower().endswith('amd64') or platform.machine().lower().endswith('x86_64'):
                    executable_path = os.path.join(os.path.dirname(__file__), "bin", platform.system(), "x64", "vhd")
                elif platform.machine().lower().endswith('arm64') or platform.machine().lower().endswith('aarch64'):
                    executable_path = os.path.join(os.path.dirname(__file__), "bin", platform.system(), "arm64", "vhd")
            elif platform.system() == 'Darwin':
                executable_path = os.path.join(os.path.dirname(__file__), "bin", platform.system(), "vhd")
            # chmod
            if not os.access(executable_path, os.X_OK):
                os.chmod(executable_path, 0o755)

        ON_POSIX = 'posix' in sys.builtin_module_names
        self._pid = Popen([executable_path,
                        "untitled-mesh.txt",
                        "untitled-bone.txt",
                        "untitled-weight.txt",
                        str(context.scene.voxel_resolution),
                        str(context.scene.voxel_loops),
                        str(context.scene.voxel_samples),
                        str(context.scene.voxel_influence),
                        str(context.scene.voxel_falloff),
                        "y" if context.scene.detect_voxel_solidify else "n",
                        "y" if context.scene.voxel_use_half_cpu_cores else "n"],
                        cwd = os.path.join(os.path.dirname(__file__), "data"),
                        stdout = PIPE,
                        bufsize = 1,
                        close_fds = ON_POSIX)

        # do the job in background
        bpy.context.scene.voxel_job_finished = False

        self._queue = Queue()
        t = Thread(target=enqueue_output, args=(self._pid.stdout, self._queue))
        t.daemon = True
        t.start()

        self._start_time = time.time()
        # start timer to poll data
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        # remove timer
        context.window_manager.event_timer_remove(self._timer)
        self._objs = []
        self._permulation = []
        self._selected_indices = []
        self._selected_group_index_weights = []

        bpy.context.scene.voxel_job_finished = True

        return {'CANCELLED'}

def init_properties():
    bpy.types.Scene.voxel_resolution = IntProperty(
        name = "Voxel Resolution",
        description = "Maximum voxel grid size",
        default = 128,
        min = 32,
        max = 1024)

    bpy.types.Scene.voxel_loops = IntProperty(
        name = "Diffuse Loops",
        description = "Heat diffuse pass = Voxel Resolution * Diffuse Loops",
        default = 5,
        min = 1,
        max = 9)

    bpy.types.Scene.voxel_samples = IntProperty(
        name = "Sample Rays",
        description = "Ray samples count",
        default = 64,
        min = 32,
        max = 128)

    bpy.types.Scene.voxel_influence = IntProperty(
        name = "Influence Bones",
        description = "Max influence bones per vertex, please decrease the value (such as 4) for mobile devices",
        default = 8,
        min = 1,
        max = 128)

    bpy.types.Scene.voxel_falloff = FloatProperty(
        name = "Diffuse Falloff",
        description = "Heat diffuse falloff",
        default = 0.2,
        min = 0.01,
        max = 0.99)

    bpy.types.Scene.voxel_protect = BoolProperty(
        name = "Protect Selected Vertex Weight",
        description = "Protect selected vertex weight",
        default = False)

    bpy.types.Scene.voxel_job_finished = BoolProperty(
        name = "Voxel Job Finished",
        description = "Whether or not the voxel job has finished",
        default = True)

    bpy.types.Scene.detect_voxel_solidify = BoolProperty(
        name = "Detect Solidify",
        description = "Detect solidified clothes, if you enable this option, make sure that all bones are in the charecter's volume, otherwise, the result may be wrong",
        default = False)

    bpy.types.Scene.voxel_use_selected_bones = BoolProperty(
        name = "Use Selected Bones",
        description = "Use only selected bones",
        default = False)

    bpy.types.Scene.voxel_use_half_cpu_cores = BoolProperty(
        name = "Use Half CPU Cores",
        description = "Use only half of the CPU cores, if your computer get stuck, please enable this option to keep your computer running smoothly",
        default = False)

def clear_properties():
    props = ["voxel_resolution",
    "voxel_samples",
    "voxel_falloff",
    "voxel_loops",
    "voxel_influence",
    "voxel_protect",
    "voxel_job_finished",
    "detect_voxel_solidify",
    "voxel_use_selected_bones",
    "voxel_use_half_cpu_cores"]

    for p in props:
        if p in bpy.types.Scene.bl_rna.properties:
            exec("del bpy.types.Scene." + p)

class VXL_PT_VoxelHeatDiffuseSkinningPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Voxel Heat Diffuse Skinning"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Mesh Online'

    @classmethod
    def poll(self, context):
        return True


    def draw(self, context):
        layout = self.layout

        layout.prop(context.scene, 'voxel_resolution', icon='BLENDER', toggle=True)
        layout.prop(context.scene, 'voxel_loops', icon='BLENDER', toggle=True)
        layout.prop(context.scene, 'voxel_samples', icon='BLENDER', toggle=True)
        layout.prop(context.scene, 'voxel_influence', icon='BLENDER', toggle=True)
        layout.prop(context.scene, 'voxel_falloff', icon='BLENDER', toggle=True)
        layout.prop(context.scene, 'voxel_protect')
        layout.prop(context.scene, 'detect_voxel_solidify')
        layout.prop(context.scene, 'voxel_use_selected_bones')
        layout.prop(context.scene, 'voxel_use_half_cpu_cores')

        row = layout.row()
        row.operator("wm.voxel_heat_diffuse")


def register_voxel_heat_diffuse_skinning():
    bpy.utils.register_class(VXL_PT_VoxelHeatDiffuseSkinningPanel)
    bpy.utils.register_class(VXL_OT_ModalTimerOperator)
    init_properties()


def unregister_voxel_heat_diffuse_skinning():
    bpy.utils.unregister_class(VXL_PT_VoxelHeatDiffuseSkinningPanel)
    bpy.utils.unregister_class(VXL_OT_ModalTimerOperator)
    clear_properties()


if __name__ == "__main__":
    register_voxel_heat_diffuse_skinning()
