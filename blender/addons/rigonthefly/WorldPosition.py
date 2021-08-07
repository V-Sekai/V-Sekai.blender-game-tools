#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils
from . PolygonShapesUtility import PolygonShapes

class WorldPositionUtils:

    def WorldPosition (self, context):
        PolygonShapes.AddControllerShapes() #add conrtoller shapes to the scene

        obj = bpy.context.object
        armature = obj.data

        unusedLayer = obj.unusedRigBonesLayer

        #force edit mode
        StateUtility.SetEditMode()

        #list selected bones' names
        selectedBonesNames = list()
        for selectedBone in bpy.context.selected_editable_bones:
            selectedBonesNames.append(selectedBone.name)

        #duplicate base armature. Duplicate bones are selected from this operation.
        bpy.ops.armature.duplicate()

        #add .rig suffix to duplicate bones now known as rig bones.
        for copiedBone in bpy.context.selected_editable_bones: 
            copiedBone.name = copiedBone.name.replace(".rig.001",".world.rig")

            #find the matrix coordinates of the armature object
            armatureMatrix = obj.matrix_world
            #invert armature's matrix to find where global(0,0,0) is in relation to the armature's position/roation
            armatureMatrixInvert= armatureMatrix.copy()
            armatureMatrixInvert.invert()
            #set aim bone position to global (0,0,0) with axis following world's
            copiedBone.matrix = armatureMatrixInvert

            copiedBone.length = armature.bones[copiedBone.name.replace(".world.rig",".rig")].length

        #list duplicated bones' names
        duplicatedBonesNames = list()
        for duplicatedBone in bpy.context.selected_editable_bones:
            duplicatedBonesNames.append(duplicatedBone.name)
            duplicatedBone.parent = None

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #
        for duplicatedBone in bpy.context.selected_pose_bones:
            duplicatedBone.custom_shape = bpy.data.objects["RotF_Square"]
            armature.bones[duplicatedBone.name].show_wire = True

            copyTransform = duplicatedBone.constraints.new('COPY_TRANSFORMS')
            copyTransform.target = obj
            copyTransform.subtarget = duplicatedBone.name.replace(".world.rig",".rig")
        
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
                        
                        targetBoneP = obj.pose.bones[boneP.name.replace(".world.rig",".rig")]
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

        bpy.ops.pose.select_all(action='DESELECT')

        #
        for selectedBoneName in selectedBonesNames:
            armature.bones[selectedBoneName].select =True

            copyTransform = obj.pose.bones[selectedBoneName].constraints.new('COPY_TRANSFORMS')
            copyTransform.target = obj
            copyTransform.subtarget = selectedBoneName.replace(".rig",".world.rig")

        if obj.animation_data:
            #clear all key frames of selected bones
            StateUtility.KeyframeClear()

        #move bones to unused layer
        StateUtility.MoveBonesToLayer(unusedLayer)

        #
        for duplicatedBoneName in duplicatedBonesNames:
            armature.bones[duplicatedBoneName].select =True