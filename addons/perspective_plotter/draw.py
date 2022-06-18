
import bgl
import gpu
import bmesh
from gpu_extras.batch import batch_for_shader
from math import pi, cos, sin
from . import util, operators
from mathutils import Vector
from bpy_extras import view3d_utils

_shader_map = {}

def get_shader(str_type):
    '''Get a cached shader'''
    global _shader_map
    if str_type not in _shader_map:
        _shader_map[str_type] = gpu.shader.from_builtin(str_type)
    return _shader_map[str_type]

def draw_line_3d(color, start, end, width=1):
    """draw a 3d line"""
    bgl.glLineWidth(width)

    vertices = [start, end]
    shader = get_shader('3D_UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINE_STRIP', {'pos' : vertices})
    shader.bind()
    shader.uniform_float('color', color)
    batch.draw(shader)

def circle(x, y, radius, segments):
    '''draw a circle'''
    coords = []
    m = (1.0 / (segments - 1)) * (pi * 2)

    for p in range(segments):
        p1 = x + cos(m * p) * radius
        p2 = y + sin(m * p) * radius
        coords.append((p1, p2))
    return coords


def draw_axis_line_2d(color, start, end, line_width=1, circle_diameter=10):
    """draw a 3d line representing an axis"""
    if not (start and end):
        return

    bgl.glLineWidth(line_width)
    
    shader = get_shader('2D_UNIFORM_COLOR')

    vector = (start - end)
    vector.normalize()
    vertices = [start - (vector * circle_diameter), end + (vector * circle_diameter)]    
    batch_line = batch_for_shader(shader, 'LINES', {'pos' : vertices})
    
    circle_co = circle(start[0], start[1], circle_diameter, 16)
    batch_circle1 = batch_for_shader(shader, 'TRI_FAN', {'pos' : circle_co})
    
    circle_co = circle(end[0], end[1], circle_diameter, 16)
    batch_circle2 = batch_for_shader(shader, 'TRI_FAN', {'pos' : circle_co})

    shader.bind()
    shader.uniform_float('color', color)
    
    batch_line.draw(shader)
    batch_circle1.draw(shader)
    batch_circle2.draw(shader)

def draw_measurement_line_2d(color, start, end, line_width=1, diameter=10):
    """draw a 3d line representing an axis"""
    if not (start and end):
        return

    bgl.glLineWidth(line_width)
    
    shader = get_shader('2D_UNIFORM_COLOR')

    vector = (start - end)
    vector.normalize()
    vertices = [start, end]    
    batch_line = batch_for_shader(shader, 'LINES', {'pos' : vertices})

    orth_vec = vector.orthogonal().normalized()
    vertices = [start - (orth_vec*diameter), start + (orth_vec*diameter)]
    batch_line_top = batch_for_shader(shader, 'LINES', {'pos' : vertices})
    vertices = [end - (orth_vec*diameter), end + (orth_vec*diameter)]
    batch_line_bottom = batch_for_shader(shader, 'LINES', {'pos' : vertices})


    shader.bind()
    shader.uniform_float('color', color)
    
    batch_line.draw(shader)
    batch_line_top.draw(shader)
    batch_line_bottom.draw(shader)

def draw_axis_perspective_line_2d(color, start, end):
    """draw a 3d line for perspective"""
    if not (start and end):
        return

    bgl.glLineWidth(1)
    
    shader = get_shader('2D_UNIFORM_COLOR')

    vector = (start - end)
    vector.normalize()
    vertices = [start - (vector), end + (vector)]    
    batch_line = batch_for_shader(shader, 'LINES', {'pos' : vertices})

    shader.bind()
    shader.uniform_float('color', color)
    
    batch_line.draw(shader)

def draw_vanishing_point_2d(color, point, line_width=1, circle_diameter=10):
    """draw a vanishing point"""
    bgl.glLineWidth(line_width)
    
    shader = get_shader('2D_UNIFORM_COLOR')
    
    circle_co = circle(point[0], point[1], circle_diameter, 16)
    batch_circle = batch_for_shader(shader, 'TRI_FAN', {'pos' : circle_co})

    shader.bind()
    shader.uniform_float('color', color)
    
    batch_circle.draw(shader)

def draw_principal_point_2d(color, point, line_width=1, circle_diameter=10, solid=False):
    """draw the principal point"""
    bgl.glLineWidth(line_width)
    
    shader = get_shader('2D_UNIFORM_COLOR')
    
    circle_co = circle(point[0], point[1], circle_diameter, 16)
    style = 'LINE_LOOP' if not solid else 'TRI_FAN'
    batch_circle = batch_for_shader(shader, style, {'pos' : circle_co})

    shader.bind()
    shader.uniform_float('color', color)
    
    batch_circle.draw(shader)


