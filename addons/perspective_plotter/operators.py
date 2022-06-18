import bpy
from bpy.utils import register_class, unregister_class
from bpy.props import *

from mathutils import Vector, Euler, geometry

from bpy_extras import view3d_utils


from . import util, draw

import uuid

class MESH_OT_ProjectMoveOperator(bpy.types.Operator):
    """Move Along View"""
    bl_idname = "view3d.move_along_view"
    bl_label = "Move Along View"
    bl_options = { "REGISTER", "UNDO"}

    amount : FloatProperty(default=0.0, options={'SKIP_SAVE'})
    
    view = None
    first_mouse_x = 0
    first_mouse_y = 0
    min_view_x = 0
    min_view_y = 0
    max_view_x = 0
    max_view_y = 0
    mouse_x_offset = 0
    mouse_y_offset = 0
    region = None
    loc_cache = {}
    is_shift_mode = False
    multiplier = 1
    delta_x = 0
    delta_y = 0

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.area.type == 'VIEW_3D'

    def invoke(self, context, event):
        """initialise for execution"""

        #grab coordinates of mouse.
        self.first_mouse_x = event.mouse_region_x
        self.first_mouse_y = event.mouse_region_y
        self.initial_amount = 0.00
        self.amount = 0
        self.multiplier = 1
        self.mouse_x_offset = 0
        self.mouse_y_offset = 0
        self.loc_cache.clear()
        self.is_shift_mode = False
        self.delta_x = 0
        self.delta_y = 0

        #get information about the viewing region.
        self.region = context.region
        space, i = util.get_quadview_index(context, event.mouse_x, event.mouse_y)
        view = None
        if space is not None:
            if i is None:
                view = space.region_3d
            else:
                view = space.region_quadviews[i]

        if not view:
            return {'CANCELLED'}

        self.view = view

        #record screen bounds.
        self.min_view_x = 0
        self.min_view_y = 0
        self.max_view_x = context.region.width
        self.max_view_y = context.region.height

        # the arguments we pass the the callback

        #calculate average vector information
        average_vector = Vector((0,0,0))
        average_coord = Vector((0,0,0))

        # initialise the cache
        util.move_along_view(context.region, self.view, context.active_object, self.loc_cache, self.amount)

        lines = []
        axis_lines = []
        for loc_cache_key in self.loc_cache:
            loc_cache_entry = self.loc_cache[loc_cache_key]
            loc_3d = loc_cache_entry[0]
            move_vector = loc_cache_entry[1]
            length = move_vector * 100

            line = (loc_3d - length, loc_3d + length)

            lines.append(  line )


        args = (self, context, lines)
        # Add the region OpenGL drawing callback
        # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
        self._handle_3d = bpy.types.SpaceView3D.draw_handler_add(draw.draw_callback_3d_move_along_view, args, 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}


    def modal(self, context, event):

        context.area.tag_redraw()

        # determine amount
        if event.type == 'MOUSEMOVE':

            region = self.region

            #cope with when the mouse goes over a boundary by resetting the initial variables.
            if event.mouse_region_x > self.max_view_x:
                #the mouse has gone to the right.
                context.window.cursor_warp(region.x, event.mouse_y)
                self.mouse_x_offset += region.width
                return {'RUNNING_MODAL'}
            if event.mouse_region_x < self.min_view_x:
                #the mouse has gone to the left.
                context.window.cursor_warp(region.x + region.width, event.mouse_y)
                self.mouse_x_offset += -region.width
                return {'RUNNING_MODAL'}
            if event.mouse_region_y > self.max_view_y:
                #the mouse has gone to the top.
                context.window.cursor_warp(event.mouse_x, region.y)
                self.mouse_y_offset += region.height
                return {'RUNNING_MODAL'}
            if event.mouse_region_y < self.min_view_y:
                #the mouse has gone to the bottom.
                context.window.cursor_warp(event.mouse_x, region.y + region.height)
                self.mouse_y_offset += -region.height
                return {'RUNNING_MODAL'}

            # If the shift mode is selected, adjust the amount by a smaller degree.
            if event.shift:
                if not self.is_shift_mode:
                    self.is_shift_mode = True
                    self.initial_amount = self.amount
                    self.multiplier = 0.1
                    self.delta_x =  event.mouse_region_x + self.mouse_x_offset - self.first_mouse_x
                    self.delta_y =  event.mouse_region_y + self.mouse_y_offset- self.first_mouse_y
                    return {'RUNNING_MODAL'}
            else:
                if self.is_shift_mode:
                    self.is_shift_mode = False
                    self.initial_amount = self.amount
                    self.multiplier = 1
                    self.delta_x =  event.mouse_region_x + self.mouse_x_offset - self.first_mouse_x
                    self.delta_y =  event.mouse_region_y + self.mouse_y_offset- self.first_mouse_y
                    return {'RUNNING_MODAL'}

            current_delta_x =  (event.mouse_region_x + self.mouse_x_offset - self.first_mouse_x)
            current_delta_y =  (event.mouse_region_y + self.mouse_y_offset- self.first_mouse_y)

            magnitude = ((current_delta_x - self.delta_x) + (current_delta_y - self.delta_y)) * 0.001


            self.amount = self.initial_amount + magnitude * self.multiplier
            

            # perform the movement
            util.move_along_view(context.region, self.view, context.active_object, self.loc_cache, self.amount)


        elif event.type == 'LEFTMOUSE':
            
            bpy.types.SpaceView3D.draw_handler_remove(self._handle_3d, 'WINDOW')
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle_3d, 'WINDOW')

            util.move_along_view(context.region, self.view, context.active_object, self.loc_cache, self.amount, reset=True)


            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def execute(self, context):
        #perform the extrusion
        util.move_along_view(context.region, self.view, context.active_object, self.loc_cache, self.amount)
        return {'FINISHED'}


