#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . import rotfBake
  
def KeyRange():
    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    context = bpy.context
    scene = context.scene

    smartChannels = scene.rotf_smart_channels
    smartChannelsWasOff = False
    if not smartChannels:
        scene.smartChannels = True
        smartChannelsWasOff = True
    smartFrames = scene.rotf_smart_frames
    smartFramesWasOff = False
    if not smartFrames:
        scene.smartFrames = True
        smartFramesWasOff = True

    for obj in context.selected_objects:
        action = obj.animation_data.action #current action

        frames = list() #list of frames to key
        frameRangeStart = scene.rotf_frame_range_start
        frameRangeEnd = scene.rotf_frame_range_end
        frameRangeStep = scene.rotf_frame_range_step

        frames = [*range(int(frameRangeStart), int(frameRangeEnd) + 1, frameRangeStep)]

        pboneList = dict() #dictionary containing which channels to key on selected pose bones 

        for boneP in context.selected_pose_bones:
            channelsList = list()
            
            targetBoneDataPath = boneP.path_from_id()

            #looking for translation channels
            for i in range(3):
                fcurve = action.fcurves.find(targetBoneDataPath + ".location",index=i)
                if fcurve:
                    if i == 0: #if location X channel
                        channelsList.append(rotfBake.Channel.locationX)
                    if i == 1: #if location Y channel
                        channelsList.append(rotfBake.Channel.locationY)
                    if i == 2: #if location Z channel
                        channelsList.append(rotfBake.Channel.locationZ)
                    GetFramePointFromFCurve(fcurve, frames)

            if boneP.rotation_mode == 'QUATERNION':
                #looking for quaternion channels
                for i in range(4):
                    fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=i)
                    if fcurve:
                        if i == 0: #if euler X channel
                            channelsList.append(rotfBake.Channel.quaternionW)
                        if i == 1: #if euler X channel
                            channelsList.append(rotfBake.Channel.quaternionX)
                        if i == 2: #if euler Y channel
                            channelsList.append(rotfBake.Channel.quaternionY)
                        if i == 3: #if euler Z channel
                            channelsList.append(rotfBake.Channel.quaternionZ)
                        GetFramePointFromFCurve(fcurve, frames)
            else:
                #looking for euler channels
                for i in range(3):
                    fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=i)
                    if fcurve:
                        if i == 0: #if euler X channel
                            channelsList.append(rotfBake.Channel.eulerX)
                        if i == 1: #if euler Y channel
                            channelsList.append(rotfBake.Channel.eulerY)
                        if i == 2: #if euler Z channel
                            channelsList.append(rotfBake.Channel.eulerZ)
                        GetFramePointFromFCurve(fcurve, frames)                    
                
            #looking for scale channels
            for i in range(3):
                fcurve = action.fcurves.find(targetBoneDataPath + ".scale",index=i)
                if fcurve:
                    if i == 0: #if scale X channel
                        channelsList.append(rotfBake.Channel.scaleX)
                    if i == 1: #if scale Y channel
                        channelsList.append(rotfBake.Channel.scaleY)
                    if i == 2: #if scale Z channel
                        channelsList.append(rotfBake.Channel.scaleZ)
                    GetFramePointFromFCurve(fcurve, frames)
            pboneList[boneP] = channelsList

        rotfBake.RotfBake(obj, action, frames, pboneList)

def GetFramePointFromFCurve(fcurve, frames=list()):
    keyFramePoints = fcurve.keyframe_points
    for point in keyFramePoints:
        f = point.co[0]
        if f not in frames:
            frames.append(f)