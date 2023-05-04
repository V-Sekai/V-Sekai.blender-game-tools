bl_info = {
    "name": "QOL Ground objects",
    "author": "Rico Holmes",
    "blender": (3, 2, 0),
    "category": "Interface",
    "version": (1,2,1),
    "warning": "",
    "wiki_url": "",}

import bpy
from bpy.props import EnumProperty
from mathutils import Vector
from .prefs import *


def sendtoGround(MoveType,WhereTo,SitOrSwim,PivotPlace,context):
    originalSelection = context.selected_objects
    TargetObjects = []
    objBounds={"minX":0,"maxX":0,"minY":0,"maxY":0,"minZ":0,"maxZ":0,}
    objBoundsGrp={
    "minAll_X":999999999,"maxAll_X":-999999999,
    "minAll_Y":999999999,"maxAll_Y":-999999999,
    "minAll_Z":999999999,"maxAll_Z":-999999999,
    }
    def getObjBounds(obj):
        if obj.type == "MESH":
            mx = obj.matrix_world
            components = obj.data.vertices
            objBounds["minX"] = min((mx @ v.co)[0] for v in components)
            objBounds["minY"] = min((mx @ v.co)[1] for v in components)
            objBounds["minZ"] = min((mx @ v.co)[2] for v in components)
            objBounds["maxZ"] = max((mx @ v.co)[2] for v in components)
            objBounds["maxX"] = max((mx @ v.co)[0] for v in components)
            objBounds["maxY"] = max((mx @ v.co)[1] for v in components)

        else:
            bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            objBounds["minX"] = min([v[0] for v in bbox_corners])
            objBounds["maxX"] = max([v[0] for v in bbox_corners])
            objBounds["minY"] = min([v[1] for v in bbox_corners])
            objBounds["maxY"] = max([v[1] for v in bbox_corners])
            objBounds["minZ"] = min([v[2] for v in bbox_corners])
            objBounds["maxZ"] = max([v[2] for v in bbox_corners])
        return objBounds

    def getObjBoundsGrp():
        if objBounds["minX"] < objBoundsGrp["minAll_X"]: objBoundsGrp["minAll_X"] = objBounds["minX"]
        if objBounds["minY"] < objBoundsGrp["minAll_Y"]: objBoundsGrp["minAll_Y"] = objBounds["minY"]
        if objBounds["minZ"] < objBoundsGrp["minAll_Z"]: objBoundsGrp["minAll_Z"] = objBounds["minZ"]   
        if objBounds["maxZ"] > objBoundsGrp["maxAll_Z"]: objBoundsGrp["maxAll_Z"] = objBounds["maxZ"]        
        if objBounds["maxX"] > objBoundsGrp["maxAll_X"]: objBoundsGrp["maxAll_X"] = objBounds["maxX"]
        if objBounds["maxY"] > objBoundsGrp["maxAll_Y"]: objBoundsGrp["maxAll_Y"] = objBounds["maxY"]
        return objBoundsGrp

    for obj in originalSelection:
        TargetObjects.append(obj)

    for obj in TargetObjects:
        objBounds =getObjBounds(obj)
        objBoundsGrp = getObjBoundsGrp()
    for obj in TargetObjects:
        mx = obj.matrix_world
        objBounds =getObjBounds(obj)
        if MoveType == "group" and WhereTo == "worldzero" and SitOrSwim == "sit" :
            mx.translation.x -= ((objBoundsGrp["minAll_X"]+objBoundsGrp["maxAll_X"])/2)
            mx.translation.y -= ((objBoundsGrp["minAll_Y"]+objBoundsGrp["maxAll_Y"])/2)
            mx.translation.z -= objBoundsGrp["minAll_Z"]
        if MoveType == "individual" and WhereTo == "worldzero" and SitOrSwim == "sit":
            mx.translation.x -= ((objBounds["minX"]+objBounds["maxX"])/2)
            mx.translation.y -= ((objBounds["minY"]+objBounds["maxY"])/2)
            mx.translation.z -= objBounds["minZ"]
        if MoveType == "group" and WhereTo == "straightdn" and SitOrSwim == "sit":
            mx.translation.z -= objBoundsGrp["minAll_Z"]
        if MoveType == "individual" and WhereTo == "straightdn" and SitOrSwim == "sit":
            mx.translation.z -= objBounds["minZ"]
        if MoveType == "group" and WhereTo == "worldzero" and SitOrSwim == "swim" :
            mx.translation.x -= ((objBoundsGrp["maxAll_X"] + objBoundsGrp["minAll_X"])/2)
            mx.translation.y -= ((objBoundsGrp["maxAll_Y"] + objBoundsGrp["minAll_Y"])/2)
            mx.translation.z -= ((objBoundsGrp["maxAll_Z"] + objBoundsGrp["minAll_Z"])/2)
        if MoveType == "individual" and WhereTo == "worldzero" and SitOrSwim == "swim":
            mx.translation.x -= ((objBounds["maxX"] + objBounds["minX"])/2)
            mx.translation.y -= ((objBounds["maxY"] + objBounds["minY"])/2)
            mx.translation.z -= ((objBounds["maxZ"] + objBounds["minZ"])/2)
        if MoveType == "group" and WhereTo == "straightdn" and SitOrSwim == "swim":                
            mx.translation.z -= ((objBoundsGrp["maxAll_Z"] + objBoundsGrp["minAll_Z"])/2)
        if MoveType == "individual" and WhereTo == "straightdn" and SitOrSwim == "swim":
            mx.translation.z -= ((objBounds["maxZ"] + objBounds["minZ"])/2)