class MESH_OT_PerspectivePlotterOperator(bpy.types.Operator):
    """Plot Perspective Lines"""
    bl_idname = "view3d.perspective_plotter"
    bl_label = "Plot Perspective"
    bl_options = { "INTERNAL" }

    _last_clicked_point_key = None

    _last_camera_distance = None

    _running_uuid = None

    _handle_3d = None


    def invoke(self, context, event):

        camera_obj = util.get_camera(context, context.region)
        if not camera_obj:
            return {'CANCELLED'}

        # initialise the calculation of the view
        camera_obj.perspective_plotter.is_dirty = True
        
        # generate a running id and to the operation associate the camera with it to keep track of draw functions.
        running_uuid = str(uuid.uuid4())
        self._running_uuid = camera_obj.perspective_plotter.running_uuid = running_uuid

        # push an undo event before altering anything.
        bpy.ops.ed.undo_push()

        # assign the draw handler
        args = (running_uuid, context)
        self._handle_3d = bpy.types.SpaceView3D.draw_handler_add(draw.draw_callback_3d_perspective_plotter, args, 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)

        context.area.tag_redraw()

        return {'RUNNING_MODAL'}


    def modal(self, context, event):

        # Check for valid states.any(iterable)
        
        # get the relevant camera and check we have a running uuid associated with the camera.
        camera_obj = util.get_valid_camera(self._running_uuid)
        if not camera_obj or not camera_obj.perspective_plotter.running_uuid:
            return {'FINISHED'}

        # get valid viewing regions for this camera
        regions = util.get_valid_regions(context, camera_obj)
        if  not regions:
            return {'FINISHED'}
            
        # if it is looking good, proceed with the function for every viewing region.
        user_preferences = context.preferences
        addon_prefs = user_preferences.addons[__package__].preferences

        mouse_x = event.mouse_x
        mouse_y = event.mouse_y

        # got each region, detect if there is any user action we need to orchestrate.
        for region in regions:

            # don't do anything if the mouse is outside this region.
            if not (mouse_x >= region.x and
                mouse_y >= region.y and
                mouse_x < region.width + region.x and
                mouse_y < region.height + region.y):
                continue

            # if this is not the right camera for the view, just return
            view_camera = util.get_camera(context, region)
            if camera_obj != view_camera:
                continue

            if camera_obj.perspective_plotter.disable_control_points:
                continue

            # obtain the viewing border for the camera.
            frame_px = util.view3d_camera_border(context, region)

            # we need to offset by the region's global position in the modal function.
            for f in frame_px:
                if not f:
                    return {'CANCELLED'}
                f.x += region.x
                f.y += region.y

            # get border information for the frame.
            border_min_x = min([v[0] for v in frame_px])
            border_min_y = min([v[1] for v in frame_px])
            border_max_x = max([v[0] for v in frame_px])
            border_max_y = max([v[1] for v in frame_px])
            border_width = border_max_x - border_min_x
            border_height = border_max_y - border_min_y

            # get all the different axis control point pixel points offset by the border as the stored points are percentages.
            axis_vp1_point_a, axis_vp1_point_b, axis_vp1_point_c, axis_vp1_point_d, axis_vp2_point_a, axis_vp2_point_b, axis_vp2_point_c, axis_vp2_point_d, axis_vp3_point_a, axis_vp3_point_b, axis_vp3_point_c, axis_vp3_point_d \
                = util.get_axis_points(camera_obj, border_min_x, border_width, border_min_y, border_height)


            # based on what perspective mode we are in, we get different control points.
            grid_point = util.get_grid_point(camera_obj, border_min_x, border_width, border_min_y, border_height)
            if camera_obj.perspective_plotter.vanishing_point_num in {'1'}:
                # get the horizon line.
                horizon_point_a, horizon_point_b = util.get_horizon_points(camera_obj, border_min_x, border_width, border_min_y, border_height)
                points_map = {
                    "grid_point" : grid_point,
                    "axis_vp1_point_a" : axis_vp1_point_a,
                    "axis_vp1_point_b" : axis_vp1_point_b,
                    "axis_vp1_point_c" : axis_vp1_point_c,
                    "axis_vp1_point_d" : axis_vp1_point_d,
                    "horizon_point_a" : horizon_point_a,
                    "horizon_point_b" : horizon_point_b,
                }
            elif camera_obj.perspective_plotter.vanishing_point_num in {'2'}:
                points_map = {
                    "grid_point" : grid_point,
                    "axis_vp1_point_a" : axis_vp1_point_a,
                    "axis_vp1_point_b" : axis_vp1_point_b,
                    "axis_vp1_point_c" : axis_vp1_point_c,
                    "axis_vp1_point_d" : axis_vp1_point_d,
                    "axis_vp2_point_a" : axis_vp2_point_a,
                    "axis_vp2_point_b" : axis_vp2_point_b,
                    "axis_vp2_point_c" : axis_vp2_point_c,
                    "axis_vp2_point_d" : axis_vp2_point_d,
                }
            elif  camera_obj.perspective_plotter.vanishing_point_num in {'3'}:
                points_map = {
                    "grid_point" : grid_point,
                    "axis_vp1_point_a" : axis_vp1_point_a,
                    "axis_vp1_point_b" : axis_vp1_point_b,
                    "axis_vp1_point_c" : axis_vp1_point_c,
                    "axis_vp1_point_d" : axis_vp1_point_d,
                    "axis_vp2_point_a" : axis_vp2_point_a,
                    "axis_vp2_point_b" : axis_vp2_point_b,
                    "axis_vp2_point_c" : axis_vp2_point_c,
                    "axis_vp2_point_d" : axis_vp2_point_d,
                    "axis_vp3_point_a" : axis_vp3_point_a,
                    "axis_vp3_point_b" : axis_vp3_point_b,
                    "axis_vp3_point_c" : axis_vp3_point_c,
                    "axis_vp3_point_d" : axis_vp3_point_d
                }

            # also add the principal point control point if we are manually controling the principal point of the camera.
            if camera_obj.perspective_plotter.vanishing_point_num in {'1', '2'} and camera_obj.perspective_plotter.principal_point_mode == 'manual':
                principal_point = util.get_principal_point(camera_obj, border_min_x, border_width, border_min_y, border_height)
                points_map['principal_point'] = principal_point

            if camera_obj.perspective_plotter.ref_distance_mode  != 'camera_distance':
                grid_point = util.get_grid_point(camera_obj, border_min_x, border_width, border_min_y, border_height)
                vp_to_project_to_px = util.get_vp_to_project_to(camera_obj, border_min_x, border_width, border_min_y, border_height)
                length_point_a_2d, length_point_b_2d = util.get_length_points(grid_point, vp_to_project_to_px, camera_obj.perspective_plotter.length_point_a, camera_obj.perspective_plotter.length_point_b)
                points_map['length_point_a'] = length_point_a_2d
                points_map['length_point_b'] = length_point_b_2d

            # determine whether we are close enough to a point to change the mouse cursor.
            found_key = None
            mouse_coords = Vector((mouse_x, mouse_y))
            for point_key in points_map:
                point = points_map[point_key]

                if point_key.startswith('axis_') and \
                    (Vector(point) - mouse_coords).length < addon_prefs.sensitivity_axis_point:
                    context.window.cursor_set("SCROLL_XY")
                    found_key = point_key
                    break
                if point_key.startswith('length_point_')  and \
                    (Vector(point) - mouse_coords).length < addon_prefs.sensitivity_measuring_point:
                    context.window.cursor_set("CROSSHAIR")
                    found_key = point_key
                    break
                if point_key.startswith('horizon_point_')  and \
                    (Vector(point) - mouse_coords).length < addon_prefs.sensitivity_axis_point:
                    context.window.cursor_set("SCROLL_XY")
                    found_key = point_key
                    break
                if point_key == 'grid_point' and \
                    (Vector(point) - mouse_coords).length < addon_prefs.sensitivity_grid_point:
                    context.window.cursor_set("SCROLL_XY")
                    found_key = point_key
                    break
                if point_key == 'principal_point' and \
                    (Vector(point) - mouse_coords).length < addon_prefs.sensitivity_principal_point:
                    context.window.cursor_set("SCROLL_XY")
                    found_key = point_key
                    break


            if not found_key:
                context.window.cursor_set("DEFAULT")
            
            # register whether the user clicked and moved the point.
            if event.value == 'PRESS' and event.type == 'LEFTMOUSE' and found_key:
                bpy.ops.ed.undo_push()
                self._last_clicked_point_key = found_key
                self._last_camera_distance = camera_obj.perspective_plotter.camera_distance
            if event.value == 'RELEASE'and event.type == 'LEFTMOUSE':
                if self._last_clicked_point_key:
                    bpy.ops.ed.undo_push()
                self._last_clicked_point_key = None
            if event.type == 'MOUSEMOVE' and self._last_clicked_point_key and \
                not(event.ctrl and event.alt) and self._last_clicked_point_key in points_map:


                x, y = mouse_x, mouse_y
                mouse_point = Vector((x, y))
                old_mouse_point = Vector((event.mouse_prev_x, event.mouse_prev_y))

                if self._last_clicked_point_key not in {'length_point_a', 'length_point_b'}:


                    new_percentage_point = Vector(util.get_percentage_point(mouse_point.x, mouse_point.y, border_min_x, border_min_y, border_width, border_height))

                    if event.shift:
                        current_percentage_point = Vector(getattr(camera_obj.perspective_plotter, self._last_clicked_point_key))
                        percentage_vec = Vector(new_percentage_point - current_percentage_point)
                        new_percentage_point = current_percentage_point + (percentage_vec * 0.1)

                    if self._last_clicked_point_key not in {'principal_point', 'grid_point'}:
                        if new_percentage_point[0] < 0:
                            new_percentage_point[0] = 0
                        if new_percentage_point[0] > 100:
                            new_percentage_point[0] = 100
                        if new_percentage_point[1] < 0:
                            new_percentage_point[1] = 0
                        if new_percentage_point[1] > 100:
                            new_percentage_point[1] = 100


                    if getattr(camera_obj.perspective_plotter, self._last_clicked_point_key) != new_percentage_point:
                        setattr(camera_obj.perspective_plotter, self._last_clicked_point_key, new_percentage_point)
                        util.calc_view(context, camera_obj, region)
                elif camera_obj.perspective_plotter.ref_distance_mode != 'camera_distance':

                    length_point_a_2d = points_map['length_point_a']
                    length_point_b_2d = points_map['length_point_b']

                    # determine 2d intersection.
                    intersect_point_line = geometry.intersect_point_line(mouse_point, length_point_a_2d, length_point_b_2d)
                    point_intersect = intersect_point_line[0]
                    point_intersect_percentage = intersect_point_line[1]

                    new_val = camera_obj.perspective_plotter.length_point_a + ((camera_obj.perspective_plotter.length_point_b - camera_obj.perspective_plotter.length_point_a) * point_intersect_percentage)

                    if event.shift:
                        current_val = getattr(camera_obj.perspective_plotter, self._last_clicked_point_key)
                        percentage_vec = new_val - current_val
                        new_val = current_val + (percentage_vec * 0.01)

                    if getattr(camera_obj.perspective_plotter, self._last_clicked_point_key) != new_val:
                        setattr(camera_obj.perspective_plotter, self._last_clicked_point_key, new_val)
                        util.calc_view(context, camera_obj, region)

                return {'RUNNING_MODAL'}


        return {'PASS_THROUGH'}

    def __del__(self):
        try:
            valid_cameras = util.get_valid_cameras(self._running_uuid)
            for valid_camera in valid_cameras:
                valid_camera.perspective_plotter.running_uuid = ''
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle_3d, 'WINDOW')
            except ValueError:
                # extra catch in case the reference is lost on reload.
                pass
            bpy.context.window.cursor_set("DEFAULT")
            for area in bpy.context.screen.areas:
                area.tag_redraw()
        except ReferenceError:
            pass


