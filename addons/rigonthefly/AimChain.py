#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils
from . PolygonShapesUtility import PolygonShapes

class AimChainUtils:

    def ChangeToAimChain (self, context):
        PolygonShapes.AddControllerShapes() #add conrtoller shapes to the scene

        obj = bpy.context.object
        armature = obj.data

        unusedLayer = obj.unusedRigBonesLayer

        #armature set to pose mode
        bpy.ops.object.mode_set(mode='POSE')

        selectedRigBoneNameList = list()
        for pbone in bpy.boneSelection:
            selectedRigBoneNameList.append(pbone.name)
        
        #force edit mode
        StateUtility.SetEditMode()

        selectedRigBonesListE = list()
        for boneN in selectedRigBoneNameList:
            selectedRigBonesListE.append(armature.edit_bones[boneN])
        
        #duplicate rig bones to be used as aim bones
        bpy.ops.armature.duplicate()
       
        #add .aim.rig suffix to duplicate bones now known as aim bones.
        for copiedBoneE in bpy.context.selected_editable_bones:
            copiedBoneE.name = copiedBoneE.name.replace(".rig.001",".aim.rig")

            #find the matrix coordinates of the armature object
            armatureMatrix = obj.matrix_world
            #invert armature's matrix to find where global(0,0,0) is in relation to the armature's position/roation
            armatureMatrixInvert= armatureMatrix.copy()
            armatureMatrixInvert.invert()
            #set aim bone position to global (0,0,0) with axis following world's
            copiedBoneE.matrix = armatureMatrixInvert

            copiedBoneE.length = armature.bones[copiedBoneE.name.replace(".aim.rig",".rig")].length

        #unparent aim bones for world Chain translation
        aimBonesListE = bpy.context.selected_editable_bones.copy()
        aimBoneNameList = list()
        for aimBone in aimBonesListE:
            aimBoneNameList.append(aimBone.name)
            aimBone.parent = None

        #armature set to pose mode
        bpy.ops.object.mode_set(mode='POSE')

        aimBonesListN = list()
        for bone in selectedRigBoneNameList:
            aimBonesListN.append(bone.replace(".rig",".aim.rig"))
        ikBonesListN = aimBonesListN[:-1]
        ikSubtargetListN = aimBonesListN[1:]


        #change rig bones' display to square, rotation mode to euler YZX and adds copy transform constraint to copy the rig bones animation.
        for aimBoneN in aimBonesListN:
            aimBone = obj.pose.bones[aimBoneN]
            aimBone.custom_shape = bpy.data.objects["RotF_SquarePointer+Y"]
            armature.bones[aimBoneN].show_wire = True
            aimBone.rotation_mode = 'YZX'
            copyTransforms = aimBone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = obj
            copyTransforms.subtarget = aimBoneN.replace(".aim.rig",".rig")

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
                        
                        targetBoneP = obj.pose.bones[boneP.name.replace(".aim.rig",".rig")]
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

        #make bone list "aim" at their child with IK constraint
        for i in range(len(ikBonesListN)):
            ikPBone = obj.pose.bones[ikBonesListN[i]]            
            ik = ikPBone.constraints.new('IK')
            ik.target = obj
            ik.subtarget = ikSubtargetListN[i]
            ik.chain_count = 1
            
            #add custom property to ikSubtargetPBone to help point at the aim bone pointing to it.
            ikSubtargetPBone = obj.pose.bones[ikSubtargetListN[i]]
            rna_ui = ikSubtargetPBone.get('_RNA_UI')
            if rna_ui is None:
                ikSubtargetPBone['_RNA_UI'] = {}
                rna_ui = ikSubtargetPBone['_RNA_UI']

            aimParentN = ikBonesListN[i]
            ikSubtargetPBone["Aim Parent"] = str(aimParentN)

        #make rig bones follow coresponding aim bones
        for aimBoneN in aimBonesListN:
            copyTransforms = obj.pose.bones[aimBoneN.replace(".aim.rig",".rig")].constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = obj
            copyTransforms.subtarget = aimBoneN

        #select rig bones to move them to hidden bone layer 3
        bpy.ops.pose.select_all(action='DESELECT')
        for rigBoneN in selectedRigBoneNameList:            
            armature.bones[rigBoneN].select = True
            
        if obj.animation_data:
            #clear all key frames of selected bones
            StateUtility.KeyframeClear()
        StateUtility.MoveBonesToLayer(unusedLayer)

        #end script with new aim bones selected
        bpy.ops.pose.select_all(action='DESELECT')
        for aimBoneN in aimBonesListN:
            armature.bones[aimBoneN].select = True
        