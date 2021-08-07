#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
import math
from math import degrees
from . Utility import StateUtility, Channel
from . PolygonShapesUtility import PolygonShapes
from . DypsloomBake import DypsloomBakeUtils

class IKLimbNoPoleUtils:

    def IKLimbNoPole (self, context):
        PolygonShapes.AddControllerShapes() #add conrtoller shapes to the scene

        obj = bpy.context.active_object
        armature = obj.data

        stretchIK = bpy.context.scene.ikStretch

        #add bone name to selectedBonesN to have it's generated IK controller selected at the end of the script
        selectedBonesN = list()
        for bone in bpy.context.selected_pose_bones:
            selectedBonesN.append(bone.name)

        for targetBoneN in selectedBonesN:
            targetBoneP = obj.pose.bones[targetBoneN]

            #get the parent and parent's parent of one of the selected bones in pose mode
            poleBoneP = bpy.context.object.pose.bones[targetBoneN].parent
            baseBoneP = bpy.context.object.pose.bones[targetBoneN].parent.parent
            #get the name of the parent and parent's parent of one of the selected bones
            poleBoneN = poleBoneP.name
            baseBoneN = baseBoneP.name

            #move poleBone and baseBone to the same layer as targetBone
            for layer in range(32):
                armature.bones[poleBoneN].layers[layer] = armature.bones[targetBoneN].layers[layer]
                armature.bones[baseBoneN].layers[layer] = armature.bones[targetBoneN].layers[layer]

            #force edit mode
            StateUtility.SetEditMode()

            #deselect all
            bpy.ops.armature.select_all(action='DESELECT')

            #selects and duplicates the last bone in the hierarchy of the original selection
            bpy.context.object.data.edit_bones[targetBoneN].select=True
            bpy.context.object.data.edit_bones[targetBoneN].select_head=True
            bpy.context.object.data.edit_bones[targetBoneN].select_tail=True
            bpy.ops.armature.duplicate()
            #rename ik bone
            bpy.context.object.data.edit_bones[targetBoneN +".001"].name = targetBoneN.replace(".rig",".IK.rig")

            ikTargetBoneN = targetBoneN.replace(".rig",".IK.rig")
            #remove parent
            bpy.context.selected_editable_bones[0].parent = None

            #snap tail of selectedPoleBoneN to ikTargetBoneN head's position
            poleBoneOldLength = armature.edit_bones[poleBoneN].length
            armature.edit_bones[poleBoneN].tail = armature.edit_bones[ikTargetBoneN].head
            poleBoneNewLength = armature.edit_bones[poleBoneN].length
            poleBoneLengthFactor = poleBoneOldLength/poleBoneNewLength

            #to keep poleBone's custom shape visual size in case snapping it's tail onto targetBone's head changed poleBone's length
            poleBoneP.custom_shape_scale *= poleBoneLengthFactor
            

            #if stretchIK is on, selects and duplicates the base an pole bone that will be able to stretch
            if stretchIK:
                bpy.ops.armature.select_all(action='DESELECT')
                for boneN in [baseBoneN,poleBoneN]:
                    armature.edit_bones[boneN].select=True
                    armature.edit_bones[boneN].select_head=True
                    armature.edit_bones[boneN].select_tail=True

                bpy.ops.armature.duplicate()
                #rename ik stretch bones
                baseStretchN = baseBoneN.replace(".rig",".stretch.IK.rig")
                armature.edit_bones[baseBoneN +".001"].name = baseStretchN
                
                poleStretchN = poleBoneN.replace(".rig",".stretch.IK.rig")
                armature.edit_bones[poleBoneN +".001"].name = poleStretchN  

            #force pose mode
            bpy.ops.object.mode_set(mode='POSE')
            #change rig bones' display to square, rotation mode to euler YZX and adds copy transform constraint to copy the base armature's animation.
            ikTargetBoneP = bpy.context.object.pose.bones[ikTargetBoneN]
            ikTargetBoneP.custom_shape = bpy.data.objects["RotF_Square"]
            bpy.context.object.data.bones[ikTargetBoneN].show_wire = True
            copyTransforms = ikTargetBoneP.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = bpy.context.object
            copyTransforms.subtarget = targetBoneN

            if stretchIK:
                #change rig bones' display to square, rotation mode to euler YZX and adds copy transform constraint to copy the base armature's animation.
                baseStretchP = obj.pose.bones[baseStretchN]
                baseStretchP.custom_shape = bpy.data.objects["RotF_Square"]
                baseStretchP.ik_stretch = 0.001
                copyTransforms = baseStretchP.constraints.new('COPY_TRANSFORMS')
                copyTransforms.target = bpy.context.object
                copyTransforms.subtarget = baseBoneN

                #change rig bones' display to square, rotation mode to euler YZX and adds copy transform constraint to copy the base armature's animation.
                poleStretchP = obj.pose.bones[poleStretchN]
                poleStretchP.custom_shape = bpy.data.objects["RotF_Square"]
                poleStretchP.ik_stretch = 0.001
                copyTransforms = poleStretchP.constraints.new('COPY_TRANSFORMS')
                copyTransforms.target = bpy.context.object
                copyTransforms.subtarget = poleBoneN

            #add ikTargetBoneN to selection
            armature.bones[ikTargetBoneN].select = True
            if stretchIK:
                armature.bones[baseStretchN].select = True
                armature.bones[poleStretchN].select = True

            #bake animation on selection and remove constraints
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
                        quaternionWXYZList = [Channel.quaternionW, Channel.quaternionX, Channel.quaternionY, Channel.quaternionZ]
                        eulerXYZList = [Channel.eulerX, Channel.eulerY, Channel.eulerZ]
                        #scaleXYZList = [Channel.scaleX, Channel.scaleY, Channel.scaleZ]

                        channelsList = list()
                        for boneP in [baseBoneP, poleBoneP,targetBoneP]:
                            bonePDataPath = boneP.path_from_id()
                            for transform in [".translation",".rotation_euler",".scale"]:
                                for i in range(3):
                                    fcurve = action.fcurves.find(bonePDataPath + transform, index=i)
                                    if fcurve:
                                        StateUtility.GetFramePointFromFCurve(fcurve, frames)
                                        channelsList.extend(locationXYZList)
                            for i in range(4):
                                fcurve = action.fcurves.find(bonePDataPath +".rotation_quaternion",index=i)
                                if fcurve:
                                    StateUtility.GetFramePointFromFCurve(fcurve, frames)
                                    channelsList.extend(locationXYZList)

                        if channelsList:
                            bonesToBake = [ikTargetBoneP]
                            if stretchIK:
                                bonesToBake.extend([baseStretchP, poleStretchP])

                            for boneP in bonesToBake:
                                if boneP.rotation_mode == 'QUATERNION':
                                    bonePChannelsToBake[boneP] = channelsList + quaternionWXYZList
                                    
                                else:
                                    bonePChannelsToBake[boneP] = channelsList + eulerXYZList
                                
                                targetBoneDataPath = targetBoneP.path_from_id()
                                for i in range(3):
                                    fcurve = action.fcurves.find(targetBoneDataPath + ".scale",index=i)
                                    if fcurve:
                                        if i == 0: #if scale X channel
                                            bonePChannelsToBake[boneP].append(Channel.scaleX)
                                        if i == 1: #if scale Y channel
                                            bonePChannelsToBake[boneP].append(Channel.scaleY)
                                        if i == 2: #if scale Z channel
                                            bonePChannelsToBake[boneP].append(Channel.scaleZ)
                        DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)
                    
                    StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                    obj.animation_data.action = initialAction
                StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
                #------------------------------------------------------------------------------------------------------------------------------------
            
            StateUtility.RemoveConstraintsOfSelectedPoseBones()

            if stretchIK:
                #adds ik constraint to selectedPoleBoneN
                ikBone = obj.pose.bones[poleStretchN]
            else:
                #adds ik constraint to selectedPoleBoneN
                ikBone = bpy.context.object.pose.bones[poleBoneN]

            ik = ikBone.constraints.new('IK')
            ik.target = bpy.context.object
            ik.subtarget = ikTargetBoneN
            ik.chain_count = 2

            #selectedTargetBone follow ikTargetBone transforms
            selectedTargetBone = bpy.context.object.pose.bones[targetBoneN]
            copyRotation = selectedTargetBone.constraints.new('COPY_ROTATION')
            copyRotation.target = bpy.context.object
            copyRotation.subtarget = selectedTargetBone.name.replace(".rig",".IK.rig")

            copyScale = selectedTargetBone.constraints.new('COPY_SCALE')
            copyScale.target = bpy.context.object
            copyScale.subtarget = selectedTargetBone.name.replace(".rig",".IK.rig")

            if stretchIK:
                #copy rotation and Y scale
                copyRotation = baseBoneP.constraints.new('COPY_ROTATION')
                copyRotation.target = obj
                copyRotation.subtarget = baseStretchN
                copyScale = baseBoneP.constraints.new('COPY_SCALE')
                copyScale.target = obj
                copyScale.subtarget = baseStretchN
                copyScale.use_x = False
                copyScale.use_z = False

                #copy rotation and Y scale
                copyRotation = poleBoneP.constraints.new('COPY_ROTATION')
                copyRotation.target = obj
                copyRotation.subtarget = poleStretchN
                copyScale = poleBoneP.constraints.new('COPY_SCALE')
                copyScale.target = obj
                copyScale.subtarget = poleStretchN
                copyScale.use_x = False
                copyScale.use_z = False

            #deselect all to prevent baking bones that were left selected
            bpy.ops.pose.select_all(action='DESELECT')

            armature.bones[targetBoneN].select = True
            armature.bones[poleBoneN].select = True

            if stretchIK:
                armature.bones[baseBoneN].select = True

            if obj.animation_data:
                #clear all key frames of selected bones
                StateUtility.KeyframeClear()

            #deselect all to prevent baking bones that were left selected
            bpy.ops.pose.select_all(action='DESELECT')

            unusedLayer = obj.unusedRigBonesLayer

            #move non relevant bones to unused layer
            bonesToMove = [targetBoneN, poleBoneN]
            if stretchIK:
                bonesToMove.extend([baseBoneN, poleStretchN])

            for boneN in bonesToMove:
                bone = armature.bones[boneN]
                bone.use_inherit_scale = False

            for boneN in bonesToMove:
                bone = armature.bones[boneN]
                bone.layers[unusedLayer]=True
                for layer in range(32):
                    if layer == unusedLayer:
                        continue
                    else:
                        bone.layers[layer]=False

        #end script with new ik handles selected
        for targetBoneN in selectedBonesN:
            bpy.context.object.data.bones[targetBoneN.replace(".rig",".IK.rig")].select = True