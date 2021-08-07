#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils
from . PolygonShapesUtility import PolygonShapes
from mathutils import Matrix, Euler, Vector
from math import radians

class StretchWorldUtils:

    def ChangeToStretchWorld (self, context):
        PolygonShapes.AddControllerShapes() #add conrtoller shapes to the scene

        obj = bpy.context.object
        armature = obj.data

        unusedLayer = obj.unusedRigBonesLayer

        #armature set to pose mode
        bpy.ops.object.mode_set(mode='POSE')

        boneNamesList = list()
        selectedRigBoneNameList = list()
        aimBonesListN = list()
        for pbone in bpy.context.selected_pose_bones:
            selectedRigBoneNameList.append(pbone.name)
            aimBonesListN.append(pbone.name.replace(".rig",".aim.rig"))

            rigBoneN = pbone.name
            baseN = rigBoneN.replace(".rig","")
            aimBoneN = baseN + ".aim.rig"
            aimCopyN = baseN + ".aimCopy.rig"
            aimOffsetN = baseN + ".aimOffset.rig"
            aimTempN = baseN + ".aimTemp.rig"

            boneNamesList.append((rigBoneN, aimBoneN, aimCopyN, aimOffsetN, aimTempN))

        #force edit mode
        StateUtility.SetEditMode()
        
        #duplicate rig bones to be used as aim bones
        bpy.ops.armature.duplicate()
        bpy.ops.armature.duplicate()
        bpy.ops.armature.duplicate()
        bpy.ops.armature.duplicate()

        #add .aim.rig suffix to duplicate bones now known as aim bones.
        for rigBoneN, aimBoneN, aimCopyN, aimOffsetN, aimTempN in boneNamesList:
            rigBoneE = armature.edit_bones[rigBoneN]

            aimBoneE = armature.edit_bones[rigBoneN +".001"]
            aimBoneE.name = aimBoneN

            aimCopyE = armature.edit_bones[rigBoneN +".002"]
            aimCopyE.name = aimCopyN

            aimOffsetE = armature.edit_bones[rigBoneN +".003"]
            aimOffsetE.name = aimOffsetN

            aimTempE = armature.edit_bones[rigBoneN +".004"]
            aimTempE.name = aimTempN

            #find the matrix coordinates of the armature object
            armatureMatrix = obj.matrix_world
            #invert armature's matrix to find where global(0,0,0) is in relation to the armature's position/roation
            armatureMatrixInvert= armatureMatrix.copy()
            armatureMatrixInvert.invert()
            #set aim bone position to global (0,0,0) with axis following world's
            aimBoneE.matrix = armatureMatrixInvert

            aimBoneE.length = rigBoneE.length * 0.4
            aimBoneE.parent = None

            aimCopyE.parent = aimOffsetE

            aimTempE.parent = rigBoneE

            x, y, z = aimOffsetE.matrix.to_3x3().col
            # rotation matrix 30 degrees around local x axis thru head
            if obj.aimAxis == '+Y':
                continue
            else:
                if obj.aimAxis == '-Y':
                    a = z
                    s = 2 
                elif obj.aimAxis == '+X':
                    a = z
                    s = -1
                elif obj.aimAxis == '+Z':
                    a = x
                    s = 1
                elif obj.aimAxis == '-X':
                    a = z
                    s = 1
                elif obj.aimAxis == '-Z':
                    a = x
                    s = -1
                R = (Matrix.Translation(aimOffsetE.head) @
                    Matrix.Rotation(radians(s*90), 4, a) @
                    Matrix.Translation(-aimOffsetE.head)
                    )
                aimOffsetE.matrix = R @ aimOffsetE.matrix
                aimTempE.matrix = R @ aimTempE.matrix

        #armature set to pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #deselect all pose bones
        bpy.ops.pose.select_all(action='DESELECT')

        #change rig bones' display to locator and adds copy location constraint to copy the rig bones tail animation.
        for rigBoneN, aimBoneN, aimCopyN, aimOffsetN, aimTempN in boneNamesList:

            aimOffsetP = obj.pose.bones[aimOffsetN]

            copyTransforms = aimOffsetP.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = obj
            copyTransforms.subtarget = aimTempN

            aimCopyP = obj.pose.bones[aimCopyN]
            if not aimCopyP.bone.use_inherit_rotation:
                aimCopyP.bone.use_inherit_rotation = True
            if not aimCopyP.bone.use_inherit_scale:
                aimCopyP.bone.use_inherit_scale = True

            aimBoneP = obj.pose.bones[aimBoneN]

            aimBoneP = obj.pose.bones[aimBoneN]
            aimBoneP.custom_shape = bpy.data.objects["RotF_Locator"]
            aimBoneP.bone.show_wire = True
            aimBoneP.custom_shape_transform = None
            for i in range(3):
                aimBoneP.lock_location[i] = False

            copyLocation = aimBoneP.constraints.new('COPY_LOCATION')
            copyLocation.target = obj
            copyLocation.subtarget = aimOffsetN
            copyLocation.head_tail = 0.001

            #and add limit distance constraint so that all aim bones are at the same distance away from the rig bone
            limitDistance = aimBoneP.constraints.new('LIMIT_DISTANCE')

            limitDistance.target = obj
            limitDistance.subtarget = aimOffsetN
            limitDistance.limit_mode = 'LIMITDIST_ONSURFACE' #'LIMITDIST_OUTSIDE'
            aimDistance = obj.aimDistance
            limitDistance.distance = aimDistance

            aimBoneP.bone.select = True
            aimOffsetP.bone.select = True

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

        #deselect all pose bones
        bpy.ops.pose.select_all(action='DESELECT')

        #move rigBone and aimCopy to the unused layer
        for rigBoneN, aimBoneN, aimCopyN, aimOffsetN, aimTempN in boneNamesList:
            armature.bones[rigBoneN].select = True
            armature.bones[aimCopyN].select = True
            StateUtility.MoveBonesToLayer(unusedLayer)
        
        #deselect all pose bones
        bpy.ops.pose.select_all(action='DESELECT')

        #make rig bones follow coresponding aim bones
        for rigBoneN, aimBoneN, aimCopyN, aimOffsetN, aimTempN in boneNamesList:

            aimOffsetP = obj.pose.bones[aimOffsetN]
            if ".world." in aimOffsetN:
                aimOffsetP.custom_shape = bpy.data.objects["RotF_SquarePointer+Y"]
            else:
                aimOffsetP.custom_shape = bpy.data.objects["RotF_CirclePointer+Y"]

            stretchConstraint = aimOffsetP.constraints.new('STRETCH_TO')
            stretchConstraint.target = obj
            stretchConstraint.subtarget = aimBoneN

            rigBoneP = obj.pose.bones[rigBoneN]

            copyTransforms = rigBoneP.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = obj
            copyTransforms.subtarget = aimCopyN

            aimBoneP = obj.pose.bones[aimBoneN]
            aimBoneP.bone.select = True

            #armature set to edit mode
            bpy.ops.object.mode_set(mode='EDIT')
            armature.edit_bones.remove(armature.edit_bones[aimTempN])

            #armature set to pose mode
            bpy.ops.object.mode_set(mode='POSE')
            