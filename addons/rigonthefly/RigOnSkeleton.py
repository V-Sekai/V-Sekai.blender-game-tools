#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . PolygonShapesUtility import PolygonShapes
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils

class RigOnSkeletonUtils:
    
    def RigOnSkeleton (self, context):
        #add controller shapes to the scene
        PolygonShapes.AddControllerShapes()

        #set aside the armature as a variable
        obj = bpy.context.object
        armature = obj.data
        originalLayers = list()
        layersToTurnOff = list()
        for layer in range(32):
            if armature.layers[layer] == True:
                originalLayers.append(layer)
            else: 
                armature.layers[layer] = True
                layersToTurnOff.append(layer)

        baseLayer = obj.baseBonesLayer
        rigLayer = obj.rigBonesLayer
        
        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        for boneP in bpy.context.selected_pose_bones:
            boneP.bone.select = False
            
        for layer in range(32):
            if layer in layersToTurnOff:
                armature.layers[layer] = False

        #select base armature
        bpy.ops.pose.select_all(action='SELECT')

        bonesToRigN = list()
        for pbone in bpy.context.selected_pose_bones:
            bonesToRigN.append(pbone.name)

        #create and assign bone groups to selected pose bones
        StateUtility.PoseBoneGroups()

        #force edit mode
        StateUtility.SetEditMode()

        #select base armature
        bpy.ops.armature.select_all(action='DESELECT')
        bpy.ops.armature.select_all(action='SELECT')

        #move rig bones to the rig layer. 
        StateUtility.MoveBonesToLayer(baseLayer)
        #make rig layer visible
        armature.layers[baseLayer] = True
        #hide originally visible layers
        for layer in range(32):
            if layer != baseLayer:
                armature.layers[layer] = False

        for baseBoneE in bpy.context.selected_editable_bones:
            baseBoneE.use_connect = False

        StateUtility.DuplicateBones(obj,".rig")

        #move rig bones to the rig layer. 
        StateUtility.MoveBonesToLayer(rigLayer)

        #make rig layer visible
        armature.layers[rigLayer] = True

        #armature is in pose mode
        bpy.ops.object.mode_set(mode='POSE')
        

        #change rig bones' display to circle, rotation mode to euler YZX and adds copy transform constraint to copy the base armature's animation.
        selectedPBones = bpy.context.selected_pose_bones.copy()
        selectedPBones.sort(key = lambda x:len(x.parent_recursive))
        for i, rigBoneP in enumerate(selectedPBones):
            rigBoneP.custom_shape = bpy.data.objects["RotF_Circle"]
            armature.bones[rigBoneP.name].show_wire = True
            #rigBoneP.rotation_mode = 'YZX'

            #for the first two bones of the hierarchy have the controller size bigger
            if i < 2:
                objDimensions = (obj.dimensions[0] + obj.dimensions[1] + obj.dimensions[2])/3
                objWorldScaleV = obj.matrix_world.to_scale()
                objWorldScale = (objWorldScaleV[0] + objWorldScaleV[1] + objWorldScaleV[2])/3
                objSize = objDimensions / objWorldScale
                sizeMultiplyer = objSize / rigBoneP.length
                rigBoneP.custom_shape_scale *= sizeMultiplyer/(2*(i+3))

        #for rigBoneP in bpy.context.selected_pose_bones:
        for boneN in bonesToRigN:
            rigBoneN = StateUtility.LeftRightSuffix(boneN) +".rig"
            rigBoneP = obj.pose.bones[rigBoneN]
            copyTransforms = rigBoneP.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = obj
            copyTransforms.subtarget = boneN #rigBoneP.name.replace(".rig","")

        #if object being rigged has animation data
        if obj.animation_data:
            #bake rig bones animation so that they have the same animation as the base armature.
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
                    #quaternionWXYZList = [Channel.quaternionW, Channel.quaternionX, Channel.quaternionY, Channel.quaternionZ]
                    eulerXYZList = [Channel.eulerX, Channel.eulerY, Channel.eulerZ]
                    #scaleXYZList = [Channel.scaleX, Channel.scaleY, Channel.scaleZ]

                    #for boneP in bpy.context.selected_pose_bones:
                    for boneN in bonesToRigN:
                        rigBoneN = StateUtility.LeftRightSuffix(boneN) +".rig"
                        boneP = obj.pose.bones[rigBoneN]
                        channelsList = list()
                        
                        targetBoneP = obj.pose.bones[boneN] #obj.pose.bones[boneP.name.replace(".rig","")]
                        targetBoneDataPath = targetBoneP.path_from_id()

                        #looking for translation channels
                        for i in range(3):
                            fcurve = action.fcurves.find(targetBoneDataPath + ".location",index=i)
                            if fcurve:
                                if i == 0: #if location X channel
                                    channelsList.append(Channel.locationX)
                                if i == 1: #if location Y channel
                                    channelsList.append(Channel.locationY)
                                if i == 2: #if location Z channel
                                    channelsList.append(Channel.locationZ)
                                StateUtility.GetFramePointFromFCurve(fcurve, frames)
                        if boneP.rotation_mode == targetBoneP.rotation_mode:
                            #looking for euler channels
                            for i in range(3):
                                fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=i)
                                if fcurve:
                                    if i == 0: #if euler X channel
                                        channelsList.append(Channel.eulerX)
                                    if i == 1: #if euler Y channel
                                        channelsList.append(Channel.eulerY)
                                    if i == 2: #if euler Z channel
                                        channelsList.append(Channel.eulerZ)
                                    StateUtility.GetFramePointFromFCurve(fcurve, frames)                        
                        else:
                            #looking for quaternion channels
                            for i in range(4):
                                fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=i)
                                if fcurve:
                                    channelsList.extend(eulerXYZList)
                                    StateUtility.GetFramePointFromFCurve(fcurve, frames)
                            #looking for euler channels
                            for i in range(3):
                                fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=i)
                                if fcurve:
                                    channelsList.extend(eulerXYZList)
                                    StateUtility.GetFramePointFromFCurve(fcurve, frames)
                        #looking for scale channels
                        for i in range(3):
                            fcurve = action.fcurves.find(targetBoneDataPath + ".scale",index=i)
                            if fcurve:
                                if i == 0: #if scale X channel
                                    channelsList.append(Channel.scaleX)
                                if i == 1: #if scale Y channel
                                    channelsList.append(Channel.scaleY)
                                if i == 2: #if scale Z channel
                                    channelsList.append(Channel.scaleZ)
                                StateUtility.GetFramePointFromFCurve(fcurve, frames)

                        bonePChannelsToBake[boneP] = channelsList
                    DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)
                
                StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                obj.animation_data.action = initialAction
            StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
            #------------------------------------------------------------------------------------------------------------------------------------
        StateUtility.RemoveConstraintsOfSelectedPoseBones()


        #hide first layer to show only rig bones.

        armature.layers[baseLayer] = False

        #deselect all rig bones
        bpy.ops.pose.select_all(action='TOGGLE')

        #display base armature layer and hide rig armature layer 
        armature.layers[baseLayer] = True
        armature.layers[rigLayer] = False

        #select base armature
        bpy.ops.pose.select_all(action='SELECT')

        #base armature now follows rig armature
        for bone in bpy.context.selected_pose_bones:
            copyTransforms = bone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = obj
            copyTransforms.subtarget = StateUtility.LeftRightSuffix(bone.name) + ".rig"

        if obj.animation_data:
            #clear all key frames of selected bones
            StateUtility.KeyframeClear()

        #deselect base armature
        bpy.ops.pose.select_all(action='DESELECT')

        #show rig armature
        armature.layers[rigLayer] = True
        armature.layers[baseLayer] = False

    def RestPoseTrack (self, context):
        obj = bpy.context.object

        initialFrame = bpy.context.scene.frame_current
        
        bpy.ops.object.mode_set(mode='POSE') #force pose mode

        bpy.ops.pose.select_all(action='SELECT') #select all available pose bones

        #if armature object does not have animation key current pose
        if not obj.animation_data:
            bpy.ops.anim.keyframe_insert_menu(type='LocRotScale') #add keyframe to all selected bones, adding in the process a new action
        initialAction = obj.animation_data.action #store initial action to return to it once the script is done

        restPoseAction = bpy.data.actions.new(obj.name + " Rest Pose") #create new action used for storing the rest pose
        obj.animation_data.action = restPoseAction #assign reste pose action to store the rest pose of the armature
        bpy.context.scene.frame_current = 0 #go to frame 0

        initialBlendType = obj.animation_data.action_blend_type
        obj.animation_data.action_blend_type = 'REPLACE'
        bpy.ops.pose.transforms_clear()#put selected bones intos rest pose
        bpy.ops.anim.keyframe_insert_menu(type='LocRotScale') #key rest pose

        initialAreaType = bpy.context.area.type #store initial area type
        bpy.context.area.type = 'NLA_EDITOR' #change area type to NLA_EDITOR to get the right context for the operator
        for track in obj.animation_data.nla_tracks:# deselect all tracks before adding the restPoseTrack
            track.select = False
        restPoseTrack = obj.animation_data.nla_tracks.new() #add new restPoseTrack, it gets selected by default
        restPoseTrack.name = "RotF Rest Pose " + obj.name #name it appropriately
        restPoseStrip = restPoseTrack.strips.new("RotF Rest Pose "+ obj.name, 0, restPoseAction) #add new restPoseStrip containing the restPoseAction
        restPoseStrip.blend_type = 'REPLACE'
        bpy.ops.anim.channels_move(direction='BOTTOM') #move selected tracks to the bottom of the nla
        
        obj.animation_data.action_blend_type = initialBlendType
        bpy.context.area.type = initialAreaType #return to initial area type
        obj.animation_data.action = initialAction #return to initial action
        bpy.context.scene.frame_current = initialFrame #return to initial frame

    def ArmatureMotionToBone(self, context):
        obj = bpy.context.object
        armature = obj.data
        
        initialAction = obj.animation_data.action

        #tracksStateDict, soloTrack, activeActionBlendMode = StateUtility.SoloRestPoseTrack(obj) #add an nla track to solo so that baking is done without other tracks influencing the result

        wasInTweakMode = False
        if obj.animation_data.use_tweak_mode:
            wasInTweakMode = True
            obj.animation_data.use_tweak_mode = False #exit nla tweak mode

        actionList = list()

        objHasAnimation = False
        if obj.animation_data:
            if obj.animation_data.action:
                currentAction = obj.animation_data.action
                actionList.append(currentAction) #add the current action name to objectActionsDictionary[object name][list]

            for nlaTrack in obj.animation_data.nla_tracks: #go through object's nla tracks
                for actionStrip in nlaTrack.strips: #go through the strips in it's nla tracks
                    action = actionStrip.action
                    if action not in actionList: #if action used in strips of the nla tracks are not yet in actionList
                        actionList.append(action) #add the action name to actionList

        #check all relevant actions to see if armature object has animation
        for action in actionList:

            obj.animation_data.action = action
            for i in range(3):
                location = action.fcurves.find("location",index=i)
                if location:
                    objHasAnimation = True
                rotationEuler = action.fcurves.find("rotation_euler",index=i)
                if rotationEuler:
                    objHasAnimation = True
                scale = action.fcurves.find("scale",index=i)
                if scale:
                    objHasAnimation = True
            for i in range(4):
                rotationQuaternion = action.fcurves.find("rotation_quaternion",index=i)
                if rotationQuaternion:
                    objHasAnimation = True

        if objHasAnimation:
            if obj.pose.bone_groups.get('RigOnTheFly Armature Motion') is None:
                armatureMotionBoneGroup = obj.pose.bone_groups.new(name="RigOnTheFly Armature Motion")
                armatureMotionBoneGroup.color_set = 'THEME11'
            else:
                armatureMotionBoneGroup = obj.pose.bone_groups['RigOnTheFly Armature Motion']

            #force edit mode
            StateUtility.SetEditMode()

            #create new bone
            newBoneN = "RotF_ArmatureMotion"
            newEBone = armature.edit_bones.new(newBoneN)
            newEBone.use_deform = False
            newEBone.tail = (0,1,0) #tail position
            
            objDimensions = (obj.dimensions[0] + obj.dimensions[1] + obj.dimensions[2])/3
            objWorldScaleV = obj.matrix_world.to_scale()
            objWorldScale = (objWorldScaleV[0] + objWorldScaleV[1] + objWorldScaleV[2])/3
            objSize = objDimensions / objWorldScale
            sizeMultiplyer = objSize / newEBone.length
            newEBone.length = sizeMultiplyer/3

            for ebone in armature.edit_bones:
                if ebone.parent == None: #and ".rig" in ebone.name:
                    ebone.parent = newEBone

            #force pose mode
            bpy.ops.object.mode_set(mode='POSE')
            newPBone = obj.pose.bones[newBoneN]
            newPBone.rotation_mode = obj.rotation_mode
            newPBone.bone_group = armatureMotionBoneGroup

            boneDataPath = newPBone.path_from_id()
            for action in actionList:
                #copy the armature's object motion to the new bone
                for transformType in ["location","rotation_euler","rotation_quaternion","scale"]:
                    index = int()
                    if transformType == "rotation_quaternion":
                        index = 4
                    else:
                        index = 3
                        
                    for i in range(index):
                        objFCurve = action.fcurves.find(transformType,index=i)
                        if not objFCurve:
                            continue
                        else:
                            data_path = boneDataPath+"."+transformType
                            fcurve = action.fcurves.find(data_path, index=i)
                            
                            if fcurve == None:
                                fcurve = action.fcurves.new(data_path, index=i, action_group=newPBone.name)
                                
                            num_keys = len(objFCurve.keyframe_points)
                            keys_to_add = num_keys - len(fcurve.keyframe_points) #find how many keyframe points need to be added
                            fcurve.keyframe_points.add(keys_to_add) #add the needed keyframe points
                            
                            for key in range(num_keys):
                                fcurve.keyframe_points[key].co = objFCurve.keyframe_points[key].co
                                fcurve.keyframe_points[key].handle_left = objFCurve.keyframe_points[key].handle_left
                                fcurve.keyframe_points[key].handle_right = objFCurve.keyframe_points[key].handle_right
                        
                        #remove fcurve on armature object
                        action.fcurves.remove(objFCurve)
                
                #zero armature's object transforms
                obj.location = (0,0,0)
                obj.rotation_euler = (0,0,0)
                obj.rotation_quaternion = (1,0,0,0)
                obj.scale = (1,1,1)
        #StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
        obj.animation_data.action = initialAction
        
        if wasInTweakMode:
            obj.animation_data.use_tweak_mode = True

        return objHasAnimation

    def ArmatureMotionBoneShape(self, context):
        obj = bpy.context.object
        armature = obj.data
        
        for pbone in obj.pose.bones:
            if "RotF_ArmatureMotion" in pbone.name and ".rig" in pbone.name:
                pbone.custom_shape = bpy.data.objects["RotF_Square"]
                armature.bones[pbone.name].show_wire=True

