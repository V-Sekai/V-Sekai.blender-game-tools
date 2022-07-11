import bpy

from .main import ToolPanel, separator
#from ..operators import info
from ..core.icon_manager import Icons


class RigStatePanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_rigState'
    bl_label = 'Rig State'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        row = layout.row(align=True)
        row.operator('rotf.save_rig_state', text="Save")
        
        row.operator('rotf.load_file_path', text="Folder Path")

        row = layout.row(align=True)
        row.label(text='Load from: ' + scene.rotf_folder_name)
        
        row = layout.row(align=True) 
        row.prop(context.scene, "rotf_bake_on_load", text="Bake on Load")
        row.operator('rotf.bake_rig', text="Bake Rig")

        col = layout.column(align=False)
        for item in context.scene.rotf_state_collection:
            loadRigStateOperator = col.operator('rotf.load_rig_state', text=item.filename)
            loadRigStateOperator.filename = item.filename
            