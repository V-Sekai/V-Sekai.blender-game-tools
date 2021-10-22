#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils
from . AddExtraBone import AddExtraBoneUtils
from . PolygonShapesUtility import PolygonShapes

class AimOffsetUtils:

    def AimOffset (self, context):
        PolygonShapes.AddControllerShapes() #add conrtoller shapes to the scene

        targetPBonesList = list()
        for selectedPBone in bpy.context.selected_pose_bones:
            #armature set to pose mode
            bpy.ops.object.mode_set(mode='POSE')

            selectedNBone = selectedPBone.name

            obj = selectedPBone.id_data
            armature = obj.data

            unusedLayer = obj.unusedRigBonesLayer

            #deselect all pose bones
            bpy.ops.pose.select_all(action='DESELECT')

            aimTargetPBone = AddExtraBoneUtils.AddExtraBone(self, context)
            aimTargetPBone.name = selectedNBone.replace(".rig",".aim.rig")

            #snap new pAimTarget to the 3d cursor's position
            bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)

            childOf = aimTargetPBone.constraints.new('CHILD_OF')
            childOf.target = obj
            childOf.subtarget = selectedPBone.name

            armature.bones.active = aimTargetPBone.bone
            for c in aimTargetPBone.constraints:
                if c.type == "CHILD_OF":
                    context_copy = bpy.context.copy()
                    context_copy["constraint"] = c
                    bpy.ops.constraint.childof_set_inverse(context_copy, constraint=c.name, owner='BONE')
            
            #deselect all pose bones
            bpy.ops.pose.select_all(action='DESELECT')

            #select activeBone for duplication
            selectedPBone.bone.select = True

            #force edit mode
            StateUtility.SetEditMode()

            #duplicate activeBone to have offsetBone. It will point towards the new aimTargetBone
            bpy.ops.armature.duplicate()

            offsetNBone = selectedNBone.replace(".rig",".aimOffset.rig")
            bpy.context.selected_editable_bones[0].name = offsetNBone

            #duplicate offsetBone to have aimCopyBone. It will be set as child of the offsetBone and the activeBone will be constraint to it.
            bpy.ops.armature.duplicate()

            aimCopyNBone = selectedNBone.replace(".rig",".aimCopy.rig")
            bpy.context.selected_editable_bones[0].name = aimCopyNBone
            bpy.context.selected_editable_bones[0].parent = armature.edit_bones[offsetNBone]

            #armature set to pose mode
            bpy.ops.object.mode_set(mode='POSE')

            aimCopyPBone = bpy.context.selected_pose_bones[0]

            offsetPBone = obj.pose.bones[offsetNBone]
            offsetPBone.custom_shape = bpy.data.objects["RotF_CirclePointer+Y"]
            offsetPBone.custom_shape_scale *= 1.5

            if not aimCopyPBone.bone.use_inherit_rotation:
                aimCopyPBone.bone.use_inherit_rotation = True
            if not aimCopyPBone.bone.use_inherit_scale:
                aimCopyPBone.bone.use_inherit_scale = True

            for pbone in [aimCopyPBone, offsetPBone]:
                copyTransforms = pbone.constraints.new('COPY_TRANSFORMS')
                copyTransforms.target = obj
                copyTransforms.subtarget = selectedNBone

            ik = offsetPBone.constraints.new('IK')
            ik.target = obj
            ik.subtarget = aimTargetPBone.name
            ik.chain_count = 1

            aimTargetPBone.bone.select = True
            offsetPBone.bone.select = True

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

                         

                        targetBoneP = obj.pose.bones[selectedNBone]
                        targetBoneDataPath = targetBoneP.path_from_id()

                        locationXYZList = [Channel.locationX, Channel.locationY, Channel.locationZ]                  

                        for boneP in bpy.context.selected_pose_bones:
                            channelsList = list()
                            
                            #looking for translation channels
                            for i in range(3):
                                fcurve = action.fcurves.find(targetBoneDataPath + ".location",index=i)
                                if fcurve:
                                    channelsList.extend(locationXYZList)
                                    StateUtility.GetFramePointFromFCurve(fcurve, frames)
                            #looking for quaternion channels
                            for i in range(4):
                                fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=i)
                                if fcurve:
                                    channelsList.extend(locationXYZList)
                                    StateUtility.GetFramePointFromFCurve(fcurve, frames)
                            #looking for euler channels
                            for i in range(3):
                                fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=i)
                                if fcurve:
                                    channelsList.extend(locationXYZList)
                                    StateUtility.GetFramePointFromFCurve(fcurve, frames)

                            bonePChannelsToBake[boneP] = channelsList
                        DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)
                        
                    StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                    obj.animation_data.action = initialAction
                StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
                #------------------------------------------------------------------------------------------------------------------------------------
            StateUtility.RemoveConstraintsOfSelectedPoseBones()

            copyTransforms = selectedPBone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = obj
            copyTransforms.subtarget = aimCopyNBone

            ik = offsetPBone.constraints.new('IK')
            ik.target = obj
            ik.subtarget = aimTargetPBone.name
            ik.chain_count = 1

            #deselect all pose bones
            bpy.ops.pose.select_all(action='DESELECT')

            selectedPBone.bone.select = True

            if obj.animation_data:
                #clear all key frames of selected bones
                StateUtility.KeyframeClear()

            aimCopyPBone.bone.select = True

            StateUtility.MoveBonesToLayer(unusedLayer)

            #deselect all pose bones
            bpy.ops.pose.select_all(action='DESELECT')

            targetPBonesList.append(aimTargetPBone)

        for pbone in targetPBonesList:
            pbone.bone.select = True


        