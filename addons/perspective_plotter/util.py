
from math import degrees, sqrt, pi, atan2, atan, tan, radians, asin
import bpy
from bpy_extras import view3d_utils
import bmesh
from numpy import *
from mathutils import Vector, Matrix, Euler, geometry


#
# Move Along View operations
#

def get_quadview_index(context, x, y):
    '''Get the index of a quad view based on supplied coordinates'''
    for area in context.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        is_quadview = len(area.spaces.active.region_quadviews) == 0
        i = -1
        for region in area.regions:
            if region.type == 'WINDOW':
                i += 1
                if (x >= region.x and
                    y >= region.y and
                    x < region.width + region.x and
                    y < region.height + region.y):

                    return (area.spaces.active, None if is_quadview else i)
    return (None, None)

def calc_move_vector(region, view, loc_3d):
    '''Get the vector from the view to a point in 3d space.'''

    view2d_co = view3d_utils.location_3d_to_region_2d(region, \
                                    view, \
                                    loc_3d)

    if view2d_co:
    
        move_vector = view3d_utils.region_2d_to_vector_3d(region, \
                            view, \
                          view2d_co)

        move_vector.normalize()

        return move_vector
    return None

def check_vector(new_point, region, view):
    '''Checks whether the new point is behind the view, which cannot be supported in all cases'''
    check_vec = view3d_utils.location_3d_to_region_2d(region, \
                view, \
                new_point)
    if check_vec:
        return new_point
    else:
        return None

def calc_point(obj, index, co, region, view, loc_cache, amount, reset):
    '''Calculate a point moved along a move vector by a given amount.  Will use cache if index is present.'''
    if index in loc_cache:
        loc_tuple = loc_cache[index]
        loc_3d = loc_tuple[0]
        move_vector = loc_tuple[1]
    else:
        loc_3d = obj.matrix_world @ co
        move_vector = calc_move_vector(region, view, loc_3d) 
        if move_vector:
            loc_cache[index] = (loc_3d, move_vector)

    if not move_vector:
        return None
        

    if not reset:
        new_point = obj.matrix_world.inverted() @ (loc_3d + (move_vector * amount))
    else:
        new_point = obj.matrix_world.inverted() @ loc_3d

    return check_vector(new_point, region, view)

def calc_obj_point(obj, region, view, loc_cache, amount, reset):
    '''Calculate object location moved along a move vector by a given amount.  Will use cache if index is present.'''
    index = obj.name
    co = obj.location.copy()

    if index in loc_cache:
        loc_tuple = loc_cache[index]
        loc_3d = loc_tuple[0]
        move_vector = loc_tuple[1]
    else:
        loc_3d = co
        move_vector = calc_move_vector(region, view, loc_3d) 
        if move_vector:
            loc_cache[index] = (loc_3d, move_vector)
    
    if not move_vector:
        return None

    if not reset:
        new_point = loc_3d + (move_vector * amount)
    else:
        new_point = loc_3d

    return check_vector(new_point, region, view)

def move_along_view(region, view, obj, loc_cache, amount, reset=False):
    '''Perform the movement of selected vertices or object aling the view line'''
    # perform the movement
    if obj.type == 'MESH' and obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)

        selected_verts = [v for v in bm.verts if v.select]

        for v in selected_verts:
            new_point = calc_point(obj, v.index, v.co, region, view, loc_cache, amount, reset)
            if new_point:
                v.co = new_point

        bmesh.update_edit_mesh(obj.data)
    elif obj.mode == 'OBJECT':
        new_point = calc_obj_point(obj, region, view, loc_cache, amount, reset)
        if new_point:
            obj.location = calc_obj_point(obj, region, view, loc_cache, amount, reset)

#
# Perspective Plotter operations
#
def construct_axis_lines(point, multiplier=100):
    '''contruct a standard line given a point. the multiplier is the length of the line.'''
    axis_lines = []
    
    x_vec =  Vector((multiplier, 0, 0 ))
    y_vec =  Vector((0, multiplier, 0 ))
    z_vec =  Vector((0, 0, multiplier ))

    x_axis = (point - x_vec, point + x_vec)
    y_axis = (point - y_vec, point + y_vec)
    z_axis = (point - z_vec, point + z_vec)

    axis_lines.append(x_axis)
    axis_lines.append(y_axis)
    axis_lines.append(z_axis)

    return axis_lines

def calc_point_percentage_region(point_percentage, x, width, y, height):
    '''calculate a point in a given rectangular border region, where the point is a percentage'''
    return Vector((     x +       ((point_percentage[0] * .01 ) * width),    y +    ((point_percentage[1]  * .01) * height)                  ))

