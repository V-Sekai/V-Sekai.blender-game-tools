import bpy
from bpy.types import Window, Area

from uvflow.addon_utils import Register
from uvflow.addon_utils.types import BBOX_2
from uvflow.addon_utils.utils.cursor import Cursor

from bpy.types import Context


def get_gn_editor(wnd: Window) -> Area or None:
    for _area in wnd.screen.areas:
        if _area.type == 'NODE_EDITOR' and _area.ui_type == 'GeometryNodeTree':
            print("Get GN Editor")
            return _area
    return None


def get_uv_editor(wnd: Window) -> Area or None:
    for _area in wnd.screen.areas:
        if _area.type == 'IMAGE_EDITOR' and _area.ui_type == 'UV':
            return _area
    return None


def create_gn_editor(wnd: Window) -> Area or None:
    print("Create GN Editor")
    for area in wnd.screen.areas:
        if area.type == 'VIEW_3D':
            # Create and Setup new GN Editor.
            with bpy.context.temp_override(window=wnd, area=area):
                all_areas_memaddress = {area.as_pointer() for area in wnd.screen.areas}
                bpy.ops.screen.area_split(factor=0.01, direction='HORIZONTAL')
                for _area in wnd.screen.areas:
                    if _area.as_pointer() not in all_areas_memaddress:
                        _area.type = 'NODE_EDITOR'
                        _area.ui_type = 'GeometryNodeTree'
                        return _area
            break


def ensure_gn_editor(wnd: Window) -> Area or None:
    if gn_editor := get_gn_editor(wnd):
        return gn_editor, False
    return create_gn_editor(wnd), True


@Register.OPS.GENERIC
class ToggleUVEditor:
    def setup_uv_editor(self, area: bpy.types.Area):
        area.type = 'IMAGE_EDITOR'
        area.spaces[0].image = None # UVs are much easier to see without the checker texture
        area.ui_type = 'UV'
        area.spaces[0].use_image_pin = True

        # Fitting to the view would be nice, but context override here crashes Blender
        '''
        with context.temp_override(window=wnd, area=area):
            bpy.ops.image.view_all(fit_view=True)
        '''
        '''
        if alignment in {'RIGHT', 'TOP'}:
            uv_area_bbox = BBOX_2.from_area(area)
            if alignment == 'RIGHT':
                # Currently is at the left.
                cursor = (uv_area_bbox.min_x, uv_area_bbox.min_y + 20)
            elif alignment == 'TOP':
                # Currently is at the bottom.
                cursor = (uv_area_bbox.min_x + 20, uv_area_bbox.max_y)
            bpy.ops.screen.area_swap(cursor=cursor)
        '''


    def action(self, context: Context):
        from uvflow.prefs import UVFLOW_Preferences
        prefs = UVFLOW_Preferences.get_prefs(context)
        direction: str = prefs.uv_editor_alignment
        use_separated_window = direction == 'WINDOW'

        context.scene.uvflow.uv_editor_enabled = not context.scene.uvflow.uv_editor_enabled

        ''' WINDOW OPTION. '''
        if use_separated_window:
            if context.scene.uvflow.uv_editor_enabled:
                bpy.ops.wm.window_new()
                new_wnd = context.window_manager.windows[-1]
                self.setup_uv_editor(new_wnd.screen.areas[0])
            else:
                for wnd in context.window_manager.windows:
                    if len(wnd.screen.areas) != 1:
                        continue
                    area = wnd.screen.areas[0]
                    if area.type == 'IMAGE_EDITOR' and area.ui_type == 'UV':
                        with context.temp_override(window=wnd, area=area):
                            bpy.ops.wm.window_close()
                        break
            return

        ''' AREA OPTION. '''
        wnd = context.window

        if context.scene.uvflow.uv_editor_enabled:
            current_view3d_area_pointers: set[int] = {area.as_pointer() for area in context.screen.areas if area.type == 'VIEW_3D'}
            bpy.ops.screen.area_split(factor=0.3, direction=direction)
            for area in context.screen.areas:
                if area.type != 'VIEW_3D':
                    continue
                if area.as_pointer() in current_view3d_area_pointers:
                    continue
                self.setup_uv_editor(area)
        else:
            uv_editor_areas = [area for area in context.screen.areas if area.type == 'IMAGE_EDITOR' and area.ui_type == 'UV']
            if len(uv_editor_areas) == 0:
                # No UV Editors to close!
                return -1
            if len(uv_editor_areas) == 1:
                uv_area = uv_editor_areas[0]
            else:
                uv_area = None
                # Detect which UV Editor is the correct one.
                view3d_area_bbox = BBOX_2.from_area(context.area)
                view3d_area_corners = view3d_area_bbox.corners
                for _uv_area in uv_editor_areas:
                    uv_area_bbox = BBOX_2.from_area(_uv_area)
                    # View3D and UV Editors should share 2 corners.
                    match_corners = [True for view3d_corner in view3d_area_corners for uv_corner in uv_area_bbox.corners if view3d_corner.distance(uv_corner) <= 2]
                    if len(match_corners) == 2:
                        uv_area = _uv_area
                        break

            if uv_area is None:
                return -1

            '''
            delta = 0
            uv_area_bbox = BBOX_2.from_area(uv_area)
            if alignment in {'BOTTOM'}:
                expected_height = context.area.height + uv_area.height
                delta = -uv_area.height
            elif alignment in {'RIGHT'}:
                expected_width = context.area.width + uv_area.width
                delta = -uv_area.width
            '''

            with context.temp_override(window=wnd, area=uv_area):
                bpy.ops.screen.area_close()

            '''
            if delta != 0:
                if alignment in {'BOTTOM'}:
                    if expected_height == context.area.height:
                        return
                    wnd.cursor_warp(uv_area_bbox.min_x + 20, uv_area_bbox.max_y)
                    # Cursor.wrap(context.area.x + int(context.area.width/2), context.area.y)
                elif alignment in {'RIGHT'}:
                    if expected_width == context.area.width:
                        return
                    wnd.cursor_warp(uv_area_bbox.min_x, uv_area_bbox.min_y + 20)
                    # Cursor.wrap(context.area.x, context.area.y + int(context.area.height/2))
                bpy.ops.screen.area_move(delta=delta)
            '''


@Register.OPS.GENERIC
class ToggleGNEditor:
    def action(self, context: Context):
        if gn_editor := get_gn_editor(context.window):
            with context.temp_override(window=context.window, area=gn_editor):
                bpy.ops.screen.area_close()
        else:
            create_gn_editor(context.window)
