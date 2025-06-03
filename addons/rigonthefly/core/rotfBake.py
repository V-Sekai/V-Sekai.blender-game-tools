#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy

from enum import IntFlag

class Channel (IntFlag):
    locationX = 1
    locationY = 2
    locationZ = 4

    quaternionW = 8
    quaternionX = 16
    quaternionY = 32
    quaternionZ = 64

    eulerX = 128
    eulerY = 256
    eulerZ = 512

    scaleX = 1024
    scaleY = 2048
    scaleZ = 4096

    #grouped channels
    locationXYZ = locationX + locationY + locationZ

    quaternionWXYZ = quaternionW + quaternionX + quaternionY + quaternionZ

    eulerXYZ = eulerX + eulerY + eulerZ

    rotationQE = quaternionWXYZ + eulerXYZ

    locationRotationQE = locationXYZ + rotationQE

    scaleXYZ = scaleX + scaleY + scaleZ

    transformsEuler = locationXYZ + eulerXYZ + scaleXYZ

    transformsQuaternion = locationXYZ + quaternionWXYZ + scaleXYZ

    allChannels = locationXYZ + quaternionWXYZ + eulerXYZ + scaleXYZ

def RotfBake(obj, action, frames, pboneList):

    iter = RotfBake_iter(obj, action, pboneList)
    iter.send(None)

    scene = bpy.context.scene
    frame_back = scene.frame_current

    try:
        for frame in frames:
            frameInt = int(frame)
            subframe = frame - frameInt
            scene.frame_set(frameInt, subframe= subframe)
            bpy.context.view_layer.update()
            iter.send(frame)
        scene.frame_set(frame_back)
        return iter.send(None)
    except StopIteration: pass

def RotfBake_iter(obj, action, pboneList):
    pose_info = []

    while True:
        # Caller is responsible for setting the frame and updating the scene.
        frame = yield None

        # Signal we're done!
        if frame is None:
            break

        matrix = {}
        for pbone in pboneList:
            # Get the final transform of the bone in its own local space...
            matrix[pbone] = obj.convert_space(
                pose_bone=pbone, 
                matrix=pbone.matrix, 
                from_space='POSE', 
                to_space='LOCAL')
        pose_info.append((frame, matrix))

    # Apply transformations to action

    # pose

    def store_keyframe(bone_name, prop_type, fc_array_index, frame, value):
        fc_data_path = 'pose.bones["' + bone_name + '"].' + prop_type
        fc_key = (fc_data_path, fc_array_index)
        if not keyframes.get(fc_key):
            keyframes[fc_key] = []
        keyframes[fc_key].extend((frame, value))


    #For selected pose bones
    for pbone in pboneList:
        boneName = pbone.name
        #channelsToBake = pboneList[pbone]
        
        # Create compatible eulers, quats.
        euler_prev = None
        quat_prev = None
        keyframes = {}

        #store keyframe values for each transform
        for (f, matrix) in pose_info:
            pbone.matrix_basis = matrix[pbone].copy()
            
            for arr_idx, value in enumerate(pbone.location):
                #if Channel(Channel.locationX << arr_idx) in channelsToBake:
                store_keyframe(boneName, "location", arr_idx, f, value)
            
            rotation_mode = pbone.rotation_mode
            if rotation_mode == 'QUATERNION':
                if quat_prev is not None:
                    quat = pbone.rotation_quaternion.copy()
                    quat.make_compatible(quat_prev)
                    pbone.rotation_quaternion = quat
                    quat_prev = quat
                    del quat
                else:
                    quat_prev = pbone.rotation_quaternion.copy()

                for arr_idx, value in enumerate(pbone.rotation_quaternion):
                    #if Channel(Channel.quaternionW << arr_idx) in channelsToBake:
                    store_keyframe(boneName, "rotation_quaternion", arr_idx, f, value)

            elif rotation_mode == 'AXIS_ANGLE':
                for arr_idx, value in enumerate(pbone.rotation_axis_angle):
                    store_keyframe(boneName, "rotation_axis_angle", arr_idx, f, value)

            else:  # euler, XYZ, ZXY etc
                if euler_prev is not None:
                    euler = pbone.rotation_euler.copy()
                    euler.make_compatible(euler_prev)
                    pbone.rotation_euler = euler
                    euler_prev = euler
                    del euler
                else:
                    euler_prev = pbone.rotation_euler.copy()

                for arr_idx, value in enumerate(pbone.rotation_euler):
                    #if Channel(Channel.eulerX << arr_idx) in channelsToBake:
                    store_keyframe(boneName, "rotation_euler", arr_idx, f, value)

            for arr_idx, value in enumerate(pbone.scale):
                #if Channel(Channel.scaleX << arr_idx) in channelsToBake:
                store_keyframe(boneName, "scale", arr_idx, f, value)

        # Add all keyframe points to the fcurves at once and set their coordinates them after
        # (best performance, inserting keyframes with pbone.keyframe_insert() is about 3 times slower)
        for fc_key, key_values in keyframes.items():
            
            data_path, index = fc_key
            fcurve = action.fcurves.find(data_path=data_path, index=index)
            if fcurve == None:
                fcurve = action.fcurves.new(data_path, index=index, action_group=boneName)

            keyframePointsInterpolationDict = dict() #set aside keyframe point's interpolation's types
            for point in fcurve.keyframe_points:
                framePoint = point.co[0]
                interpolation = point.interpolation
                leftHandle = point.handle_left_type
                righHandle = point.handle_right_type
                keyframePointsInterpolationDict[framePoint] = [interpolation, leftHandle, righHandle]
                #if interpolation != 'BEZIER':
                #    print("not bezier")
                #    print(interpolation)
            
            num_keys = len(key_values) // 2
            keys_to_add = num_keys - len(fcurve.keyframe_points) #find how many keyframe points need to be added
            if keys_to_add > 0: #if the number of keyframe points to add is positive
                fcurve.keyframe_points.add(keys_to_add) #add the needed keyframe points
            
            if keys_to_add < 0: #if the number of keyframe points to add is negative
                
                for point in fcurve.keyframe_points:
                    fcurve.keyframe_points.remove(point) #remove keyframe point
                    
                    if len(fcurve.keyframe_points) == num_keys: #stop removing keyframe points if the amount is equal to the amount needed
                        break
            
            fcurve.keyframe_points.foreach_set('co', key_values)
            
            #reset keyframe point to bezier autoclamped
            for point in fcurve.keyframe_points:
                pointFrame = point.co[0]
                if pointFrame in keyframePointsInterpolationDict.keys():
                    point.interpolation = keyframePointsInterpolationDict[pointFrame][0]
                    point.handle_left_type = keyframePointsInterpolationDict[pointFrame][1]
                    point.handle_right_type = keyframePointsInterpolationDict[pointFrame][2]

                else:
                    point.interpolation = 'BEZIER'
                    point.handle_left_type = 'AUTO_CLAMPED'
                    point.handle_right_type = 'AUTO_CLAMPED'

            fcurve.update()

