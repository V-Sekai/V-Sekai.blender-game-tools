#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils

class KeyRangeUtils:    
    def KeyRange (self, context):

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')
        
        smartChannels = bpy.context.scene.smartChannels
        smartChannelsWasOff = False
        if not smartChannels:
            bpy.context.scene.smartChannels = True
            smartChannelsWasOff = True
        smartFrames = bpy.context.scene.smartFrames
        smartFramesWasOff = False
        if not smartFrames:
            bpy.context.scene.smartFrames = True
            smartFramesWasOff = True

        for obj in bpy.context.selected_objects:
            action = obj.animation_data.action #current action

            frames = list() #list of frames to key
            frameRangeStart = bpy.context.scene.smartRangeStart
            frameRangeEnd = bpy.context.scene.smartRangeEnd
            frameRangeStep = bpy.context.scene.smartRangeStep
            frames = [*range(int(frameRangeStart), int(frameRangeEnd) + 1, frameRangeStep)]

            bonePChannelsToBake = dict() #dictionary containing which channels to key on selected pose bones 

            for boneP in bpy.context.selected_pose_bones:
                channelsList = list()
                
                targetBoneDataPath = boneP.path_from_id()

                #looking for translation channels
                for i in range(3):
                    fcurve = action.fcurves.find(targetBoneDataPath + ".location",index=i)
                    if fcurve:
                        if i == 0: #if location X channel
                            channelsList.append(Channel.locationX)
                        if i == 1: #if location Y channel
                            channelsList.append(Channel.locationY)
                        if i == 2: #if location Z channel
                            channelsList.append(Channel.locationZ)
                        StateUtility.GetFramePointFromFCurve(fcurve, frames)

                if boneP.rotation_mode == 'QUATERNION':
                    #looking for quaternion channels
                    for i in range(4):
                        fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=i)
                        if fcurve:
                            if i == 0: #if euler X channel
                                channelsList.append(Channel.quaternionW)
                            if i == 1: #if euler X channel
                                channelsList.append(Channel.quaternionX)
                            if i == 2: #if euler Y channel
                                channelsList.append(Channel.quaternionY)
                            if i == 3: #if euler Z channel
                                channelsList.append(Channel.quaternionZ)
                            StateUtility.GetFramePointFromFCurve(fcurve, frames)
                else:
                    #looking for euler channels
                    for i in range(3):
                        fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=i)
                        if fcurve:
                            if i == 0: #if euler X channel
                                channelsList.append(Channel.eulerX)
                            if i == 1: #if euler Y channel
                                channelsList.append(Channel.eulerY)
                            if i == 2: #if euler Z channel
                                channelsList.append(Channel.eulerZ)
                            StateUtility.GetFramePointFromFCurve(fcurve, frames)                    
                    
                #looking for scale channels
                for i in range(3):
                    fcurve = action.fcurves.find(targetBoneDataPath + ".scale",index=i)
                    if fcurve:
                        if i == 0: #if scale X channel
                            channelsList.append(Channel.scaleX)
                        if i == 1: #if scale Y channel
                            channelsList.append(Channel.scaleY)
                        if i == 2: #if scale Z channel
                            channelsList.append(Channel.scaleZ)
                        StateUtility.GetFramePointFromFCurve(fcurve, frames)
                bonePChannelsToBake[boneP] = channelsList
            DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)

        if smartChannelsWasOff:
            bpy.context.scene.smartChannels = False
        if smartFramesWasOff:
            bpy.context.scene.smartFrames = False