class MESH_OT_PerspectivePlotterCancelOperator(bpy.types.Operator):
    """Plot Perspective Lines"""
    bl_idname = "view3d.perspective_plotter_cancel"
    bl_label = "Plot Perspective"
    bl_options = { "INTERNAL" }

    _last_clicked_point_key = None

    running_uuid = None

    def invoke(self, context, event):

        camera_obj = util.get_camera(context, context.region)

        if camera_obj and camera_obj.perspective_plotter.running_uuid:
            camera_obj.perspective_plotter.running_uuid = ''
            return {'FINISHED'}

        return {'CANCELLED'}

def get_match_bg_description():
    return (
    "Match scene render resolution to main background image of this camera.\n"
    "\n"
    " WARNING: All cameras are affected"
    )    

class MESH_OT_MatchResolutionToBG(bpy.types.Operator):

    bl_idname = "view3d.pp_match_resolution_to_bg_image"
    bl_label = "Affects all scene cameras and their perspective guides."
    bl_description = get_match_bg_description()
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return util.get_camera(context, context.region)

    def invoke(self, context, event):
        if len([o for o in context.visible_objects if o.type == 'CAMERA']) > 1:
            return context.window_manager.invoke_confirm(self, event)
        else:
            return self.execute(context)

    def execute(self, context):
        camera_obj = util.get_camera(context, context.region)
        img = util.get_background_image(camera_obj)
        if not img:
            return {'CANCELLED'}

        util.match_img(context, img)

        camera_obj.perspective_plotter.is_dirty = True

        for area in context.screen.areas:
            area.tag_redraw()
        
        return {'FINISHED'}

