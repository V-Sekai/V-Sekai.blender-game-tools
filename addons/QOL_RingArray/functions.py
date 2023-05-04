import bpy,math
import numpy as np

def RotatedMove(Axis,Radians,Distance):
    #return new location after applying rotation and distance in x,y,z
    if Axis == "Z":
        return (math.cos(Radians)*Distance,math.sin(Radians)*Distance,0)
    if Axis == "X":
        return (0,math.cos(Radians)*Distance,math.sin(Radians)*Distance)
    if Axis == "Y":
        return (math.cos(Radians)*Distance,0,math.sin(Radians)*Distance)

def getNearestAxis(axN):
    orientation_dict = {
        (90,90,0)   :'X',
        (0,90,90)   :'X',
        (180,90,90) :'X',
        (270,90,90) :'X',
        (90,90,180) :'X',
        (90,90,270) :'X',

        (0,180,0)   :'Y',
        (0,0,270)   :'Y',
        (90,0,0)    :'Y',
        (90,0,270)  :'Y',
        (90,0,180)  :'Y',

        (0,0,0)     :'Z',        
        (0,90,0)    :'Z',
        (180,90,0)  :'Z',
        (180,0,90)  :'Z',
        (270,90,0)  :'Z',
        (0,0,180)   :'Z',
        (0,0,90)    :'Z',
        (0,180,90)  :'Z',
        (0,180,0)   :'Z',
        (180,0,0)   :'Z',
        (270,0,0)   :'Z',
        }
    return orientation_dict.get(axN,'Z')

def nno(deg):
    return round (deg / 90) * 90
def quantAxis(self,context):
    view_matrix = bpy.context.space_data.region_3d.view_matrix
    oe = view_matrix.to_euler()
    a, b, c = map(math.degrees, (oe[0], oe[1], oe[2]))
    axN = (abs(nno(a)), abs(nno(b)), abs(nno(c)))
    return getNearestAxis(axN)
def getRotationEuler(hub_axis,RotRadians):
    if hub_axis == "X": return (RotRadians,0,0)
    if hub_axis == "Y": return (0,(RotRadians*-1),0)
    if hub_axis == "Z": return (0,0,RotRadians)


def createRingArray(self,context,act_obj,hub_axis,offset_angle,number_of_objects):
    CreatedObjects = []
    for stepper in range(number_of_objects):
        #convert euler to radians
        RotRadians = math.radians(offset_angle+(360/number_of_objects*stepper))
        newXform = RotatedMove(hub_axis,RotRadians,self.radius_of_circle)
        #deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        #select active object
        act_obj.select_set(True)
        #make active object active
        bpy.context.view_layer.objects.active = act_obj
        bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked":self.linked_data, "mode":'TRANSLATION'},
            TRANSFORM_OT_translate={
                "value":newXform,
                "orient_type":'GLOBAL',
                })
        clone = bpy.context.active_object
        if self.resize != 1:
            clone.scale = (self.resize,self.resize,self.resize)
        clone.rotation_euler = getRotationEuler(hub_axis,RotRadians)
        if self.rx != 0:
            clone.rotation_euler.rotate_axis("X",math.radians(self.rx))
        if self.ry != 0:
            clone.rotation_euler.rotate_axis("Y",math.radians(self.ry))
        if self.rz != 0:
            clone.rotation_euler.rotate_axis("Z",math.radians(self.rz))
        
        CreatedObjects.append(clone)
        clone.select_set(False)
    return CreatedObjects