def get_axis_points(camera_obj, x, width, y, height):
    '''get all control points for axis controls'''
    return  calc_point_percentage_region(camera_obj.perspective_plotter.axis_vp1_point_a, x, width, y, height), \
            calc_point_percentage_region(camera_obj.perspective_plotter.axis_vp1_point_b, x, width, y, height), \
            calc_point_percentage_region(camera_obj.perspective_plotter.axis_vp1_point_c, x, width, y, height), \
            calc_point_percentage_region(camera_obj.perspective_plotter.axis_vp1_point_d, x, width, y, height), \
            calc_point_percentage_region(camera_obj.perspective_plotter.axis_vp2_point_a, x, width, y, height), \
            calc_point_percentage_region(camera_obj.perspective_plotter.axis_vp2_point_b, x, width, y, height), \
            calc_point_percentage_region(camera_obj.perspective_plotter.axis_vp2_point_c, x, width, y, height), \
            calc_point_percentage_region(camera_obj.perspective_plotter.axis_vp2_point_d, x, width, y, height), \
            calc_point_percentage_region(camera_obj.perspective_plotter.axis_vp3_point_a, x, width, y, height), \
            calc_point_percentage_region(camera_obj.perspective_plotter.axis_vp3_point_b, x, width, y, height), \
            calc_point_percentage_region(camera_obj.perspective_plotter.axis_vp3_point_c, x, width, y, height), \
            calc_point_percentage_region(camera_obj.perspective_plotter.axis_vp3_point_d, x, width, y, height)

def get_horizon_points(camera_obj, x, width, y, height):
    '''get control points for the horizon'''
    return  calc_point_percentage_region(camera_obj.perspective_plotter.horizon_point_a, x, width, y, height), \
            calc_point_percentage_region(camera_obj.perspective_plotter.horizon_point_b, x, width, y, height)

def get_grid_point(camera_obj, x, width, y, height):
    '''get the middle controlling point for the view'''
    grid_point_x = x + (width * (camera_obj.perspective_plotter.grid_point[0] / 100))
    grid_point_y = y + (height * (camera_obj.perspective_plotter.grid_point[1] / 100))
    return Vector((grid_point_x, grid_point_y))

def get_length_points(grid_point, vp_to_project_to, length_point_a, length_point_b):
    '''get control points for the length measure lines'''
    
    vec_line = (vp_to_project_to - grid_point)

    result = (grid_point + (vec_line * length_point_a)), \
            (grid_point + (vec_line * length_point_b))

    return result

def get_vp_to_project_to(camera_obj, x, width, y, height):
    '''get the middle controlling point for the view'''
    vp_to_project_to_x = x + (width * (camera_obj.perspective_plotter.vp_to_project_to[0] / 100))
    vp_to_project_to_y = y + (height * (camera_obj.perspective_plotter.vp_to_project_to[1] / 100))
    return Vector((vp_to_project_to_x, vp_to_project_to_y))

def get_principal_point(camera_obj, x, width, y, height):
    '''get the middle controlling point for the view'''
    principal_point_x = x + (width * (camera_obj.perspective_plotter.principal_point[0] / 100))
    principal_point_y = y + (height * (camera_obj.perspective_plotter.principal_point[1] / 100))
    return Vector((principal_point_x, principal_point_y))


def view3d_camera_border(context, region):
    cam = get_camera(context, region)
    scene = context.scene
    # region = context.region

    frame = cam.data.view_frame(scene=scene)

    # move from object-space into world-space 
    frame = [cam.matrix_world @ v for v in frame]

    # move into pixelspace
    from bpy_extras.view3d_utils import location_3d_to_region_2d
    rv3d = region.data
    frame_px = [location_3d_to_region_2d(region, rv3d, v) for v in frame]
    return frame_px


def _h(a,A,b,B,c,C):

    if A==B:b,B,c,C=c,C,b,B
    m=(a-b)/(B-A)
    return m,C-m*c

def find_orthocenter(a,A,b,B,c,C):
    '''Imported helper code to find the ortho center of a triangle for viewing calculations'''
    m,q=_h(a,A,b,B,c,C)
    k,z=_h(c,C,b,B,a,A)
    x=(q-z)/(k-m)
    return Vector((x,k*x+z))

