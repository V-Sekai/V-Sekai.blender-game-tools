bl_info = {
    "name": "QOL Smart Smooth",
    "blender": (3, 0, 0),
    "category": "Interface",
    "author": "Rico Holmes",
    "version": (1, 0, 1),
    "description": "Simple smooth op",
    "category": "Interface",
}

import bpy,math
from bpy.props import (IntProperty,FloatProperty,BoolProperty)

class QOLSmartSmooth(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.qolsmartsmooth"
    bl_label = "QOL Smart Smooth"
    bl_options = {'REGISTER', 'UNDO'}

    smoothAngle: FloatProperty(
            name = 'Smooth Angle',
            default = 30,
            min = 0,
            max = 360,
            description = 'Degree for Auto-Smooth',
            )
    #add boolean property fixCustomSplit
    fixCustomSplit: BoolProperty(
            name = "Fix Custom Split",
            default = True,)
    #add boolean property setToFaces
    setToFaces: BoolProperty(
            name = "Set To Faces",
            default = False,)

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        #self.smooth angle to radians
        # self.smoothAngle = math.radians(self.smoothAngle)
        act_obj = context.active_object
        for obj in context.selected_objects:
            if obj.type in {"MESH"}:
                #set active object to obj
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)
                if self.setToFaces:
                    print("Setting To Faces")
                    #obj to edit mode
                    bpy.ops.object.mode_set(mode='EDIT')
                    #select all faces
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.set_normals_from_faces()
                    #obj to object mode
                    bpy.ops.object.mode_set(mode='OBJECT')
             
                #set object to smooth shading
                bpy.ops.object.shade_smooth()
                #set smooth angle to self.smoothAngle
                if self.fixCustomSplit:
                    print("Fixing Custom Split")
                    bpy.ops.mesh.customdata_custom_splitnormals_clear()
                print(self.smoothAngle)                
                bpy.context.object.data.auto_smooth_angle = math.radians(self.smoothAngle)
                
                bpy.context.object.data.use_auto_smooth = True

        context.view_layer.objects.active = act_obj
        return {'FINISHED'}

def draw(self, context):
    self.layout.operator("object.qolsmartsmooth", text="QOL Smart Smooth")

def register():
    bpy.utils.register_class(QOLSmartSmooth)
    bpy.types.VIEW3D_MT_object_context_menu.prepend(draw)

def unregister():
    bpy.utils.unregister_class(QOLSmartSmooth)
    bpy.types.VIEW3D_MT_object_context_menu.remove(draw)



if __name__ == "__main__":
    register()
