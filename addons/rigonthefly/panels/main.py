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

def separator(layout, scale=1):
    # Add small separator
    row = layout.row(align=True)
    row.scale_y = scale
    row.label(text='')

# Main panel
class Panel(ToolPanel, bpy.types.Panel):
    bl_idname = 'VIEW3D_PT_rotf_v2'
    bl_label = 'Rig On The Fly 2'

    print("\n### ReceiverPanel ...")

    def draw(self, context):
        #print("\n### Draw ...")
        layout = self.layout
        layout.use_property_split = False

        col = layout.column()
