import bgl
import bpy
import gpu
from bpy.props import BoolProperty, EnumProperty
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector

from ..core import faceit_utils as futils


def draw_bone_range_lines(c_vec_min, c_vec_max, axis_index, bone_location, c_rig_rotation,
                          draw_perpendicular_corner_lines=True):

    line_vertices = []

    vec_min = bone_location + c_vec_min
    # Corner point maximum
    vec_max = bone_location + c_vec_max

    line_vertices.extend((vec_min, vec_max))

    ############### Orthogonal End Vectors ###########################

    if draw_perpendicular_corner_lines:

        get_perpendicular_axis = {
            0: Vector((0, 0, 1)),
            1: Vector((0, 1, 0)),
            2: Vector((0, 1, 0))
        }

        ref_vec = get_perpendicular_axis[axis_index]
        ref_vec.rotate(c_rig_rotation)

        cross_vec = c_vec_min.copy() if c_vec_min.length > 0 else c_vec_max.copy()

        if cross_vec.length > 0:
            orth_vec = cross_vec.length / 5 * Vector.cross(cross_vec, ref_vec).normalized()
            orth_vec_00 = bone_location + (orth_vec)
            orth_vec_01 = bone_location - (orth_vec)

            line_vertices.extend((orth_vec_00 + c_vec_min, orth_vec_01 + c_vec_min))
            line_vertices.extend((orth_vec_00 + c_vec_max, orth_vec_01 + c_vec_max))
        else:
            print('cross vector with 0 length...')

    return line_vertices


def draw_bone_range_rectangle(
        min_value_X, max_value_X, min_value_Y, max_value_Y, axis_X, axis_Y, bone_location,
        bone_rotation_euler):

    rectangle_vertices = []

# Corner point minimum X
    vec = Vector((0, 0, 0))

    v_0 = vec.copy()

    v_0[axis_X] = min_value_X
    v_0[axis_Y] = min_value_Y
    v_0.rotate(bone_rotation_euler)
    v_0 += bone_location

    v_1 = vec.copy()
    v_1[axis_X] = max_value_X
    v_1[axis_Y] = min_value_Y
    v_1.rotate(bone_rotation_euler)
    v_1 += bone_location

    # Corner point minimum Y
    v_2 = vec.copy()
    v_2[axis_X] = max_value_X
    v_2[axis_Y] = max_value_Y
    v_2.rotate(bone_rotation_euler)
    v_2 += bone_location

    # Corner point maximum Y
    v_3 = vec.copy()
    v_3[axis_X] = min_value_X
    v_3[axis_Y] = max_value_Y
    v_3.rotate(bone_rotation_euler)
    v_3 += bone_location

    rectangle_vertices.extend((v_0, v_1))
    rectangle_vertices.extend((v_1, v_2))
    rectangle_vertices.extend((v_2, v_3))
    rectangle_vertices.extend((v_3, v_0))

    # rectangle_vertices.extend((line_0, line_1, line_2, line_3))

    return rectangle_vertices


