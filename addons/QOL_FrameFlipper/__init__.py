bl_info = {
    "name": "QOL Frame Flipper",
    "blender": (3, 0, 0),
    "category": "Interface",
    "author": "Rico Holmes",
    "version": (1, 2, 1),
    "description": "Flip between two frames",
    "category": "Interface",
}

import bpy
from bpy.props import IntProperty

def lazySetFrames(self, context, mode=0):
    active_object = bpy.context.active_object
    active_object_animation_data = active_object.animation_data
    active_object_animation_data_action = active_object_animation_data.action
    active_object_animation_data_action_fcurves = active_object_animation_data_action.fcurves

    #get a list of the selected keyframes
    selected_keyframes = []
    for fcurve in active_object_animation_data_action_fcurves:
        for keyframe in fcurve.keyframe_points:
            if keyframe.select_control_point:
                selected_keyframes.append(keyframe.co[0])
    
    #check if there are any *selected* keyframes
    if len(selected_keyframes) != 0:
        first_selected_keyframe = min(selected_keyframes)
        last_selected_keyframe = max(selected_keyframes)
    else:
        if len (active_object_animation_data_action.frame_range) == 0:
            return
        first_selected_keyframe = active_object_animation_data_action.frame_range[0]
        if len (active_object_animation_data_action.frame_range) == 1:
            last_selected_keyframe = active_object_animation_data_action.frame_range[0]
        else:
            last_selected_keyframe = active_object_animation_data_action.frame_range[1]

    #set the frame A and frame B
    if mode == 0:
        bpy.context.scene.FFSets.frame_A = int(first_selected_keyframe)
    if mode == 1:
        bpy.context.scene.FFSets.frame_B = int(last_selected_keyframe)
    if mode == 2:
        bpy.context.scene.FFSets.frame_A = int(first_selected_keyframe)
        bpy.context.scene.FFSets.frame_B = int(last_selected_keyframe)



class MySettings(bpy.types.PropertyGroup):
    frame_A : bpy.props.IntProperty(name="QOL FF frame_A",default=0)
    frame_B : bpy.props.IntProperty(name="QOL FF frame_B",default=250)
    frame_C : bpy.props.IntProperty(name="QOL FF frame_C",default=0)

class QOL_FrameFlip(bpy.types.Operator):
    """Flips between frame A and B"""
    bl_idname = "wm.frame_flip"
    bl_label = "operator to flip between frames"

    def invoke(self, context, event):
        if event.alt:
            lazySetFrames(self, context,2)
        return self.execute(context)

    def execute(self, context):
        FFSets = context.scene.FFSets
        current_frame = context.scene.frame_current
        if FFSets.frame_C == FFSets.frame_A:
            FFSets.frame_C = FFSets.frame_B
        else:
            FFSets.frame_C = FFSets.frame_A
        bpy.context.scene.frame_set(FFSets.frame_C)
        return {'FINISHED'}

class QOL_FFSet_A(bpy.types.Operator):
    """Sets A key to current frame"""
    bl_idname = "wm.frame_seta"
    bl_label = "A"

    def invoke(self, context, event):
        if event.alt:
            lazySetFrames(self, context,0)
            return {'FINISHED'}
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        scene.FFSets.frame_A = scene.frame_current
        return {'FINISHED'}

class QOL_FFSet_B(bpy.types.Operator):
    """Sets B key to current frame"""
    bl_idname = "wm.frame_setb"
    bl_label = "B"

    def invoke(self, context, event):
        if event.alt:
            lazySetFrames(self, context,1)
            return {'FINISHED'}
        return self.execute(context)
    def execute(self, context):
        scene = context.scene
        scene.FFSets.frame_B = scene.frame_current
        return {'FINISHED'}

def draw(self, context):
    scene = context.scene
    layout = self.layout
    box = layout.box()
    grid = box.grid_flow(row_major=True, columns=5, even_columns=True, even_rows=True, align=True)
    grid.scale_x = 0.85
    grid.operator("wm.frame_seta", text="A")
    grid.prop(scene.FFSets, "frame_A", text="")
    grid.operator("wm.frame_flip", text="FLIP")
    grid.prop(scene.FFSets, "frame_B", text="")
    grid.operator("wm.frame_setb", text="B")

classes = [
MySettings,
QOL_FrameFlip,
QOL_FFSet_A,
QOL_FFSet_B,
]

def register():
    for c in classes:   bpy.utils.register_class(c)
    bpy.types.Scene.FFSets = bpy.props.PointerProperty(type=MySettings)
    bpy.types.GRAPH_HT_header.prepend(draw)
    bpy.types.DOPESHEET_HT_header.prepend(draw)

def unregister():
    for c in classes:   bpy.utils.unregister_class(c)
    bpy.types.GRAPH_HT_header.remove(draw)
    bpy.types.DOPESHEET_HT_header.remove(draw)

if __name__ == "__main__":
    register()