_euler_type_map = {
    ('X','Y') : Euler(map(radians,  (  0,    0,   0)), 'XYZ'),
    ('X','Z') : Euler(map(radians,  (  90,   0,   0)), 'XYZ'),
    ('X','-Y') : Euler(map(radians, ( 180,   0,   0)), 'XYZ'),
    ('X','-Z') : Euler(map(radians, ( -90,   0,   0)), 'XYZ'),
    
    ('Y','X') : Euler(map(radians,  ( 180,   0,  90)), 'XYZ'),
    ('Y','Z') : Euler(map(radians,  (  90,   0,  90)), 'XYZ'),
    ('Y','-X') : Euler(map(radians, (   0,   0,  90)), 'XYZ'),
    ('Y','-Z') : Euler(map(radians, ( -90,   0,  90)), 'XYZ'),

    ('Z','X') : Euler(map(radians,  (   0, -90, -90)), 'XYZ'),
    ('Z','Y') : Euler(map(radians,  (   0, -90,   0)), 'XYZ'),
    ('Z','-X') : Euler(map(radians, (   0, -90,  90)), 'XYZ'),
    ('Z','-Y') : Euler(map(radians, (   0, -90, 180)), 'XYZ'),

    ('-X','Y') : Euler(map(radians, ( 180,   0, 180)), 'XYZ'),
    ('-X','Z') : Euler(map(radians, (  90,   0, 180)), 'XYZ'),
    ('-X','-Y') : Euler(map(radians,(   0,   0, 180)), 'XYZ'),
    ('-X','-Z') : Euler(map(radians,( -90,   0, 180)), 'XYZ'),
    
    ('-Y','X') : Euler(map(radians, (   0,   0, -90)), 'XYZ'),
    ('-Y','Z') : Euler(map(radians, (  90,   0, -90)), 'XYZ'),
    ('-Y','-X') : Euler(map(radians,( 180,   0, -90)), 'XYZ'),
    ('-Y','-Z') : Euler(map(radians,( -90,   0, -90)), 'XYZ'),

    ('-Z','X') : Euler(map(radians, (  90,  90,  0)), 'XYZ'),
    ('-Z','Y') : Euler(map(radians, (   0,  90,  0)), 'XYZ'),
    ('-Z','-X') : Euler(map(radians,( -90,  90,  0)), 'XYZ'),
    ('-Z','-Y') : Euler(map(radians,( 180,  90,  0)), 'XYZ'),

}
def get_euler_offset(vp_1_type, vp_2_type):
    '''Get the extra offset needed for the different vanishing point types'''
    key = (vp_1_type, vp_2_type)
    global _euler_type_map
    if key in _euler_type_map:
        return _euler_type_map[key]
    return None

def flatten_control_point(axis_point_a, axis_point_b, vp_ideal):
    control_points = [axis_point_a, axis_point_b]
    # for control_1, get furthest point
    def magnitude(pt):
        return (vp_ideal - pt).magnitude
    furthest_pt = max(control_points, key=magnitude)
    #project the points onto the new line.
    return geometry.intersect_point_line(axis_point_a, vp_ideal, furthest_pt)[0], \
            geometry.intersect_point_line(axis_point_b, vp_ideal, furthest_pt)[0]

def flatten_horizon(camera_obj):
    if camera_obj.perspective_plotter.vanishing_point_num in {'1'}:
        horizon_point_a = Vector(camera_obj.perspective_plotter.horizon_point_a)
        horizon_point_b = Vector(camera_obj.perspective_plotter.horizon_point_b)

        all_ys = [horizon_point_a[1], horizon_point_b[1]]
        av_y = sum(all_ys) / len(all_ys)

        camera_obj.perspective_plotter.horizon_point_a[1] = av_y
        camera_obj.perspective_plotter.horizon_point_b[1] = av_y

    elif camera_obj.perspective_plotter.vanishing_point_num in {'2', '3'}:

        axis_vp1_point_a = Vector(camera_obj.perspective_plotter.axis_vp1_point_a)
        axis_vp1_point_b = Vector(camera_obj.perspective_plotter.axis_vp1_point_b)
        axis_vp1_point_c = Vector(camera_obj.perspective_plotter.axis_vp1_point_c)
        axis_vp1_point_d = Vector(camera_obj.perspective_plotter.axis_vp1_point_d)

        axis_vp2_point_a = Vector(camera_obj.perspective_plotter.axis_vp2_point_a)
        axis_vp2_point_b = Vector(camera_obj.perspective_plotter.axis_vp2_point_b)
        axis_vp2_point_c = Vector(camera_obj.perspective_plotter.axis_vp2_point_c)
        axis_vp2_point_d = Vector(camera_obj.perspective_plotter.axis_vp2_point_d)

        vp_1 = seg_intersect(axis_vp1_point_a, axis_vp1_point_b, axis_vp1_point_c, axis_vp1_point_d)
        vp_2 = seg_intersect(axis_vp2_point_a, axis_vp2_point_b, axis_vp2_point_c, axis_vp2_point_d)

        # get ideal horizon line vanishing points
        all_ys = [vp_1[1], vp_2[1]]
        av_y = sum(all_ys) / len(all_ys)

        vp_1_ideal = Vector((vp_1[0], av_y))
        # vp_1
        axis_vp1_point_a, axis_vp1_point_b = flatten_control_point(axis_vp1_point_a, axis_vp1_point_b, vp_1_ideal)

        axis_vp1_point_c, axis_vp1_point_d = flatten_control_point(axis_vp1_point_c, axis_vp1_point_d, vp_1_ideal)


        # vp_2
        vp_2_ideal = Vector((vp_2[0], av_y))
        axis_vp2_point_a, axis_vp2_point_b = flatten_control_point(axis_vp2_point_a, axis_vp2_point_b, vp_2_ideal)

        axis_vp2_point_c, axis_vp2_point_d = flatten_control_point(axis_vp2_point_c, axis_vp2_point_d, vp_2_ideal)

        camera_obj.perspective_plotter.axis_vp1_point_a = axis_vp1_point_a
        camera_obj.perspective_plotter.axis_vp1_point_b = axis_vp1_point_b
        camera_obj.perspective_plotter.axis_vp1_point_c = axis_vp1_point_c
        camera_obj.perspective_plotter.axis_vp1_point_d = axis_vp1_point_d
        camera_obj.perspective_plotter.axis_vp2_point_a = axis_vp2_point_a
        camera_obj.perspective_plotter.axis_vp2_point_b = axis_vp2_point_b
        camera_obj.perspective_plotter.axis_vp2_point_c = axis_vp2_point_c
        camera_obj.perspective_plotter.axis_vp2_point_d = axis_vp2_point_d


