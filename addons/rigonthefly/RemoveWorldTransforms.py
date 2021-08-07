#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils

class RemoveWorldTransformsUtils:

    def RemoveWorldTransforms (self, context):
        obj = bpy.context.object
        armature = obj.data

        unusedLayer = obj.unusedRigBonesLayer

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #list selected bones names
        selectedBonesP = bpy.context.selected_pose_bones.copy()

        worldBonesN = list()

        for selectedBoneP in selectedBonesP:
            if ".world.rig" in selectedBoneP.name:
                worldBonesN.append(selectedBoneP.name)

        #deselects all
        bpy.ops.pose.select_all(action='DESELECT')
        #select local bones related to previously selected world space bones
        for worldBoneN in worldBonesN:
            boneN = worldBoneN.replace(".world.rig",".rig")
            for layer in range(32):
                armature.bones[boneN].layers[layer] = armature.bones[worldBoneN].layers[layer]
            armature.bones[boneN].layers[unusedLayer] = False
            
            armature.bones[boneN].select =True

        print("selection")
        for pbone in bpy.context.selected_pose_bones:
            print(pbone.name)
        print("baking")
        #if object being rigged has animation data
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

                                        

                    for boneP in bpy.context.selected_pose_bones:
                        channelsList = list()
                        
                        targetBoneP = obj.pose.bones[boneP.name.replace(".rig", ".world.rig")]
                        targetBoneDataPath = targetBoneP.path_from_id()

                        #if one category of transforms (location, rotation, scale) is found. Add all index of the transform (XYZ, WXYZ) to the channelsList to be keyed.
                        DypsloomBakeUtils.AllTranformsChannels(action, frames, targetBoneDataPath, channelsList)

                        bonePChannelsToBake[boneP] = channelsList
                    DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)
                
                StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                obj.animation_data.action = initialAction
            StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
            #------------------------------------------------------------------------------------------------------------------------------------
        StateUtility.RemoveConstraintsOfSelectedPoseBones()


        #deselects all
        bpy.ops.pose.select_all(action='DESELECT')
        #select local bones related to previously selected world space bones
        for worldBoneN in worldBonesN:
            armature.bones[worldBoneN].select =True
            
        if obj.animation_data:
            #clear all key frames of selected bones
            StateUtility.KeyframeClear()

        #remove selected world space bones
        StateUtility.SetEditMode()
        armature = armature
        for boneN in worldBonesN:
            armature.edit_bones.remove(armature.edit_bones[boneN])
        
        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #deselects all
        bpy.ops.pose.select_all(action='DESELECT')
        #select local bones related to previously selected world space bones
        for worldBoneN in worldBonesN:
            armature.bones[worldBoneN.replace(".world.rig",".rig")].select =True