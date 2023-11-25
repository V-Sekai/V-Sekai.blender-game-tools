import bpy
from bpy.types import Window, Area

def get_gn_editor(wnd: Window) -> Area or None:
    for _area in wnd.screen.areas:
        if _area.type == 'NODE_EDITOR' and _area.ui_type == 'GeometryNodeTree':
            print("Get GN Editor")
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