def draw_grid_point_2d(color, point, circle_diameter=10):
    """draw the grid point"""
    bgl.glLineWidth(1)
    
    shader = get_shader('2D_UNIFORM_COLOR')
    
    circle_co = circle(point[0], point[1], circle_diameter, 16)
    batch_circle = batch_for_shader(shader, 'TRI_FAN', {'pos' : circle_co})

    shader.bind()
    shader.uniform_float('color', color)
    
    batch_circle.draw(shader)

def draw_callback_3d_move_along_view(self, context, lines):
    """callback function to draw a line for move along view"""

    bgl.glEnable(bgl.GL_BLEND)
    user_preferences = context.preferences
    addon_prefs = user_preferences.addons[__package__].preferences

    if not context.region_data.is_perspective:
        for line in lines:
            start = line[0]
            end = line[1]
            
            draw_line_3d(addon_prefs.line_color, start, end, addon_prefs.line_thickness)

        
    axes = []
    obj = context.active_object
    if obj.type == 'MESH' and obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)

        selected_verts = [v for v in bm.verts if v.select]

        for v in selected_verts:
            axes.append(util.construct_axis_lines(obj.matrix_world @ v.co))
    elif obj.mode == 'OBJECT':
        axes.append(util.construct_axis_lines(obj.matrix_world.to_translation()))


    if addon_prefs.show_axis:
        for axis in axes:
            x_line = axis[0]
            y_line = axis[1]
            z_line = axis[2]
            
            draw_line_3d(addon_prefs.x_axis_color, x_line[0], x_line[1], addon_prefs.line_thickness)
            draw_line_3d(addon_prefs.y_axis_color, y_line[0], y_line[1], addon_prefs.line_thickness)
            draw_line_3d(addon_prefs.z_axis_color, z_line[0], z_line[1], addon_prefs.line_thickness)


    # # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)

def get_axis_color(context, vp_type):
    """Get the specified color of the axis"""
    user_preferences = context.preferences
    addon_prefs = user_preferences.addons[__package__].preferences
    last_char = vp_type[-1].lower()
    return getattr(addon_prefs, last_char + '_axis_color')



