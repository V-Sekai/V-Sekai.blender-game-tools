bl_info = {
    "name": "QOL GridCut V2",
    "author": "Rico Holmes",
    "version": (2, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D",
    "description": "Boolean diff for quick sketch modelling",
    "warning": "",
}

import bpy,bmesh,os,math
from bpy.types import Operator
from bpy.props import (EnumProperty,FloatProperty,BoolProperty,IntProperty)
from mathutils import Vector
from copy import copy

os.system("cls")

def world_bounding_box(obj):
    world_matrix = obj.matrix_world
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    # Apply the object's world matrix to the bmesh vertices
    for v in bm.verts:
        v.co = world_matrix @ v.co
    # Calculate the bounding box
    min_coord = Vector((float('inf'), float('inf'), float('inf')))
    max_coord = Vector((-float('inf'), -float('inf'), -float('inf')))
    for v in bm.verts:
        min_coord.x = min(min_coord.x, v.co.x)
        min_coord.y = min(min_coord.y, v.co.y)
        min_coord.z = min(min_coord.z, v.co.z)
        max_coord.x = max(max_coord.x, v.co.x)
        max_coord.y = max(max_coord.y, v.co.y)
        max_coord.z = max(max_coord.z, v.co.z)
    bm.free()
    return min_coord, max_coord


def getLargestDimension(self,obj):
    bb_world = self.bb_world
    x = bb_world[1].x - bb_world[0].x
    y = bb_world[1].y - bb_world[0].y
    z = bb_world[1].z - bb_world[0].z

    if x > y and x > z:
        axis = "x"
        length = x
          
    elif y > x and y > z:
        axis = "y"
        length = y
    else:
        axis = "z"
        length = z

    return axis, length


def getAxisLength(self,obj,axis):
    bb_world = self.bb_world
    if axis == "x":
        length = bb_world[1].x - bb_world[0].x
    elif axis == "y":
        length = bb_world[1].y - bb_world[0].y
    else:
        length = bb_world[1].z - bb_world[0].z
    return length


class QOL_OT_GridCutTwo(Operator):
    bl_idname = "object.qol_grid_cut"
    bl_label = "QOL GridCut"
    bl_options = {'REGISTER', 'UNDO'}

    divisions : IntProperty(name="Divisions", default=10, min=1, max=1000)
    xcut : BoolProperty(name="X Axis", default=True)
    ycut : BoolProperty(name="Y Axis", default=True)
    zcut : BoolProperty(name="Z Axis", default=True)

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'


    def execute(self, context):
        obj = context.active_object
        self.bb_world = world_bounding_box(obj)
        axis, length = getLargestDimension(self,obj)
        self.spacing = length / self.divisions

        context.view_layer.objects.active = obj

        if getAxisLength(self,obj,"x") > self.spacing and self.xcut:
            Julienne(self,context,obj,"X")
        if getAxisLength(self,obj,"y") > self.spacing and self.ycut:
            Julienne(self,context,obj,"Y")
        if getAxisLength(self,obj,"z") > self.spacing and self.zcut:
            Julienne(self,context,obj,cutAxis="Z")
        return {'FINISHED'}
    

def makeCutters(self,context,axis="X"):
        bb_world = self.bb_world
        spacing = self.spacing
        
        if axis == "X":
            linesX = []
            for i in range(0, self.divisions):
                if i != 0 and bb_world[0].x + spacing * i <= bb_world[1].x:
                    linesX.append((Vector((bb_world[0].x + spacing * i, bb_world[0].y, bb_world[0].z)),
                                Vector((bb_world[0].x + spacing * i, bb_world[1].y, bb_world[1].z))))
            #prepare a new object for the lines
            knifeObjX = bpy.data.objects.new("GridCut_X", bpy.data.meshes.new("GridCutTwo"))
            #with bmesh create a mesh edge for each line in lines
            bm = bmesh.new()
            for line in linesX:
                bm.verts.new(line[0])
                bm.verts.new(line[1])
            bm.verts.ensure_lookup_table()
            for i in range(0, len(bm.verts), 2):
                bm.edges.new((bm.verts[i], bm.verts[i+1]))
            bm.to_mesh(knifeObjX.data)
            bm.free()
            context.collection.objects.link(knifeObjX)
            returnObject = knifeObjX
            knifeObjX.select_set(False)

        if axis == "Y":     
            linesY = []
            for i in range(0, self.divisions):
                if i != 0 and bb_world[0].y + spacing * i <= bb_world[1].y:
                    linesY.append((Vector((bb_world[0].x, bb_world[0].y + spacing * i, bb_world[0].z)),
                                Vector((bb_world[1].x, bb_world[0].y + spacing * i, bb_world[1].z))))
            #prepare a new object for the lines
            knifeObjY = bpy.data.objects.new("GridCut_Y", bpy.data.meshes.new("GridCutTwo"))
            #with bmesh create a mesh edge for each line in lines
            bm = bmesh.new()
            for line in linesY:
                bm.verts.new(line[0])
                bm.verts.new(line[1])
            bm.verts.ensure_lookup_table()
            for i in range(0, len(bm.verts), 2):
                bm.edges.new((bm.verts[i], bm.verts[i+1]))
            bm.to_mesh(knifeObjY.data)
            bm.free()
            context.collection.objects.link(knifeObjY)
            returnObject = knifeObjY
            knifeObjY.select_set(False)

        if axis == "Z":
            linesZ = []
            for i in range(0, self.divisions):
                if i != 0 and bb_world[0].z + spacing * i <= bb_world[1].z:
                    linesZ.append((Vector((bb_world[0].x, bb_world[0].y, bb_world[0].z + spacing * i)),
                                Vector((bb_world[1].x, bb_world[1].y, bb_world[0].z + spacing * i))))

            #prepare a new object for the lines
            knifeObjZ = bpy.data.objects.new("knifeObjZ", bpy.data.meshes.new("GridCutTwo"))
            #with bmesh create a mesh edge for each line in lines
            bm = bmesh.new()
            for line in linesZ:
                bm.verts.new(line[0])
                bm.verts.new(line[1])
            bm.verts.ensure_lookup_table()
            for i in range(0, len(bm.verts), 2):
                bm.edges.new((bm.verts[i], bm.verts[i+1]))
            bm.to_mesh(knifeObjZ.data)
            bm.free()
            context.collection.objects.link(knifeObjZ)
            returnObject = knifeObjZ
            knifeObjZ.select_set(False)
        

        context.view_layer.update()
        return returnObject





def Julienne(self,context,obj,cutAxis):
    vp = context.region_data
    perspective = copy(vp.view_perspective)
    camera_zoom = copy(vp.view_camera_zoom)
    location = copy(vp.view_location)
    rotation = copy(vp.view_rotation)
    distance = copy(vp.view_distance)

    bb_world = self.bb_world

    obj.select_set(True)

    if cutAxis == 'X':
        knifeObjX = makeCutters(self,context,axis="X")
        if (bb_world[1].z - bb_world[0].z) == 0:
            bpy.ops.view3d.view_axis(type='TOP')
        else:
            bpy.ops.view3d.view_axis(type='FRONT')
        vp.update()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        knifeObjX.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.mesh.knife_project(cut_through=True)
        bpy.ops.object.mode_set(mode='OBJECT')
        knifeObjX.select_set(False)
        bpy.data.objects.remove(knifeObjX)

    if cutAxis == 'Y':
        knifeObjY = makeCutters(self,context,axis="Y")
        # using bbworld,get the height of the object
        if (bb_world[1].z - bb_world[0].z) == 0:
            bpy.ops.view3d.view_axis(type='TOP')
        else:
            bpy.ops.view3d.view_axis(type='LEFT')
        vp.update()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        knifeObjY.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.mesh.knife_project(cut_through=True)
        bpy.ops.object.mode_set(mode='OBJECT')
        knifeObjY.select_set(False)
        bpy.data.objects.remove(knifeObjY)

    if cutAxis == 'Z':
        knifeObjZ = makeCutters(self,context,axis="Z")
        if (bb_world[1].x - bb_world[0].x) == 0:
            bpy.ops.view3d.view_axis(type='LEFT')
        else:
            bpy.ops.view3d.view_axis(type='FRONT')
        vp.update()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        knifeObjZ.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.mesh.knife_project(cut_through=True)
        bpy.ops.object.mode_set(mode='OBJECT')
        knifeObjZ.select_set(False)
        bpy.data.objects.remove(knifeObjZ)


    vp.view_perspective = perspective
    vp.view_camera_zoom = camera_zoom
    vp.view_location = location
    vp.view_rotation = rotation
    vp.view_distance = distance
    vp.update()



classes = (
    QOL_OT_GridCutTwo,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()







