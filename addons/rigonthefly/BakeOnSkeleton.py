#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils

class BakeOnSkeletonUtils:
    def BakeOnSkeleton (self, context):

        obj = bpy.context.object
        armature = obj.data

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        originalLayers = list()
        for layer in range(32):
            if obj.data.layers[layer] == True:
                originalLayers.append(layer)
            else:
                armature.layers[layer] = True

        #deselect all pose bones
        bpy.ops.pose.select_all(action='DESELECT')

        #select only bones that have a ".rig" equivalent
        for bone in armature.bones:
            if ".rig" in bone.name:
                if ".orient." in bone.name:
                    continue
                try:
                    armature.bones[bone.name.replace(".rig", "")].select = True
                except:
                    #if original bone had side as a suffix, it will try to select it
                    StateUtility.FindOriginalBone(bone)
                    continue
        
        if bpy.context.selected_pose_bones:
            #if object has animation data, bake skin bones
            if obj.animation_data:
                # -----------------------------------------------------------------------------------------------------------------------------------
                #BAKE SELECTED BONES
                objectActionsDictionary = StateUtility.FindActions() #find relevant action for each selected object
                ActionInitialState = StateUtility.ActionInitialState(objectActionsDictionary) #store objects' actions state to know if they were in tweak mode
                for obj in objectActionsDictionary:
                    initialAction = obj.animation_data.action

                    tracksStateDict, soloTrack, activeActionBlendMode = StateUtility.SoloRestPoseTrack(obj) #add an nla track to solo so that baking is done without other tracks influencing the result
                    
                    for action in objectActionsDictionary[obj]:
                        obj.animation_data.action = action #switch obj's current action
                        

                        frames = list() #list of frames to key
                        bonePChannelsToBake = dict() #dictionary containing which channels to key on selected pose bones 

                        if not bpy.context.scene.smartFrames:
                            frameRange = action.frame_range
                            frames = [*range(int(frameRange.x), int(frameRange.y) + 1, 1)]

                                           

                        #locationXYZList = [Channel.locationX, Channel.locationY, Channel.locationZ]
                        quaternionWXYZList = [Channel.quaternionW, Channel.quaternionX, Channel.quaternionY, Channel.quaternionZ]
                        eulerXYZList = [Channel.eulerX, Channel.eulerY, Channel.eulerZ]
                        #scaleXYZList = [Channel.scaleX, Channel.scaleY, Channel.scaleZ]

                        for boneP in bpy.context.selected_pose_bones:
                            channelsList = list()
                            rigBN = StateUtility.LeftRightSuffix(boneP.name) +".rig"
                            targetBoneP = obj.pose.bones[rigBN]#obj.pose.bones[boneP.name + ".rig"]
                            targetBoneDataPath = targetBoneP.path_from_id()

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
                            if boneP.rotation_mode == targetBoneP.rotation_mode:
                                if boneP.rotation_mode == 'QUATERNION':
                                    #looking for euler channels
                                    for i in range(4):
                                        fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=i)
                                        if fcurve:
                                            if i == 0: #if quaternion W channel
                                                channelsList.append(Channel.quaternionW)
                                            if i == 1: #if quaternion X channel
                                                channelsList.append(Channel.quaternionX)
                                            if i == 2: #if quaternion Y channel
                                                channelsList.append(Channel.quaternionY)
                                            if i == 3: #if quaternion Z channel
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
                            else:
                                if boneP.rotation_mode == 'QUATERNION':
                                    rotationList = quaternionWXYZList
                                else:
                                    rotationList = eulerXYZList
                                #looking for quaternion channels
                                for i in range(4):
                                    fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=i)
                                    if fcurve:
                                        channelsList.extend(rotationList)
                                        StateUtility.GetFramePointFromFCurve(fcurve, frames)
                                #looking for euler channels
                                for i in range(3):
                                    fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=i)
                                    if fcurve:
                                        channelsList.extend(rotationList)
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
                    
                    StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                    obj.animation_data.action = initialAction
                StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
                #------------------------------------------------------------------------------------------------------------------------------------
            StateUtility.RemoveConstraintsOfSelectedPoseBones()

            #deselect all
            bpy.ops.pose.select_all(action='DESELECT')

            #select bones that will not need animation
            for bone in armature.bones:
                if ".rig" in bone.name:
                    armature.bones[bone.name].select = True
                    
            if obj.animation_data:
                #clear all key frames of selected bones
                StateUtility.KeyframeClear()

            #force edit mode
            StateUtility.SetEditMode()

            #remove .rig bones
            armature = armature
            for bone in armature.bones:
                if ".rig" in bone.name:
                    armature.edit_bones.remove(armature.edit_bones[bone.name])

            #force pose mode
            bpy.ops.object.mode_set(mode='POSE')

            #only leave the base layer and the originally visible layers
            for i in range(32):
                if i == obj.rigBonesLayer or i == obj.unusedRigBonesLayer:
                    armature.layers[i] = False

                #skip base layer
                elif i == obj.baseBonesLayer:
                    continue

                elif i in originalLayers:
                        continue
                else:
                    armature.layers[i] = False

        else:
            for i in range(32):
                if i in originalLayers:
                        continue
                else:
                    armature.layers[i] = False
            print("no bones to bake")
            return [{'WARNING'}, "no .rig bones to bake"]
            
    def BoneMotionToArmature (self, context):
        obj = bpy.context.object
        armature = obj.data

        #action = obj.animation_data.action

        motionPBone = obj.pose.bones.get('RotF_ArmatureMotion')
        if motionPBone:
            motionPBone.bone.select = True
        objectActionsDictionary = StateUtility.FindActions() #find relevant action for each selected object
        ActionInitialState = StateUtility.ActionInitialState(objectActionsDictionary) #store objects' actions state to know if they were in tweak mode
        if motionPBone:
            boneDataPath = motionPBone.path_from_id()
            for obj in objectActionsDictionary:
                initialAction = obj.animation_data.action

                tracksStateDict, soloTrack, activeActionBlendMode = StateUtility.SoloRestPoseTrack(obj) #add an nla track to solo so that baking is done without other tracks influencing the result
                
                for action in objectActionsDictionary[obj]:
                    
                    #copy the armature's object motion to the new bone
                    for transformType in ["location","rotation_euler","rotation_quaternion","scale"]:
                        index = int()
                        if transformType == "rotation_quaternion":
                            index = 4
                        else:
                            index = 3
                            
                        for i in range(index):
                            data_path = boneDataPath+"."+transformType
                            fcurve = action.fcurves.find(data_path, index=i)
                            if not fcurve:
                                continue
                            else:
                                objFCurve = action.fcurves.find(transformType,index=i)
                                
                                if objFCurve == None:
                                    objFCurve = action.fcurves.new(transformType, index=i, action_group="Object Transforms")
                                    
                                num_keys = len(fcurve.keyframe_points)
                                keys_to_add = num_keys - len(objFCurve.keyframe_points) #find how many keyframe points need to be added
                                objFCurve.keyframe_points.add(keys_to_add) #add the needed keyframe points
                                
                                for key in range(num_keys):
                                    objFCurve.keyframe_points[key].co = fcurve.keyframe_points[key].co
                                    objFCurve.keyframe_points[key].handle_left = fcurve.keyframe_points[key].handle_left
                                    objFCurve.keyframe_points[key].handle_right = fcurve.keyframe_points[key].handle_right
                            
                            #remove fcurve on armature object
                            action.fcurves.remove(fcurve)
                    
            StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
            obj.animation_data.action = initialAction

            #force edit mode
            StateUtility.SetEditMode()
            armature.edit_bones.remove(armature.edit_bones['RotF_ArmatureMotion'])
            #armature is in pose mode
            bpy.ops.object.mode_set(mode='POSE')

            StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
        