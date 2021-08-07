#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from mathutils import Matrix, Euler, Vector
from typing import NamedTuple
from bpy_extras.io_utils import axis_conversion
from enum import Enum
import re

from bpy_extras import anim_utils

class StateUtility:

    @staticmethod
    def SetEditMode (toggleMirror=False):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.context.object.data.use_mirror_x = toggleMirror

    @staticmethod
    def SaveState ():
        mode = bpy.context.mode
        selectionEditableBones = bpy.context.selected_editable_bones
        selectionPoseBones = bpy.context.selected_pose_bones
        return StateData(mode,selectionEditableBones,selectionPoseBones)

    @staticmethod
    def RecoverState (stateData):
        bpy.ops.object.mode_set(mode= stateData.mode)
    
    @staticmethod
    def RemoveEditableBone(boneToRemove):
        StateUtility.SetEditMode()
        armature = bpy.context.object.data
        for bone in armature.edit_bones:
            if bone.name == boneToRemove.name:
                armature.edit_bones.remove(bone)

    @staticmethod
    def BoneListToNameList(boneList):
        nameList = []
        for b in boneList:
            nameList.append(b.name)
        return nameList       
    
    @staticmethod
    def LeftRightSuffix (name):
        leftSide = ["left","_l",".l","-l"," left"]
        rightSide = ["right","_r",".r","-r"," right"]
        suffix = str()
        prefix = str()

        for left in leftSide:
            if name.casefold().endswith(left):
                suffix = left
                prefix = "L."
        
        for right in rightSide:
            if name.casefold().endswith(right):
                suffix = right
                prefix = "R."

        if suffix:
            suffixSize = len(suffix)
            newName = prefix + name[:-suffixSize]
        else:
            newName = name
        return newName

    @staticmethod
    def FindOriginalBone (bone):
        leftSide = ["left","_l",".l","-l"," left","Left","LEFT","_L",".L","-L"," Left"," LEFT"]
        rightSide = ["right","_r",".r","-r"," right","Right","RIGHT","_R",".R","-R"," Right", " RIGHT"]
        sideSuffixes = list()
        armature = bone.id_data
        rigName = bone.name
        rigSuffix = str()

        if ".orient.rig" in rigName:
            rigSuffix = ".orient.rig"
        else:
            rigSuffix = ".rig"

        if rigName.startswith("L."):
            sideName = rigName.replace(rigSuffix,"")
            baseName = sideName.replace("L.","")
            sideSuffixes = leftSide

        elif rigName.startswith("R."):
            sideName = rigName.replace(rigSuffix,"")
            baseName = sideName.replace("R.","")
            sideSuffixes = rightSide

        for side in sideSuffixes:
            originalBN = baseName + side
            try:
                armature.bones[originalBN].select = True
                #print("found " + originalBN)
                break
            except:
                #print("did not find " + originalBN)
                continue

    @staticmethod
    def DuplicateBones(obj, nameIndex):
        initialMode = obj.mode
        armature = obj.data
        targetBoneDictionary = dict() #to contain the bones info from the target proxy rig needed create a copy of it that is not linked/referenced

        bpy.ops.object.mode_set(mode='EDIT')

        #add bone info to copy to targetBoneDictionary
        for boneE in bpy.context.selected_editable_bones:
            
            boneN = StateUtility.LeftRightSuffix(boneE.name)

            boneMatrix = boneE.matrix #head position and roll in edit mode
            boneTail = boneE.tail #tail position in edit mode
            #parent name
            if boneE.parent == None:
                boneParentN = ""
            else:
                originalParentN = boneE.parent.name
                newBoneParentN = StateUtility.LeftRightSuffix(originalParentN)
                
                if boneE.parent.select:
                    boneParentN = newBoneParentN + nameIndex
                else:    
                    boneParentN = originalParentN
            boneLayers = boneE.layers
            
            pBoneGroup = obj.pose.bones[boneE.name].bone_group #pose bone's group name

            targetBoneDictionary[boneN] = [boneMatrix, boneTail, boneParentN, boneLayers, pBoneGroup]

        #deselect all
        bpy.ops.armature.select_all(action='DESELECT')

        #create duplicate bones
        for boneN in targetBoneDictionary:
            newBone = armature.edit_bones.new(boneN + nameIndex)
            newBone.use_deform = False
            newBone.matrix = targetBoneDictionary[boneN][0] #head position and roll
            newBone.tail = targetBoneDictionary[boneN][1] #tail position
            newboneParentN = targetBoneDictionary[boneN][2] #parent name
            newBone.layers = targetBoneDictionary[boneN][3] #bone display layers
            
            newBoneParent = armature.edit_bones.get(newboneParentN) #convert parent name to edit bone        
            newBone.parent = newBoneParent #set a newBoneParent as parent of boneN

            newBone.select = True #add new bone to selection
            
        #set to pose mod
        bpy.ops.object.mode_set(mode='POSE')
        for boneN in targetBoneDictionary:
            boneP = obj.pose.bones[boneN + nameIndex]
            boneP.bone_group = targetBoneDictionary[boneN][4] #set pose bone group

        bpy.ops.object.mode_set(mode=initialMode)

    @staticmethod
    def BakeAnimationWithOptions(bakeOptions):

        #bake copied bones animation so that they have the same animation as the base armature.
        bpy.ops.nla.bake(
            frame_start=bakeOptions.frame_start, 
            frame_end=bakeOptions.frame_end, 
            only_selected=bakeOptions.only_selected, 
            visual_keying=bakeOptions.visual_keying, 
            clear_constraints=bakeOptions.clear_constraints,
            clear_parents=bakeOptions.clear_parents,
            use_current_action=bakeOptions.use_current_action, 
            bake_types={'POSE'}
        )

    @staticmethod
    def FindActions():
        objectActionsDictionary = dict()
        objectsList = list()
        #find object of selected bones
        for boneP in bpy.context.selected_pose_bones: #go through selected bones
            if boneP.id_data not in objectsList: #if bone's object is not yet on objectsList
                objectsList.append(boneP.id_data) #add bone's object to objectsList

        #find all actions used by objects in objectsList in their NLA tracks and puts them objectActionsDictionary
        for obj in objectsList: #go through objects in objectsList
            objectActionsDictionary[obj] = [] #add object name as key for objectActionsDictionary

            if obj.animation_data:
                if obj.animation_data.action:
                    currentAction = obj.animation_data.action
                    objectActionsDictionary[obj].append(currentAction) #add the current action to objectActionsDictionary[object name][list]

                for nlaTrack in obj.animation_data.nla_tracks: #go through object's nla tracks
                    for actionStrip in nlaTrack.strips: #go through the strips in it's nla tracks
                        action = actionStrip.action
                        if action not in objectActionsDictionary[obj]: #if action used in strips of the nla tracks are not yet in objectActionsDictionary...
                            objectActionsDictionary[obj].append(action) #add the action to objectActionsDictionary[object name][list]
            
            #if no animation data continue
            else:
                continue
        return objectActionsDictionary
    
    @staticmethod
    def SoloRestPoseTrack(obj):
        activeActionBlendMode = obj.animation_data.action_blend_type
        obj.animation_data.action_blend_type = 'REPLACE'
        trackDict = dict()
        soloTrack = None
        for track in obj.animation_data.nla_tracks:
            muteState = track.mute
            trackDict[track] = [muteState]
            if track.is_solo:
                soloTrack = track
            track.mute = True
            track.is_solo = False
            if track.name == "RotF Rest Pose " + obj.name:
                track.mute = False
        return trackDict, soloTrack, activeActionBlendMode
    
    @staticmethod
    def RestoreTracksState(obj, trackDict, soloTrack, activeActionBlendMode):
        for track in obj.animation_data.nla_tracks:
            track.mute = trackDict[track][0]
        if soloTrack:
            soloTrack.is_solo = True
        obj.animation_data.action_blend_type = activeActionBlendMode

    @staticmethod
    def PoseBoneGroups():
        obj = bpy.context.active_object
        #add pose bone's groups
        if obj.pose.bone_groups.get('RigOnTheFly Base') is None:
            baseBoneGroup = obj.pose.bone_groups.new(name="RigOnTheFly Base")
            baseBoneGroup.color_set = 'THEME09'
        else:
            baseBoneGroup = obj.pose.bone_groups['RigOnTheFly Base']

        if obj.pose.bone_groups.get('RigOnTheFly Right') is None:
            rightBoneGroup = obj.pose.bone_groups.new(name="RigOnTheFly Right")
            rightBoneGroup.color_set = 'THEME01'
        else:
            rightBoneGroup = obj.pose.bone_groups['RigOnTheFly Right']

        if obj.pose.bone_groups.get('RigOnTheFly Left') is None:
            leftBoneGroup = obj.pose.bone_groups.new(name="RigOnTheFly Left")
            leftBoneGroup.color_set = 'THEME04'
        else:
            leftBoneGroup = obj.pose.bone_groups['RigOnTheFly Left']

        leftSide = ["left","_l","l_",".l","l.","-l","l-"," left","left "]
        rightSide = ["right","_r","r_",".r","r.","-r","r-"," right","right "]

        #assign bone groups to selected pose bones
        for poseBone in bpy.context.selected_pose_bones:
            if any(poseBone.name.casefold().startswith(left) or poseBone.name.casefold().endswith(left) for left in leftSide):
                poseBone.bone_group = leftBoneGroup
            elif any(poseBone.name.casefold().startswith(right) or poseBone.name.casefold().endswith(right) for right in rightSide):
                poseBone.bone_group = rightBoneGroup
            elif "RotF_ArmatureMotion" in poseBone.name:
                continue
            else:
                poseBone.bone_group = baseBoneGroup

    @staticmethod
    def GetLayerArray(index):
        layers = list()
        for i in range(32):
            layers.append(index==i)
        return layers

    @staticmethod
    def MoveBonesToLayer(index):
        if bpy.context.mode == 'EDIT_ARMATURE':
            bpy.ops.armature.bone_layers(layers=StateUtility.GetLayerArray(index))          

        if bpy.context.mode == 'POSE':
            bpy.ops.pose.bone_layers(layers=StateUtility.GetLayerArray(index)) 

    @staticmethod
    def KeyframeClear():
        obj = bpy.context.object
        objectActionsDictionary = StateUtility.FindActions() #find relevant action for each selected object
        wasInTweakMode = False
        
        for obj in objectActionsDictionary:
            try:
                wasInTweakMode = obj.animation_data.use_tweak_mode
            except:
                wasInTweakMode = False
            if obj.animation_data: #check if obj has animation data
                initialAction = obj.animation_data.action
                obj.animation_data.use_tweak_mode = False #exit nla tweak mode
                for action in objectActionsDictionary[obj]:
                    obj.animation_data.action = action #switch obj's current action
                    #--------------Clearing Keyframes---------------
                    #clear all key frames of selected bones
                    bpy.ops.anim.keyframe_clear_v3d()
                    #---------------Keyframes Cleared---------------
                obj.animation_data.action = initialAction
        obj.animation_data.use_tweak_mode = wasInTweakMode

    @staticmethod
    def CopyTransformConstraint(action, boneP, constraint) :
        print("has a copy transforms constraint")
        channelsList = list()

        locationXYZList = [Channel.locationX, Channel.locationY, Channel.locationZ]

        quaternionWXYZList = [Channel.quaternionW, Channel.quaternionX, Channel.quaternionY, Channel.quaternionZ]
        eulerXYZList = [Channel.eulerX, Channel.eulerY, Channel.eulerZ]

        scaleXYZList = [Channel.scaleX, Channel.scaleY, Channel.scaleZ]

        targetObj = constraint.target
        subtargetBoneN = constraint.subtarget
        targetBoneP = targetObj.pose.bones[subtargetBoneN]
        print(targetBoneP)

        targetBoneDataPath = targetBoneP.path_from_id()        
        print(targetBoneDataPath)
        

        #check if targetBone has keys in location channels in the action
        if action.fcurves.find(targetBoneDataPath + ".location",index=0):
            print("found Location X")
            channelsList.append(Channel.locationX)
        if action.fcurves.find(targetBoneDataPath + ".location",index=1):
            print("found Location Y")
            channelsList.append(Channel.locationY)
        if action.fcurves.find(targetBoneDataPath + ".location",index=2):
            print("found Location Z")
            channelsList.append(Channel.locationZ)

        #check if targetBone and boneP have the same rotation mode
        if targetBoneP.rotation_mode == boneP.rotation_mode:
            #check if targetBone has keys in quaternion channels in the action
            if action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=0):
                print("found Quaternion W")
                channelsList.append(Channel.quaternionW)
            if action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=1):
                print("found Quaternion X")
                channelsList.append(Channel.quaternionX)
            if action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=2):
                print("found Quaternion Y")
                channelsList.append(Channel.quaternionY)
            if action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=3):
                print("found Quaternion Z")
                channelsList.append(Channel.quaternionZ)

            #check if targetBone has keys in euler channels in the action
            if action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=0):
                print("found Euler X")
                channelsList.append(Channel.eulerX)
            if action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=1):
                print("found Euler Y")
                channelsList.append(Channel.eulerY)
            if action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=2):
                print("found Euler Z")
                channelsList.append(Channel.eulerZ)

        #if targetBone and boneP have different rotation modes
        else:
            print("rotation mode is different")
            if boneP.rotation_mode == 'QUATERNION':
                print("rotation mode is quaternion")
                for i in range(4):
                    if action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=i):
                        print("found Quaternion WXYZ")
                        channelsList.extend(quaternionWXYZList)
                for i in range(3):
                    print(i)
                    if action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=i):
                        print("found Euler XYZ")
                        channelsList.extend(quaternionWXYZList)
            else:
                print("rotation mode is euler")
                for i in range(4):
                    print(i)
                    if action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=i):
                        print("found Quaternion WXYZ")
                        channelsList.extend(eulerXYZList)
                for i in range(3):
                    print(i)
                    if action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=i):
                        print("found Euler XYZ")
                        channelsList.extend(eulerXYZList)
                

        #check if targetBone has keys in location channels in the action
        if action.fcurves.find(targetBoneDataPath + ".scale",index=0):
            print("found Scale X")
            channelsList.append(Channel.scaleX)
        if action.fcurves.find(targetBoneDataPath + ".scale",index=1):
            print("found Scale X")
            channelsList.append(Channel.scaleY)
        if action.fcurves.find(targetBoneDataPath + ".scale",index=2):
            print("found Scale X")
            channelsList.append(Channel.scaleZ)

        #----------------------------------------------------------------
        #using the OrientRig button
        if targetBoneP.name == boneP.name.replace(".orient.rig",".orient") or targetBoneP.name == boneP.name + ".orient.child" :
            if targetBoneP.name == boneP.name.replace(".orient.rig",".orient"):
                orientRigTargetN = targetBoneP.name.replace(".orient","")
            if targetBoneP.name == boneP.name + ".orient.child":
                orientRigTargetN = boneP.name + ".orient.rig"
            print(orientRigTargetN)
            orientRigDataPath = targetBoneDataPath.replace(targetBoneP.name,orientRigTargetN)
            #check if targetBone has keys in location channels in the action
            if action.fcurves.find(orientRigDataPath + ".location",index=0):
                print("found Location X")
                channelsList.append(Channel.locationX)
            if action.fcurves.find(orientRigDataPath + ".location",index=1):
                print("found Location Y")
                channelsList.append(Channel.locationY)
            if action.fcurves.find(orientRigDataPath + ".location",index=2):
                print("found Location Z")
                channelsList.append(Channel.locationZ)

            #check if targetBone and boneP have the same rotation mode
            if targetBoneP.rotation_mode == boneP.rotation_mode:
                #check if targetBone has keys in quaternion channels in the action
                if action.fcurves.find(orientRigDataPath + ".rotation_quaternion",index=0):
                    print("found Quaternion W")
                    channelsList.append(Channel.quaternionW)
                if action.fcurves.find(orientRigDataPath + ".rotation_quaternion",index=1):
                    print("found Quaternion X")
                    channelsList.append(Channel.quaternionX)
                if action.fcurves.find(orientRigDataPath + ".rotation_quaternion",index=2):
                    print("found Quaternion Y")
                    channelsList.append(Channel.quaternionY)
                if action.fcurves.find(orientRigDataPath + ".rotation_quaternion",index=3):
                    print("found Quaternion Z")
                    channelsList.append(Channel.quaternionZ)

                #check if targetBone has keys in euler channels in the action
                if action.fcurves.find(orientRigDataPath + ".rotation_euler",index=0):
                    print("found Euler X")
                    channelsList.append(Channel.eulerX)
                if action.fcurves.find(orientRigDataPath + ".rotation_euler",index=1):
                    print("found Euler Y")
                    channelsList.append(Channel.eulerY)
                if action.fcurves.find(orientRigDataPath + ".rotation_euler",index=2):
                    print("found Euler Z")
                    channelsList.append(Channel.eulerZ)

            #if targetBone and boneP have different rotation modes
            else:
                print("rotation mode is different")
                if boneP.rotation_mode == 'QUATERNION':
                    print("rotation mode is quaternion")
                    for i in range(4):
                        if action.fcurves.find(orientRigDataPath + ".rotation_quaternion",index=i):
                            print("found Quaternion WXYZ")
                            channelsList.extend(quaternionWXYZList)
                    for i in range(3):
                        print(i)
                        if action.fcurves.find(orientRigDataPath + ".rotation_euler",index=i):
                            print("found Euler XYZ")
                            channelsList.extend(quaternionWXYZList)
                else:
                    print("rotation mode is euler")
                    for i in range(4):
                        print(i)
                        if action.fcurves.find(orientRigDataPath + ".rotation_quaternion",index=i):
                            print("found Quaternion WXYZ")
                            channelsList.extend(eulerXYZList)
                    for i in range(3):
                        print(i)
                        if action.fcurves.find(orientRigDataPath + ".rotation_euler",index=i):
                            print("found Euler XYZ")
                            channelsList.extend(eulerXYZList)

            #check if targetBone has keys in location channels in the action
            if action.fcurves.find(orientRigDataPath + ".scale",index=0):
                print("found Scale X")
                channelsList.append(Channel.scaleX)
            if action.fcurves.find(orientRigDataPath + ".scale",index=1):
                print("found Scale X")
                channelsList.append(Channel.scaleY)
            if action.fcurves.find(orientRigDataPath + ".scale",index=2):
                print("found Scale X")
                channelsList.append(Channel.scaleZ)

        #----------------------------------------------------------------


        default4x4Matrix = Matrix(((1.0, 0.0, 0.0, 0.0),(0.0, 1.0, 0.0, 0.0),(0.0, 0.0, 1.0, 0.0),(0.0, 0.0, 0.0, 1.0)))

        if boneP.parent:
            boneSpace = boneP.parent.matrix
        else:
            boneSpace = default4x4Matrix

        if targetBoneP.parent:
            targetSpace = targetBoneP.parent.matrix
        else:
            targetSpace = default4x4Matrix

        #check if boneP's parent and targetBoneP's parent have different matrices. If they have the same it means boneP and targetBoneP have the same transforms relative to their parent
        if boneSpace != targetSpace:
            print("different space")
            if any (channel in channelsList for channel in locationXYZList):
                channelsList.extend(locationXYZList)

            if any (channel in channelsList for channel in quaternionWXYZList):
                channelsList.extend(quaternionWXYZList)

            if any (channel in channelsList for channel in eulerXYZList):
                channelsList.extend(eulerXYZList)

            if any (channel in channelsList for channel in scaleXYZList):
                channelsList.extend(scaleXYZList)

        return channelsList
        #return [Channel.locationX, Channel.locationY]

    @staticmethod
    def ActionInitialState(objectActionsDictionary):
        wasInTweakMode = False
        #find if relevant objects have an action strip in tweak mode 
        if bpy.context.scene.is_nla_tweakmode: #if an action strip in the scene is in tweak mode (TAB)
            for obj in objectActionsDictionary:
                activeTrack = obj.animation_data.nla_tracks.active
                if activeTrack != None: #if there is an active strip on the NLA track
                    for strip in activeTrack.strips: #go through the NLA track to find the active strip
                        if strip.active:
                            wasInTweakMode = True                
                obj.animation_data.use_tweak_mode = False #exit nla tweak mode
        return wasInTweakMode

    @staticmethod
    def RestoreActionState(wasInTweakMode, objectActionsDictionary):
         for obj in objectActionsDictionary:
            if wasInTweakMode:
                obj.animation_data.use_tweak_mode = True #return to nla tweak mode

    @staticmethod
    def RemoveConstraintsOfSelectedPoseBones():
        bpy.context.view_layer.update()
        #CLEAR CONSTRAINTS AFTER BAKING
        for boneP in bpy.context.selected_pose_bones:
            obj = boneP.id_data

            #if there is no animation data on the object, keeptransform from the constraint
            if not obj.animation_data:
                # Get the matrix in world space.
                #bone = context.pose_bone
                mat = obj.matrix_world @ boneP.matrix
            for constraint in boneP.constraints:
                constraint.influence = 0.0
            #set matrix
            if not obj.animation_data:
                boneP.matrix = obj.matrix_world.inverted() @ mat

            while boneP.constraints:
                boneP.constraints.remove(boneP.constraints[0])

    @staticmethod
    def GetFramePointFromFCurve(fcurve, frames=list()):
        if bpy.context.scene.smartFrames:
            keyFramePoints = fcurve.keyframe_points
            for point in keyFramePoints:
                f = point.co[0]
                if f not in frames:
                    frames.append(f)

class Channel (Enum):
    locationX = 1
    locationY = 2
    locationZ = 3

    quaternionW = 4
    quaternionX = 5
    quaternionY = 6
    quaternionZ = 7

    eulerX = 8
    eulerY = 9
    eulerZ = 10

    scaleX = 11
    scaleY = 12
    scaleZ = 13

class BakeOptions():
    mode:str
    frame_start=0
    frame_end=1
    only_selected=True
    visual_keying=True
    clear_parents=False
    clear_constraints=False

    use_current_action=True
    bake_types={'POSE'}

class StateData(NamedTuple):
    mode:str
    selectionEditableBones:bpy.types.EditBone
    selectionPoseBones:bpy.types.PoseBone