def calc_view(context, camera_obj, region):
    '''calculate the view position of the camera through vanishing points'''

    if not context or not context.screen:
        return

    user_preferences = context.preferences
    addon_prefs = user_preferences.addons[__package__].preferences

    vp_1_type = camera_obj.perspective_plotter.vp_1_type
    vp_2_type = camera_obj.perspective_plotter.vp_2_type
    vp_3_type = get_last_axis(vp_1_type, vp_2_type).upper()

    rotation_axis_offset = get_euler_offset(vp_1_type, vp_2_type)

    if not rotation_axis_offset:
        camera_obj.perspective_plotter.error_message = "Rotation config invalid."
        camera_obj.perspective_plotter.is_valid = False
        return

    # Performs calculations of view based on https://www.coursera.org/lecture/robotics-perception/how-to-compute-intrinsics-from-vanishing-points-jnaLs

    # Firstly, get the camera viewing border. We will be using this to calculate the positions of the axis guides.
    frame_px = view3d_camera_border(context, region)
    if not frame_px:
        return

    # calculate the dimensions of the border
    try:
        border_min_x = min([v[0] for v in frame_px])
        border_min_y = min([v[1] for v in frame_px])
        border_max_x = max([v[0] for v in frame_px])
        border_max_y = max([v[1] for v in frame_px])
    except TypeError:
        return

    border_width = border_max_x - border_min_x
    border_height = border_max_y - border_min_y

    # calculate the axis guide points based on the camera viewing border.
    axis_vp1_point_a, axis_vp1_point_b, axis_vp1_point_c, axis_vp1_point_d, axis_vp2_point_a, axis_vp2_point_b, axis_vp2_point_c, axis_vp2_point_d, axis_vp3_point_a, axis_vp3_point_b, axis_vp3_point_c, axis_vp3_point_d \
            = get_axis_points(camera_obj, border_min_x, border_width, border_min_y, border_height)
    
    # get hirozon control points if they are needed.
    horizon_point_a, horizon_point_b = get_horizon_points(camera_obj, border_min_x, border_width, border_min_y, border_height)

    # calculate the 2D positions of the vanishing points
    vp_1 = seg_intersect(axis_vp1_point_a, axis_vp1_point_b, axis_vp1_point_c, axis_vp1_point_d)
    vp_2 = seg_intersect(axis_vp2_point_a, axis_vp2_point_b, axis_vp2_point_c, axis_vp2_point_d)
    vp_3 = seg_intersect(axis_vp3_point_a, axis_vp3_point_b, axis_vp3_point_c, axis_vp3_point_d)

    # get the direction vector to the horizon.
    if camera_obj.perspective_plotter.vanishing_point_num in {'2', '3'}:
        horizon_vec = (vp_1 - vp_2).normalized()
    else:
        if horizon_point_a.x > horizon_point_b.x:
            horizon_vec = (horizon_point_a - horizon_point_b).normalized()
        else:
            horizon_vec = (horizon_point_b - horizon_point_a).normalized()
    
    # the center point of the view.
    central_point = Vector((border_min_x + (border_width/2), border_min_y + (border_height/2)))

    # determine where the relative 'center' of the view is.
    if camera_obj.perspective_plotter.vanishing_point_num in {'1', '2'}:
        if camera_obj.perspective_plotter.principal_point_mode == 'manual':
            principal_point = get_principal_point(camera_obj, border_min_x, border_width, border_min_y, border_height)
        else:
            principal_point = central_point.copy()
    elif camera_obj.perspective_plotter.vanishing_point_num == '3':
        principal_point = find_orthocenter(vp_1[0], vp_1[1], vp_2[0], vp_2[1], vp_3[0], vp_3[1])

    # this is where the grid point is in 2d space, which will be Vector((0,0,0)) in world space
    grid_point = get_grid_point(camera_obj, border_min_x, border_width, border_min_y, border_height)

    # determine perpendicular intersection point with horizon
    if camera_obj.perspective_plotter.vanishing_point_num in {'2', '3'}:
        intersect_point_line = geometry.intersect_point_line(principal_point, vp_1, vp_2)
        horizon_intersect = intersect_point_line[0]
        horizon_intersect_percentage = intersect_point_line[1]
        if not (0 < horizon_intersect_percentage < 1):
            camera_obj.perspective_plotter.error_message = "Principal point outside vanishing points."
            camera_obj.perspective_plotter.is_valid = False
            return
    else:
        intersect_point_line = geometry.intersect_point_line(principal_point, vp_1, vp_1 + horizon_vec)
        horizon_intersect = intersect_point_line[0]
        horizon_intersect_percentage = intersect_point_line[1]

    # calculate distance from vanishing points to the central point's intersection with the horizon
    vp_1_to_center_dist = (vp_1 - horizon_intersect).magnitude
    vp_2_to_center_dist = (vp_2 - horizon_intersect).magnitude

    # define the distance vector between the image center point and  the perpendicular intersect with the horizon.
    principal_point_horizon_intersect = (horizon_intersect - principal_point)
    principal_point_horizon_intersect_dist = principal_point_horizon_intersect.magnitude

    # check the proportion of the viewing border to inform calculations
    is_landscape = border_width > border_height

    if camera_obj.perspective_plotter.vanishing_point_num in {'2', '3'}:

        focal_dist_2d_sqd = (vp_1_to_center_dist * vp_2_to_center_dist) - principal_point_horizon_intersect_dist**2

        if focal_dist_2d_sqd < 0:
            camera_obj.perspective_plotter.error_message = "Error calculating vanishing points."
            camera_obj.perspective_plotter.is_valid = False
            return

        focal_dist_2d = sqrt( focal_dist_2d_sqd  )

        camera_to_horizon_intersect_dist = sqrt( vp_1_to_center_dist * vp_2_to_center_dist  )

        # calculate angle from vp_1 to the camera center point
        theta = atan(vp_1_to_center_dist / camera_to_horizon_intersect_dist)
        # calculate angle from vp_2 to the camera center point
        beta = atan(vp_2_to_center_dist / camera_to_horizon_intersect_dist)
        
        # determine the tilt, alpha, where we will need to provide a negative distance if either
        # the central point is below the horizon or the vanishing points are swapped.
        # REMEMBER the y position starts with zero at the top and decreases as you go down.
        principal_point_horizon_intersect_dist_signed = principal_point_horizon_intersect_dist
        if (principal_point[1] < horizon_intersect[1] and vp_1[0] < vp_2[0]) or \
            (principal_point[1] > horizon_intersect[1] and vp_1[0] > vp_2[0]):
            principal_point_horizon_intersect_dist_signed *= -1

    else:
        # we need to calculate the hypothetical 2d focal distance with only one vanishing point
        # https://b3d.interplanety.org/en/how-to-get-camera-fov-in-degrees-from-focal-length-in-mm/
        
        if camera_obj.data.sensor_fit == 'AUTO':
            # in auto mode,      sensor width parameter is seemingly always used instead of the height.
            viewing_angle = 2 * atan( camera_obj.data.sensor_width  / (2 * camera_obj.perspective_plotter.one_point_focal_length))
            if (is_landscape):
                border_to_center_dist = ((border_min_x + border_width) - central_point[0])
            else:
                border_to_center_dist =  ((border_min_y + border_height) - central_point[1])
        elif camera_obj.data.sensor_fit == 'VERTICAL':
            viewing_angle = 2 * atan( camera_obj.data.sensor_height  / (2 * camera_obj.perspective_plotter.one_point_focal_length))
            border_to_center_dist = ((border_min_y + border_height) - central_point[1])
        elif camera_obj.data.sensor_fit == 'HORIZONTAL':
            viewing_angle = 2 * atan( camera_obj.data.sensor_width  / (2 * camera_obj.perspective_plotter.one_point_focal_length))
            border_to_center_dist = ((border_min_x + border_width) - central_point[0])

        focal_dist_2d = border_to_center_dist / tan(viewing_angle / 2)
        camera_to_horizon_intersect_dist = sqrt( focal_dist_2d**2 + principal_point_horizon_intersect_dist**2  )

        # to determine the tilt, alpha, where we will need to provide a negative distance if 
        # the central point is below the horizon.
        # REMEMBER the y position starts with zero at the top and decreases as you go down.
        principal_point_horizon_intersect_dist_signed = principal_point_horizon_intersect_dist
        if principal_point[1] > horizon_intersect[1]:
            principal_point_horizon_intersect_dist_signed *= -1

        theta = atan(vp_1_to_center_dist / camera_to_horizon_intersect_dist)
        if (vp_1.x - horizon_intersect.x) < 0:
            theta*=-1


    # calculate the tilt, alpha.
    alpha = atan2(principal_point_horizon_intersect_dist_signed, focal_dist_2d)

    # calculate angle between camera and horizon line
    angle_horizon = Vector((1, 0)).angle_signed(horizon_vec)

    # get camera to look at vanishing point 1.
    cam_rotation = Euler(map(radians, (0, 0, 0)), 'XYZ')
    cam_rotation.rotate_axis('X', radians(90))
    cam_rotation.rotate_axis('Y', radians(-90))
    cam_rotation.rotate_axis('Y', theta)
    cam_rotation.rotate_axis('X', -alpha)
    cam_rotation.rotate_axis('Z', angle_horizon)
    if rotation_axis_offset:
        cam_rotation.rotate(rotation_axis_offset)
    if camera_obj.perspective_plotter.camera_origin_mode == 'manual':
        cam_rotation.rotate(camera_obj.perspective_plotter.camera_rotation)

    # # calculate the focal angle of the lens, which an be determined by the width (or height) of the viewing border and the focal distance.
    if (is_landscape):
        focal_angle = 2 * atan((central_point - Vector((border_min_x, border_min_y + (border_height/2)))).magnitude / focal_dist_2d)
    else:
        focal_angle = 2 * atan((central_point - Vector((border_min_x + (border_width/2) , border_min_y))).magnitude / focal_dist_2d)

    # move the camera away from the center along the negative direction of view.
    vec = Vector((-1.0, 0.0, 0.0))
    view_rotation_euler = Euler(map(radians, (0, 0, 0)), 'XYZ')     
    view_rotation_euler.rotate_axis('Z', theta)
    view_rotation_euler.rotate_axis('Y', alpha)
    view_rotation_euler.rotate_axis('X', -angle_horizon)
    if rotation_axis_offset:
        view_rotation_euler.rotate(rotation_axis_offset)
    if camera_obj.perspective_plotter.camera_origin_mode == 'manual':        
        view_rotation_euler.rotate(camera_obj.perspective_plotter.camera_rotation)
    vec.rotate(view_rotation_euler)

    # calculate final vanishing points
    if camera_obj.perspective_plotter.vanishing_point_num == '1':
        # We cannot get the right axis from vp_1 and we will need to infer the vanishing point.
        vp_1_calc = vp_1
        vp_2_calc = calc_second_vanishing_point(vp_1, focal_dist_2d, principal_point, horizon_vec)
        vp_3_calc = calc_third_vanishing_point(principal_point, horizon_intersect, vp_1_calc, vp_2_calc)
    elif camera_obj.perspective_plotter.vanishing_point_num == '2':
        vp_1_calc = vp_1
        vp_2_calc = vp_2
        vp_3_calc = calc_third_vanishing_point(principal_point, horizon_intersect, vp_1_calc, vp_2_calc)
    elif camera_obj.perspective_plotter.vanishing_point_num == '3':
        vp_1_calc = vp_1
        vp_2_calc = vp_2
        vp_3_calc = vp_3

    if vp_1_calc == None or vp_2_calc == None or vp_3_calc == None:
            camera_obj.perspective_plotter.error_message = "Could not calculate all vanishing points."
            camera_obj.perspective_plotter.is_valid = False
            return

    vps = {}
    vps[vp_1_type[-1]]= vp_1_calc
    vps[vp_2_type[-1]]= vp_2_calc
    vps[vp_3_type[-1]]= vp_3_calc

    # append these points to a property map for viewing by the draw package.
    camera_obj.perspective_plotter_visualisation.vp_1 = vp_1_calc
    camera_obj.perspective_plotter_visualisation.vp_2 = vp_2_calc
    camera_obj.perspective_plotter_visualisation.vp_3 = vp_3_calc
    camera_obj.perspective_plotter_visualisation.horizon_vec = horizon_vec
    camera_obj.perspective_plotter_visualisation.principal_point = principal_point
    camera_obj.perspective_plotter_visualisation.grid_point = grid_point


    if camera_obj.perspective_plotter.ref_distance_mode != 'camera_distance':

        vp_to_project_to = vps[camera_obj.perspective_plotter.ref_distance_mode]

        camera_obj.perspective_plotter_visualisation.vp_to_project_to = vp_to_project_to
        camera_obj.perspective_plotter.vp_to_project_to = get_percentage_point(vp_to_project_to[0], vp_to_project_to[1], border_min_x, border_min_y, border_width, border_height)

        vp_to_project_to_px = get_vp_to_project_to(camera_obj, border_min_x, border_width, border_min_y, border_height)

        point_a, point_b = get_length_points(grid_point, vp_to_project_to_px, camera_obj.perspective_plotter.length_point_a, camera_obj.perspective_plotter.length_point_b)

        camera_obj.perspective_plotter_visualisation.length_point_a = point_a
        camera_obj.perspective_plotter_visualisation.length_point_b = point_b

    if not camera_obj.perspective_plotter.is_dirty:
        return


    # calculate how far from the middle of the world the camera should be.
    # only change if the camera movement is significant enough.
    if camera_obj.perspective_plotter.is_camera_sync:

        # shift the camera view by the offset of the principal point from the middle of the screen.
        if (is_landscape):
            shift_x = ( principal_point.x - central_point.x)  / border_width
            shift_y = ( principal_point.y - central_point.y)  / border_width # needs to be the width to stay proportional to the camera square shape
        else:
            shift_x = ( principal_point.x - central_point.x)  / border_height
            shift_y = ( principal_point.y - central_point.y)  / border_height # needs to be the height to stay proportional to the camera square shape
        shift_x *=-1
        shift_y *=-1


        # assign approprate views to the camera.
        camera_obj.rotation_euler = cam_rotation

        if camera_obj.perspective_plotter.vanishing_point_num in {'2', '3'}:
            camera_obj.data.angle = focal_angle
        else:
            camera_obj.data.angle = viewing_angle

        camera_obj.data.shift_x = shift_x 
        camera_obj.data.shift_y = shift_y



        cam_location = Vector((0,0,0)) + vec * camera_obj.perspective_plotter.camera_distance

        # Calculate Grid Offset position.
        vec_cam_to_gp = calc_point_2d_to_vector_3d(grid_point, principal_point, focal_dist_2d, view_rotation_euler )
        point_intersect = geometry.intersect_line_plane(cam_location, cam_location + vec_cam_to_gp.normalized(), Vector((0,0,0)), vec)

        if point_intersect:
            cam_location = (point_intersect*-1) + vec * camera_obj.perspective_plotter.camera_distance
            
        else:
            camera_obj.perspective_plotter.error_message = "Could not calculate grid projection for camera."
            camera_obj.perspective_plotter.is_valid = False
            return

        # Calculate axis position by projecting measure and determining the difference in expected length
        if camera_obj.perspective_plotter.ref_distance_mode != 'camera_distance':

            length_point_a_3d, length_point_b_3d = get_length_locations(cam_location, region, camera_obj, principal_point, focal_dist_2d, view_rotation_euler, camera_obj.perspective_plotter_visualisation.length_point_a , camera_obj.perspective_plotter_visualisation.length_point_b)

            if length_point_a_3d and length_point_b_3d and (length_point_b_3d - length_point_a_3d).magnitude:
                norm_func = camera_obj.perspective_plotter.ref_length / (length_point_b_3d - length_point_a_3d).magnitude
                if norm_func > 0:
                    camera_obj.perspective_plotter.camera_distance *= norm_func
                    cam_location *= norm_func

        if camera_obj.perspective_plotter.camera_origin_mode == 'manual':
            camera_obj.location = cam_location + camera_obj.perspective_plotter.camera_offset
        else:
            camera_obj.location = cam_location

    # if we go this far without error mark the view as valid.
    camera_obj.perspective_plotter.is_valid = True
    camera_obj.perspective_plotter.is_dirty = False
    camera_obj.perspective_plotter.error_message = ""


