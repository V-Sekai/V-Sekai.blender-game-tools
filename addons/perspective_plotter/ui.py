import bpy
from bpy.types import Panel
from bpy.utils import register_class, unregister_class

from . import operators, util

import textwrap

class PERSPECTIVEPLOTTER_PT_GeneralPanel(bpy.types.Panel):
    """Perspective Plotter Object Panel"""
    bl_idname = "PERSPECTIVEPLOTTER_PT_GeneralPanel"
    bl_label = "Perspective Plotter"
    bl_category = "P.Plotter"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    
    @classmethod
    def poll(self, context):
        camera_obj = util.get_camera(context, context.region)
        return len(util.get_valid_regions(context, camera_obj)) != 0

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        props = row.operator("mesh.ppplot_open_help_url", icon='QUESTION', text="")
        props.url = "https://perspective-plotter.readthedocs.io/"
        props.description = "Open Perspective Plotter Documentation"

        row.separator()



    def draw(self, context):
        pass


class PERSPECTIVEPLOTTER_PT_PlotterPanel(bpy.types.Panel):
    """Perspective Plotter Object Panel"""
    bl_idname = "PERSPECTIVEPLOTTER_PT_PlotterPanel"
    bl_label = "Perspective Plotter"
    bl_category = "P.Plotter"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = 'PERSPECTIVEPLOTTER_PT_GeneralPanel'
    bl_options = {'HIDE_HEADER'}

    @classmethod
    def poll(self, context):
        camera_obj = util.get_camera(context, context.region)
        return len(util.get_valid_regions(context, camera_obj)) != 0

    def draw(self, context):



        layout = self.layout
        col = layout.column()
        
        col.enabled = self.poll(context)

        camera_obj = util.get_camera(context, context.region)

        if camera_obj and not camera_obj.perspective_plotter.is_valid:
            alert_col = col.column(align=True)
            alert_col.alignment = 'CENTER'
            alert_col.alert=True
            # an_row.label(text="Invalid Configuration")
            text = "Invalid Configuration"
            alert_col.operator("mesh.ppplot_open_help_url", icon='ERROR', text="Invalid Configuration", emboss=False).url = "https://perspective-plotter.readthedocs.io/en/latest/troubleshooting.html#invalid-configuration"

        if camera_obj and camera_obj.perspective_plotter.error_message:
            wrapp = textwrap.TextWrapper(width=30)

            wList = wrapp.wrap(text=camera_obj.perspective_plotter.error_message) 

            error_col = col.column(align=True)
            error_col.alignment = 'CENTER'
            error_col.alert=True
            for text in wList: 
                error_row = error_col.row()
                error_row.alignment = 'CENTER'
                error_row.label(text=text)

        box = col.box()
        box_col = box.column()

        text = "Plotting..." if camera_obj.perspective_plotter.running_uuid else "Plot Perspective"
        operator_id = 'view3d.perspective_plotter' if not camera_obj.perspective_plotter.running_uuid else 'view3d.perspective_plotter_cancel'
        box_col.operator(operator_id, depress=camera_obj.perspective_plotter.running_uuid != '', text=text, icon='GRID',)



        box_col_props = box_col.column()
        box_col_props_row = box_col_props.split(factor=0.7)
        box_col_props_row.label(text="Vanishing Points: ")
        box_col_props_row.prop(camera_obj.perspective_plotter, 'vanishing_point_num', text="")

        box_col_props_row = box_col_props.split(factor=0.8)
        box_col_props_row.label(text="Update Camera: ")
        box_col_props_row.alignment="RIGHT"
        box_col_props_row2 = box_col_props_row.row()
        box_col_props_row2.alignment="RIGHT"
        box_col_props_row2.prop(camera_obj.perspective_plotter, 'is_camera_sync', text="")

