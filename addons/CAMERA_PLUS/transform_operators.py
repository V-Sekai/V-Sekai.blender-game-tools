import bpy
import blf
from bpy.types import Operator
from mathutils import Vector, Matrix
from bpy.props import EnumProperty



class CAMGIZ_OT_orbit(Operator):
    bl_idname = "camgiz.orbit"
    bl_label = "Orbit Rotate"
    bl_options = {'REGISTER', 'UNDO'}

    __slots__ = (
        "axis_orient",
        )

    axis: EnumProperty(
        name='Axis',
        description='Axis',
        items=[
            ('GLOBAL', 'Global', '', '', 0),
            ('CURSOR', 'Cursor', '', '', 1)],
            default='GLOBAL',
            )
            

    def modal(self, context, event):
        user_orient = bpy.context.scene.tool_settings.transform_pivot_point
        if event.value != 'RELEASE': #event.pressure > props.pressure: #
            bpy.context.scene.tool_settings.transform_pivot_point = 'CURSOR'
            bpy.ops.transform.rotate('INVOKE_DEFAULT',constraint_axis=(False, False, True),orient_type=self.axis_orient, release_confirm = True)
            bpy.context.scene.tool_settings.transform_pivot_point = user_orient
            return {'FINISHED'}

        return {'FINISHED'}


    def invoke(self, context, event):
        if self.axis == 'GLOBAL':
            self.axis_orient = 'GLOBAL'
        else: # self.axis == 'CURSOR':
            self.axis_orient = 'CURSOR'
        context.window_manager.modal_handler_add(self)
        return{'RUNNING_MODAL'}



######################################################################################################################################
target_obj = None



class CAMGIZ_OT_target_object(Operator):
    bl_idname = "camgiz.target_object"
    bl_label = "Add"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        global target_obj
        target_obj = context.active_object
        return {'FINISHED'}



class CAMGIZ_OT_del_target(Operator):
    bl_idname = "camgiz.del_target"
    bl_label = "Remove"
    bl_options = {'REGISTER', 'UNDO'}

    
    def execute(self, context):
        global target_obj
        target_obj = None
        return {'FINISHED'} 




# --- TRACK TO
def get_camera():
    camera = bpy.context.active_object
    return camera




class CAMGIZ_OT_track_to(Operator):
    bl_idname = "camgiz.track_to"
    bl_label = "Camera Track To"
    #bl_options = {"REGISTER","UNDO"}

    

    def __init__(self):
        self._timer = None
        self.camera = None
  

    def modal(self, context, event):
        #print('Modal')
        global target_obj
        props = context.preferences.addons[__package__.split(".")[0]].preferences
        
        if event.ctrl and event.type == 'Z':
            props.target_visible = False
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            return {'FINISHED'}

        if props.target_visible:
            if event.type == 'TIMER':
                if target_obj == None:
                    target_vec = context.scene.cursor.location
                else:
                    target_vec = target_obj.location 

                
                obj_vec = self.camera.location
                view_vec = obj_vec - target_vec 
                new_quat = view_vec.to_track_quat('Z', 'Y')

                rotation_mode = context.object.rotation_mode
                if rotation_mode == 'QUATERNION':
                    self.camera.rotation_quaternion = new_quat

                elif rotation_mode in ['XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX']:
                    self.camera.rotation_euler = new_quat.to_euler(rotation_mode)

                elif rotation_mode == 'AXIS_ANGLE':
                    ax_ang = new_quat.to_axis_angle()
                    ax_ang_f = (ax_ang[1], ax_ang[0][0], ax_ang[0][1], ax_ang[0][2])
                    self.camera.rotation_axis_angle = ax_ang_f

        else:
            props.target_visible = False
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            return {'FINISHED'}

        """ if self.undo:
            bpy.ops.ed.undo_push()
            self.undo = False """
        return {'PASS_THROUGH'}


    def invoke(self, context, event):
        #print('Invoke')
        #bpy.ops.ed.undo_push()
        self.camera = get_camera()
        self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
        context.window_manager.modal_handler_add(self)
        return{'RUNNING_MODAL'}







class CAMGIZ_OT_trackball_two(Operator):
    bl_idname = "camgiz.trackball_two"
    bl_label = "Trackball"
    bl_options = {'REGISTER', 'UNDO'}
  
    def modal(self, context, event):
        user_lock = bpy.context.object.lock_rotation[1] 

        if event.value != 'RELEASE': 
            bpy.context.object.lock_rotation[1] = True
            bpy.ops.transform.trackball('INVOKE_DEFAULT', release_confirm = True)
            bpy.context.object.lock_rotation[1] = user_lock
            return {'FINISHED'}

        return {'FINISHED'}


    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return{'RUNNING_MODAL'}



class CAMGIZ_OT_resetrotation(Operator):
    bl_idname = "camgiz.resetrotation"
    bl_label = "Reset Rotation 3d Cursor"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        bpy.context.scene.cursor.rotation_euler[0] = 0.0
        bpy.context.scene.cursor.rotation_euler[1] = 0.0
        bpy.context.scene.cursor.rotation_euler[2] = 0.0
        return {'FINISHED'} 



classes = [
    CAMGIZ_OT_orbit,

    CAMGIZ_OT_target_object,
    CAMGIZ_OT_del_target,
    
    CAMGIZ_OT_track_to,

    CAMGIZ_OT_trackball_two,
    CAMGIZ_OT_resetrotation,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)