def calc_point_2d_to_vector_3d(point, principal_point, focal_dist_2d, view_rotation_euler ):
    principal_point_3d_rel = Vector((0,-principal_point.to_3d()[0],principal_point.to_3d()[1]))
    grid_point_3d_rel = Vector((0,-point.to_3d()[0],point.to_3d()[1])) - principal_point_3d_rel
    cam_loc_3d_rel = Vector((-focal_dist_2d,0,0))
    vec_cam_to_p = (cam_loc_3d_rel - grid_point_3d_rel)
    vec_cam_to_p.rotate(view_rotation_euler)
    return vec_cam_to_p

def perp( a ) :
    b = empty_like(a)
    b[0] = -a[1]
    b[1] = a[0]
    return b

def seg_intersect(a1,a2, b1,b2) :
    '''determine segment intersect'''
    da = a2-a1
    db = b2-b1
    dp = a1-b1
    dap = perp(da)
    denom = dot( dap, db)
    num = dot( dap, dp )
    return Vector((num / denom.astype(float))*db + b1)

def region_exists(r):
    '''determine if a given view region is still present'''
    wm = bpy.context.window_manager
    for window in wm.windows:
        for area in window.screen.areas:
            for region in area.regions:
                if region == r: return True
    return False

def get_valid_regions(context, camera_obj):
    '''get all relevant valid regions for the perspective plotter'''
    regions = []
    if context.screen.areas:
        for area in context.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for area_region in area.regions:
                if area_region.type == 'WINDOW' and \
                    area_region.data.is_perspective and \
                    area_region.data.view_perspective == 'CAMERA' and \
                        area.spaces.active.camera == camera_obj and \
                        region_exists(area_region):
                    regions.append(area_region)
    return regions