_measure_icon = "FIXED_SIZE" if bpy.app.version >= (3, 0, 0) else "ORIENTATION_VIEW"
class PERSPECTIVEPLOTTER_PT_Advanced(Panel):
    bl_space_type = 'VIEW_3D'
    bl_label = 'Parameters'
    bl_region_type = 'UI'
    bl_category = "P.Plotter"
    bl_idname = "PERSPECTIVEPLOTTER_PT_Advanced"
    bl_parent_id = 'PERSPECTIVEPLOTTER_PT_PlotterPanel'
    # bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):

        layout = self.layout
        col = layout.column()


        box = col.box()
        box_col = box.column()
        box_col_props = box_col.column(align=True)


        camera_obj = util.get_camera(context, context.region)

        box_col_props.enabled = camera_obj.perspective_plotter.running_uuid != ''

        box_col_props.label(text="Focal Length:")
        if int(camera_obj.perspective_plotter.vanishing_point_num) == 1:
            
            box_col_props.prop(camera_obj.perspective_plotter, 'one_point_focal_length', text="") 
        else:
            box_col_props_lens = box_col_props.column(align=True)
            box_col_props_lens.alignment = 'CENTER'
            box_col_props_lens_row = box_col_props.row(align=True)
            box_col_props_lens_row.alignment = 'CENTER'
            box_col_props_lens_row.label(text=str(round(camera_obj.data.lens, 2)) + ' mm')
            
        box_col_props.separator()
        box_col_props.label(text="Reference Distance:")
        box_col_props.prop(camera_obj.perspective_plotter, 'ref_distance_mode', text="")

        
        box_col_props_box = box_col_props.box()
        box_col_props_box_col = box_col_props_box.column(align=True)

        global _measure_icon
        if camera_obj.perspective_plotter.ref_distance_mode == 'camera_distance':
            box_col_props_box_col.label(text="Camera Distance: ")
            box_col_props_box_col.prop(camera_obj.perspective_plotter, 'camera_distance', text="")
        elif camera_obj.perspective_plotter.ref_distance_mode != 'camera_distance':
            box_col_props_box_col.label(text="Reference Length: ")
            box_col_props_box_col_row = box_col_props_box_col.split(factor=0.9, align=True)
            box_col_props_box_col_row.prop(camera_obj.perspective_plotter, 'ref_length', text="")
            box_col_props_box_col_row.prop(camera_obj.perspective_plotter, 'is_manual_length_point', text="", icon=_measure_icon)
            
            if camera_obj.perspective_plotter.is_manual_length_point:
                box_col_props_box_col.separator()
                box_col_props_box_col_row = box_col_props_box_col.split(factor=0.1, align=True)
                box_col_props_box_col_row.label(icon=_measure_icon, text="")
                box_col_props_box_col_row.prop(camera_obj.perspective_plotter, 'length_point_a', text="A:")
                box_col_props_box_col_row = box_col_props_box_col.split(factor=0.1, align=True)
                box_col_props_box_col_row.label(icon=_measure_icon, text="")
                box_col_props_box_col_row.prop(camera_obj.perspective_plotter, 'length_point_b', text="B:")

        box_col_props.separator()

        box_col_props.label(text="Vanishing Point 1:")
        box_col_props.prop(camera_obj.perspective_plotter, 'vp_1_type', text="")

        box_col_props.separator()

        box_col_props.label(text="Vanishing Point 2:")
        box_col_props.prop(camera_obj.perspective_plotter, 'vp_2_type', text="")

        box_col_props.separator()


        if int(camera_obj.perspective_plotter.vanishing_point_num) < 3:
            box_col_props_pp = box_col_props.column()
            box_col_props_pp.label(text="Principal Point:")
            box_col_props_pp.prop(camera_obj.perspective_plotter, 'principal_point_mode', text="")
            box_col_props.separator()
            if camera_obj.perspective_plotter.principal_point_mode == 'manual':
                box_col_props_row = box_col_props.split(factor=0.5)
                box_col_props_row_row = box_col_props_row.row(align=True)
                box_col_props_row_row.alignment = 'RIGHT'
                box_col_props_row_row.label(text="Shift X:")
                box_col_props_row_row = box_col_props_row.row(align=True)
                box_col_props_row_row.alignment = 'CENTER'
                box_col_props_row_row.label(text=str(round(camera_obj.data.shift_x, 3)) )

                box_col_props_row = box_col_props.split(factor=0.5)
                box_col_props_row_row = box_col_props_row.row(align=True)
                box_col_props_row_row.alignment = 'RIGHT'
                box_col_props_row_row.label(text="Y:")
                box_col_props_row_row = box_col_props_row.row(align=True)
                box_col_props_row_row.alignment = 'CENTER'
                box_col_props_row_row.label(text=str(round(camera_obj.data.shift_y, 3)) )
                
                box_col_props.separator()

        box_col_props.label(text="Target Location:")
        box_col_props.row(align=True).prop(camera_obj.perspective_plotter, 'camera_origin_mode', text="")
        if camera_obj.perspective_plotter.camera_origin_mode == 'manual':
            box_col_props.row(align=True).prop(camera_obj.perspective_plotter, 'camera_offset', text="")
            box_col_props.row(align=True).prop(camera_obj.perspective_plotter, 'camera_rotation', text="")

            box_col_props.operator('view3d.pp_set_target_origin')

        box_col_props.separator()



        box_col_props_row = box_col_props.split(factor=0.8)
        box_col_props_row.label(text="Freeze Guides: ")
        box_col_props_row.alignment="RIGHT"
        box_col_props_row2 = box_col_props_row.row()
        box_col_props_row2.alignment="RIGHT"
        box_col_props_row2.prop(camera_obj.perspective_plotter, 'disable_control_points', text="")

        box_col_props.separator()
        box_col_props.operator('view3d.pp_reset_defaults', text="Reset Defaults")
        box_col_props.separator()


