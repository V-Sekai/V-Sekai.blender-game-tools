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
from . PolygonShapesUtility import PolygonShapes

class RemoveLocalAimChainUtils:

    @staticmethod
    def SelectFullAimChain (pbone):
        obj = pbone.id_data

        pbonesFromChainList = list()

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
                    #if ".aim.rig" in cSubtarget:
                    targetPBone = cTarget.pose.bones[cSubtarget]
                    targetPBone.bone.select = True
                    aimPBone = targetPBone

                    #add targetPBone to pbonesFromChainList
                    if not targetPBone in pbonesFromChainList:
                        pbonesFromChainList.append(targetPBone)

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

                #add aimParentPBone to pbonesFromChainList
                if not aimParentPBone in pbonesFromChainList:
                    pbonesFromChainList.append(aimParentPBone)
            else:
                isAimTarget = False

        return(pbonesFromChainList)

    def RemoveLocalAimChain (self, context):

        obj = bpy.context.object

        pbonesFromChainList = list()

        #sort selected pose bones to exclude the ones not containing ".aim.rig" and select the rest of aim chains if they are partially selected
        for pbone in bpy.context.selected_pose_bones:
            #check if pbone is part of an aim chain
            pbonesFromChainList += RemoveLocalAimChainUtils.SelectFullAimChain(pbone)
            
        #checking if all bones from aim chains are selected
        for pbone in pbonesFromChainList:
            if not pbone in bpy.context.selected_pose_bones:
                print("part of aim chain is not selectable")
                return [{'WARNING'}, "part of aim chain is hidden"]

        #deselect bones without IK or Stretch To constraints
        for pbone in bpy.context.selected_pose_bones:
            if not pbone.constraints:
                pbone.bone.select = False
            else:
                for constraint in pbone.constraints:
                    if any (constraint.type == cType for cType in ['IK','STRETCH_TO']):
                        pbone.bone.select = True
                    else:
                        pbone.bone.select = False

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
                        for constraint in boneP.constraints:
                            if any (constraint.type == cType for cType in ['IK','STRETCH_TO']):
                                targetBoneN = constraint.subtarget
                                targetBoneP = obj.pose.bones[targetBoneN]
                                targetBoneDataPath = targetBoneP.path_from_id()

                        #looking for translation channels
                        for i in range(3):
                            fcurve = action.fcurves.find(targetBoneDataPath + ".location",index=i)
                            if fcurve:
                                channelsList.extend(rotationQEList)
                                StateUtility.GetFramePointFromFCurve(fcurve, frames)
                                if boneP.constraints.get('Stretch To') is not None:
                                    channelsList.extend(scaleXYZList)
                        """
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
                        """

                        bonePChannelsToBake[boneP] = channelsList
                    DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)

                StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                obj.animation_data.action = initialAction
            StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
            #------------------------------------------------------------------------------------------------------------------------------------
        StateUtility.RemoveConstraintsOfSelectedPoseBones()

        PolygonShapes.AddControllerShapes() #add conrtoller shapes to the scene

        for pbone in bpy.context.selected_pose_bones:
            if pbone.custom_shape == bpy.data.objects["RotF_CirclePointer+Y"]:
                pbone.custom_shape = bpy.data.objects["RotF_Circle"]
            elif pbone.custom_shape == bpy.data.objects["RotF_SquarePointer+Y"]:
                pbone.custom_shape = bpy.data.objects["RotF_Square"]