def get_camera(context, region):
    '''get the camera for this view'''
    for area in context.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for area_region in area.regions:
            if area_region != region:
                continue
            return area.spaces.active.camera
    return None

def get_valid_cameras(running_uuid):
    '''Get cameras with the given running uuid'''
    cameras_to_return = []
    for c in [o for o in bpy.data.objects if o.type == 'CAMERA']:
        if c.perspective_plotter.running_uuid == running_uuid:
             cameras_to_return.append(c)
    return cameras_to_return

def get_valid_camera(running_uuid):
    '''Get a camera with the given running uuid'''
    valid_cameras = get_valid_cameras(running_uuid)
    if len(valid_cameras) != 1:
        return None
    return valid_cameras[0]


def get_percentage_point(x, y, border_min_x, border_min_y, border_width, border_height):
    ''' get a coordinate in terms of a percentage of the viewing border'''
    new_percentage_point_x = (x - border_min_x) / (border_width) * 100
    new_percentage_point_y = (y - border_min_y) / (border_height) * 100

    new_percentage_point = [new_percentage_point_x, new_percentage_point_y]

    return new_percentage_point

def get_length_locations(cam_location, region, camera_obj, principal_point, focal_dist_2d, view_rotation_euler, axis_a, axis_b):
    '''get axis control locations'''
    
    if camera_obj.perspective_plotter.ref_distance_mode == 'X':
        plane_no = Vector((1,0,0))
    elif camera_obj.perspective_plotter.ref_distance_mode == 'Y':
        plane_no = Vector((0,1,0))
    elif camera_obj.perspective_plotter.ref_distance_mode == 'Z':
        plane_no = Vector((0,0,1))

    if camera_obj.perspective_plotter.camera_origin_mode == 'manual':
        plane_no.rotate(camera_obj.perspective_plotter.camera_rotation)
    
    vec_cam_to_axis_a = calc_point_2d_to_vector_3d(Vector(axis_a), principal_point, focal_dist_2d, view_rotation_euler )
    points = geometry.intersect_line_line(cam_location, cam_location + vec_cam_to_axis_a.normalized(), Vector((0,0,0)), plane_no)
    length_point_a_3d = points[1]

    vec_cam_to_axis_b = calc_point_2d_to_vector_3d(Vector(axis_b), principal_point, focal_dist_2d, view_rotation_euler )
    points = geometry.intersect_line_line(cam_location, cam_location + vec_cam_to_axis_b.normalized(), Vector((0,0,0)), plane_no)
    length_point_b_3d = points[1]

    return length_point_a_3d, length_point_b_3d

