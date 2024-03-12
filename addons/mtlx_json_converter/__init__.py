bl_info = {
    "name": "MaterialX JSON Converter",
    "author": "K. S. Ernest (iFire) Lee",
    "version": (1, 0),
    "blender": (4, 00, 0),
    "location": "View3D > Tool Shelf > My Panel",
    "description": "Converts MaterialX files to JSON and vice versa",
    "category": "Development",
}

import bpy
from .mtlx_json_converter import mtlx_to_json, json_to_mtlx

class FilePathProps(bpy.types.PropertyGroup):
    input_filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    output_filepath: bpy.props.StringProperty(subtype="FILE_PATH")

class MTLX_OT_Converter(bpy.types.Operator):
    bl_idname = "object.convert_mtlx"
    bl_label = "Convert MaterialX/JSON"
    bl_options = {'REGISTER', 'UNDO'}

    files: bpy.props.PointerProperty(type=FilePathProps)
    filter_glob: bpy.props.StringProperty(default="*.mtlx;*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        files = context.scene.files

        if files.input_filepath == "":
            self.report({'ERROR'}, "No input file selected")
            return {'CANCELLED'}

        if files.output_filepath == "":
            self.report({'ERROR'}, "No output file selected")
            return {'CANCELLED'}

        if files.input_filepath.endswith('.mtlx'):
            json_output = mtlx_to_json(files.input_filepath)
            with open(files.output_filepath, 'w') as f:
                f.write(json_output)
        elif files.input_filepath.endswith('.json'):
            mtlx_output = json_to_mtlx(files.input_filepath)
            with open(files.output_filepath, 'w') as f:
                f.write(mtlx_output)

        return {'FINISHED'}


class MTLX_PT_Panel(bpy.types.Panel):
    bl_label = "MaterialX JSON Converter"
    bl_idname = "OBJECT_PT_my_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout

        operator = layout.operator("object.convert_mtlx")

        col = layout.column(align=True)
        col.prop(context.scene.files, "input_filepath", text="Input File")
        col.prop(context.scene.files, "output_filepath", text="Output File")

def register():
    bpy.utils.register_class(FilePathProps)
    bpy.types.Scene.files = bpy.props.PointerProperty(type=FilePathProps)
    bpy.utils.register_class(MTLX_OT_Converter)
    bpy.utils.register_class(MTLX_PT_Panel)

def unregister():
    bpy.utils.unregister_class(MTLX_OT_Converter)
    bpy.utils.unregister_class(MTLX_PT_Panel)
    del bpy.types.Scene.files
    
if __name__ == "__main__":
    register()