def GetFramePointFromFCurve(fcurve, frames=list()):
    if bpy.context.scene.smartFrames:
        keyFramePoints = fcurve.keyframe_points
        for point in keyFramePoints:
            f = point.co[0]
            if f not in frames:
                frames.append(f)

def FindActions(pboneList):
    objectActionsDictionary = dict()
    objectsList = list()
    #find object of selected bones
    for boneP in pboneList: #go through selected bones
        if boneP.id_data not in objectsList: #if bone's object is not yet on objectsList
            objectsList.append(boneP.id_data) #add bone's object to objectsList

    #find all actions used by objects in objectsList in their NLA tracks and puts them objectActionsDictionary
    for obj in objectsList: #go through objects in objectsList
        objectActionsDictionary[obj] = [] #add object as key for objectActionsDictionary
        #print(obj.name)
        if obj.animation_data:
            #print("has animation data")
            if obj.animation_data.action:
                currentAction = obj.animation_data.action
                currentBlendType = obj.animation_data.action_blend_type
                objectActionsDictionary[obj].append([currentAction, currentBlendType]) #add the current action to objectActionsDictionary[object name][list]
                #print(currentAction.name)
            if len(obj.rotf_sfp_rig_state) == 0: #check if object is not in single frame pose "mode"
                #print("is not in single frame pose")
                for nlaTrack in obj.animation_data.nla_tracks: #go through object's nla tracks
                    if not nlaTrack.mute: #ignore strips that reside in a muted track
                        for actionStrip in nlaTrack.strips: #go through the strips in it's nla tracks
                            if not actionStrip.mute: #ignore if strip is mute
                                stripBlendType = actionStrip.blend_type
                                action = actionStrip.action
                                if action not in objectActionsDictionary[obj]: #if action used in strips of the nla tracks are not yet in objectActionsDictionary...
                                    objectActionsDictionary[obj].append([action, stripBlendType]) #add the action to objectActionsDictionary[object name][list]
            
        #if no animation data continue
        else:
            continue
    return objectActionsDictionary