_axes = ['x', 'y', 'z']
def get_last_axis(vp_1_type, vp_2_type):
    """Get the last axis based on the first two types that are chosen."""
    last_vp_1_char = vp_1_type[-1].lower()
    last_vp_2_char = vp_2_type[-1].lower()
    remaining = list(set(_axes).difference([last_vp_1_char, last_vp_2_char]))
    return remaining[0]


def line_intersection(line1, line2):
    '''conventional function for 2D line intersection'''

    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
       return None, None

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return x, y

def calc_second_vanishing_point(Fu, f, P, horizonDir):
    '''Calculated second vanising point based on the first, a focal length, the center of projection and the desired horizon tilt angle'''
    if (Fu - P).magnitude < 1e-7:
      return None

    Fup = Vector((Fu.x - P.x,  Fu.y - P.y))

    k = -(Fup.x * Fup.x + Fup.y * Fup.y + f * f) / (Fup.x * horizonDir.x + Fup.y * horizonDir.y)
    Fv = Vector((
      Fup.x + k * horizonDir.x + P.x,
      Fup.y + k * horizonDir.y + P.y
    ))
    return Fv

def calc_third_vanishing_point(principal_point, horizon_intersect, vp_1, vp_2):
    '''Get third vanishing point given the other two'''
    point_intersect = geometry.intersect_point_line(vp_2, vp_1, principal_point)[0]

    x, y = line_intersection((vp_2, point_intersect), (horizon_intersect, principal_point))

    if x == None and y == None:
        return None

    return Vector((x, y))