class MESH_OT_ResetCameraDefaults(bpy.types.Operator):
    """Reset Perspective Plotter Defaults"""
    bl_idname = "view3d.pp_reset_defaults"
    bl_label = "Reset Perspective Plotter Defaults"
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        camera_obj = util.get_camera(context, context.region)
        return camera_obj and camera_obj.perspective_plotter.running_uuid

    def invoke(self, context, event):
        camera_obj = util.get_camera(context, context.region)
        if camera_obj:
            for prop in camera_obj.bl_rna.properties:
                if prop.identifier == 'perspective_plotter':
                    perspective_plotter = getattr(camera_obj, prop.identifier)
                    for perspective_plotter_prop in perspective_plotter.bl_rna.properties:
                        if perspective_plotter_prop.identifier in {'running_uuid'}:
                            continue
                        if hasattr(perspective_plotter_prop, 'default'):
                            if getattr(perspective_plotter_prop, 'is_array', False):
                                setattr(perspective_plotter, perspective_plotter_prop.identifier, perspective_plotter_prop.default_array)
                            else:
                                setattr(perspective_plotter, perspective_plotter_prop.identifier, perspective_plotter_prop.default)
        return {'FINISHED'}

class MESH_OT_SetKeyFrame(bpy.types.Operator):
    """Set Keyframes for Camera"""
    bl_idname = "view3d.pp_set_keyframe"
    bl_label = "Set Keyframe"
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return util.get_camera(context, context.region)

    def invoke(self, context, event):
        currentFrame = context.scene.frame_current
        camera_obj = util.get_camera(context, context.region)
        camera_obj_name = camera_obj.name
        camera_obj.keyframe_insert(data_path="location", frame=currentFrame)
        camera_obj.keyframe_insert(data_path="rotation_euler", frame=currentFrame)
        camera_obj.data.keyframe_insert("lens", frame=currentFrame)
        camera_obj.data.keyframe_insert("shift_x", frame=currentFrame)
        camera_obj.data.keyframe_insert("shift_y", frame=currentFrame)

        for area in context.screen.areas:
            area.tag_redraw()

        return {'FINISHED'}

