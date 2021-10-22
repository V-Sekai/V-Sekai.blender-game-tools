#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils

class ParentSpaceUtils:

    @staticmethod
    def ParentSpaceCondition ():
        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')
        for activeBoneParent in bpy.context.active_pose_bone.parent_recursive:
            for selectedBoneP in bpy.context.selected_pose_bones:
                if activeBoneParent == selectedBoneP:
                    return [{'WARNING'}, "target parent is child of selection"]
    
    @staticmethod
    def ParentSelectionCondition ():
        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')
        if len(bpy.context.selected_pose_bones)<= 1 :
            return [{'WARNING'}, "select more than one bone"]

    @staticmethod
    def ParentDuplicateRename ():

        #force edit mode in case it was not
        StateUtility.SetEditMode()

        #active bone will become the parent of the rest of the selected bones
        activeBoneN = bpy.context.active_bone.name
        parentBoneN = str()
        tempParentBoneN = str()
        
        #possible suffixes for bone name extensions
        suffixToDelete = ["IK","parent", "child", "world", "top", "rig", "parentCopy", "aimOffset"]
        activeBoneNSplit = activeBoneN.split(".")

        #loop over each word split by '.' in the bone name
        previousMatch = False
        first = True
        for word in activeBoneNSplit:
            match = False
            
            #check if one of the suffixes matches the word 
            for suffix in suffixToDelete:
                if word == suffix:
                    match = True

            #if match remember word in case next word does not match 
            if match:
                tempParentBoneN = tempParentBoneN + "."+ word
                previousMatch = True
            else:

                #if previous was a match use the temp words that was cached 
                if previousMatch:
                    parentBoneN = parentBoneN + tempParentBoneN
                    previousMatch = False
                    tempParentBoneN = str()
                
                #the first word does not start with a '.' but the others do
                if first:
                    parentBoneN = parentBoneN + word
                else:
                    parentBoneN = parentBoneN +"."+ word

                
            first = False
               
        parentBoneN = parentBoneN + ".rig"

        mainParentObjectBoneList = [bpy.context.active_object.name, parentBoneN]  #set aside active bone's object name and bone name
        #deselect active bone to not duplicate it in the next step.
        bpy.context.active_bone.select = False
        bpy.context.active_bone.select_head = False
        bpy.context.active_bone.select_tail = False

        #duplicate selected rig bones
        bpy.ops.armature.duplicate()

        #rename duplicated bones
        for boneE in bpy.context.selected_editable_bones:
            boneE.name = boneE.name.replace(".rig.001", ".child.rig")

        return mainParentObjectBoneList

    @staticmethod
    def SortSelectionIntoDictionaries ():
        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        activeObjectChildrenNList = list()
        nonActiveObjectDictionary = dict()

        #go through duplcated selected pose bones
        for boneP in bpy.context.selected_pose_bones:

            #if boneP is part of the active object, add it to the activeObjectDictionary using object name as key
            if boneP.id_data == bpy.context.active_object:
                activeObjectChildrenNList.append(boneP.name)
            
            #if boneP is not part of the active object, add it to nonActiveObjectDictionary using object name as key
            else:
                if boneP.id_data.name in nonActiveObjectDictionary:
                    nonActiveObjectDictionary[boneP.id_data.name].append(boneP.name)
                else:
                    nonActiveObjectDictionary[boneP.id_data.name] = [boneP.name]

        return [activeObjectChildrenNList, nonActiveObjectDictionary]
   
    @staticmethod    
    def ParentActiveArmature (activeObjectChildrenNList, mainParentObjectBoneList):

        #force edit mode
        StateUtility.SetEditMode()

        parentObjectN = mainParentObjectBoneList[0]
        activeObject = bpy.data.objects[parentObjectN]
        activeArmature = activeObject.data
        parentBoneN = mainParentObjectBoneList[1]
        parentBoneE = activeArmature.edit_bones[parentBoneN]

        #change bones' parent in the activeObjectChildrenNList to parentBoneE
        for boneN in activeObjectChildrenNList:
            boneE = activeArmature.edit_bones[boneN]
            boneE.parent = parentBoneE

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #deselects all pose bones
        bpy.ops.pose.select_all(action='DESELECT')
        
        #select bones in activeObjectChildrenNList so they are the only ones baked in this step along with parentBoneE
        for childBoneN in activeObjectChildrenNList:
            activeArmature.bones[childBoneN].select = True

        #change child bones' display to octagon, rotation mode to euler YZX and add copy transform constraint to copy the rig bones' animation.
        for boneN in activeObjectChildrenNList:
            boneP = activeObject.pose.bones[boneN]
            boneP.custom_shape = bpy.data.objects["RotF_Octagon"]
            boneP.custom_shape_scale *= 1.2
            copyTransforms = boneP.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = activeObject
            copyTransforms.subtarget = boneN.replace(".child.rig",".rig")
        
        #if object being rigged has animation data
        if activeObject.animation_data:
            # -----------------------------------------------------------------------------------------------------------------------------------
            #BAKE SELECTED BONES
            objectActionsDictionary = StateUtility.FindActions() #find relevant action for each selected object
            ActionInitialState = StateUtility.ActionInitialState(objectActionsDictionary) #store objects' actions state to know if they were in tweak mode
            
            initialAction = activeObject.animation_data.action

            for obj in objectActionsDictionary:
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
                        
                        targetBoneP = obj.pose.bones[boneP.name.replace(".child.rig",".rig")]
                        targetBoneDataPath = targetBoneP.path_from_id()

                        #if one category of transforms (location, rotation, scale) is found. Add all index of the transform (XYZ, WXYZ) to the channelsList to be keyed.
                        DypsloomBakeUtils.AllTranformsChannels(action, frames, targetBoneDataPath, channelsList)

                        bonePChannelsToBake[boneP] = channelsList

                    DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)

                StateUtility.RestoreTracksState(activeObject, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                activeObject.animation_data.action = initialAction
            
            StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
            #------------------------------------------------------------------------------------------------------------------------------------
        StateUtility.RemoveConstraintsOfSelectedPoseBones()

        #deselects all pose bones
        bpy.ops.pose.select_all(action='DESELECT')

        #initially selected bones follow .child.rig bones
        for childBoneN in activeObjectChildrenNList:
            rigBone = activeObject.pose.bones[childBoneN.replace(".child.rig",".rig")]
            copyTransforms = rigBone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = activeObject
            copyTransforms.subtarget = childBoneN
            #select initial rig bones to switch them to hidden layer 3 later
            activeArmature.bones[childBoneN.replace(".child.rig",".rig")].select = True
        
        if activeObject.animation_data:
                #clear all key frames of selected bones
                StateUtility.KeyframeClear()
        
        #move originally selected bones to the unused layer
        unusedLayer = activeObject.unusedRigBonesLayer
        StateUtility.MoveBonesToLayer(unusedLayer)
        #deselects all
        bpy.ops.pose.select_all(action='DESELECT')

    @staticmethod
    def ParentNonActiveArmature (nonActiveObjectDictionary, mainParentObjectBoneList):
        for childObjectN in nonActiveObjectDictionary:

            #force edit mode
            StateUtility.SetEditMode()

            #get all the data for the main parent
            mainObjectN = mainParentObjectBoneList[0]
            mainObject = bpy.data.objects[mainObjectN]
            mainArmature = mainObject.data
            mainParentBoneN = mainParentObjectBoneList[1]

            obj = bpy.data.objects[childObjectN]
            armature = obj.data        
            childrenBoneNList = nonActiveObjectDictionary[childObjectN]

            #set unused layer to visible
            unusedLayer = obj.unusedRigBonesLayer
            armature.layers[unusedLayer] = True

            #add a new bone that will act as parent for the children bones of non active armatures
            newParentBoneE = armature.edit_bones.new(mainParentBoneN.replace(".rig",".parentCopy.rig"))
            newParentBoneE.length = mainArmature.edit_bones[mainParentBoneN].length
            newParentBoneE.use_deform = False
            newParentBoneN = newParentBoneE.name

            #go through the selected bones in the children armature
            for childBoneN in childrenBoneNList:
                childBoneE = armature.edit_bones[childBoneN]
                #change bone parent to active bone
                childBoneE.parent = newParentBoneE

            #force pose mode
            bpy.ops.object.mode_set(mode='POSE')
            #change child bones' display to octagon, rotation mode to euler YZX and adds copy transform constraint to copy the rig bones' animation.
            for childBoneN in childrenBoneNList:
                childBoneP = obj.pose.bones[childBoneN]
                childBoneP.custom_shape = bpy.data.objects["RotF_Octagon"]
                childBoneP.custom_shape_scale *= 1.2
                copyTransforms = childBoneP.constraints.new('COPY_TRANSFORMS')
                copyTransforms.target = obj
                copyTransforms.subtarget = childBoneN.replace(".child.rig",".rig")
                #select childBone for future baking
                obj.data.bones[childBoneN].select = True

            #change parent bone's display to octagon, rotation mode to euler YZX and adds copy transform constraint to copy the rig bone's animation.
            newParentBoneP = obj.pose.bones[newParentBoneN]
            newParentBoneP.custom_shape = bpy.data.objects["RotF_Octagon"]
            newParentBoneP.custom_shape_scale *= 1.2
            armature.bones[newParentBoneN].show_wire = True
            copyTransforms = newParentBoneP.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = mainObject
            copyTransforms.subtarget = mainParentBoneN

            #if object being rigged has animation data
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
                            
                            #targetBoneP = mainObject.pose.bones[mainParentBoneN] # obj.pose.bones[boneP.name.replace(".child.rig",".rig")]
                            targetBoneP = obj.pose.bones[boneP.name.replace(".child.rig",".rig")]
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

            #initially selected bones follow child bones
            for childBoneN in childrenBoneNList:
                rigBone = obj.pose.bones[childBoneN.replace(".child.rig",".rig")]
                copyTransforms = rigBone.constraints.new('COPY_TRANSFORMS')
                copyTransforms.target = obj
                copyTransforms.subtarget = childBoneN
                #select initial rig bones switch to hidden layer 3
                obj.data.bones[rigBone.name].select = True

            #select newParentBone to switch to hidden layer 3
            obj.data.bones[newParentBoneN].select = True

            if obj.animation_data:
                #clear all key frames of selected bones
                StateUtility.KeyframeClear()
            #moves initially selected bone to unused layer
            StateUtility.MoveBonesToLayer(unusedLayer)
            #deselects all
            bpy.ops.pose.select_all(action='DESELECT')
            #set layer 3 to visible to prevent issues with bpy.ops.armature.select_all(action='DESELECT')
            obj.data.layers[unusedLayer] = False

    @staticmethod
    def ParentCopyActiveArmature (activeObjectChildrenNList, mainParentObjectBoneList):

        #force edit mode
        StateUtility.SetEditMode()

        parentObjectN = mainParentObjectBoneList[0]
        activeObject = bpy.data.objects[parentObjectN]
        activeArmature = activeObject.data
        activeBoneN = mainParentObjectBoneList[1]

        #find parent bone in edit mode
        activeBoneE = activeArmature.edit_bones[activeBoneN]

        #deselect all bones
        bpy.ops.armature.select_all(action='DESELECT')

        #select parentBoneE
        activeBoneE.select = True
        activeBoneE.select_head = True
        activeBoneE.select_tail = True

        #duplicate active bone
        bpy.ops.armature.duplicate()

        #set duplicated bone as parentBoneE and rename it with ".parentCopy.rig"
        parentBoneE = bpy.context.active_bone
        parentBoneE.name = parentBoneE.name.replace(".rig.001", ".parentCopy.rig")
        parentBoneN = parentBoneE.name
        parentBoneE.parent = None #set it's parent to None

        #remove the active bone's parent
        parentBoneE = activeArmature.edit_bones[parentBoneN]
        parentBoneE.parent = None

        for boneN in activeObjectChildrenNList:
            boneE = activeArmature.edit_bones[boneN]
            boneE.parent = parentBoneE

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #change parent bone display to octagon, rotation mode to euler YZX and add copy transform constraint to copy the rig bone's animation.
        parentBoneP = activeObject.pose.bones[parentBoneN]
        if "CoM" in parentBoneN:
            parentBoneP.custom_shape = bpy.data.objects["RotF_Sphere"]
        else:
            parentBoneP.custom_shape = bpy.data.objects["RotF_Octagon"]
        activeObject.data.bones[parentBoneN].show_wire = True
        parentBoneP.custom_shape_scale *= 1.5
        copyParentTransforms = parentBoneP.constraints.new('COPY_TRANSFORMS')
        copyParentTransforms.target = activeObject
        copyParentTransforms.subtarget = parentBoneN.replace(".parentCopy.rig",".rig")


        #change child bones' display to octagon, rotation mode to euler YZX and adds copy transform constraint to copy the rig bones animation.
        for boneN in activeObjectChildrenNList:
            bone = activeObject.pose.bones[boneN]
            bone.custom_shape = bpy.data.objects["RotF_Octagon"]
            bone.custom_shape_scale *= 1.2
            copyTransforms = bone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = activeObject
            copyTransforms.subtarget = boneN.replace(".child.rig",".rig")
            activeArmature.bones[boneN].select = True

        #if object being rigged has animation data
        if activeObject.animation_data:
            # -----------------------------------------------------------------------------------------------------------------------------------
            #BAKE SELECTED BONES
            objectActionsDictionary = StateUtility.FindActions() #find relevant action for each selected object
            ActionInitialState = StateUtility.ActionInitialState(objectActionsDictionary) #store objects' actions state to know if they were in tweak mode
            
            initialAction = activeObject.animation_data.action
            
            for obj in objectActionsDictionary:
                print("object " + obj.name)
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

                        print("selected pbone "+ boneP.name)
                        
                        targetBoneP = obj.pose.bones[boneP.name.replace(".child.rig",".rig")]
                        targetBoneP = obj.pose.bones[boneP.name.replace(".parentCopy.rig",".rig")]
                        print("target pbone "+ targetBoneP.name)
                        targetBoneDataPath = targetBoneP.path_from_id()

                        #if one category of transforms (location, rotation, scale) is found. Add all index of the transform (XYZ, WXYZ) to the channelsList to be keyed.
                        DypsloomBakeUtils.AllTranformsChannels(action, frames, targetBoneDataPath, channelsList)

                        bonePChannelsToBake[boneP] = channelsList

                    DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)
            
                StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack

            activeObject.animation_data.action = initialAction
            
            StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
            #------------------------------------------------------------------------------------------------------------------------------------
        StateUtility.RemoveConstraintsOfSelectedPoseBones()

        #deselects all
        bpy.ops.pose.select_all(action='DESELECT')

        #initially selected bones follow child bones
        for childBoneN in activeObjectChildrenNList:
            rigBone = activeObject.pose.bones[childBoneN.replace(".child.rig",".rig")]
            copyTransforms = rigBone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = activeObject
            copyTransforms.subtarget = childBoneN
            #select initial rig bones to switch them to hidden layer 3 later
            activeArmature.bones[childBoneN.replace(".child.rig",".rig")].select = True
        
        if activeObject.animation_data:
                #clear all key frames of selected bones
                StateUtility.KeyframeClear()
        
        unusedLayer = activeObject.unusedRigBonesLayer
        StateUtility.MoveBonesToLayer(unusedLayer)      
        #deselects all
        bpy.ops.pose.select_all(action='DESELECT')