def draw_bone_range_cube(
    min_value_X, max_value_X, min_value_Y, max_value_Y, min_value_Z, max_value_Z, bone_location,
        bone_rotation_euler):

    rectangle_vertices = []

    v_0 = Vector((min_value_X, min_value_Y, min_value_Z))
    v_0.rotate(bone_rotation_euler)
    v_0 += bone_location

    v_1 = Vector((max_value_X, min_value_Y, min_value_Z))
    v_1.rotate(bone_rotation_euler)
    v_1 += bone_location

    # Corner point minimum Y
    v_2 = Vector((max_value_X, max_value_Y, min_value_Z,))
    v_2.rotate(bone_rotation_euler)
    v_2 += bone_location

    # Corner point maximum Y
    v_3 = Vector((min_value_X, max_value_Y, min_value_Z))
    v_3.rotate(bone_rotation_euler)
    v_3 += bone_location

    # Corner point minimum Y
    v_4 = Vector((min_value_X, max_value_Y, max_value_Z))
    v_4.rotate(bone_rotation_euler)
    v_4 += bone_location

    # Corner point maximum Y
    v_5 = Vector((max_value_X, max_value_Y, max_value_Z))
    v_5.rotate(bone_rotation_euler)
    v_5 += bone_location

    v_6 = Vector((max_value_X, min_value_Y, max_value_Z))
    v_6.rotate(bone_rotation_euler)
    v_6 += bone_location

    v_7 = Vector((min_value_X, min_value_Y, max_value_Z))
    v_7.rotate(bone_rotation_euler)
    v_7 += bone_location

    rectangle_vertices.extend((v_0, v_1))
    rectangle_vertices.extend((v_1, v_2))
    rectangle_vertices.extend((v_2, v_3))
    rectangle_vertices.extend((v_3, v_4))
    rectangle_vertices.extend((v_4, v_5))
    rectangle_vertices.extend((v_5, v_6))
    rectangle_vertices.extend((v_6, v_7))
    rectangle_vertices.extend((v_7, v_0))

    rectangle_vertices.extend((v_3, v_0))
    rectangle_vertices.extend((v_4, v_7))
    rectangle_vertices.extend((v_5, v_2))
    rectangle_vertices.extend((v_6, v_1))

    return rectangle_vertices