def get_background_image(camera_obj):
    bkg_images = camera_obj.data.background_images
    # bkg_images = [bpy.data.objects['Empty'].data]
    if len(bkg_images) == 0:
        return None
    elif len(bkg_images) >= 1:
        # If there is only one background image, take that one
        return bkg_images[0]
    return None

def match_img(context, img):
    if img.image and img.source == 'IMAGE':
        context.scene.render.resolution_x = img.image.size[0]
        context.scene.render.resolution_y = img.image.size[1]
    elif img.clip and img.source == 'MOVIE_CLIP':
        context.scene.render.resolution_x = img.clip.size[0]
        context.scene.render.resolution_y = img.clip.size[1]

def does_img_match(context, img):
    if img.image and img.source == 'IMAGE':
        scene_resolution_aspect_ratio = context.scene.render.resolution_x / context.scene.render.resolution_y
        background_image_aspect_ratio = img.image.size[0] / img.image.size[1]
        return scene_resolution_aspect_ratio == background_image_aspect_ratio
    elif img.clip and img.source == 'MOVIE_CLIP':
        scene_resolution_aspect_ratio = context.scene.render.resolution_x / context.scene.render.resolution_y
        background_image_aspect_ratio = img.clip.size[0] / img.clip.size[1]
        return scene_resolution_aspect_ratio == background_image_aspect_ratio
    return False