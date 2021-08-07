# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****

import bpy
import bmesh
import sys
import os
import time
import platform
import math
import mathutils
import random
import copy
import numpy as np
from bpy.props import *
from bpy.types import Operator

class CSB_OT_ModalTimerOperator(bpy.types.Operator):
    """Operator which runs its self from a timer"""
    bl_idname = "wm.corrective_smooth_baker"
    bl_label = "Corrective Smooth Baker"
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None

    _arm = None
    _objs = None
    _should_terminate = False
    _inverse_bind_pose_dic = None
    _static_positions = None
    _sharp_vertex_index_dics = None
    _transform_matrix_dics = None
    _dynamic_positions = None
    _mesh_index = 0
    _pose_index = 0
    _vertex_index = 0
    _optimize_stage_index = 0
    _current_pose_dic = None
    _transform_matrix_stack = None

    _start_time = None

    def save_current_poses(self):
        self._current_pose_dic = {}
        for bone in self._arm.pose.bones:
            self._current_pose_dic[bone] = copy.deepcopy(bone.matrix_basis)


    def restore_current_poses(self):
        for bone in self._arm.pose.bones:
            bone.matrix_basis = self._current_pose_dic[bone]


    def reset_armature(self, ob):
        if bpy.app.version < (2, 80):
            # ready to switch mode
            ob.hide = False
            # select the object
            ob.select = True
            # must set to active object
            bpy.context.scene.objects.active = ob
        else:
            # ready to switch mode
            ob.hide_set(False)
            # select the object
            ob.select_set(True)
            # must set to active object
            bpy.context.view_layer.objects.active = ob
        # must be in pose mode to reset transform of selected bones
        bpy.ops.object.mode_set(mode='POSE', toggle=False)
        # select all bones
        bpy.ops.pose.select_all(action='SELECT')
        # Reset location, rotation, and scaling of selected bones to their default values
        bpy.ops.pose.transforms_clear()
        # exit pose mode
        bpy.ops.object.mode_set(mode='OBJECT')

    def twist_armature(self, ob, twist_angle):
        # must be in pose mode to rotate bones
        bpy.ops.object.mode_set(mode='POSE', toggle=False)
        for bone in ob.data.bones:
            pose_bone = ob.pose.bones[bone.name]
            save_rotation_mode = pose_bone.rotation_mode
            pose_bone.rotation_mode = 'XYZ'
            axis = random.choice(['X', 'Y', 'Z'])
            angle = random.uniform(-twist_angle, twist_angle)
            pose_bone.rotation_euler.rotate_axis(axis, math.radians(angle))
            pose_bone.rotation_mode = save_rotation_mode
        # exit pose mode
        bpy.ops.object.mode_set(mode='OBJECT')

    def get_inverse_bind_pose_dic(self, ob):
        pose_dic = {}
        for bone in ob.data.bones:
            if bone.use_deform:
                if bpy.app.version < (2, 80):
                    pose_dic[bone.name] = (ob.matrix_world * bone.matrix_local).inverted()
                else:
                    pose_dic[bone.name] = (ob.matrix_world @ bone.matrix_local).inverted()
        return pose_dic

    def get_transform_matrix_dic(self, ob, inverse_bind_pose_dic):
        pose_dic = {}
        for bone in ob.data.bones:
            if bone.use_deform:
                if bpy.app.version < (2, 80):
                    pose_dic[bone.name] = ob.matrix_world * ob.pose.bones[bone.name].matrix * inverse_bind_pose_dic[bone.name]
                else:
                    pose_dic[bone.name] = ob.matrix_world @ ob.pose.bones[bone.name].matrix @ inverse_bind_pose_dic[bone.name]
        return pose_dic

    def get_static_vertex_positions(self, ob):
        positions = []
        me = ob.data
        vertex_matrix = ob.matrix_world
        for vertex in me.vertices:
            if bpy.app.version < (2, 80):
                positions.append(vertex_matrix * vertex.co)
            else:
                positions.append(vertex_matrix @ vertex.co)
        return positions

    def get_dynamic_vertex_positions(self, ob, mod, show_viewport):
        positions = []
        mod.show_viewport = show_viewport
        if bpy.app.version < (2, 80):
            bpy.context.scene.update()
        else:
            bpy.context.view_layer.update()
        if bpy.app.version < (2, 80):
            me = ob.to_mesh(bpy.context.scene, apply_modifiers=True, settings='PREVIEW')
        else:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            ob_eval = ob.evaluated_get(depsgraph)
            me = ob_eval.to_mesh()
        vertex_matrix = ob.matrix_world
        for vertex in me.vertices:
            if bpy.app.version < (2, 80):
                positions.append(vertex_matrix * vertex.co)
            else:
                positions.append(vertex_matrix @ vertex.co)
        return positions

    def make_transform_matrix_stack(self):
        bone_names = list(self._inverse_bind_pose_dic.keys())
        transform_matrix_list = []
        for pose_index in range(len(self._dynamic_positions)):
            for bone_name in bone_names:
                transform_matrix_list.append(self._transform_matrix_dics[pose_index][bone_name])
        self._transform_matrix_stack = np.vstack(transform_matrix_list)

    def optimize_stage_0(self, objs):
        exist_any_corrective_smooth_modifiers = False
        for ob in objs:
            for mod in ob.modifiers:
                if type(mod) == bpy.types.CorrectiveSmoothModifier:
                    exist_any_corrective_smooth_modifiers = True
                    break
            if exist_any_corrective_smooth_modifiers:
                break
        # increase optimize stage index
        self._optimize_stage_index += 1
        return exist_any_corrective_smooth_modifiers

    def optimize_stage_1(self, arm):
        # get inverse bind pose dic
        self.reset_armature(arm)
        if bpy.app.version < (2, 80):
            bpy.context.scene.update()
        else:
            bpy.context.view_layer.update()
        self._inverse_bind_pose_dic = self.get_inverse_bind_pose_dic(arm)
        # increase optimize stage index
        self._optimize_stage_index += 1

    def optimize_stage_2(self, objs):
        # get static positions
        self._static_positions = []
        for ob in objs:
            self._static_positions.append([])
            for mod in ob.modifiers:
                if type(mod) == bpy.types.CorrectiveSmoothModifier:
                    self._static_positions[-1] = self.get_static_vertex_positions(ob)
                    # ignore multiple corrective smooth modifiers
                    break
        # increase optimize stage index
        self._optimize_stage_index += 1

    def optimize_stage_3(self, objs):
        # init sharp vertex index dics
        self._sharp_vertex_index_dics = []
        for ob in objs:
            self._sharp_vertex_index_dics.append({})

        # get transform matrix dic and dynamic positions
        self._transform_matrix_dics = []
        self._dynamic_positions = []
        # increase optimize stage index
        self._optimize_stage_index += 1

    def optimize_stage_4(self, arm, objs, twist_angle, deviation_threshold, bake_quality, bake_range):
        self.reset_armature(arm)
        if bpy.app.version < (2, 80):
            bpy.context.scene.update()
        else:
            bpy.context.view_layer.update()
        self.twist_armature(arm, twist_angle)
        if bpy.app.version < (2, 80):
            bpy.context.scene.update()
        else:
            bpy.context.view_layer.update()
        self._transform_matrix_dics.append(self.get_transform_matrix_dic(arm, self._inverse_bind_pose_dic))
        self._dynamic_positions.append([])
        for (j, ob) in enumerate(objs):
            self._dynamic_positions[-1].append([])
            for mod in ob.modifiers:
                if type(mod) == bpy.types.CorrectiveSmoothModifier:
                    smooth_positions = self.get_dynamic_vertex_positions(ob, mod, True)
                    origin_positions = self.get_dynamic_vertex_positions(ob, mod, False)
                    self._dynamic_positions[-1][-1] = smooth_positions
                    for k in range(len(origin_positions)):
                        # distance as deviation
                        deviation = (origin_positions[k] - smooth_positions[k]).length
                        # add to sharp vertex index dic, and keep the maximum deviation
                        if bake_range == 'All' or (bake_range == 'Selected' and ob.data.vertices[k].select) or (bake_range == 'Deviation' and deviation > deviation_threshold):
                            if k not in self._sharp_vertex_index_dics[j]:
                                self._sharp_vertex_index_dics[j][k] = deviation
                            elif deviation > self._sharp_vertex_index_dics[j][k]:
                                self._sharp_vertex_index_dics[j][k] = deviation
                    # ignore multiple corrective smooth modifiers
                    break
        # increase pose index
        self._pose_index += 1
        # increase optimize stage index
        if self._pose_index == math.ceil(len(self._inverse_bind_pose_dic)*bake_quality):
            # restore current poses
            self.restore_current_poses()
            # increase optimize stage index
            self._optimize_stage_index += 1

    def optimize_stage_5(self):
        # make transform matrix stack
        self.make_transform_matrix_stack()
        # no longer need the transform matrix dic
        self._transform_matrix_dics = None
        # increase optimize stage index
        self._optimize_stage_index += 1

    def optimize_stage_6(self, objs, linear_system_solver, influence_count, prune_threshold, time_out):
        # finished
        if self._mesh_index == len(objs):
            self._should_terminate = True
            return 0

        sharp_vertex_index_count = len(self._sharp_vertex_index_dics[self._mesh_index])
        # no sharp vertices in this mesh
        if sharp_vertex_index_count == 0:
            self._mesh_index += 1
            return 0

        # start to optimize
        start_time = time.time()
        sharp_vertex_indices = list(self._sharp_vertex_index_dics[self._mesh_index].items())
        # sort by inverse deviation
        sharp_vertex_indices.sort(key=lambda x:x[1], reverse=True)
        pose_count = len(self._dynamic_positions)
        bone_names = list(self._inverse_bind_pose_dic.keys())
        bone_count = len(bone_names)
        A = np.empty((pose_count*3, bone_count))
        b = np.empty((pose_count*3, 1))
        block_size = 0
        while time.time() - start_time < time_out:
            sharp_vertex_index = sharp_vertex_indices[self._vertex_index][0]
            static_position = self._static_positions[self._mesh_index][sharp_vertex_index]
            # calculate the vertex transform of all deform bones of all poses in batch
            transform_position_stack = np.dot(self._transform_matrix_stack, np.array([[static_position[0]],[static_position[1]],[static_position[2]],[1.0]]))
            # fill in A and b of the linear system: Ax = b
            for pose_index in range(pose_count):
                dynamic_position = self._dynamic_positions[pose_index][self._mesh_index][sharp_vertex_index]
                pose_index_per_coordinate = pose_index * 3
                b[pose_index_per_coordinate  ][0] = dynamic_position[0]
                b[pose_index_per_coordinate+1][0] = dynamic_position[1]
                b[pose_index_per_coordinate+2][0] = dynamic_position[2]
                bone_count_per_pose = pose_index * bone_count
                for bone_index in range(bone_count):
                    position_index_per_coordinate = (bone_count_per_pose + bone_index) * 4
                    A[pose_index_per_coordinate  ][bone_index] = transform_position_stack[position_index_per_coordinate  ]
                    A[pose_index_per_coordinate+1][bone_index] = transform_position_stack[position_index_per_coordinate+1]
                    A[pose_index_per_coordinate+2][bone_index] = transform_position_stack[position_index_per_coordinate+2]
            # fastest and stable solver
            if linear_system_solver == 'STD':
                A_T = A.T
                x = np.linalg.solve(np.dot(A_T, A), np.dot(A_T, b))
            # fastest and stable solver
            elif linear_system_solver == 'CHOLESKY':
                A_T = A.T
                L = np.linalg.cholesky(np.dot(A_T, A))
                y = np.linalg.solve(L, np.dot(A_T, b))
                x = np.linalg.solve(L.T.conj(), y)
            # fastest and stable solver
            elif linear_system_solver == 'QR':
                q,r = np.linalg.qr(A)
                x = np.linalg.solve(r, np.dot(q.T, b))
            # fastest and stable solver
            elif linear_system_solver == 'INV':
                A_T = A.T
                inv = np.linalg.inv(np.dot(A_T, A))
                x = np.dot(np.dot(inv, A_T), b)
            # fastest and stable solver
            elif linear_system_solver == 'PINV':
                A_T = A.T
                pinv = np.linalg.pinv(np.dot(A_T, A))
                x = np.dot(np.dot(pinv, A_T), b)
            # faster and stable solver
            elif linear_system_solver == 'LSTSQ':
                A_T = A.T
                if bpy.app.version < (2, 80):
                    (x, residuals, rank, s) = np.linalg.lstsq(np.dot(A_T, A), np.dot(A_T, b))
                else:
                    (x, residuals, rank, s) = np.linalg.lstsq(np.dot(A_T, A), np.dot(A_T, b), rcond=None)
            # fast and stable solver
            elif linear_system_solver == 'SVD':
                # solve the linear system via SVD, support lossy compression to speed up.
                u, s, vh = np.linalg.svd(A, full_matrices=False)
                lossy_compression = False
                if lossy_compression:
                    # lossy compression with 99.9 percents of information kept
                    total_sum = np.sum(s)
                    sum = 0.0
                    for i in range(s.shape[0]):
                        sum += s[i]
                        idx = i
                        if sum / total_sum >= 0.999:
                            break
                    idx += 1
                    u, s, vh = u[:,:idx], s[:idx], vh[:idx,:]

                B = np.dot(u.T, b)
                X = B
                for i in range(s.shape[0]):
                    X[i][0] /= s[i]
                x = np.dot(vh.T, X)

            # sort by weight
            bone_weights = x.tolist()
            bone_weight_list = list(zip(bone_names, bone_weights))
            bone_weight_list.sort(key=lambda x:x[1][0], reverse=True)
            # get weight pairs
            bone_weight_pairs = bone_weight_list[:influence_count]
            # get weights sum
            weight_sum = 0.0
            for i in range(len(bone_weight_pairs)):
                weight_sum += bone_weight_pairs[i][1][0]
            # prune small weights
            if weight_sum != 0.0:
                weight_accumulate = 0.0
                for i in range(len(bone_weight_pairs)):
                    if weight_accumulate / weight_sum > (1.0 - prune_threshold):
                        bone_weight_pairs[i][1][0] = 0.0
                    else:
                        weight_accumulate += bone_weight_pairs[i][1][0]
                # get weights sum
                weight_sum = 0.0
                for i in range(len(bone_weight_pairs)):
                    weight_sum += bone_weight_pairs[i][1][0]
            # normalize weights
            if weight_sum != 0.0:
                for i in range(len(bone_weight_pairs)):
                    bone_weight_pairs[i][1][0] /= weight_sum
            # remove the sharp vertex index from all vertex groups
            for vertex_group in objs[self._mesh_index].vertex_groups:
                vertex_group.remove([sharp_vertex_index])
            # add vertex weights
            for bone_weight_pair in bone_weight_pairs:
                (group_name, group_weight) = bone_weight_pair
                if objs[self._mesh_index].vertex_groups.get(group_name) == None:
                    objs[self._mesh_index].vertex_groups.new(name = group_name)
                objs[self._mesh_index].vertex_groups[group_name].add([sharp_vertex_index], group_weight[0], 'REPLACE')

            block_size += 1

            # increase vertex index
            self._vertex_index += 1
            if self._vertex_index == len(self._sharp_vertex_index_dics[self._mesh_index]):
                # increase mesh index
                self._mesh_index += 1
                # reset vertex index
                self._vertex_index = 0
                break

        return block_size

    def centimeter_to_current_system_unit(self, context):
        scale = 1.0
        if context.scene.unit_settings.system == 'NONE':
            scale *= 0.01
        elif context.scene.unit_settings.system == 'METRIC':
            if context.scene.unit_settings.length_unit == 'ADAPTIVE':
                scale *= 0.01
            elif context.scene.unit_settings.length_unit == 'KILOMETERS':
                scale *= 0.00001
            elif context.scene.unit_settings.length_unit == 'METERS':
                scale *= 0.01
            elif context.scene.unit_settings.length_unit == 'CENTIMETERS':
                pass
            elif context.scene.unit_settings.length_unit == 'MILLIMETERS':
                scale *= 10.0
            elif context.scene.unit_settings.length_unit == 'MICROMETERS':
                scale *= 10000.0
            scale *= context.scene.unit_settings.scale_length
        elif context.scene.unit_settings.system == 'IMPERIAL':
            if context.scene.unit_settings.length_unit == 'ADAPTIVE':
                scale *= 0.39370079
            elif context.scene.unit_settings.length_unit == 'MILES':
                scale *= 0.00000621
            elif context.scene.unit_settings.length_unit == 'FEET':
                scale *= 0.0328084
            elif context.scene.unit_settings.length_unit == 'INCHES':
                scale *= 0.39370079
            elif context.scene.unit_settings.length_unit == 'THOU':
                scale *= 393.7007874
            scale *= context.scene.unit_settings.scale_length
        return scale

    def modal(self, context, event):
        if event.type == 'ESC':
            return self.cancel(context)

        if event.type == 'TIMER':
            # background task is still running
            if not self._should_terminate:
                if self._optimize_stage_index == 0:
                    exist_any_corrective_smooth_modifiers_modifier = self.optimize_stage_0(self._objs)
                    if not exist_any_corrective_smooth_modifiers_modifier:
                        self.report({'ERROR'}, "No corrective smooth modifier found, please add a corrective smooth modifier to the mesh object")
                        return self.cancel(context)
                elif self._optimize_stage_index == 1:
                    self.optimize_stage_1(self._arm)
                    message_text = "Get inverse bind poses"
                    context.scene.progress_bar = message_text
                elif self._optimize_stage_index == 2:
                    self.optimize_stage_2(self._objs)
                    message_text = "Get static positions"
                    context.scene.progress_bar = message_text
                elif self._optimize_stage_index == 3:
                    self.optimize_stage_3(self._objs)
                    message_text = "Get sharp vertices"
                    context.scene.progress_bar = message_text
                elif self._optimize_stage_index == 4:
                    # vertex has three channel, we can compress the data by rows, if rows count is greator than the unknows number,
                    # the linear sysem has definite solution, we can solve it by pinverse, svd, or least square methods.
                    bake_quality = float(context.scene.bake_quality)
                    # It seems that it does not need to convert centimeters to current system unit, I don't know the reason.
                    # deviation_threshold = context.scene.deviation_threshold * self.centimeter_to_current_system_unit(context)
                    # We simply convert centimeters to meters.
                    deviation_threshold = 0.01 * context.scene.deviation_threshold
                    self.optimize_stage_4(self._arm, self._objs, context.scene.twist_angle, deviation_threshold, bake_quality, context.scene.bake_range)
                    message_text = "Twisting bones: {}/{}".format(self._pose_index, math.ceil(len(self._inverse_bind_pose_dic)*bake_quality))
                    context.scene.progress_bar = message_text
                elif self._optimize_stage_index == 5:
                    self.optimize_stage_5()
                    message_text = "Make transform matrix stack"
                    context.scene.progress_bar = message_text
                elif self._optimize_stage_index == 6:
                    time_out = 1.0 / context.scene.refresh_frequency
                    before_optimize_time = time.time()
                    block_size = self.optimize_stage_6(self._objs, context.scene.linear_system_solver, context.scene.influence_bones, context.scene.prune_threshold, time_out)
                    if block_size != 0 and self._mesh_index != len(self._objs) and len(self._sharp_vertex_index_dics[self._mesh_index]) != 0:
                        optimize_time = time.time() - before_optimize_time
                        remain_time = (len(self._sharp_vertex_index_dics[self._mesh_index]) - self._vertex_index) * optimize_time / block_size
                        message_text = "Complete: {:.1f}%, Vertex: {}/{}, Remain: {}:{}:{}".format(100.0 * self._vertex_index/(len(self._sharp_vertex_index_dics[self._mesh_index])), self._vertex_index, len(self._sharp_vertex_index_dics[self._mesh_index]), str(int(remain_time / 3600)), str(int(remain_time / 60)), str(int(remain_time % 60)))
                        context.scene.progress_bar = message_text
            else:
                # background task finished running
                running_time = time.time() - self._start_time
                self.report({'INFO'}, "".join(("Complete, ", "running time: ", \
                str(int(running_time / 60))," minutes ", str(int(running_time % 60)), " seconds")))
                return self.cancel(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
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

        for obj in objs:
            # focus on the mesh
            if bpy.app.version < (2, 80):
                bpy.context.scene.objects.active = obj
            else:
                bpy.context.view_layer.objects.active = obj
            # synchronize data
            bpy.ops.object.mode_set(mode='OBJECT')

        self._arm = arm
        self._objs = objs
        self._should_terminate =False
        self._inverse_bind_pose_dic = None
        self._static_positions = None
        self._sharp_vertex_index_dics = None
        self._transform_matrix_dics = None
        self._dynamic_positions = None
        self._mesh_index = 0
        self._pose_index = 0
        self._vertex_index = 0
        self._optimize_stage_index = 0
        self._current_pose_dic = None
        self._transform_matrix_stack = None
        context.scene.progress_bar = ""

        self._start_time = time.time()

        # save current poses
        self.save_current_poses()

        # start timer to poll data
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        # restore current poses
        self.restore_current_poses()
        # remove timer
        context.window_manager.event_timer_remove(self._timer)
        self._arm = None
        self._objs = None
        self._should_terminate = False
        self._inverse_bind_pose_dic = None
        self._static_positions = None
        self._sharp_vertex_index_dics = None
        self._transform_matrix_dics = None
        self._dynamic_positions = None
        self._mesh_index = 0
        self._pose_index = 0
        self._vertex_index = 0
        self._optimize_stage_index = 0
        self._current_pose_dic = None
        self._transform_matrix_stack = None
        context.scene.progress_bar = ""
        return {'CANCELLED'}

def init_properties():
    bpy.types.Scene.bake_range = EnumProperty(
            name="Bake Range",
            description="Where or not to bake vertex weights for all vertices",
            items=(('All', "All Vertices", "Bake vertex weights for all vertices"),
                   ('Selected', "Selected Vertices", "Bake vertex weights for selected vertices"),
                   ('Deviation', "By Deviation Threshold", "Bake vertex weights for highly distorted vertices")),
            default='Deviation',
            )

    bpy.types.Scene.deviation_threshold = FloatProperty(
        name = "Deviation Threshold",
        description = "Skip all the vertices whose position changes(in centimeters) are below the deviation threshold",
        default = 0.1,
        min = 0.0,
        max = 1000000.0)

    bpy.types.Scene.bake_quality = EnumProperty(
            name="Bake Quality",
            description="Balance the quality and the speed",
            items=(('0.5', "Low", "Low quality with fastest speed"),
                   ('0.75', "Medium", "Medium quality with fast speed"),
                   ('1.0', "High", "High quality with slow speed"),
                   ('2.0', "Very High", "Very high quality with much slower speed"),
                   ('3.0', "Highest", "Highest quality with slowest speed")),
            default='1.0',
            )

    bpy.types.Scene.twist_angle = FloatProperty(
        name = "Twist Angle",
        description = "Maximum twist angle of the deform bones",
        default = 45.0,
        min = 0.0,
        max = 360.0)

    bpy.types.Scene.influence_bones = IntProperty(
        name = "Influence Bones",
        description = "Max influence bones per vertex",
        default = 4,
        min = 1,
        max = 128)

    bpy.types.Scene.prune_threshold = FloatProperty(
        name = "Prune Threshold",
        description = "Prune vertex weights which below the threshold",
        default = 0.01,
        min = 0.0,
        max = 0.1)

    bpy.types.Scene.progress_bar = StringProperty(
        name = "Progress Bar",
        description = "Progress bar",
        default = "",)

    bpy.types.Scene.linear_system_solver = EnumProperty(
            name="Linear System Solver",
            description="Linear system solver",
            items=(('STD', "Standard Solver", "Standard solver"),
                   ('CHOLESKY', "Cholesky Solver", "Cholesky solver"),
                   ('QR', "QR Solver", "QR solver"),
                   ('INV', "Inverse Solver", "Inverse solver"),
                   ('PINV', "Pseudo Inverse Solver", "Pseudo inverse solver"),
                   ('LSTSQ', "Least Square Solver", "Least square solver"),
                   ('SVD', "SVD Solver", "SVD solver")),
            default='PINV',
            )

    bpy.types.Scene.refresh_frequency = FloatProperty(
        name = "Refresh Frequency",
        description = "How often(fps) to refresh the status bar, too high refresh frequency may reduce the baking speed",
        default = 1.0,
        min = 0.1,
        max = 10.0)

def clear_properties():
    props = ["bake_range",
    "deviation_threshold",
    "bake_quality",
    "twist_angle",
    "influence_bones",
    "prune_threshold",
    "progress_bar",
    "linear_system_solver",
    "refresh_frequency"]

    for p in props:
        if p in bpy.types.Scene.bl_rna.properties:
            exec("del bpy.types.Scene." + p)

class CSB_PT_CorrectiveSmoothBakerPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Corrective Smooth Baker"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Skeleton Corrective Baker'

    @classmethod
    def poll(self, context):
        arm_count = 0
        obj_count = 0
        for ob in bpy.context.selected_objects:
            if 'ARMATURE' == ob.type:
                arm_count += 1
            if 'MESH' == ob.type:
                obj_count += 1
        return (bpy.context.mode == 'OBJECT' and arm_count == 1 and obj_count >= 1)


    def draw(self, context):
        layout = self.layout

        layout.prop(context.scene, 'bake_range', icon='NONE', toggle=True)
        layout.prop(context.scene, 'deviation_threshold', icon='BLENDER', toggle=True)
        layout.prop(context.scene, 'bake_quality', icon='NONE', toggle=True)
        layout.prop(context.scene, 'twist_angle', icon='BLENDER', toggle=True)
        layout.prop(context.scene, 'influence_bones', icon='BLENDER', toggle=True)
        layout.prop(context.scene, 'prune_threshold', icon='BLENDER', toggle=True)
        layout.prop(context.scene, 'linear_system_solver', icon='NONE', toggle=True)
        layout.prop(context.scene, 'refresh_frequency', icon='BLENDER', toggle=True)

        row = layout.row()
        row = layout.row()
        row.operator("wm.corrective_smooth_baker")

        row = layout.row()
        layout.prop(context.scene, 'progress_bar', icon='NONE', toggle=True)


def register_corrective_smooth_baker():
    bpy.utils.register_class(CSB_PT_CorrectiveSmoothBakerPanel)
    bpy.utils.register_class(CSB_OT_ModalTimerOperator)
    init_properties()


def unregister_corrective_smooth_baker():
    bpy.utils.unregister_class(CSB_PT_CorrectiveSmoothBakerPanel)
    bpy.utils.unregister_class(CSB_OT_ModalTimerOperator)
    clear_properties()


if __name__ == "__main__":
    register_corrective_smooth_baker()
