import bpy
import os
from bpy.utils.toolsystem import ToolDef
from bpy.types import WorkSpaceTool, Panel, Operator

 
import bpy.utils.previews 
from gpu_extras.presets import draw_circle_2d






class TOOL_GGT_gizmo_camera(WorkSpaceTool):
    bl_space_type='VIEW_3D'
    bl_context_mode='OBJECT'

    bl_idname = "tool.gizmo_camera"
    bl_label = "Camera Gizmo"
    bl_description = ("Control transformation\n"
                     "and setup active Camera"
                     )


    bl_icon = os.path.join(os.path.dirname(__file__), 'icons', 'gizmo_camera') 

    #bl_widget = "gizmo.pro"
   
    bl_keymap = "3D View Tool: Select Box"
  

    def draw_settings(context, layout, tool):
        if context.active_object != None:
            props = context.preferences.addons[__package__.split(".")[0]].preferences
            #layout.use_property_split = True
            layout.prop(context.space_data, 'show_gizmo_object_translate', text='Move',toggle=True)

            row = layout.row(align=True)
            if context.object.type == 'CAMERA':
                row.prop(props,'target_visible', text='Target', toggle=True)
     

            if props.target_visible:
                row.operator("camgiz.target_object",text='',icon='EYEDROPPER')
                row.operator("camgiz.del_target",text='',icon='X')

            row = layout.row(align=True)
            row.prop(props,'show_gizmo',text="Gizmo",icon="PIVOT_CURSOR")
            row.operator("view3d.snap_cursor_to_center",text="",icon="EMPTY_ARROWS")
            row.operator("camgiz.resetrotation",text="",icon="ORIENTATION_GIMBAL") 
            row.operator('view3d.snap_cursor_to_selected',text='',icon='RESTRICT_SELECT_OFF')

            if context.space_data.lock_camera == False:
                layout.prop(context.space_data, 'lock_camera',text='View',icon='DECORATE_UNLOCKED',toggle=True)
            else:
                layout.prop(context.space_data, 'lock_camera',text='View',icon='DECORATE_LOCKED',toggle=True)

            ob = context.object
            if ob and ob.type == 'CAMERA':
                cam = context.object.data

                row = layout.row()
                row.prop(cam, "type",text='')

                if cam.type == 'PERSP':
                    row = layout.row()
                    row.prop(cam, "lens_unit",text='')
                    if cam.lens_unit == 'MILLIMETERS':
                        row.prop(cam, "lens")
                    elif cam.lens_unit == 'FOV':
                        row.prop(cam, "angle")
                    

                elif cam.type == 'ORTHO':
                    row.prop(cam, "ortho_scale")

                elif cam.type == 'PANO':
                    engine = context.engine
                    if engine == 'CYCLES':
                        ccam = cam.cycles
                        row.prop(ccam, "panorama_type")
                        if ccam.panorama_type == 'FISHEYE_EQUIDISTANT':
                            row.prop(ccam, "fisheye_fov")
                        elif ccam.panorama_type == 'FISHEYE_EQUISOLID':
                            row.prop(ccam, "fisheye_lens", text="Lens")
                            row.prop(ccam, "fisheye_fov")
                        elif ccam.panorama_type == 'EQUIRECTANGULAR':
                            sub = row.row(align=True)
                            sub.prop(ccam, "latitude_min", text="Latitude Min")
                            sub.prop(ccam, "latitude_max", text="Max")
                            sub = row.row(align=True)
                            sub.prop(ccam, "longitude_min", text="Longitude Min")
                            sub.prop(ccam, "longitude_max", text="Max")
                    elif engine in {'BLENDER_RENDER', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'}:
                        if cam.lens_unit == 'MILLIMETERS':
                            row.prop(cam, "lens")
                        elif cam.lens_unit == 'FOV':
                            row.prop(cam, "angle")
                        row.prop(cam, "lens_unit")

                row = layout.row()
                row.scale_x=0.9
                sub = row.row(align=True)
                sub.prop(cam, "clip_start", text="Clip Start")
                sub.prop(cam, "clip_end", text="End")

                sub = row.row(align=True)
                sub.prop(cam, "shift_x", text="Shift X")
                sub.prop(cam, "shift_y", text="Y")

            

            
            

            


            for i in range(1):
                layout.separator_spacer()
        
classes = [
]
preview_collections = {}


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.utils.register_tool(TOOL_GGT_gizmo_camera, separator=True, group=False)
  

    pcoll = bpy.utils.previews.new()
    my_icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    pcoll.load("location_icon", os.path.join(my_icons_dir, "location.png"), 'IMAGE')
    preview_collections["main"] = pcoll
  

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.utils.unregister_tool(TOOL_GGT_gizmo_camera)