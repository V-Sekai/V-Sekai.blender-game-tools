import bpy
import bmesh  
import mathutils 
from bpy.types import GizmoGroup
from mathutils import Matrix, Vector
from math import radians
from .active_tool import cam_gizmo_active



class GIZMO_GGT_camera_tool(GizmoGroup):
    bl_idname = "gizmo.camera_tool"
    bl_label = "Gizmo Camera"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D','PERSISTENT','SHOW_MODAL_ALL'} #'DEPTH_3D' , 'TOOL_INIT', 'SELECT', , 'SCALE'


    @classmethod
    def poll(cls, context):
        return cam_gizmo_active()
     

    def setup(self, context):
        ### translate
       
        tilt = self.gizmos.new("GIZMO_GT_dial_3d")
        tilt_op = tilt.target_set_operator("transform.rotate")
        tilt_op.constraint_axis=(True, False, False)
        tilt_op.orient_type = 'LOCAL'
        tilt.line_width = 3
        tilt.color = 1.0, 0.1, 0.2
        tilt.alpha = 0.6
        tilt.color_highlight = 1.0, 0.5, 0.0
        tilt.alpha_highlight = 1.0
        tilt.scale_basis = 1.3
        tilt.use_draw_modal = True
        
        roll = self.gizmos.new("GIZMO_GT_dial_3d")
        roll_op = roll.target_set_operator("transform.rotate")
        roll_op.constraint_axis=(False, False, True)
        roll_op.orient_type = 'LOCAL'
        roll.line_width = 3
        roll.color = 0.6, 1.0, 0.3
        roll.alpha = 0.6
        roll.color_highlight = 1.0, 0.5, 0.0
        roll.alpha_highlight = 1.0
        roll.scale_basis = 1.0
        roll.use_draw_modal = True

        pan = self.gizmos.new("GIZMO_GT_dial_3d")
        pan_op = pan.target_set_operator("transform.rotate")
        pan_op.constraint_axis=(False, False, True)
        pan_op.orient_type = 'GLOBAL'
        pan.line_width = 4
        pan.color = 0.0, 0.4, 1.0
        pan.alpha = 0.6
        pan.color_highlight = 1.0, 0.5, 0.0
        pan.alpha_highlight = 1.0
        pan.scale_basis = 1.6
        pan.use_draw_modal = True

        ### CURSOR ORBIT ------------------------------------------------------------
        orbit = self.gizmos.new("GIZMO_GT_dial_3d")
        orbit_op = orbit.target_set_operator("camgiz.orbit")
        orbit_op.axis = 'CURSOR'
        orbit.line_width = 4
        orbit.color = 0.0, 0.4, 1.0
        orbit.alpha = 0.6
        orbit.color_highlight = 1.0, 0.5, 0.0
        orbit.alpha_highlight = 1.0
        orbit.scale_basis = 1.6
        orbit.use_draw_modal = True


        dial_cursor = self.gizmos.new("GIZMO_GT_move_3d")
        dial_cursor.draw_options = {"ALIGN_VIEW"}
        dial_cursor.line_width = 2.0
        dial_cursor.color = 1.0, 0.5, 0.0
        dial_cursor.scale_basis = 0.2

        but_cursor = self.gizmos.new("GIZMO_GT_button_2d")
        but_cursor_op = but_cursor.target_set_operator("transform.translate")
        but_cursor_op.cursor_transform = True
        but_cursor.icon = 'BLANK1'
        but_cursor.draw_options = {'BACKDROP', 'OUTLINE'}
        but_cursor.show_drag = True
        but_cursor.alpha = 0.0
        but_cursor.alpha_highlight = 0.1
        but_cursor.scale_basis = 0.2

        ### TRANSLATE ------------------------------------------------------------

        self.tilt = tilt
        self.roll = roll
        self.pan = pan

        self.orbit = orbit
        self.dial_cursor = dial_cursor
        self.but_cursor = but_cursor



    def draw_prepare(self, context):
        #props = context.preferences.addons[__package__.split(".")[0]].preferences
    
        #-------------------------------ORIENTATIONS-------------------------------------------------------------------------------------------------------------------------------------
        ob = context.object.matrix_world
        orient_slots = context.window.scene.transform_orientation_slots[0].type
        orig_loc, orig_rot, orig_scale = ob.decompose() 

        ### GLOBAL
        orig_loc_mat = Matrix.Translation(orig_loc)
            
        orig_scale_mat = Matrix.Scale(orig_scale[0], 4, (1, 0, 0)) @ Matrix.Scale(orig_scale[1], 4, (0, 1, 0)) @ Matrix.Scale(orig_scale[2], 4, (0, 0, 1))
        
        x_rot_mat = Matrix.Rotation(radians(90), 4, 'Y') 
        y_rot_mat = Matrix.Rotation(radians(-90), 4, 'X') 
        z_rot_mat =  Matrix.Rotation(radians(-90), 4, 'Z') 

        x_rot_mat_dial = Matrix.Rotation(radians(-90), 4, 'Y')  
        y_rot_mat_dial = Matrix.Rotation(radians(90), 4, 'X')  
        z_rot_mat_dial = Matrix.Rotation(radians(0), 4, 'Z') 

        x_matrix_world_g = orig_loc_mat @ x_rot_mat @ orig_scale_mat  
        y_matrix_world_g = orig_loc_mat @ y_rot_mat @ orig_scale_mat  
        z_matrix_world_g = orig_loc_mat @ z_rot_mat @ orig_scale_mat 
        
        x_matrix_world_dial_g = orig_loc_mat @ x_rot_mat_dial @ orig_scale_mat 
        y_matrix_world_dial_g = orig_loc_mat @ y_rot_mat_dial @ orig_scale_mat  
        z_matrix_world_dial_g = orig_loc_mat @ z_rot_mat_dial @ orig_scale_mat 
        ### LOCAL
        orig_loc_mat = Matrix.Translation(orig_loc)
        orig_scale_mat = Matrix.Scale(orig_scale[0], 4, (1, 0, 0)) @ Matrix.Scale(orig_scale[1], 4, (0, 1, 0)) @ Matrix.Scale(orig_scale[2], 4, (0, 0, 1))
        
        x_rot_mat = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(90), 4, 'Y') 
        y_rot_mat = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(-90), 4, 'X') 
        z_rot_mat = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(-90), 4, 'Z') 

        x_rot_mat_dial = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(-90), 4, 'Y')  
        y_rot_mat_dial = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(90), 4, 'X')  
        z_rot_mat_dial = orig_rot.to_matrix().to_4x4() 
            
        #-------------NEW MATRIX WORLD
        x_matrix_world = orig_loc_mat @ x_rot_mat @ orig_scale_mat  
        y_matrix_world = orig_loc_mat @ y_rot_mat @ orig_scale_mat  
        z_matrix_world = orig_loc_mat @ z_rot_mat @ orig_scale_mat 
        
        x_matrix_world_dial = orig_loc_mat @ x_rot_mat_dial @ orig_scale_mat 
        y_matrix_world_dial = orig_loc_mat @ y_rot_mat_dial @ orig_scale_mat  
        z_matrix_world_dial = orig_loc_mat @ z_rot_mat_dial @ orig_scale_mat 

        ### CURSOR
        cursor = context.scene.cursor
        orig_loc, orig_rot, orig_scale = cursor.matrix.decompose()
        orig_loc_mat = Matrix.Translation(orig_loc)
        x_rot_mat = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(90), 4, 'Y')
        y_rot_mat = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(-90), 4, 'X') 
        x_matrix = orig_loc_mat @ x_rot_mat 
        y_matrix = orig_loc_mat @ y_rot_mat 


        ### translate
        tilt = self.tilt
        tilt.matrix_basis = x_matrix_world_dial.normalized()

        roll = self.roll
        roll.matrix_basis = z_matrix_world.normalized()

        pan = self.pan
        pan.matrix_basis = z_matrix_world_dial_g.normalized()


        orbit = self.orbit
        orbit.matrix_basis = cursor.matrix.normalized()

        dial_cursor = self.dial_cursor 
        dial_cursor.matrix_basis = cursor.matrix.normalized()
        but_cursor = self.but_cursor 
        but_cursor.matrix_basis = cursor.matrix.normalized()