_keyframe_search_points = ['location', 'rotation_euler', 'lens', 'shift_x', 'shift_y']
class MESH_OT_DeleteKeyFrame(bpy.types.Operator):
    """Delete Keyframes for Camera"""
    bl_idname = "view3d.pp_delete_keyframe"
    bl_label = "Delete Keyframe"
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return util.get_camera(context, context.region)


    @classmethod
    def poll(cls, context):
        '''Check for presence of relevant keyframes'''
        camera_obj = util.get_camera(context, context.region)
        if not camera_obj.animation_data:
            return False
            
        global _keyframe_search_points
        keyframe_search_points = _keyframe_search_points[:]

        currentFrame = context.scene.frame_current
        
        fcurves = camera_obj.animation_data.action.fcurves[:]
        fcurves.extend(camera_obj.data.animation_data.action.fcurves)

        for curve in fcurves:
            keyframePoints = curve.keyframe_points
            for keyframe in keyframePoints:
                if curve.data_path in keyframe_search_points and keyframe.co[0] == currentFrame:
                    keyframe_search_points.remove(curve.data_path)
        

        return len(keyframe_search_points) == 0

    def invoke(self, context, event):
        '''Delete current keyframe'''
        global _keyframe_search_points
        keyframe_search_points = _keyframe_search_points[:]
        camera_obj = util.get_camera(context, context.region)
        currentFrame = context.scene.frame_current
        fcurves = camera_obj.animation_data.action.fcurves[:]
        fcurves.extend(camera_obj.data.animation_data.action.fcurves)
        
        for curve in fcurves:
            keyframePoints = curve.keyframe_points
            pointsToRemove = []
            for keyframe in keyframePoints:
                if curve.data_path in keyframe_search_points and keyframe.co[0] == currentFrame:
                    pointsToRemove.append(keyframe)

            while(pointsToRemove):
                keyframe = pointsToRemove.pop()
                curve.keyframe_points.remove(keyframe)

        for area in context.screen.areas:
            area.tag_redraw()

        remaining_keyframes = False
        fcurves = camera_obj.animation_data.action.fcurves[:]
        fcurves.extend(camera_obj.data.animation_data.action.fcurves)
        for curve in fcurves:
            keyframePoints = curve.keyframe_points
            pointsToRemove = []
            for keyframe in keyframePoints:
                if curve.data_path in keyframe_search_points:
                    remaining_keyframes = True

        if not remaining_keyframes:
            bpy.ops.view3d.pp_delete_all_keyframes('INVOKE_DEFAULT')

        return {'FINISHED'}

