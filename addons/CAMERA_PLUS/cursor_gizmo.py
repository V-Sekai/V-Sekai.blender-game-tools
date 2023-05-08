import bpy
from bpy.types import GizmoGroup, Gizmo, Operator

import mathutils
from mathutils import Matrix, Vector
from math import radians

from bpy.props import IntProperty, FloatProperty

from .active_tool import cursor_gizmo_active



class GIZMO_GGT_3d_cursor(GizmoGroup):
    bl_idname = "gizmo.3d_cursor"
    bl_label = "Gizmo for 3d Cursor"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SHOW_MODAL_ALL'}



    @classmethod
    def poll(cls, context):
        return cursor_gizmo_active()
            
 
    def setup(self, context):
        # --- Move X
        arrow_x = self.gizmos.new("GIZMO_GT_arrow_3d")
        ar_x = arrow_x.target_set_operator("transform.translate")
        ar_x.cursor_transform = True
        ar_x.orient_type='GLOBAL'
        ar_x.constraint_axis = (True, False, False)
        ar_x.release_confirm = True
        arrow_x.line_width = 2
        arrow_x.color = 1.0, 0.1, 0.2
        arrow_x.alpha = 0.6
        arrow_x.color_highlight = 1.0, 0.5, 0.0
        arrow_x.alpha_highlight = 1.0
        arrow_x.scale_basis = 1.3
        arrow_x.use_draw_modal = True
        
        # --- Move Y
        arrow_y = self.gizmos.new("GIZMO_GT_arrow_3d")
        ar_y = arrow_y.target_set_operator("transform.translate")
        ar_y.cursor_transform = True
        ar_y.orient_type = 'GLOBAL'
        ar_y.constraint_axis = (False, True, False)
        ar_y.release_confirm = True

        arrow_y.color = 0.6, 1.0, 0.3
        arrow_y.alpha = 0.6
        arrow_y.color_highlight = 1.0, 0.5, 0.0
        arrow_y.alpha_highlight = 1.0
        arrow_y.scale_basis = 1.3
        arrow_y.use_draw_modal = True
         

        # --- Move Z
        arrow_z = self.gizmos.new("GIZMO_GT_arrow_3d")
        ar_z = arrow_z.target_set_operator("transform.translate")
        ar_z.cursor_transform = True
        ar_z.orient_type = 'GLOBAL'
        ar_z.constraint_axis = (False, False, True)
        ar_z.release_confirm = True
        arrow_z.line_width = 2
        arrow_z.color = 0.0, 0.4, 1.0
        arrow_z.alpha = 0.6
        arrow_z.color_highlight = 1.0, 0.5, 0.0
        arrow_z.alpha_highlight = 1.0
        arrow_z.scale_basis = 1.3
        arrow_z.use_draw_modal = True
        
        
        
        self.arrow_x = arrow_x
        self.arrow_y = arrow_y
        self.arrow_z = arrow_z

    
    def draw_prepare(self, context):  
        cursor = context.scene.cursor
        
        # --- This is rotate arrow
        orig_loc, orig_rot, orig_scale = cursor.matrix.decompose()
        orig_loc_mat = Matrix.Translation(orig_loc)
  
        x_rot_mat = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(90), 4, 'Y') #@ Matrix.Translation(vec)
        y_rot_mat = orig_rot.to_matrix().to_4x4() @ Matrix.Rotation(radians(-90), 4, 'X') 
  
        x_matrix = orig_loc_mat @ x_rot_mat 
        y_matrix = orig_loc_mat @ y_rot_mat 
        

        # --- Move
        arrow_x = self.arrow_x
        arrow_x.matrix_basis = x_matrix.normalized()
        
        arrow_y = self.arrow_y
        arrow_y.matrix_basis = y_matrix.normalized()
        
        arrow_z = self.arrow_z
        arrow_z.matrix_basis = cursor.matrix.normalized()

        del orig_scale


classes = [
    GIZMO_GGT_3d_cursor,    
]


def register():
    for c in classes:
        bpy.utils.register_class(c)     


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)