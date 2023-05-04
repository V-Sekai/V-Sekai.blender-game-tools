bl_info = {
    "name": "QOL Select Same Size",
    "author": "Rico Holmes",
    "version": (1, 00, 5),
    "blender": (3, 0, 0),
    "location": "View3D",
    "description": "Select all object with similar size",
    "warning": "",
    "wiki_url": "",
    "category": "Interface",
    }

from pydoc import describe
import bpy
from bpy.props import (FloatProperty,EnumProperty,BoolProperty)


# ---------------------------------------------------------------------------------------
def getDimensions(obj,sized):
    bb = obj.bound_box
    if not sized:
        bb_length = (round(bb[6][0]-bb[0][0],4),round(bb[6][1]-bb[0][1],4),round(bb[6][2]-bb[0][2],4))
    else:
        bb_length = (round(bb[6][0]-bb[0][0],4)*obj.scale[0],round(bb[6][1]-bb[0][1],4)*obj.scale[1],round(bb[6][2]-bb[0][2],4)*obj.scale[2])
    return bb_length
class QOL_OT_SelectSameSize(bpy.types.Operator):
    """Grab Same Size Objects"""
    bl_idname = "object.selectsamesize"
    bl_label = "QOL Select Same Size"
    bl_options = {'REGISTER', 'UNDO'}
    wiggleroom: FloatProperty(
    name = 'Wiggle room',
    default = 0.1,
    precision=4,
    min = 0,
    description = 'Boolean operation type',
    )
    size_select: EnumProperty(
        name = 'Size Select',
        items = [('LARGER','LARGER','LARGER'),('SMALLER','SMALLER','SMALLER'),('EQUAL','EQUAL','EQUAL')],
        default = 'EQUAL',
        description = 'Choose whether to select larger, smaller or equal objects',
    )
    with_scale: BoolProperty(
        name = 'With Scale Applied',
        default = True,
        description = 'Use applied scale when comparing size',
        )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == "MESH"
        # return context.active_object.type == "MESH"

    def execute(self, context):
        obj = context.active_object
        if self.with_scale:
            act_objSize = getDimensions(obj,True)
        else:
            act_objSize = getDimensions(obj,False)

        foundObjects = []
        w = self.wiggleroom

        for obj in bpy.context.view_layer.objects:
            if obj.type =="MESH":
                if self.with_scale:
                    objSize = getDimensions(obj,True)
                else:
                    objSize = getDimensions(obj,False)
                #compare difference in objSize and act_objSize and if less than wiggleroom then add to foundObjects
                if (abs(objSize[0]-act_objSize[0])<w) and (abs(objSize[1]-act_objSize[1])<w) and (abs(objSize[2]-act_objSize[2])<w):
                    foundObjects.append(obj)

        #compare obj in foundObjects and select only those that are smaller than act_objSize
        if self.size_select == 'SMALLER':
            for obj in foundObjects:
                if self.with_scale:
                    objSize = getDimensions(obj,True)
                else: 
                    objSize = getDimensions(obj,False)
                if objSize[0]<=act_objSize[0] and objSize[1]<=act_objSize[1] and objSize[2]<=act_objSize[2]:
                    obj.select_set(True)
        #compare obj in foundObjects and select only those that are larger than act_objSize
        if self.size_select == 'LARGER':
            for obj in foundObjects:
                found = 0
                if self.with_scale:
                    objSize = getDimensions(obj,True)
                else:
                    objSize = getDimensions(obj,False)
                if objSize[0]>=act_objSize[0]:
                    found += 1
                if objSize[1]>=act_objSize[1]:
                    found += 1
                if objSize[2]>=act_objSize[2]:
                    found += 1
                if found == 3:
                    obj.select_set(True)
        if self.size_select == 'EQUAL':
            for obj in foundObjects:
                obj.select_set(True)
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(QOL_OT_SelectSameSize.bl_idname, text=QOL_OT_SelectSameSize.bl_label)
def register():
    bpy.utils.register_class(QOL_OT_SelectSameSize)
    bpy.types.VIEW3D_MT_select_object.append(menu_func)
def unregister():
    bpy.utils.unregister_class(QOL_OT_SelectSameSize)
    bpy.types.VIEW3D_MT_select_object.remove(menu_func)

if __name__ == "__main__":
    register()