""" class GIZMO_GGT_camera_target(GizmoGroup):
    bl_idname = "gizmo.camera_target"
    bl_label = "Gizmo Camera"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D','PERSISTENT','SHOW_MODAL_ALL'} #'DEPTH_3D' , 'TOOL_INIT', 'SELECT', , 'SCALE'

    @classmethod
    def poll(cls, context):
        props = context.preferences.addons[__package__.split(".")[0]].preferences
        if props.target_visible == True:
            if active_tool().idname == "tool.gizmo_camera": 
                if context.active_object != None:  
                    if context.active_object.select_get():
                        if context.space_data.show_gizmo == True:
                            if context.space_data.overlay.show_overlays == True:
                                ob = context.object
                                return ob and ob.type == 'CAMERA'
     
    def setup(self, context):
        cam = context.object
        orig_loc, orig_rot, orig_scale = cam.matrix_world.decompose()
        orig_loc_mat = Matrix.Translation(orig_loc)
        matrix = orig_loc_mat 
        del orig_rot
        del orig_scale


        dial_target = self.gizmos.new("GIZMO_GT_move_3d")
        dial_target.draw_options = {"ALIGN_VIEW"}
        dial_target.line_width = 2.0
        dial_target.color = 1.0, 0.5, 0.0
        dial_target.scale_basis = 0.2
        dial_target.matrix_basis = matrix.normalized()


        but_target = self.gizmos.new("GIZMO_GT_button_2d")
        but_target_op = but_target.target_set_operator("transform.translate")
        but_target_op.cursor_transform = True
        but_target.icon = 'BLANK1'
        but_target.draw_options = {'BACKDROP', 'OUTLINE'}
        but_target.show_drag = True
        but_target.alpha = 0.0
        but_target.alpha_highlight = 0.1
        but_target.scale_basis = 0.2
        but_target.matrix_basis = matrix.normalized()


        self.dial_target = dial_target
        self.but_target = but_target
    def draw_prepare(self, context):
        #props = context.preferences.addons[__package__.split(".")[0]].preferences
    
        #-------------------------------ORIENTATIONS-------------------------------------------------------------------------------------------------------------------------------------
        ob = context.object.matrix_world
        orient_slots = context.window.scene.transform_orientation_slots[0].type
        orig_loc, orig_rot, orig_scale = ob.decompose() 

        ### GLOBAL
        orig_loc_mat = Matrix.Translation(orig_loc)
            
        orig_scale_mat = Matrix.Scale(orig_scale[0], 4, (1, 0, 0)) @ Matrix.Scale(orig_scale[1], 4, (0, 1, 0)) @ Matrix.Scale(orig_scale[2], 4, (0, 0, 1))
        
        x_rot_mat = Matrix.Rotation(radians(90), 4, 'Y') 
        y_rot_mat = Matrix.Rotation(radians(-90), 4, 'X') 
        z_rot_mat =  Matrix.Rotation(radians(-90), 4, 'Z') 

        x_rot_mat_dial = Matrix.Rotation(radians(-90), 4, 'Y')  
        y_rot_mat_dial = Matrix.Rotation(radians(90), 4, 'X')  
        z_rot_mat_dial = Matrix.Rotation(radians(0), 4, 'Z') 

        x_matrix_world_g = orig_loc_mat @ x_rot_mat @ orig_scale_mat  
        y_matrix_world_g = orig_loc_mat @ y_rot_mat @ orig_scale_mat  
        z_matrix_world_g = orig_loc_mat @ z_rot_mat @ orig_scale_mat 
        
        x_matrix_world_dial_g = orig_loc_mat @ x_rot_mat_dial @ orig_scale_mat 
        y_matrix_world_dial_g = orig_loc_mat @ y_rot_mat_dial @ orig_scale_mat  
        z_matrix_world_dial_g = orig_loc_mat @ z_rot_mat_dial @ orig_scale_mat 
        ### LOCAL
        orig_loc_mat = Matrix.Translation(orig_loc)
        orig_scale_mat = Matrix.Scale(orig_scale[0], 4, (1, 0, 0)) @ Matrix.Scale(orig_scale[1], 4, (0, 1, 0)) @ Matrix.Scale(orig_scale[2], 4, (0, 0, 1))
        
        x_rot_mat = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(90), 4, 'Y') 
        y_rot_mat = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(-90), 4, 'X') 
        z_rot_mat = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(-90), 4, 'Z') 

        x_rot_mat_dial = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(-90), 4, 'Y')  
        y_rot_mat_dial = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(90), 4, 'X')  
        z_rot_mat_dial = orig_rot.to_matrix().to_4x4() 
            
        #-------------NEW MATRIX WORLD
        x_matrix_world = orig_loc_mat @ x_rot_mat @ orig_scale_mat  
        y_matrix_world = orig_loc_mat @ y_rot_mat @ orig_scale_mat  
        z_matrix_world = orig_loc_mat @ z_rot_mat @ orig_scale_mat 
        
        x_matrix_world_dial = orig_loc_mat @ x_rot_mat_dial @ orig_scale_mat 
        y_matrix_world_dial = orig_loc_mat @ y_rot_mat_dial @ orig_scale_mat  
        z_matrix_world_dial = orig_loc_mat @ z_rot_mat_dial @ orig_scale_mat 

        ### CURSOR
        cursor = context.scene.cursor
        orig_loc, orig_rot, orig_scale = cursor.matrix.decompose()
        orig_loc_mat = Matrix.Translation(orig_loc)
        x_rot_mat = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(90), 4, 'Y')
        y_rot_mat = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(-90), 4, 'X') 
        x_matrix = orig_loc_mat @ x_rot_mat 
        y_matrix = orig_loc_mat @ y_rot_mat 


        dial_target = self.dial_target
        dial_target.matrix_basis = z_matrix_world_dial.normalized()
        but_target = self.but_target 
        but_target.matrix_basis = z_matrix_world_dial.normalized() """



classes = [
    GIZMO_GGT_camera_tool,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

        
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)