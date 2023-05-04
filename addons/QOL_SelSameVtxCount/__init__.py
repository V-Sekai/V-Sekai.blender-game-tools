bl_info = {
    "name": "QOL Select with same vertex count",
    "blender": (3, 0, 0),
    "category": "Interface",
    "author": "Rico Holmes",
    "version": (1, 0, 2),
    "description": "Select all objects with same vertex count",
    "category": "Interface",
}

import bpy
from bpy.props import (
    IntProperty,
    )

def main(wiggleroom,context):
    vCount=0
    allSelectedObjects = bpy.context.selected_objects
    if len(allSelectedObjects):
        obj =  bpy.context.active_object
        if obj.type in {"MESH"}:
            vCount = len(obj.data.vertices)

    for obj in bpy.context.view_layer.objects:
        if obj.type in {"MESH"}:
            objVCount = len(obj.data.vertices)
            difference = abs(objVCount - vCount)
            if difference <= wiggleroom:
                obj.select_set(True)

class RHSelSameVtxCnt(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.selsamevtx"
    bl_label = "QOL Same vertex count"
    bl_options = {'REGISTER', 'UNDO'}

    wiggleroom: IntProperty(
        name = 'Wiggle room',
        min = 0,
        )
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    def execute(self, context):
        main(self.wiggleroom,context)
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(RHSelSameVtxCnt.bl_idname, text=RHSelSameVtxCnt.bl_label)

def register():
    bpy.utils.register_class(RHSelSameVtxCnt)
    bpy.types.VIEW3D_MT_select_object.append(menu_func)

def unregister():
    bpy.utils.unregister_class(RHSelSameVtxCnt)
    bpy.types.VIEW3D_MT_select_object.remove(menu_func)



if __name__ == "__main__":
    register()
