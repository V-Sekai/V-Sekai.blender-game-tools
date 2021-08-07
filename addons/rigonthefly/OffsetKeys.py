#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel

class OffsetKeysUtils:

    def OffsetKeys(self, context):
        bpy.ops.object.mode_set(mode='POSE') #force pose mode
        scene = bpy.context.scene
        offsetFactor = scene.offsetValue

        for i, pbone in enumerate(bpy.boneSelection): #going through selected bones py order of selection
            obj = pbone.id_data #pbone's object
            action = obj.animation_data.action #current action

            path = pbone.path_from_id()

            offset = (i+1) * offsetFactor

            for transformType in [".location",".rotation_quaternion",".rotation_euler",".scale"]:
                if transformType == ".rotation_quaternion":
                    axis = 4
                else:
                    axis = 3
                for axe in range(axis):
                    fcurve = action.fcurves.find(path + transformType,index=axe)
                    if fcurve:
                        OffsetKeysUtils.OffsetFCurve(fcurve, offset)

    @staticmethod
    def OffsetFCurve(fcurve, offset):
        for point in fcurve.keyframe_points:
            if point.select_control_point:
                point.co[0] += offset

        keyframePoints = list()
        framesWithMultiplePoints = list()
        
        for point in fcurve.keyframe_points:
            keyframePoints.append(point)
        keyframePoints.sort(key = lambda x:x.co[0])
        
        for i, currentPoint in enumerate(keyframePoints):
            prev_point = keyframePoints[i-1]
            if prev_point.co[0] == currentPoint.co[0]:
                framesWithMultiplePoints.append(currentPoint.co[0])
        
        if framesWithMultiplePoints:
            keyframe_points = fcurve.keyframe_points
            i = 1
            while i < len(keyframe_points) - 1:
                point = keyframe_points[i]
                if point.co[0] in framesWithMultiplePoints:
                    if not point.select_control_point:
                        print(point.co[0])
                        fcurve.keyframe_points.remove(keyframe_points[i])
                    else:
                        i += 1
                else:
                    i += 1
                    
        fcurve.update()
