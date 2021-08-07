#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils
from . PolygonShapesUtility import PolygonShapes

class AimWorldUtils:

    def ChangeToAimWorld (self, context):
        PolygonShapes.AddControllerShapes() #add conrtoller shapes to the scene

        obj = bpy.context.object
        armature = obj.data

        #armature set to pose mode
        bpy.ops.object.mode_set(mode='POSE')

        selectedRigBoneNameList = list()
        aimBonesListN = list()
        for pbone in bpy.context.selected_pose_bones:
            selectedRigBoneNameList.append(pbone.name)
            aimBonesListN.append(pbone.name.replace(".rig",".aim.rig"))

        #force edit mode
        StateUtility.SetEditMode()
        
        #duplicate rig bones to be used as aim bones
        bpy.ops.armature.duplicate()
        for copiedBoneE in bpy.context.selected_editable_bones:
            copiedBoneE.name = copiedBoneE.name.replace(".rig.001",".aimTemp.rig")

            copiedBoneE.parent = armature.edit_bones[copiedBoneE.name.replace(".aimTemp.rig",".rig")]

        #duplicate rig bones to be used as aim bones
        bpy.ops.armature.duplicate()

        #add .aim.rig suffix to duplicate bones now known as aim bones.
        for copiedBoneE in bpy.context.selected_editable_bones:
            copiedBoneE.name = copiedBoneE.name.replace(".aimTemp.rig.001",".aim.rig")

            #find the matrix coordinates of the armature object
            armatureMatrix = obj.matrix_world
            #invert armature's matrix to find where global(0,0,0) is in relation to the armature's position/roation
            armatureMatrixInvert= armatureMatrix.copy()
            armatureMatrixInvert.invert()
            #set aim bone position to global (0,0,0) with axis following world's
            copiedBoneE.matrix = armatureMatrixInvert

            copiedBoneE.length = armature.bones[copiedBoneE.name.replace(".aim.rig",".rig")].length * 0.4

            copiedBoneE.parent = None
        """
        #unparent aim bones for world space translation
        aimBonesListE = bpy.context.selected_editable_bones.copy()
        aimBoneNameList = list()
        for aimPBone in aimBonesListE:
            aimBoneNameList.append(aimPBone.name)
            aimPBone.parent = None
        """

        #armature set to pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #change rig bones' display to locator and adds copy location constraint to copy the rig bones tail animation.
        for aimBoneN in aimBonesListN:
            aimTempP = obj.pose.bones[aimBoneN.replace(".aim.rig",".aimTemp.rig")]
            
            aimPBone = obj.pose.bones[aimBoneN]
            aimPBone.custom_shape = bpy.data.objects["RotF_Locator"]
            aimPBone.bone.show_wire = True
            aimPBone.custom_shape_transform = None
            for i in range(3):
                aimPBone.lock_location[i] = False

            #depending on the object's aimAxis, move aimTemp 1 unit along that axis
            if obj.aimAxis == '+Y':
                aimTempP.location[1] = 1
            elif obj.aimAxis == '-Y':
                aimTempP.location[1] = -1
            elif obj.aimAxis == '+X':
                aimTempP.location[0] = 1
            elif obj.aimAxis == '-X':
                aimTempP.location[0] = -1
            elif obj.aimAxis == '+Z':
                aimTempP.location[2] = 1
            elif obj.aimAxis == '-Z':
                aimTempP.location[2] = -1
            
            #have the aimBone copy the location of the aimTemp bone
            copyLocation = aimPBone.constraints.new('COPY_LOCATION')
            copyLocation.target = obj
            copyLocation.subtarget = aimTempP.name

            #and add limit distance constraint so that all aim bones are at the same distance away from their respective rig bone
            limitDistance = aimPBone.constraints.new('LIMIT_DISTANCE')
            limitDistance.target = obj
            limitDistance.subtarget = aimBoneN.replace(".aim.rig",".rig")
            limitDistance.limit_mode = 'LIMITDIST_ONSURFACE' #'LIMITDIST_OUTSIDE'
            aimDistance = obj.aimDistance
            limitDistance.distance = aimDistance

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
                        
                        targetBoneP = obj.pose.bones[boneP.name.replace(".aim.rig", ".rig")]
                        targetBoneDataPath = targetBoneP.path_from_id()

                        locationXYZList = [Channel.locationX, Channel.locationY, Channel.locationZ]
                        
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

        #make rig bones follow coresponding aim bones
        for aimBoneN in aimBonesListN:
            selectedBoneN = aimBoneN.replace(".aim.rig",".rig")
            selectedBoneP = obj.pose.bones[selectedBoneN]
            if ".world." in selectedBoneN:
                selectedBoneP.custom_shape = bpy.data.objects["RotF_SquarePointer+Y"]
            else:
                selectedBoneP.custom_shape = bpy.data.objects["RotF_CirclePointer+Y"]

            dampedTrack = selectedBoneP.constraints.new('DAMPED_TRACK')
            dampedTrack.target = obj
            dampedTrack.subtarget = aimBoneN

            if obj.aimAxis == '+Y':
                dampedTrack.track_axis = 'TRACK_Y'
            elif obj.aimAxis == '-Y':
                dampedTrack.track_axis = 'TRACK_NEGATIVE_Y'
            elif obj.aimAxis == '+X':
                dampedTrack.track_axis = 'TRACK_X'
            elif obj.aimAxis == '-X':
                dampedTrack.track_axis = 'TRACK_NEGATIVE_X'
            elif obj.aimAxis == '+Z':
                dampedTrack.track_axis = 'TRACK_Z'
            elif obj.aimAxis == '-Z':
                dampedTrack.track_axis = 'TRACK_NEGATIVE_Z'

            #armature set to edit mode
            bpy.ops.object.mode_set(mode='EDIT')
            armature.edit_bones.remove(armature.edit_bones[aimBoneN.replace(".aim.rig",".aimTemp.rig")])

            #armature set to pose mode
            bpy.ops.object.mode_set(mode='POSE')

            