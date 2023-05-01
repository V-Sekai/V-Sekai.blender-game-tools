import bpy
from pathlib import Path
import tempfile

class RT_MT_DEMBONES_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    intermediate_files_default: Path = Path(__file__).resolve().parent / 'intermediate_files'
    log_default: Path = Path(__file__).resolve().parent / 'log'
    
    dbg: bpy.props.IntProperty(
        name="dbg",
        description="Debug level",
    )
    intermediate_files: bpy.props.StringProperty(
        name="intermediateFiles",
        description="Directory to store intermediate files: .abc, .fbx",
        subtype="FILE_PATH",
        default=f"{intermediate_files_default}",
    )
    log: bpy.props.StringProperty(
        name="log",
        description="Log file name",
        subtype="FILE_PATH",
        default=f"{log_default / 'blender_dembones.txt'}",
    )
    
    def draw(self, context):        
        layout = self.layout

        layout.prop(self, "dbg")
        layout.prop(self, "intermediate_files")
        layout.prop(self, "log")