#                   ------------------------  Now Pivots   ----------------------------
    objBoundsGrp={
    "minAll_X":999999999,"maxAll_X":-999999999,
    "minAll_Y":999999999,"maxAll_Y":-999999999,
    "minAll_Z":999999999,"maxAll_Z":-999999999,
    }
    for obj in TargetObjects:
        objBounds =getObjBounds(obj)
        objBoundsGrp = getObjBoundsGrp()

    for obj in TargetObjects:
        piv = (0,0,0)
        objBounds =getObjBounds(obj)

        if PivotPlace == "base" and MoveType == "group":
            piv = (((objBoundsGrp["maxAll_X"] + objBoundsGrp["minAll_X"])/2),((objBoundsGrp["maxAll_Y"] + objBoundsGrp["minAll_Y"])/2),objBoundsGrp["minAll_Z"])
        if PivotPlace == "base" and MoveType == "individual":
            piv = (((objBounds["maxX"] + objBounds["minX"])/2),((objBounds["maxY"] + objBounds["minY"])/2),objBounds["minZ"])

        if PivotPlace == "center" and MoveType == "group":
            piv = (((objBoundsGrp["maxAll_X"] + objBoundsGrp["minAll_X"])/2),((objBoundsGrp["maxAll_Y"] + objBoundsGrp["minAll_Y"])/2),((objBoundsGrp["maxAll_Z"] + objBoundsGrp["minAll_Z"])/2))
        if PivotPlace == "center" and MoveType == "individual":
            piv = (((objBounds["maxX"] + objBounds["minX"])/2),((objBounds["maxY"] + objBounds["minY"])/2),((objBounds["maxZ"] + objBounds["minZ"])/2))
        
        origcursorPosVector = bpy.context.scene.cursor.location
        origcursorPos = (origcursorPosVector[0],origcursorPosVector[1],origcursorPosVector[2])
        if PivotPlace != "untouched":
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.scene.cursor.location = piv
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        bpy.context.scene.cursor.location = origcursorPos

    for obj in originalSelection:
        obj.select_set(True)

# --------------------------------------------------------------------------------------
class GroundObjects(bpy.types.Operator):
    bl_idname = "object.ground_objects"
    bl_label = "QOL- Objects to ground"
    bl_options = {'REGISTER', 'UNDO'}


    GndObjPrefs = bpy.context.preferences.addons['QOL_GroundObjects'].preferences

    MoveType: EnumProperty(
    name = 'As',
    items = [('group',"All as one group",""),
            ('individual',"All individually",""),],
    default = GndObjPrefs.MoveType,
    description = 'How to sit things',)
    
    WhereTo: EnumProperty(
    name = 'How to sit',
    items = [('worldzero',"At world zero",""),
            ('straightdn',"Straight down",""),],
    default = GndObjPrefs.WhereTo,        
    description = 'How to sit things',)
    
    SitOrSwim: EnumProperty(
    name = 'Sit or Swim',
    items = [('sit',"Sit on floor",""),
            ('swim',"Swim on surface",""),],
    default = GndObjPrefs.SitOrSwim,        
    description = 'How to sit things',)

    PivotPlace: EnumProperty(
    name = 'Pivot Placement',
    items = [('untouched',"Leave alone",""),
            ('worldzero',"At world origin",""),
            ('base',"At Base",""),
            ('center',"At Center",""),],
    default = GndObjPrefs.PivotPlace,        
    description = 'Where to place pivot after',)

    @classmethod
    def poll(cls, context):
        return context.active_object is not None 
    def execute(self, context):
        sendtoGround(self.MoveType,self.WhereTo,self.SitOrSwim,self.PivotPlace,context)
        if context.scene.tool_settings.use_keyframe_insert_auto:
            bpy.ops.anim.keyframe_insert_menu(type='LocRotScale')
        return {'FINISHED'}

# --------------------------------------------------------------------------------------
def menu_func(self, context):
    global glMoveType
    self.layout.operator(GroundObjects.bl_idname, text=GroundObjects.bl_label)
# --------------------------------------------------------------------------------------

def register():
    bpy.utils.register_class(GroundObjects)
    bpy.types.VIEW3D_MT_object.append(menu_func)
    #add to object context menu
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)
    

def unregister():
    bpy.utils.unregister_class(GroundObjects)
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    # bpy.utils.unregister_class(QOL_GroundObjects_preferences)


if __name__ == "__main__":
    register()
