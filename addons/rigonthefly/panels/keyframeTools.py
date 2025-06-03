import bpy

from .main import ToolPanel, separator
from ..core.icon_manager import Icons

class KeyframeToolsPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_keyframeTools'
    bl_label = 'Keyframe Tools'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        selectedObjects = bpy.context.selected_objects
        selectedPBones = bpy.context.selected_pose_bones

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(scene, "rotf_key_available", text="Available Only")
        row.prop(scene, "rotf_key_location", text="Location")

        row = col.row(align=True)
        row.prop(scene, "rotf_key_rotation", text="Rotation")
        row.prop(scene, "rotf_key_scale", text="Scale")

        row = col.row(align=True)
        row.operator('rotf.key_range', text="Key Range", icon='KEYFRAME_HLT')
        row.prop(scene, "rotf_frame_range_step", text="Step")

        row = col.row(align=True)
        row.prop(scene, "rotf_frame_range_start", text="Start")
        row.prop(scene, "rotf_frame_range_end", text="End")

        row = col.row(align=True)
        row.operator('rotf.key_as_active', text="Key as Active", icon='KEYFRAME')
        row.prop(scene, "rotf_selected_keys", text="Use Selection")

        

        row = layout.row(align=True)
        row.operator('rotf.offset_keys', text="Offset Keys", icon='NEXT_KEYFRAME')
        row.prop(scene, "rotf_offset_keys_factor", text="Offset")

        