class PERSPECTIVEPLOTTER_PT_Tools(Panel):
    bl_space_type = 'VIEW_3D'
    bl_label = 'Tools'
    bl_region_type = 'UI'
    bl_category = "P.Plotter"
    bl_idname = "PERSPECTIVEPLOTTER_PT_Tools"
    bl_parent_id = 'PERSPECTIVEPLOTTER_PT_GeneralPanel'
    # bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):

        layout = self.layout

        tools_col = layout.column()

        tools_col.operator('view3d.move_along_view', icon='VIEW3D', text="Move Along View")
        tools_col_match = tools_col.column()
        camera_obj = util.get_camera(context, context.region)
        match_text = "Match Background"
        if camera_obj:
            img = util.get_background_image(camera_obj)
            if img and not util.does_img_match(context, img):
                tools_col_match.alert = True
                match_text = "Background Unmatched"

        tools_col_match.operator('view3d.pp_match_resolution_to_bg_image', icon='IMAGE_PLANE', text=match_text)
        tools_col.operator('view3d.pp_flatten_horizon_line', text="Flatten Horizon Line", icon='NOCURVE')

class PERSPECTIVEPLOTTER_PT_Animation(Panel):
    bl_space_type = 'VIEW_3D'
    bl_label = 'Animation'
    bl_region_type = 'UI'
    bl_category = "P.Plotter"
    bl_idname = "PERSPECTIVEPLOTTER_PT_Animation"
    bl_parent_id = 'PERSPECTIVEPLOTTER_PT_GeneralPanel'
    # bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):

        layout = self.layout

        tools_col = layout.column()

        tools_col.operator('view3d.pp_set_keyframe', text="Set Keyframe", icon='KEYFRAME_HLT')
        tools_col.operator('view3d.pp_delete_keyframe', text="Delete Keyframe", icon='KEYFRAME')
        tools_col.operator('view3d.pp_delete_all_keyframes', text="Delete All Keyframes", icon='X')
        
class PERSPECTIVEPLOTTER_PT_About(Panel):
    bl_space_type = 'VIEW_3D'
    bl_label = 'Inspired by fSpy'
    bl_region_type = 'UI'
    bl_category = "P.Plotter"
    bl_idname = "PERSPECTIVEPLOTTER_PT_About"
    bl_parent_id = 'PERSPECTIVEPLOTTER_PT_GeneralPanel'
    # bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):

        layout = self.layout

        col = layout.column(align=True)

        wrapp = textwrap.TextWrapper(width=30)

        wList = wrapp.wrap(text="fSpy is a free standalone camera matching application which can be used with other 3D tools.") 

        msg_col = col.column(align=True)
        msg_col.alignment = 'CENTER'
        for text in wList: 
            msg_row = msg_col.row()
            msg_row.alignment = 'CENTER'
            msg_row.label(text=text)

        col.separator()
        props = col.operator("mesh.ppplot_open_help_url", text="Download fSpy")
        props.url = "https://fspy.io/"
        props.description = "Go to the fSpy tool website"


classes = [
    PERSPECTIVEPLOTTER_PT_GeneralPanel,
    PERSPECTIVEPLOTTER_PT_PlotterPanel,
    PERSPECTIVEPLOTTER_PT_Advanced,
    PERSPECTIVEPLOTTER_PT_Tools,
    PERSPECTIVEPLOTTER_PT_Animation,
    PERSPECTIVEPLOTTER_PT_About
    ]


def register():
    for cls in classes:
        register_class(cls)


def unregister():
    for cls in classes:
        unregister_class(cls)
