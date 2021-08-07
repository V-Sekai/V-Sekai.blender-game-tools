#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils
from . PolygonShapesUtility import PolygonShapes

class RotationDistributionUtils:

    def RotationDistribution (self, context):
        #add controller shapes to the scene
        PolygonShapes.AddControllerShapes()

        obj = bpy.context.object
        armature = obj.data

        #force edit mode
        StateUtility.SetEditMode()

        #list selected bones and order them in edit mode
        selectedBonesList = bpy.context.selected_editable_bones.copy()
        selectedBonesList.sort(key = lambda x:len(x.parent_recursive))

        #add selected bones names to selectedBonesN and set aside the active bone as the topBone
        selectedBonesN = list()
        for bone in selectedBonesList:
            if bone.name == bpy.context.active_bone.name:
                topBoneN = bpy.context.active_bone.name
                topRotBoneN = topBoneN.replace(".rig",".top.rig")
            else: selectedBonesN.append(bone.name)

        baseBoneN = selectedBonesN[0]

        #selects and duplicates the second bone in the hierarchy of the original selection
        bpy.ops.armature.select_all(action='DESELECT')
        armature.edit_bones[topBoneN].select=True
        armature.edit_bones[topBoneN].select_head=True
        armature.edit_bones[topBoneN].select_tail=True

        bpy.ops.armature.duplicate()

        armature.edit_bones[topBoneN +".001"].parent = armature.edit_bones[baseBoneN]
        armature.edit_bones[topBoneN +".001"].name = topRotBoneN

        #selects bones inbetween the base bone and the top bone
        bpy.ops.armature.select_all(action='DESELECT')
        for i in range(1, len(selectedBonesN)):
            inbetweenBoneN = selectedBonesN[i]
            armature.edit_bones[inbetweenBoneN].select=True
            armature.edit_bones[inbetweenBoneN].select_head=True
            armature.edit_bones[inbetweenBoneN].select_tail=True
        
        #duplicate inbetween bones twice. one copy will follow the base bone's rotation and the other copy will follow the top bone's rotation
        bpy.ops.armature.duplicate()
        bpy.ops.armature.duplicate()

        #add duplicated bones with .001 suffix to the selection. The duplicated bones with suffix .002 are already selected
        for i in range(1, len(selectedBonesN)):
            baseInbetweenBoneN = selectedBonesN[i] +".001"
            armature.edit_bones[baseInbetweenBoneN].select=True
            armature.edit_bones[baseInbetweenBoneN].select_head=True
            armature.edit_bones[baseInbetweenBoneN].select_tail=True

        #rename duplicated bones with .rig.001 suffix to .rotBase.rig and duplicated bones with .rig.002 suffix to .rotTop.rig
        for bone in bpy.context.selected_editable_bones:
            if ".rig.001" in bone.name:
                bone.parent = armature.edit_bones[baseBoneN]
                bone.name = bone.name.replace(".rig.001",".rotBase.rig")

            if ".rig.002" in bone.name:  
                bone.parent = armature.edit_bones[topRotBoneN]
                bone.name = bone.name.replace(".rig.002",".rotTop.rig")

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #add rotation contraints to duplicated bones so that they copy their originals .rig bones rotation
        for bone in bpy.context.selected_pose_bones:
            if ".rotBase.rig" in bone.name:
                armature.bones[bone.name].use_inherit_rotation = True

                copyRotation = bone.constraints.new('COPY_ROTATION')
                copyRotation.target = obj
                copyRotation.subtarget = bone.name.replace(".rotBase.rig",".rig")

            if ".rotTop.rig" in bone.name:
                armature.bones[bone.name].use_inherit_rotation = True

                copyRotation = bone.constraints.new('COPY_ROTATION')
                copyRotation.target = obj
                copyRotation.subtarget = bone.name.replace(".rotTop.rig",".rig")

        #selects topRotBone and have it display at topBone's location using the Octagon controller shape and locking it's translation
        armature.bones[topRotBoneN].select = True
        topRotBoneP = obj.pose.bones[topRotBoneN]
        topRotBoneP.custom_shape_transform = obj.pose.bones[topBoneN]
        topRotBoneP.custom_shape = bpy.data.objects["RotF_Octagon"]
        topRotBoneP.lock_location[0] = True
        topRotBoneP.lock_location[1] = True
        topRotBoneP.lock_location[2] = True

        #have topRotBone follow topBone's rotation
        copyRotation = obj.pose.bones[topRotBoneN].constraints.new('COPY_ROTATION')
        copyRotation.target = obj
        copyRotation.subtarget = topBoneN
        
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

                                        

                    #locationXYZList = [Channel.locationX, Channel.locationY, Channel.locationZ]
                    rotationQEList = [Channel.quaternionW, Channel.quaternionX, Channel.quaternionY, Channel.quaternionZ, Channel.eulerX, Channel.eulerY, Channel.eulerZ]
                    #scaleXYZList = [Channel.scaleX, Channel.scaleY, Channel.scaleZ]

                    for boneP in bpy.context.selected_pose_bones:
                        channelsList = list()
                        
                        nameReplace = str()
                        if ".rotBase.rig" in boneP.name:
                            nameReplace = ".rotBase.rig"
                        if ".rotTop.rig" in boneP.name:
                            nameReplace = ".rotTop.rig"
                        if ".top.rig" in boneP.name:
                            nameReplace = ".top.rig"

                        targetBoneP = obj.pose.bones[boneP.name.replace(nameReplace,".rig")]
                        targetBoneDataPath = targetBoneP.path_from_id()
                        
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

                        bonePChannelsToBake[boneP] = channelsList
                    DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)

                StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                obj.animation_data.action = initialAction
            StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
            #------------------------------------------------------------------------------------------------------------------------------------
        StateUtility.RemoveConstraintsOfSelectedPoseBones()
            

        #have original selected bones inbetween the baseBone and the topBone follow both its duplicate's rotations
        for i in range(1, len(selectedBonesN)):
            inbetweenBoneN = selectedBonesN[i]
            inbetweenBoneP = obj.pose.bones[inbetweenBoneN]
            
            copyBaseRotation = inbetweenBoneP.constraints.new('COPY_ROTATION')
            copyBaseRotation.target = obj
            copyBaseRotation.subtarget = selectedBonesN[i].replace(".rig",".rotBase.rig")

            copyTopRotation = inbetweenBoneP.constraints.new('COPY_ROTATION')
            copyTopRotation.target = obj
            copyTopRotation.subtarget = selectedBonesN[i].replace(".rig",".rotTop.rig")
            copyTopRotation.influence = i/(len(selectedBonesN))

        #have the topBone follow the topRotBone's rotation
        copyRotation = obj.pose.bones[topBoneN].constraints.new('COPY_ROTATION')
        copyRotation.target = obj
        copyRotation.subtarget = topRotBoneN

        armature.bones[topRotBoneN].select = False #deselect topRotBone to prevent from moving it to the unused layer
        armature.bones[topBoneN].select = True #add topBone to selection to move it to the unused layer

        #list no relevant bones to later move them to the unused layer
        nonRelevantBones = bpy.context.selected_pose_bones.copy()
        for i in range(1, len(selectedBonesN)):
            nonRelevantBones.append(obj.pose.bones[selectedBonesN[i]])
        
        #deselct all bones
        bpy.ops.pose.select_all(action='DESELECT')

        #move bones non relevant to animation to unused layer
        unusedLayer = obj.unusedRigBonesLayer
        for bone in nonRelevantBones:
            armature.bones[bone.name].layers[unusedLayer]=True
            for layer in range(32):
                if layer != unusedLayer:
                    armature.bones[bone.name].layers[layer]=False
        
        #select topRotBone
        armature.bones[topRotBoneN].select = True



