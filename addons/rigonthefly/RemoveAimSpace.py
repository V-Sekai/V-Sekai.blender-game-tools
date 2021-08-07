#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils
from . InheritRotationOn import InheritRotationOnUtils
from . InheritScaleOn import InheritScaleOnUtils

class RemoveAimSpaceUtils:

    @staticmethod
    def SelectFullAimChain (pbone):
        obj = pbone.id_data

        hasAimTarget = True
        aimPBone = pbone

        #select aim bones down the aim chain
        while hasAimTarget:
            if not aimPBone.constraints:
                hasAimTarget = False
            aimBoneConstraints = aimPBone.constraints
            for constraint in aimBoneConstraints:
                if any (constraint.type == cType for cType in ['IK','STRETCH_TO']):
                    cTarget = constraint.target
                    cSubtarget = constraint.subtarget
                    if ".aim.rig" in cSubtarget:
                        targetPBone = cTarget.pose.bones[cSubtarget]
                        targetPBone.bone.select = True
                        aimPBone = targetPBone
                    else:
                        hasAimTarget = False

        isAimTarget = True
        aimPBone = pbone
        #select aim bones up the aim chain
        while isAimTarget:
            aimParentN = aimPBone.get('Aim Parent')
            if aimParentN:
                aimParentPBone = obj.pose.bones[aimParentN]
                aimParentPBone.bone.select = True
                aimPBone = aimParentPBone
            else:
                isAimTarget = False

    def RemoveAimSpace (self, context):
        obj = bpy.context.object
        armature = obj.data

        unusedLayer = obj.unusedRigBonesLayer

        inheritedRotationListN = list()
        inheritedScaleListN = list()
        stretchChainListN = list()
        
        nbonesToremove = list()
        pbonesToSelect = list()

        #sort selected pose bones to exclude the ones not containing ".aim.rig" and select the rest of aim chains if they are partially selected
        for pbone in bpy.context.selected_pose_bones:
            if not ".aim.rig" in pbone.name:
                pbone.bone.select = False
            else:
                #check if pbone is part of an aim chain
                RemoveAimSpaceUtils.SelectFullAimChain(pbone)

        #list selected aim bones
        selectedAimBonesNameList = list()
        for selectedBoneP in bpy.context.selected_pose_bones:
            if ".aim.rig" in selectedBoneP.name:
                aimBoneN = selectedBoneP.name
                selectedAimBonesNameList.append(aimBoneN)

                boneN = aimBoneN.replace(".aim.rig",".rig")

                #move base bones to the same layer as selected aim bones
                for layer in range(32):
                    armature.bones[boneN].layers[layer] = armature.bones[aimBoneN].layers[layer]
                    armature.bones[boneN].layers[unusedLayer] = False

                #find selected bone that are a result of Stretch Chain
                if selectedBoneP.constraints.get('Stretch To') is not None:
                    
                    #find the subtarget on each bone of a Stretch Chain
                    subtargetN = selectedBoneP.constraints.get('Stretch To').subtarget
                    boneSubtargetN = subtargetN.replace(".aim.rig",".rig") #boneSubtargetN is the ".rig" version of the ".aim.rig" bone

                    #find bone that need it's inherit rotation and scale turned off to prevent baking errors
                    selectedBoneInherit = armature.bones[boneSubtargetN]

                    #set aside .rig of aim.rig subtarget of stretch chains
                    stretchChainListN.append(boneSubtargetN)

                    #set aside bones which got their inherit rotation and scale turned off
                    if selectedBoneInherit.use_inherit_rotation == True:
                        inheritedRotationListN.append(boneSubtargetN)

                    if selectedBoneInherit.use_inherit_scale == True:
                        inheritedScaleListN.append(boneSubtargetN)
                    
                    #turn off inherit rotation and scale of bones affected by stretch chain
                    selectedBoneInherit.use_inherit_rotation = False
                    selectedBoneInherit.use_inherit_scale = False

                aimOffsetN = boneN.replace(".rig",".aimOffset.rig")
                aimCopyN = boneN.replace(".rig",".aimCopy.rig")
                nbonesToremove.extend([aimOffsetN,aimCopyN])

        #deselect all bones
        bpy.ops.pose.select_all(action='DESELECT')

        #select rig bones from aim bones list
        for aimBoneN in selectedAimBonesNameList:
            nbone = aimBoneN.replace(".aim.rig",".rig")
            armature.bones[nbone].select = True
            pbone = obj.pose.bones[nbone]
            if ".child.rig" in nbone or ".top.rig" in nbone:
                pbone.custom_shape = bpy.data.objects["RotF_Octagon"]
            elif ".world.rig" in nbone:
                pbone.custom_shape = bpy.data.objects["RotF_Square"]
            else:
                pbone.custom_shape = bpy.data.objects["RotF_Circle"]

        pbonesToSelect = bpy.context.selected_pose_bones.copy()
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

                                        

                    locationXYZList = [Channel.locationX, Channel.locationY, Channel.locationZ]
                    rotationQEList = [Channel.quaternionW, Channel.quaternionX, Channel.quaternionY, Channel.quaternionZ, Channel.eulerX, Channel.eulerY, Channel.eulerZ]
                    scaleXYZList = [Channel.scaleX, Channel.scaleY, Channel.scaleZ]

                    for boneP in bpy.context.selected_pose_bones:
                        channelsList = list()
                        
                        targetBoneP = obj.pose.bones[boneP.name.replace(".rig", ".aim.rig")]
                        targetBoneDataPath = targetBoneP.path_from_id()

                        #looking for translation channels
                        for i in range(3):
                            fcurve = action.fcurves.find(targetBoneDataPath + ".location",index=i)
                            if fcurve:
                                channelsList.extend(rotationQEList)
                                StateUtility.GetFramePointFromFCurve(fcurve, frames)
                                if boneP.constraints.get('Stretch To') is not None or targetBoneP.constraints.get('Stretch To') is not None:
                                    channelsList.extend(scaleXYZList)
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
                        
                        if boneP.constraints.get('Copy Transforms') is not None:
                            targetBoneP = obj.pose.bones[boneP.name.replace(".rig", ".aim.rig")]
                            targetBoneDataPath = targetBoneP.path_from_id()

                            fcurve = action.fcurves.find(targetBoneDataPath + ".location",index=i)
                            if fcurve:
                                channelsList.extend(locationXYZList + rotationQEList)
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
            #------------------------------------------------------------------------------------------------------------------------------------
        StateUtility.RemoveConstraintsOfSelectedPoseBones()
        

        #deselect all to
        bpy.ops.pose.select_all(action='DESELECT')
        #select bones to remove, to remove their keyframes first
        for rigBone in selectedAimBonesNameList:
            armature.bones[rigBone].select = True

        for nbone in nbonesToremove:
            try:
                armature.bones[nbone].select = True
            except:
                continue

        if obj.animation_data:
            #clear all key frames of selected bones
            StateUtility.KeyframeClear()

        #remove selected aim bones
        StateUtility.SetEditMode()

        nbonesToremove.extend(selectedAimBonesNameList)

        for nbone in nbonesToremove:
            try:
                armature.edit_bones.remove(armature.edit_bones[nbone])
            except:
                continue
        
        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')
        
        bpy.ops.pose.select_all(action='DESELECT')

        #check if there are any stretch chain selected to reapply inherit rotation and scale
        if len(stretchChainListN) > 0:
            #reapply inherit rotation if it was active before launching the script
            if len(inheritedRotationListN) > 0:
                for boneN in inheritedRotationListN:
                    armature.bones[boneN].select = True
                InheritRotationOnUtils.InheritRotationOn(self, context)
            bpy.ops.pose.select_all(action='DESELECT')

            #reapply inherit scale if it was active before launching the script
            if len(inheritedScaleListN) > 0:
                for boneN in inheritedScaleListN:
                    armature.bones[boneN].select = True
                InheritScaleOnUtils.InheritScaleOn(self, context)
            bpy.ops.pose.select_all(action='DESELECT')

        #select bones affected by selected aim bones
        for pbone in pbonesToSelect:
            pbone.bone.select = True