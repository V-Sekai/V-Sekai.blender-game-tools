#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import math
import bpy
from . import rotfBake

def KeyRange():
    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    context = bpy.context
    scene = context.scene

    smartFrames = scene.rotf_smart_frames
    smartFramesWasOff = False
    if not smartFrames:
        scene.rotf_smart_frames = True
        smartFramesWasOff = True

    for obj in context.selected_objects:
        #if no action on the active object create one
        if obj.animation_data == None:
            action = bpy.data.actions.new('Action')
            obj.animation_data_create()
            obj.animation_data.action = action
        else:
            action = obj.animation_data.action #current action

        frames = list() #list of frames to key
        frameRangeStart = scene.rotf_frame_range_start
        frameRangeEnd = scene.rotf_frame_range_end
        frameRangeStep = scene.rotf_frame_range_step

        frames = [*range(int(frameRangeStart), int(frameRangeEnd) + 1, frameRangeStep)]

        pboneList = dict() #dictionary containing which channels to key on selected pose bones 

        for pbone in context.selected_pose_bones:

            #check the options to see which channel types should be keyed
            channelsToKeyList = list()
            if scene.rotf_key_location:
                channelsToKeyList.append(["location", rotfBake.Channel.locationX])
            if scene.rotf_key_rotation:
                if pbone.rotation_mode == 'QUATERNION':
                    channelsToKeyList.append(["rotation_quaternion", rotfBake.Channel.quaternionW])
                else:
                    channelsToKeyList.append(["rotation_euler", rotfBake.Channel.eulerX])
            if scene.rotf_key_scale:
                channelsToKeyList.append(["scale", rotfBake.Channel.scaleX])

            channelsList = list() #list of channels to key
            
            targetBoneDataPath = pbone.path_from_id()

            #looking for channels
            for transformType, firstChannel in channelsToKeyList:
                numberOfChannels = 3
                if transformType == "rotation_quaternion":
                    numberOfChannels = 4

                for i in range(numberOfChannels):
                    fcurve = action.fcurves.find(targetBoneDataPath +"."+ transformType,index=i)
                    
                    if scene.rotf_key_available:
                        if fcurve: #key only available fcurves
                            channel = firstChannel * math.pow(2, i)
                            channelsList.append(channel)

                            GetFramePointFromFCurve(fcurve, frames)
                    else:
                        channel = firstChannel * math.pow(2, i)
                        channelsList.append(channel)

                        if fcurve:
                            GetFramePointFromFCurve(fcurve, frames)
            
            pboneList[pbone] = channelsList

        rotfBake.RotfBake(obj, action, frames, pboneList)

def GetFramePointFromFCurve(fcurve, frames=list()):
    keyFramePoints = fcurve.keyframe_points
    for point in keyFramePoints:
        f = point.co[0]
        if f not in frames:
            frames.append(f)