class MESH_OT_DeleteAllKeyFrames(bpy.types.Operator):
    """Delete Keyframes for Camera"""
    bl_idname = "view3d.pp_delete_all_keyframes"
    bl_label = "Delete all Keyframes"
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return util.get_camera(context, context.region)

    def invoke(self, context, event):
        '''Delete all relevant keyframes'''
        global _keyframe_search_points
        keyframe_search_points = _keyframe_search_points
        camera_obj = util.get_camera(context, context.region)
        currentFrame = context.scene.frame_current

        fcurves = camera_obj.animation_data.action.fcurves
        curvesToRemove = []        
        for curve in fcurves:
            keyframePoints = curve.keyframe_points
            if curve.data_path in keyframe_search_points:
                curvesToRemove.append(curve)

        curvesToRemove = list(set(curvesToRemove))
        while(curvesToRemove):
            fCurve = curvesToRemove.pop()
            camera_obj.animation_data.action.fcurves.remove(fCurve)

        fcurves = camera_obj.data.animation_data.action.fcurves[:]
        curvesToRemove = []        
        for curve in fcurves:
            keyframePoints = curve.keyframe_points

            if curve.data_path in keyframe_search_points:
                curvesToRemove.append(curve)

        curvesToRemove = list(set(curvesToRemove))
        while(curvesToRemove):
            fCurve = curvesToRemove.pop()
            camera_obj.data.animation_data.action.fcurves.remove(fCurve)

        for area in context.screen.areas:
            area.tag_redraw()

        return {'FINISHED'}

