import bpy

#from ..core import animations
#from ..core import receiver as receiver_cls
from ..core.icon_manager import Icons
#from ..operators import receiver, recorder

row_scale = 0.75
paired_inputs = {}


# Initializes the Rig On The Fly panel in the toolbar
class ToolPanel(object):
    bl_label = 'RigOnTheFly 2'
    bl_idname = 'VIEW3D_PT_rotf'
    bl_category = 'RigOnTheFly 2'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def __init__(self):
        select()

def separator(layout, scale=1):
    # Add small separator
    row = layout.row(align=True)
    row.scale_y = scale
    row.label(text='')

def select():
    # function inspired by Alfonso Serra's Curve Tool's Object selection Order
    if bpy.context.mode == "POSE":
        selectionLength = len(bpy.context.selected_pose_bones)

        if selectionLength == 0:
            bpy.rotf_pose_bone_selection = []
        else:
            if selectionLength == 1:
                bpy.rotf_pose_bone_selection = []
                bpy.rotf_pose_bone_selection.append(bpy.context.selected_pose_bones[0])
            elif selectionLength > len(bpy.rotf_pose_bone_selection):
                for selectedPBone in bpy.context.selected_pose_bones:
                    if (selectedPBone in bpy.rotf_pose_bone_selection) == False:
                        bpy.rotf_pose_bone_selection.append(selectedPBone)

            elif selectionLength < len(bpy.rotf_pose_bone_selection):
                for pbone in bpy.rotf_pose_bone_selection:
                    if (pbone in bpy.context.selected_pose_bones) == False:
                        bpy.rotf_pose_bone_selection.remove(pbone)

# Main panel
class ReceiverPanel(ToolPanel, bpy.types.Panel):
    bl_idname = 'VIEW3D_PT_rotf_receiver_v2'
    bl_label = 'Rig On The Fly 2.0.0'

    print("\n### ReceiverPanel ...")

    def draw(self, context):
        #print("\n### Draw ...")
        layout = self.layout
        layout.use_property_split = False

        col = layout.column()

        # row = col.row(align=True)
        # row.label(text='FPS:')
        # row.enabled = not receiver.receiver_enabled
        # row.prop(context.scene, 'rsl_receiver_fps', text='')

        #row = col.row(align=True)
        #row.label(text='Scene Scale:')
