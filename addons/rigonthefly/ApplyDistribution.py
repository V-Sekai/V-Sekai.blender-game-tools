#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils

class ApplyDistributionUtils:

    def ApplyDistribution (self, context):
        bonesToBakeN = list()
        bonesToRemoveN = list() #bones to delete at the end of the script

        obj = bpy.context.object
        armature = obj.data

        unusedLayer = obj.unusedRigBonesLayer
        armature.layers[unusedLayer] = True

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #find .top.rig bones and sort bones to bake and bones to remove
        topRotBonesNDict = dict()
        for bone in bpy.context.selected_pose_bones:
            if ".top.rig" in bone.name:
                topRotBonesNDict[bone.name] = []
                for layer in range(32):
                    topRotBonesNDict[bone.name].append(layer)
                bonesToRemoveN.append(bone.name)
                bonesToBakeN.append(bone.name.replace(".top.rig",".rig"))
                for layer in range(32):
                    obj.pose.bones[bone.name.replace(".top.rig",".rig")].bone.layers[layer] = obj.pose.bones[bone.name].bone.layers[layer]
        
        #find .rotTop.rig bones children and sort bones to bake and bones to remove
        for topRotBoneN in topRotBonesNDict:
            for topRotChild in obj.pose.bones[topRotBoneN].children:
                print(topRotChild.name)
                bonesToBakeN.append(topRotChild.name.replace(".rotTop.rig",".rig"))
                for layer in range(32):
                    obj.pose.bones[topRotChild.name.replace(".rotTop.rig",".rig")].bone.layers[layer] = obj.pose.bones[topRotBoneN].bone.layers[layer]
                bonesToRemoveN.append(topRotChild.name)
                bonesToRemoveN.append(topRotChild.name.replace(".rotTop.rig",".rotBase.rig"))
        
        bpy.ops.pose.select_all(action='DESELECT')

        #change bonesToBake to the same layer as the originally selected top bones and selects them for baking
        for boneN in bonesToBakeN:
            boneP = armature.bones[boneN]
            boneP.select = True
        
        #if object has animation data
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
                    rotationQEList = [Channel.quaternionW, Channel.quaternionX, Channel.quaternionY, Channel.quaternionZ, Channel.eulerX, Channel.eulerY, Channel.eulerZ]
                    #scaleXYZList = [Channel.scaleX, Channel.scaleY, Channel.scaleZ]

                    for boneP in bpy.context.selected_pose_bones:
                        channelsList = list()

                        topBone = obj.pose.bones[topRotBoneN]
                        baseBone = topBone.parent
                        for targetBoneP in [topBone, baseBone]:
                            targetBoneDataPath = targetBoneP.path_from_id()
                        
                            #looking for quaternion channels
                            for i in range(4):
                                fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=i)
                                if fcurve:
                                    channelsList.extend(rotationQEList)
                                    StateUtility.GetFramePointFromFCurve(fcurve, frames)
                            #looking for euler channels
                            for i in range(3):
                                fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=i)
                                if fcurve:
                                    channelsList.extend(rotationQEList)
                                    StateUtility.GetFramePointFromFCurve(fcurve, frames)

                        bonePChannelsToBake[boneP] = channelsList
                    DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)
                
                StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                obj.animation_data.action = initialAction
            StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
            #------------------------------------------------------------------------------------------------------------------------------------
        StateUtility.RemoveConstraintsOfSelectedPoseBones()
        
        #deselect all to
        bpy.ops.pose.select_all(action='DESELECT')
        #select bones to remove to remove their keyframes first
        for boneN in bonesToRemoveN:
            armature.bones[boneN].select = True

        if obj.animation_data:
            #clear all key frames of selected bones
            StateUtility.KeyframeClear()

        #remove bones
        StateUtility.SetEditMode()
        armature = armature
        for boneN in bonesToRemoveN:
            armature.edit_bones.remove(armature.edit_bones[boneN])

        armature.layers[unusedLayer] = False

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')
        