class MESH_OT_OpenHelpURL(bpy.types.Operator):
    bl_idname = "mesh.ppplot_open_help_url" 
    bl_label = "Help"
    bl_options = {'INTERNAL', 'UNDO'}
    
    url : StringProperty()

    description : StringProperty()

    @classmethod
    def description(self, context, properties):
        if properties.description:
            return properties.description
        return ''

    def execute(self, context):
        bpy.ops.wm.url_open(url = self.url)
        return {'FINISHED'}




class MESH_OT_FlattenHorizonLine(bpy.types.Operator):
    """Attempt to adjust vanishing points to flatten horizon line"""
    bl_idname = "view3d.pp_flatten_horizon_line"
    bl_label = "Flatten Horizon Line"
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        camera_obj = util.get_camera(context, context.region)
        return camera_obj and camera_obj.perspective_plotter.running_uuid

    def invoke(self, context, event):
        '''Delete all relevant keyframes'''
        
        camera_obj = util.get_camera(context, context.region)

        util.flatten_horizon(camera_obj)


        return {'FINISHED'}

class MESH_OT_SetTargetOrigin(bpy.types.Operator):
    """Set from current 3D Cursor location"""
    bl_idname = "view3d.pp_set_target_origin"
    bl_label = "Set to 3D Cursor"
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        camera_obj = util.get_camera(context, context.region)
        return camera_obj and camera_obj.perspective_plotter.running_uuid

    def invoke(self, context, event):
        '''Delete all relevant keyframes'''

        cursor_location = context.scene.cursor.location
        cursor_rotation_euler = context.scene.cursor.rotation_euler
        
        camera_obj = util.get_camera(context, context.region)

        camera_obj.perspective_plotter.camera_offset = cursor_location
        camera_obj.perspective_plotter.camera_rotation = cursor_rotation_euler


        return {'FINISHED'}

classes = [
    MESH_OT_ProjectMoveOperator,
    MESH_OT_PerspectivePlotterOperator,
    MESH_OT_PerspectivePlotterCancelOperator,
    MESH_OT_MatchResolutionToBG,
    MESH_OT_ResetCameraDefaults,
    MESH_OT_SetKeyFrame,
    MESH_OT_DeleteKeyFrame,
    MESH_OT_DeleteAllKeyFrames,
    MESH_OT_OpenHelpURL,
    MESH_OT_FlattenHorizonLine,
    MESH_OT_SetTargetOrigin
    ]

def menu_func(self, context):
    # self.layout.menu(MESH_OT_ProjectMoveOperator.bl_idname, icon='IPO_BOUNCE')
    col = self.layout.column()
    col.operator_context = 'INVOKE_DEFAULT'

    col.operator(MESH_OT_ProjectMoveOperator.bl_idname, icon='VIEW3D')

def register():
    for cls in classes:
        register_class(cls)

    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(menu_func)
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)


def unregister():



    for cls in classes:
        unregister_class(cls)

    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_func)