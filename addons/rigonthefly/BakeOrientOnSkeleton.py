#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils

class BakeOrientOnSkeletonUtils:
    def BakeOrientOnSkeleton (self, context):

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        obj = bpy.context.object
        armature = obj.data

        originalLayers = list()
        for layer in range(32):
            if obj.data.layers[layer] == True:
                originalLayers.append(layer)
            else:
                armature.layers[layer] = True

        #deselect all pose bones
        bpy.ops.pose.select_all(action='DESELECT')

        #select only bones that have a ".orient.rig" equivalent
        for bone in bpy.context.object.data.bones:
            if ".orient.rig" in bone.name:
                try:
                    bpy.context.object.data.bones[bone.name.replace(".orient.rig","")].select = True
                except:
                    #if original bone had side as a suffix, it will try to select it
                    StateUtility.FindOriginalBone(bone)
                    continue

        if bpy.context.selected_pose_bones:
            rotfBonesList = list()
            for pbone in bpy.context.selected_pose_bones:
                rotfBonesList.append(pbone)
            #if object contains animation data, bake base skin bones removing constraints
            if obj.animation_data:
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

                        locationXYZList = [Channel.locationX, Channel.locationY, Channel.locationZ]
                        quaternionWXYZList = [Channel.quaternionW, Channel.quaternionX, Channel.quaternionY, Channel.quaternionZ]
                        eulerXYZList = [Channel.eulerX, Channel.eulerY, Channel.eulerZ]
                        scaleXYZList = [Channel.scaleX, Channel.scaleY, Channel.scaleZ]

                        for boneP in bpy.context.selected_pose_bones:
                            channelsList = list()
                            rigBN = StateUtility.LeftRightSuffix(boneP.name) + ".orient.rig"
                            targetBoneP = obj.pose.bones[rigBN]
                            #bonePDataPath = targetBoneP.path_from_id()
                            targetBoneDataPath = targetBoneP.path_from_id()
                            #targetBoneDataPath = bonePDataPath.replace(boneP.name, rigBN + ".orient.rig")

                            #looking for translation channels
                            for i in range(3):
                                fcurve = action.fcurves.find(targetBoneDataPath + ".location",index=i)
                                if fcurve:
                                    channelsList.extend(locationXYZList)
                                    StateUtility.GetFramePointFromFCurve(fcurve, frames)
                            #check rotation mode to know what rotation channel type key
                            if boneP.rotation_mode == 'QUATERNION':
                                #looking for quaternion channels
                                for i in range(4):
                                    fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=i)
                                    if fcurve:
                                        channelsList.extend(quaternionWXYZList)
                                        StateUtility.GetFramePointFromFCurve(fcurve, frames)
                                #looking for euler channels
                                for i in range(3):
                                    fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=i)
                                    if fcurve:
                                        channelsList.extend(quaternionWXYZList)
                                        StateUtility.GetFramePointFromFCurve(fcurve, frames)
                            else:
                                for i in range(4):
                                    fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=i)
                                    if fcurve:
                                        channelsList.extend(eulerXYZList)
                                        StateUtility.GetFramePointFromFCurve(fcurve, frames)
                                #looking for euler channels
                                for i in range(3):
                                    fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=i)
                                    if fcurve:
                                        channelsList.extend(eulerXYZList)
                                        StateUtility.GetFramePointFromFCurve(fcurve, frames)
                            #looking for scale channels
                            for i in range(3):
                                fcurve = action.fcurves.find(targetBoneDataPath + ".scale",index=i)
                                if fcurve:
                                    channelsList.extend(scaleXYZList)
                                    StateUtility.GetFramePointFromFCurve(fcurve, frames)

                            bonePChannelsToBake[boneP] = channelsList
                        #selectedPBones = bpy.context.selected_pose_bones
                        DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)
                    
                    StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                    obj.animation_data.action = initialAction
                StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
                #------------------------------------------------------------------------------------------------------------------------------------
            
            StateUtility.RemoveConstraintsOfSelectedPoseBones()
            
            #deselect all pose bones
            bpy.ops.pose.select_all(action='DESELECT')

            #select bones that will not need animation
            for bone in bpy.context.object.data.bones:
                if ".orient." in bone.name:
                    bpy.context.object.data.bones[bone.name].select = True

            if obj.animation_data:
                #clear all key frames of selected bones
                StateUtility.KeyframeClear()

            #force edit mode
            StateUtility.SetEditMode()

            #remove .orient bones
            armature = bpy.context.object.data
            for bone in armature.bones:
                if ".orient" in bone.name:
                    armature.edit_bones.remove(armature.edit_bones[bone.name])

            #force pose mode
            bpy.ops.object.mode_set(mode='POSE')

            #select only bones from rotfBonesList to move them to the baseBoneLayer
            for pbone in rotfBonesList:
                pbone.bone.select = True
            StateUtility.MoveBonesToLayer(obj.baseBonesLayer)
            
            #only leave the base layer and the originally visible layers
            for i in range(32):
                if i == obj.rigBonesLayer or i == obj.unusedRigBonesLayer or i == obj.notOrientedBonesLayer or i == obj.translatorBonesLayer :
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
            print("no .orient.rig bones")
            return [{'WARNING'}, "no .orient.rig bones to bake"]
            