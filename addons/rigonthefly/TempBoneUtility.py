#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils

class TempBoneUtility:
    
    @staticmethod
    def TempBoneCopySelectedBones():
        obj = bpy.context.object
        #force edit mode
        StateUtility.SetEditMode()

        #list selected bones in edit mode
        selectedBonesListE = bpy.context.selected_editable_bones.copy()
        selectedBonesListE.sort(key = lambda x:len(x.parent_recursive))
        
        #list selected bones' names
        selectedBonesListN = []
        for b in selectedBonesListE:
            selectedBonesListN.append(b.name)
        
        #duplicate base armature. Duplicate bones are selected from this operation.
        bpy.ops.armature.duplicate()

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')
        #add copy transform constrain to duplicated bones
        for bone in bpy.context.selected_pose_bones:
            copyTransforms = bone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = bpy.context.object
            copyTransforms.subtarget = bone.name.replace(".rig.001",".rig")

        #if object being rigged has animation data
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

                    
                    
                    rotationQEList = [Channel.quaternionW, Channel.quaternionX, Channel.quaternionY, Channel.quaternionZ, Channel.eulerX, Channel.eulerY, Channel.eulerZ]
                    scaleXYZList = [Channel.scaleX, Channel.scaleY, Channel.scaleZ]

                    for boneP in bpy.context.selected_pose_bones:
                        channelsList = list()
                        
                        targetBoneP = obj.pose.bones[boneP.name.replace(".rig.001",".rig")]
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

                        #looking for scale channels
                        for i in range(3):
                            fcurve = action.fcurves.find(targetBoneDataPath + ".scale",index=i)
                            if fcurve:
                                channelsList.extend(scaleXYZList)
                                StateUtility.GetFramePointFromFCurve(fcurve, frames)

                        bonePChannelsToBake[boneP] = channelsList
                    DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)

                StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                obj.animation_data.action = initialAction
            StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
        StateUtility.RemoveConstraintsOfSelectedPoseBones()

        return selectedBonesListN

    @staticmethod
    def SelectedBonesCopyTempBones(selectedBonesListN):
        obj = bpy.context.object
        #deselect copied bones
        bpy.ops.pose.select_all(action='DESELECT')

        #select original bone list
        for bone in selectedBonesListN:
            bpy.context.object.data.bones[bone].select = True

        #make selected bones follow duplicated bones with copy transform constraint
        for bone in bpy.context.selected_pose_bones:
            copyTransforms = bone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = bpy.context.object
            copyTransforms.subtarget = bone.name.replace(".rig",".rig.001")
        
        #if object being rigged has animation data
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

                    
                    
                    rotationQEList = [Channel.quaternionW, Channel.quaternionX, Channel.quaternionY, Channel.quaternionZ, Channel.eulerX, Channel.eulerY, Channel.eulerZ]
                    scaleXYZList = [Channel.scaleX, Channel.scaleY, Channel.scaleZ]

                    for boneP in bpy.context.selected_pose_bones:
                        channelsList = list()
                        
                        targetBoneP = obj.pose.bones[boneP.name.replace(".rig",".rig.001")]
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

                        #looking for scale channels
                        for i in range(3):
                            fcurve = action.fcurves.find(targetBoneDataPath + ".scale",index=i)
                            if fcurve:
                                channelsList.extend(scaleXYZList)
                                StateUtility.GetFramePointFromFCurve(fcurve, frames)

                        bonePChannelsToBake[boneP] = channelsList
                    DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)
                
                StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                obj.animation_data.action = initialAction
            StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
        StateUtility.RemoveConstraintsOfSelectedPoseBones()


        #deselect all to
        bpy.ops.pose.select_all(action='DESELECT')
        #select bones to remove to remove their keyframes first
        for bone in selectedBonesListN:
            bpy.context.object.data.bones[bone.replace(".rig",".rig.001")].select = True

        if obj.animation_data:
            #clear all key frames of selected bones
            StateUtility.KeyframeClear()

        #remove copied bones
        StateUtility.SetEditMode()
        armature = bpy.context.object.data
        for bone in selectedBonesListN:
            armature.edit_bones.remove(armature.edit_bones[bone +".001"])
        
        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        for rigBone in selectedBonesListN:
            bpy.context.object.data.bones[rigBone].select = True

        return selectedBonesListN
