#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils

class RestoreParentSpaceUtils:    
    def RestoreSelectedChildren (self, context):
        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #list bones containing the suffix ".child.rig" in their name
        objectNChildrenBoneNList = dict()
        for boneP in bpy.context.selected_pose_bones:
            objN = boneP.id_data.name
            boneN = boneP.name
            if ".child.rig" in boneP.name:
                if objN in objectNChildrenBoneNList:
                    objectNChildrenBoneNList[objN].append(boneN)
                else:
                    objectNChildrenBoneNList[objN] = [boneN]

        #deselects all bones
        bpy.ops.pose.select_all(action='DESELECT')

        bonesToSelectList = list()

        #from objectNChildrenBoneNList select the ".rig" version of the initially selected ".child.rig" bones
        for objN in objectNChildrenBoneNList:
            obj = bpy.data.objects[objN]
            armature = obj.data

            unusedLayer = obj.unusedRigBonesLayer
            armature.layers[unusedLayer] = True
            for childN in objectNChildrenBoneNList[objN]:
                originalBoneN = childN.replace(".child.rig", ".rig")
                originalBone = armature.bones[originalBoneN]
                originalBone.select = True
                originalPBone = obj.pose.bones[originalBoneN]
                bonesToSelectList.append(originalPBone)

                #move originalBone to the same layers as child bone
                for layer in range(32):
                    armature.bones[originalBoneN].layers[layer] = armature.bones[childN].layers[layer]

            #if object being rigged has animation data, bake the ".rig" version of the initially selected ".child.rig" bones
            if obj.animation_data:
                # -----------------------------------------------------------------------------------------------------------------------------------
                #BAKE SELECTED BONES
                objectActionsDictionary = StateUtility.FindActions() #find relevant action for each selected object
                ActionInitialState = StateUtility.ActionInitialState(objectActionsDictionary) #store objects' actions state to know if they were in tweak mode
                
                initialAction = obj.animation_data.action

                tracksStateDict, soloTrack, activeActionBlendMode = StateUtility.SoloRestPoseTrack(obj) #add an nla track to solo so that baking is done without other tracks influencing the result

                for obj in objectActionsDictionary:
                    for action in objectActionsDictionary[obj]:
                        obj.animation_data.action = action #switch obj's current action
                        
                        
                        frames = list() #list of frames to key
                        bonePChannelsToBake = dict() #dictionary containing which channels to key on selected pose bones 

                        if not bpy.context.scene.smartFrames:
                            frameRange = action.frame_range
                            frames = [*range(int(frameRange.x), int(frameRange.y) + 1, 1)]

                                           

                        for boneP in bpy.context.selected_pose_bones:
                            channelsList = list()
                            
                            targetBoneP = obj.pose.bones[boneP.name.replace(".rig", ".child.rig")]
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

            #deselects all bones
            bpy.ops.pose.select_all(action='DESELECT')

        objectNBonesNToRemoveList = objectNChildrenBoneNList

        #select ".child.rig" bones to delete them
        for objN in objectNChildrenBoneNList:
            obj = bpy.data.objects[objN]
            armature = obj.data

            #list related ".parentCopy.rig" bones in parentsToRemoveDict
            parentsToRemoveDict = dict()
            for childN in objectNChildrenBoneNList[objN]:
                parentN = obj.pose.bones[childN].parent.name
                if ".parentCopy.rig" in parentN:
                    parentsToRemoveDict[parentN] = [True]

            for parentN in parentsToRemoveDict:
                parentsChildrenPList = obj.pose.bones[parentN].children

                for child in parentsChildrenPList:
                    for childN in objectNChildrenBoneNList[objN]:
                        armature.bones[childN].select = True #add initially selected bones to selection
                        if child.name != childN:
                            parentsToRemoveDict[parentN] = [False]
                            print("not all children of .parentCopy.rig are in initial selection")
                            break
                    if parentsToRemoveDict[parentN][0] == False:
                        break
                #add to selection parents that have all their children in the initial selection
                if parentsToRemoveDict[parentN][0]:
                    armature.bones[parentN].select = True
                    objectNBonesNToRemoveList[objN].append(parentN) #add .parentCopy.rig to bones to remove
        
        for objN in objectNBonesNToRemoveList:
            obj = bpy.data.objects[objN]
            armature = obj.data

            for boneN in objectNBonesNToRemoveList[objN]:
                armature.bones[boneN].select = True
        """
        for obj in bpy.context.selectable_objects:
            if obj.animation_data:
        """
        #clear all key frames of selected bones
        StateUtility.KeyframeClear()

        #force edit mode
        StateUtility.SetEditMode()
        for objN in objectNBonesNToRemoveList:
            obj = bpy.data.objects[objN]
            armature = obj.data

            for boneN in objectNBonesNToRemoveList[objN]:
                armature.edit_bones.remove(armature.edit_bones[boneN])
            
            unusedLayer = obj.unusedRigBonesLayer
            armature.layers[unusedLayer] = False

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        for pbone in bonesToSelectList:
            pbone.bone.select = True

    def SelectSiblingsPerArmature (self, context):
        #make list out of selection
        selectedBonesPList = bpy.context.selected_pose_bones.copy()
        selectedBonesPList.sort(key = lambda x:len(x.parent_recursive))

        #list for bones containing ".child.rig" in their name
        selectedChildrenPList = list()

        for boneP in selectedBonesPList:
            if ".child.rig" in boneP.name:
                selectedChildrenPList.append(boneP)

        #list parents of ".child.rig"
        parentPList = list()

        for childP in selectedChildrenPList:
            parentP = childP.parent
            if parentP not in parentPList:
                parentPList.append(parentP)

        #list all ".child.rig" under each parent in parentPList
        childrenPToSelectList = list()

        for parentP in parentPList:
            for childP in parentP.children:
                if ".child.rig" in childP.name:
                    childrenPToSelectList.append(childP)

        #deselect all bones
        bpy.ops.pose.select_all(action='DESELECT')

        #select children bones in childrenPToSelectList
        for childP in childrenPToSelectList:
            childP.bone.select = True