def draw_callback_3d_perspective_plotter(running_uuid, context):
    """callback function to draw a line"""

    if not (context.region_data.is_perspective and context.region_data.view_perspective == 'CAMERA'):
        return

    try:

        # get the relevant camera for this running id.
        camera_obj = util.get_valid_camera(running_uuid)

        # if no camera or running_id then return
        if not camera_obj or not camera_obj.perspective_plotter.running_uuid:
            return

        # if the running id for this operator is different to the currently running one, don't do anything.
        if camera_obj.perspective_plotter.running_uuid != running_uuid:
            return

        # if the view camera is different, don't do anything.
        view_camera = util.get_camera(context, context.region)
        if camera_obj != view_camera:
            return

        util.calc_view(context, camera_obj, context.region)

        vp_1 = Vector(camera_obj.perspective_plotter_visualisation.vp_1)
        vp_2 = Vector(camera_obj.perspective_plotter_visualisation.vp_2)
        vp_3 = Vector(camera_obj.perspective_plotter_visualisation.vp_3)

        horizon_vec = Vector(camera_obj.perspective_plotter_visualisation.horizon_vec)
        principal_point = Vector(camera_obj.perspective_plotter_visualisation.principal_point)
        grid_point = Vector(camera_obj.perspective_plotter_visualisation.grid_point)

        bgl.glEnable(bgl.GL_BLEND)

        user_preferences = context.preferences
        addon_prefs = user_preferences.addons[__package__].preferences

        # Firstly, get the camera viewing border. We will be using this to calculate the positions of the axis guides.
        frame_px = util.view3d_camera_border(context, context.region)
        if not frame_px:
            return

        # calculate the dimensions of the border
        border_min_x = min([v[0] for v in frame_px])
        border_min_y = min([v[1] for v in frame_px])
        border_max_x = max([v[0] for v in frame_px])
        border_max_y = max([v[1] for v in frame_px])
        border_width = border_max_x - border_min_x
        border_height = border_max_y - border_min_y

        # get setting for perspective.
        vanishing_point_num = int(camera_obj.perspective_plotter.vanishing_point_num)

        # get colors for vanishing points
        vp_1_color = get_axis_color(context, camera_obj.perspective_plotter.vp_1_type)
        vp_2_color = get_axis_color(context, camera_obj.perspective_plotter.vp_2_type)
        vp_3_color = get_axis_color(context, util.get_last_axis(camera_obj.perspective_plotter.vp_1_type, camera_obj.perspective_plotter.vp_2_type))


        # calculate the axis guide points based on the camera viewing border.
        axis_vp1_point_a, axis_vp1_point_b, axis_vp1_point_c, axis_vp1_point_d, axis_vp2_point_a, axis_vp2_point_b, axis_vp2_point_c, axis_vp2_point_d, axis_vp3_point_a, axis_vp3_point_b, axis_vp3_point_c, axis_vp3_point_d \
            = util.get_axis_points(camera_obj, border_min_x, border_width, border_min_y, border_height)

        horizon_point_a, horizon_point_b = util.get_horizon_points(camera_obj, border_min_x, border_width, border_min_y, border_height)

        # show X axis control points.
        draw_axis_line_2d(vp_1_color, axis_vp1_point_a, axis_vp1_point_b, addon_prefs.axis_thickness, addon_prefs.axis_thickness * 5)
        draw_axis_line_2d(vp_1_color, axis_vp1_point_c, axis_vp1_point_d, addon_prefs.axis_thickness, addon_prefs.axis_thickness * 5)

        # show Y axis control points.
        if vanishing_point_num > 1:
            draw_axis_line_2d(vp_2_color, axis_vp2_point_a, axis_vp2_point_b, addon_prefs.axis_thickness, addon_prefs.axis_thickness * 5)
            draw_axis_line_2d(vp_2_color, axis_vp2_point_c, axis_vp2_point_d, addon_prefs.axis_thickness, addon_prefs.axis_thickness * 5)
        else:
            draw_axis_line_2d(vp_2_color, horizon_point_a, horizon_point_b, addon_prefs.axis_thickness, addon_prefs.axis_thickness * 5)

        # show Z axis control points.
        if vanishing_point_num == 3:
            draw_axis_line_2d(vp_3_color, axis_vp3_point_a, axis_vp3_point_b, addon_prefs.axis_thickness, addon_prefs.axis_thickness * 5)
            draw_axis_line_2d(vp_3_color, axis_vp3_point_c, axis_vp3_point_d, addon_prefs.axis_thickness, addon_prefs.axis_thickness * 5)
            draw_principal_point_2d(addon_prefs.principal_point_color, principal_point, addon_prefs.principal_point_size * 2, addon_prefs.principal_point_size * 4, True) 

        #draw principal point
        if vanishing_point_num < 3 and camera_obj.perspective_plotter.principal_point_mode == 'manual':
            draw_principal_point_2d(addon_prefs.principal_point_color, principal_point, addon_prefs.principal_point_size * 2, addon_prefs.principal_point_size * 4, False) 

        draw_grid_point_2d(addon_prefs.grid_point_color, grid_point, addon_prefs.grid_point_size) 

        # draw reference axis
        if camera_obj.perspective_plotter.ref_distance_mode != 'camera_distance':

            length_point_a_2d = Vector(camera_obj.perspective_plotter_visualisation.length_point_a)
            length_point_b_2d = Vector(camera_obj.perspective_plotter_visualisation.length_point_b)
            draw_measurement_line_2d(addon_prefs.measurement_line_color, length_point_a_2d, length_point_b_2d, line_width=addon_prefs.measurement_line_thickness)

        if camera_obj.perspective_plotter.is_valid:

            perp_axis_color = [
                vp_1_color[0],
                vp_1_color[1],
                vp_1_color[2],
                vp_1_color[3] * 0.5
            ]
            draw_axis_perspective_line_2d(perp_axis_color, axis_vp1_point_a, vp_1)
            draw_axis_perspective_line_2d(perp_axis_color, axis_vp1_point_c, vp_1)

            # show Y axis control points.

            perp_axis_color = [
                vp_2_color[0],
                vp_2_color[1],
                vp_2_color[2],
                vp_2_color[3] * 0.5
            ]
            

            if vanishing_point_num > 1:
                draw_axis_perspective_line_2d(perp_axis_color, axis_vp2_point_a, vp_2)
                draw_axis_perspective_line_2d(perp_axis_color, axis_vp2_point_c, vp_2)  

            # show Z axis control points.
            if vanishing_point_num == 3:
                perp_axis_color = [
                    vp_3_color[0],
                    vp_3_color[1],
                    vp_3_color[2],
                    vp_3_color[3] * 0.5
                ]
                draw_axis_perspective_line_2d(perp_axis_color, axis_vp3_point_a, vp_3)
                draw_axis_perspective_line_2d(perp_axis_color, axis_vp3_point_c, vp_3)

            # draw horizon line
            draw_axis_line_2d(addon_prefs.horizon_line_color, vp_1 - (horizon_vec * 100000), vp_1 + (horizon_vec * 100000), addon_prefs.horizon_line_thickness, 0) 


            # # draw vanishing points
            draw_vanishing_point_2d(addon_prefs.horizon_line_color, vp_1, addon_prefs.horizon_line_thickness, addon_prefs.horizon_line_thickness * 2) 
            if vanishing_point_num > 1:

                draw_vanishing_point_2d(addon_prefs.horizon_line_color, vp_2, addon_prefs.horizon_line_thickness, addon_prefs.horizon_line_thickness * 2) 

        # # restore opengl defaults
        bgl.glLineWidth(1)
        bgl.glDisable(bgl.GL_BLEND)

    except (ReferenceError, TypeError) as e:
        return
