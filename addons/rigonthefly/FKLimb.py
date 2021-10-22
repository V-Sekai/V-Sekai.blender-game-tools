#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils

class FKLimbUtils:

    def FKLimb (self, context):
        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        obj = bpy.context.object
        armature = obj.data
        unusedLayer = obj.unusedRigBonesLayer

        #show bone unused layer to access hidden bones
        obj.data.layers[unusedLayer] = True

        #add bone name to selectedBonesN to have it's generated IK controller selected at the end of the script
        selectedIKBonesN = dict()
        selectedWorldIKBonesP = list()
        selectedChildIKBonesP = list()

        IKBonesToRemove = list()

        bonesToSelect = list()

        for boneP in bpy.context.selected_pose_bones:  
            boneN = boneP.name
            if ".IK.world.rig" in boneN:
                selectedWorldIKBonesP.append(boneP)
                IKBoneN = boneN.replace(".IK.world.rig",".IK.rig")
                selectedIKBonesN[IKBoneN] = []
                #find to which layer ikHandle is assigned to
                for layer in range(32):
                    if obj.data.bones[boneN].layers[layer]:
                        #originalLayer = layer
                        selectedIKBonesN[IKBoneN] = [layer]

            if ".IK.child.rig" in boneN:
                selectedChildIKBonesP.append(boneP)
                IKBoneN = boneN.replace(".IK.child.rig",".IK.rig")
                selectedIKBonesN[IKBoneN] = []
                #find to which layer ikHandle is assigned to
                for layer in range(32):
                    if obj.data.bones[boneN].layers[layer]:
                        #originalLayer = layer
                        selectedIKBonesN[IKBoneN] = [layer]
                
            if ".IK.rig" in boneN:
                selectedIKBonesN[boneN] = []
                #find to which layer ikHandle is assigned to
                for layer in range(32):
                    if obj.data.bones[boneN].layers[layer]:
                        #originalLayer = layer
                        selectedIKBonesN[boneN] = [layer]
        
        for ikHandleN in selectedIKBonesN:

            #find name of FK bone from IK bone selection
            FKTipBoneN = ikHandleN.replace(".IK.rig",".rig")
            FKTipBoneP = obj.pose.bones[FKTipBoneN]
            FKPoleBoneP = FKTipBoneP.parent
            FKBaseBoneP = FKPoleBoneP.parent

            ikHandleP = obj.pose.bones[ikHandleN]

            FKTipBoneP.rotation_mode = ikHandleP.rotation_mode

            try:
                ikPoleP = obj.pose.bones[FKPoleBoneP.name.replace(".rig",".pole.rig")]
            except:
                ikPoleP = None

            try:
                baseStretchP = obj.pose.bones[FKBaseBoneP.name.replace(".rig",".stretch.IK.rig")]
                poleStretchP = obj.pose.bones[FKPoleBoneP.name.replace(".rig",".stretch.IK.rig")]
            except:
                baseStretchP = None
                poleStretchP = None

            #make list of FK bones for baking
            FKBonesNList = FKTipBoneN, obj.pose.bones[FKTipBoneN].parent.name, obj.pose.bones[FKTipBoneN].parent.parent.name

            bonesToSelect.append(FKTipBoneP)
            
            #change selection to FKBonesNList
            bpy.ops.pose.select_all(action='DESELECT')
            for rigBone in FKBonesNList:
                obj.data.bones[rigBone].select = True
            
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
                        rotationQEList = quaternionWXYZList + eulerXYZList
                        scaleXYZList = [Channel.scaleX, Channel.scaleY, Channel.scaleZ]
                        #for boneP in bpy.context.selected_pose_bones:
                            
                        channelsList = list()

                        ikBonesP = [ikHandleP]
                        if ikPoleP:
                            ikBonesP.append(ikPoleP)

                        for ikboneP in ikBonesP:
                            targetBoneDataPath = ikboneP.path_from_id()
                            for i in range(3):
                                fcurve = action.fcurves.find(targetBoneDataPath + ".location", index=i)
                                if fcurve:
                                    StateUtility.GetFramePointFromFCurve(fcurve, frames)
                                    channelsList.extend(rotationQEList)

                        if channelsList:
                            bonePChannelsToBake[FKTipBoneP] = channelsList
                            targetBoneDataPath = obj.pose.bones[ikHandleN].path_from_id()
                            for i in range(3):
                                fcurve = action.fcurves.find(targetBoneDataPath + ".scale",index=i)
                                if fcurve:
                                    StateUtility.GetFramePointFromFCurve(fcurve, frames)
                                    channelsList.extend(scaleXYZList)
                            
                        bonePChannelsToBake[FKPoleBoneP] = channelsList
                        bonePChannelsToBake[FKBaseBoneP] = channelsList
                        bonePChannelsToBake[FKTipBoneP] = channelsList

                        DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)
                        
                    StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                    obj.animation_data.action = initialAction
                StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
                #------------------------------------------------------------------------------------------------------------------------------------
            
            StateUtility.RemoveConstraintsOfSelectedPoseBones()
            
            #move FK bones to layer ikHandle's layer
            originalLayer = selectedIKBonesN[ikHandleN][0]      
            StateUtility.MoveBonesToLayer(originalLayer)

            #find relevant IK bones to remove
            IKBonesToRemove.append(ikHandleN)
            if ikPoleP:
                IKBonesToRemove.append(ikPoleP.name)
            #IKBonesToRemove.extend([ikHandleN, FKBonesNList[1].replace(".rig",".pole.rig")])
            if baseStretchP:
                IKBonesToRemove.extend([baseStretchP.name, poleStretchP.name])

            #deselect all
            bpy.ops.pose.select_all(action='DESELECT')

        #select bones to remove to remove their keyframes first
        for rigBone in IKBonesToRemove:
            try :
                obj.data.bones[rigBone].select = True
            except:
                print(rigBone)

        for boneP in selectedWorldIKBonesP:
            boneP.bone.select = True
            IKBonesToRemove.append(boneP.name)

        for boneP in selectedChildIKBonesP:
            boneP.bone.select = True
            IKBonesToRemove.append(boneP.name)

            allChildrenSelected = True
            for childrenP in boneP.parent.children:
                if not childrenP.bone.select:
                    allChildrenSelected = False
                    break
            if allChildrenSelected:
                boneP.parent.bone.select = True
                IKBonesToRemove.append(boneP.parent.name)

        if obj.animation_data:
            #clear all key frames of selected bones
            StateUtility.KeyframeClear()

        #remove IK bones
        StateUtility.SetEditMode()

        for boneN in IKBonesToRemove:
            try:
                armature.edit_bones.remove(armature.edit_bones[boneN])
            except:
                print(boneN)

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')

        for pbone in bonesToSelect:
            pbone.bone.select = True
        #hide back unused layer
        obj.data.layers[unusedLayer] = False