class FACEIT_OT_DrawCRanges(bpy.types.Operator):
    '''Draws the range of motion for selected bones in the control rig'''
    bl_idname = 'faceit.draw_c_ranges'
    bl_label = 'Draw Ranges'
    bl_options = {'UNDO', 'INTERNAL'}

    draw_type: EnumProperty(
        name='Selected Only',
        items=[
            ('SEL', 'Selected Only', 'Draws only the ranges for selected bone'),
            ('ALL', 'All', 'Draws all ranges')
        ],
        default='ALL',
        description='Display only for selected ranges'
    )
    highlight_selected: BoolProperty(
        name='Highlight Selected',
        default=False,
        description='Highlight selected bone ranges'
    )

    @classmethod
    def poll(cls, context):
        return futils.get_faceit_control_armature()

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, 'draw_type', expand=True)
        if self.draw_type == 'ALL':
            row = layout.row()
            row.prop(self, 'highlight_selected', icon='OUTLINER_OB_LIGHT')

    def invoke(self, context, event):
        self.remove_all = True
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):

        scene = context.scene

        c_rig = futils.get_faceit_control_armature()
        if not c_rig:
            self.report({'WARNING'}, 'No Control rig found.')
            return{'CANCELLED'}

        bpy.ops.faceit.remove_draw_c_ranges()

        # get all lines in
        vertices = []
        col = []
        for bone in c_rig.pose.bones:
            # c = bone.constraints.get()
            for c in bone.constraints:
                if c.type in ('LIMIT_LOCATION'):

                    highlight = False

                    if self.draw_type == 'SEL':
                        if not bone.bone.select:
                            continue
                        else:
                            highlight = True
                    else:
                        if bone.bone.select and self.highlight_selected:
                            highlight = True

                    b_world_mat = c_rig.matrix_world @ bone.matrix
                    bone_location = (b_world_mat @ Matrix.Translation(bone.location).inverted()).translation
                    rot_axis, angle = bone.rotation_quaternion.to_axis_angle()[:]
                    bone_rotation = (b_world_mat @ Matrix.Rotation(angle, 4, rot_axis).inverted()).to_euler()
                    c_rig_rotation = c_rig.matrix_world.to_euler()
                    # b_world_mat @ Matrix.Rotation(bone.rotation_quaternion.to_axis_angle()).inverted()).to_euler()
                    # Get bone color from bone groups
                    b_color = (1, 0, 0, 1)
                    b_grp = bone.bone_group
                    if b_grp:
                        if highlight:
                            b_color = b_grp.colors.active[:] + (1.0,)
                        else:
                            b_color = b_grp.colors.select[:] + (1.0,)

                    bone_layer_state = bone.bone.layers

                    bone_layer_hidden = False

                    for i, l in enumerate(bone_layer_state):
                        if l is True and c_rig.data.layers[i] is True:
                            bone_layer_hidden = False
                            break
                        else:
                            bone_layer_hidden = True
                            continue
                    if bone_layer_hidden is True:
                        continue

                    vertices_for_current_bone = []

                    use_x_limits = c.use_min_x or c.use_max_x
                    use_y_limits = c.use_min_y or c.use_max_y
                    use_z_limits = c.use_min_z or c.use_max_z

                    limits = [use_x_limits, use_y_limits, use_z_limits]

                    limit_count = limits.count(True)

                    scale_x, scale_y, scalee_z = c_rig.scale

                    min_x = scale_x * c.min_x
                    min_y = scale_y * c.min_y
                    min_z = scalee_z * c.min_z

                    max_x = scale_x * c.max_x
                    max_y = scale_y * c.max_y
                    max_z = scalee_z * c.max_z

                    min_limits_vec = Vector((min_x, min_y, min_z))
                    max_limits_vec = Vector((max_x, max_y, max_z))
                    if limit_count == 1:

                        min_limits_vec.rotate(bone_rotation)
                        max_limits_vec.rotate(bone_rotation)
                        axis_index = 0
                        for i, v in enumerate(limits):
                            if v:
                                axis_index = i
                                break
                        # draw lines
                        vertices_for_current_bone.extend(draw_bone_range_lines(
                            min_limits_vec, max_limits_vec, axis_index, bone_location.copy(), c_rig_rotation))

                    elif limit_count == 2:

                        values = []

                        axis_X = -1
                        axis_Y = -1

                        if use_x_limits:

                            axis_X = 0

                            values.append(min_x)
                            values.append(max_x)

                        if use_y_limits:

                            if axis_X == -1:
                                axis_X = 1

                            axis_Y = 1

                            values.append(min_y)
                            values.append(max_y)

                        if use_z_limits:

                            # if axis_Y == -1:
                            axis_Y = 2

                            values.append(min_z)
                            values.append(max_z)

                        if axis_X != -1 and axis_Y != -1:

                            # min_value_X, max_value_X, axis_X, min_value_Y, max_value_Y, axis_Y, bone_world_mat, bone_rotation_euler
                            vertices_for_current_bone.extend(draw_bone_range_rectangle(
                                *values, axis_X, axis_Y, bone_location.copy(), bone_rotation))

                    elif limit_count == 3:
                        values = [
                            min_x,
                            max_x,
                            min_y,
                            max_y,
                            min_z,
                            max_z
                        ]
                        vertices_for_current_bone.extend(draw_bone_range_cube(
                            *values, bone_location, bone_rotation))
                        # draw cube
                        pass
                    else:
                        # no limits
                        continue

                    vertices.extend(vertices_for_current_bone)
                    col.extend((b_color,) * len(vertices_for_current_bone))

        # get built-in shader (GLSL)
        shader = gpu.shader.from_builtin('3D_SMOOTH_COLOR')
        # Uniforms are properties that are constant per draw call.
        # They can be set using the shader.uniform_* functions after the shader has been bound.

        batch = batch_for_shader(shader, 'LINES', {"pos": vertices, "color": col})

        def draw():
            bgl.glLineWidth(4)
            shader.bind()
            batch.draw(shader)
            bgl.glLineWidth(1)

        draw_handler = bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')
        print(str(draw_handler))
        bpy.app.driver_namespace["draw_c_ranges_handler"] = draw_handler
        scene.faceit_draw_handler_name = str(draw_handler)

        for region in context.area.regions:
            region.tag_redraw()
        return{'FINISHED'}


class FACEIT_OT_RemoveDrawCRanges(bpy.types.Operator):
    '''Draws the range of motion for selected bones in the control rig'''
    bl_idname = 'faceit.remove_draw_c_ranges'
    bl_label = 'Clear Ranges'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return futils.get_faceit_control_armature()

    def execute(self, context):

        scene = context.scene

        dns = bpy.app.driver_namespace
        try:
            handle = dns['draw_c_ranges_handler']
        except KeyError:
            return{'CANCELLED'}
        try:
            bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
        except ValueError:
            print('already removed')
            return{'CANCELLED'}
        for region in context.area.regions:
            region.tag_redraw()
        return{'FINISHED'}
