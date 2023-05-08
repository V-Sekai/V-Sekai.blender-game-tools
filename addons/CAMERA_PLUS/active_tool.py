import bpy
from bl_ui.space_toolsystem_common import activate_by_id as activate_tool
from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active as view3d_tools



def active_tool():
    return view3d_tools.tool_active_from_context(bpy.context)

""" def activate_by_name(name):
    activate_tool(bpy.context, 'VIEW_3D', name) """


def cursor_gizmo_active():
    props = bpy.context.preferences.addons[__package__.split(".")[0]].preferences
    if active_tool().idname == "tool.gizmo_camera": 
        if bpy.context.space_data.show_gizmo == True:
            if bpy.context.space_data.overlay.show_cursor == True:
                return props.show_gizmo == True


def cam_gizmo_active():
    #props = bpy.context.preferences.addons[__package__.split(".")[0]].preferences
    if active_tool().idname == "tool.gizmo_camera": 
        #if props.gizmo_visible == True:
        if bpy.context.active_object != None:  
            if bpy.context.active_object.select_get():
                if bpy.context.space_data.show_gizmo == True:
                    if bpy.context.space_data.overlay.show_overlays == True:
                        ob = bpy.context.object
                        return ob and ob.type == 'CAMERA'

def but_gizmo_active():
    props = bpy.context.preferences.addons[__package__.split(".")[0]].preferences
    #if active_tool().idname == "tool.gizmo_camera": 
    if props.gizmo_visible == True:
        if bpy.context.active_object != None:  
            if bpy.context.active_object.select_get():
                if bpy.context.space_data.show_gizmo == True:
                    if bpy.context.space_data.overlay.show_overlays == True:
                        ob = bpy.context.object
                        return ob and ob.type == 'CAMERA'

classes = []


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)