def SaveAnimDataState(obj):
    objAnimData = obj.animation_data
    activeAction = objAnimData.action

    activeActionBlendMode = objAnimData.action_blend_type
    objAnimData.action_blend_type = 'REPLACE'

    soloTrack = None
    trackMuteDict = dict()
    for track in objAnimData.nla_tracks:
        muteState = track.mute
        trackMuteDict[track] = muteState
        if track.is_solo:
            soloTrack = track
        track.mute = True
        track.is_solo = False

    objAnimationDataInitialState = [activeAction, activeActionBlendMode, soloTrack, trackMuteDict]
    return objAnimationDataInitialState

def RestoreAnimDataState(obj, animDataState):
    objAnimData = obj.animation_data
    objAnimData.action = animDataState[0]

    objAnimData.action_blend_type = animDataState[1]

    soloTrack = animDataState[2]
    if soloTrack:
        soloTrack.is_solo = True

    trackMuteDict = animDataState[3]
    for track in trackMuteDict:
        track.mute = trackMuteDict[track]

def ChannelsToDataPaths(pbone, channelsToCheck):
    dataPathsToCheck = list()
    propertyTypesList = list()
    if (Channel(channelsToCheck) & Channel.locationXYZ) != 0:
        if "location" not in propertyTypesList:
            propertyTypesList.append("location")

    if channelsToCheck & Channel.quaternionWXYZ != 0:
        if "rotation_quaternion" not in propertyTypesList:
            propertyTypesList.append("rotation_quaternion")

    if channelsToCheck & Channel.eulerXYZ != 0:
        if "rotation_euler" not in propertyTypesList:
            propertyTypesList.append("rotation_euler")

    if channelsToCheck & Channel.scaleXYZ != 0:
        if "scale" not in propertyTypesList:
            propertyTypesList.append("scale")
        
    for propertyType in propertyTypesList:
        dataPath = 'pose.bones["'+ pbone.name + '"].' + propertyType
        if dataPath not in dataPathsToCheck:
            dataPathsToCheck.append(dataPath)

    return dataPathsToCheck

def FindFramesToBake(action, bonesToBakeInfo):
    frames = list()
    
    smartFrames = bpy.context.scene.rotf_smart_frames

    if smartFrames:
        for fcurve in action.fcurves:
            for pboneToBake in bonesToBakeInfo:
                print(bonesToBakeInfo[pboneToBake])
                for pboneToCheck in bonesToBakeInfo[pboneToBake]:
                    fcurvePrefix = 'pose.bones["'+pboneToCheck.name+'"].'
                    if fcurvePrefix in fcurve.data_path:
                        keyFramePoints = fcurve.keyframe_points
                        for point in keyFramePoints:
                            f = point.co[0]
                            if f not in frames:
                                frames.append(f)
    else: 
        frameRange = action.frame_range
        frames = [*range(int(frameRange.x), int(frameRange.y) + 1, 1)]

    return frames

def KeyframeClear(pboneList):
    objectActionsDictionary = FindActions(pboneList) #find relevant action for each selected object
    
    for obj in objectActionsDictionary:
        for actionBlendPair in objectActionsDictionary[obj]:
            action = actionBlendPair[0]
            for pbone in pboneList:
                if pbone.id_data == obj:
                    if action.groups.get(pbone.name):
                        for fcurve in action.groups[pbone.name].channels:
                            if fcurve.data_path:
                                action.fcurves.remove(fcurve)

def BoneHasChannelInAction(pbone, channels, action):

    dataPathsToCheck = ChannelsToDataPaths(pbone, channels)

    for fcurve in action.fcurves:
        for fcurve_data_path in dataPathsToCheck:
            if fcurve_data_path == fcurve.data_path:
                return True
    return False
   
def Bake(bonesToBakeInfo):
    #print("find actions")
    objectActionsDictionary = FindActions(bonesToBakeInfo)
    for obj in objectActionsDictionary:
        wasInTweakMode = False
        if objectActionsDictionary[obj] != []:
            animDataState = SaveAnimDataState(obj)
            objAnimData = obj.animation_data
            wasInTweakMode = objAnimData.use_tweak_mode
            objAnimData.use_tweak_mode = False
            initialAction = objAnimData.action

            #might not be needed without the smart channel feature
            for actionBlendPair in objectActionsDictionary[obj]:
                action = actionBlendPair[0]
                #print("action name " + action.name)
                blendType = actionBlendPair[1]
                objAnimData.action = action #switch obj's current action
                objAnimData.action_blend_type = blendType
                
                frames = FindFramesToBake(action, bonesToBakeInfo)#, dataPathsToCheck)
                #print("Frames to bake: ",frames)
                #print(pboneList)
                RotfBake(obj, action, frames, bonesToBakeInfo)

            RestoreAnimDataState(obj, animDataState)

            #objAnimData.nla_tracks.remove(restPoseTrack)

            if wasInTweakMode:
                objAnimData.action = initialAction
                objAnimData.use_tweak_mode = True #return to nla tweak mode