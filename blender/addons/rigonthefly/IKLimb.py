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

class IKLimbUtils:

    def PolePosition (self, context, baseBoneN, poleBoneN, targetBoneN, ikPoleBoneN, tempIKPolePointerN):
        ########################################
        # Create and place IK pole target bone #
        #          by Marco Giordano           #
        ########################################

        # Get points to define the plane on which to put the pole target
        objectE = bpy.context.active_object.data.edit_bones
        A = objectE[baseBoneN].head
        B = objectE[poleBoneN].head
        C = objectE[targetBoneN].head

        # Vector of chain root (shoulder) to chain tip (wrist)
        AC = C - A

        # Vector of chain root (shoulder) to second bone's head (elbow)
        AB = B - A

        # Multiply the two vectors to get the dot product
        dot_prod = AB @ AC
        

        # Find the point on the vector AC projected from point B
        proj = dot_prod / AC.length

        # Normalize AC vector to keep it a reasonable magnitude
        start_end_norm = AC.normalized()

        # Project an arrow from AC projection point to point B
        isStraight, axisVector =  IKLimbUtils.IsLimbStraight(self, objectE, poleBoneN, AB , AC)
        if isStraight :
            arrow_vec = axisVector
        else :
            proj_vec  = start_end_norm * proj
            arrow_vec = AB - proj_vec
        
        arrow_vec = arrow_vec.normalized()

        # Place pole target at a reasonable distance from the chain
        arrow_vec *= AC.length/2
        final_vec = arrow_vec + B

        # place pole target bone in the scene pointed to Z+        
        objectE[ikPoleBoneN].head = final_vec
        objectE[ikPoleBoneN].tail = final_vec + arrow_vec
        objectE[ikPoleBoneN].length = AC.length *0.15
        objectE[ikPoleBoneN].roll = 0.0

        objectE[tempIKPolePointerN].head = B
        objectE[tempIKPolePointerN].tail = final_vec
        objectE[tempIKPolePointerN].roll = 0

        return isStraight

    ##############
    # Pole Angle #
    # by Jerryno #
    ##############

    def signed_angle (self, context, vector_u, vector_v, normal):
        # Normal specifies orientation
        angle = vector_u.angle(vector_v)
        if vector_u.cross(vector_v).angle(normal) < 1:
            angle = -angle
        return angle

    def get_pole_angle (self, context, base_bone, poleBone, pole_location):
        ##############
        # Pole Angle #
        # by Jerryno #
        ##############
        AC = poleBone.tail - base_bone.head
        AP = pole_location - base_bone.head
        pole_normal = AC.cross(AP)
        projected_pole_axis = pole_normal.cross(base_bone.tail - base_bone.head)

        if base_bone.x_axis == projected_pole_axis.normalized(): 
            return 0
        return IKLimbUtils.signed_angle(self, context, base_bone.x_axis, projected_pole_axis, base_bone.tail - base_bone.head)

    def GetNearestRightAngle (self, context, currentAngle):
            pole_angle0 = 0 #0°
            pole_angle90 = math.pi/2 #90°
            pole_angle180 = math.pi #180°
            pole_angle270 = -math.pi/2 #-90°

            if currentAngle < pole_angle0 + math.pi/4 and currentAngle > pole_angle0 - math.pi/4:
                return pole_angle0

            if currentAngle < pole_angle90 + math.pi/4 and currentAngle > pole_angle90 - math.pi/4:
                return pole_angle90

            if abs(currentAngle) > pole_angle180 - math.pi/4:
                return pole_angle180

            if currentAngle < pole_angle270 + math.pi/4 and currentAngle > pole_angle270 - math.pi/4:
                return pole_angle270

            return pole_angle0

    def PoleAngleRadian (self, context, base_bone, ik_bone, tempPole_bone, poleBone):
        pole_angle_in_radians = IKLimbUtils.get_pole_angle(
            self, 
            context, 
            base_bone,
            poleBone,
            tempPole_bone.matrix.translation)
        return (pole_angle_in_radians)

    def IsLimbStraight (self, obj, poleBoneN, AB, AC):
        straightnessThreshold = 0.9999 # Maximum 1
        normalized_dot_product = AB.normalized() @ AC.normalized()
        if abs(normalized_dot_product) < straightnessThreshold :
            return False, obj[poleBoneN].x_axis

        defaultAxisIndex = bpy.context.scene.rotf_ik_default_pole_axis
        # default axis defined in the properties file.
        axisVector =  obj[poleBoneN].x_axis
        if defaultAxisIndex == "+X":
            axisVector = obj[poleBoneN].x_axis
        if defaultAxisIndex ==  "-X":
            axisVector = -obj[poleBoneN].x_axis
        if defaultAxisIndex ==  "+Z":
            axisVector = obj[poleBoneN].z_axis
        if defaultAxisIndex ==  "-Z":
            axisVector = -obj[poleBoneN].z_axis
        
        return True, axisVector
        
    def IKLimb (self, context):
        PolygonShapes.AddControllerShapes() #add conrtoller shapes to the scene

        obj = bpy.context.active_object
        armature = obj.data

        stretchIK = bpy.context.scene.ikStretch

        #add bone name to selectedBonesN to have it's generated IK controller selected at the end of the script
        selectedBonesN = list()
        for boneP in bpy.context.selected_pose_bones:
            selectedBonesN.append(boneP.name)

        for targetBoneN in selectedBonesN:
            targetBoneP = obj.pose.bones[targetBoneN]
            #get the parent and parent's parent of one of the selected bones in pose mode
            if not obj.pose.bones[targetBoneN].parent or not obj.pose.bones[targetBoneN].parent.parent:
                return [{'WARNING'}, "not enough parents"]
            poleBoneP = obj.pose.bones[targetBoneN].parent
            baseBoneP = obj.pose.bones[targetBoneN].parent.parent
            #get the name of the parent and parent's parent of one of the selected bones
            poleBoneN = poleBoneP.name
            baseBoneN = baseBoneP.name

            if any(".rig" not in boneName for boneName in [targetBoneN, poleBoneN, baseBoneN]):
                return [{'WARNING'}, "one of the bones needed for IK is not .rig"]

            #move poleBone and baseBone to the same layer as targetBone
            for layer in range(32):
                armature.bones[poleBoneN].layers[layer] = armature.bones[targetBoneN].layers[layer]
                armature.bones[baseBoneN].layers[layer] = armature.bones[targetBoneN].layers[layer]

            #force edit mode
            StateUtility.SetEditMode()

            #deselect all
            bpy.ops.armature.select_all(action='DESELECT')

            #selects and duplicates the last bone in the hierarchy of the original selection
            armature.edit_bones[targetBoneN].select=True
            armature.edit_bones[targetBoneN].select_head=True
            armature.edit_bones[targetBoneN].select_tail=True
            bpy.ops.armature.duplicate()
            #rename ik bone
            armature.edit_bones[targetBoneN +".001"].name = targetBoneN.replace(".rig",".IK.rig")

            ikTargetBoneN = targetBoneN.replace(".rig",".IK.rig")
            #remove parent
            bpy.context.selected_editable_bones[0].parent = None

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
                #snap tail of selectedPoleBoneN to ikTargetBoneN head's position
                armature.edit_bones[poleStretchN].tail = armature.edit_bones[ikTargetBoneN].head

            bpy.ops.armature.select_all(action='DESELECT')
            #selects and duplicates the second bone in the hierarchy of the original selection
            armature.edit_bones[poleBoneN].select=True
            armature.edit_bones[poleBoneN].select_head=True
            armature.edit_bones[poleBoneN].select_tail=True

            #duplicate once for the temporary bone that will be inbetween the base bone and the target bone pointing at the pole bone
            bpy.ops.armature.duplicate()
            #rename ik bone            
            bpy.context.selected_editable_bones[0].name = bpy.context.selected_editable_bones[0].name.replace(".rig.001",".temp.pointer.rig")
            tempIKPolePointerN = bpy.context.selected_editable_bones[0].name
            #remove parent
            armature.edit_bones[tempIKPolePointerN].parent = None

            #duplicate a second time for the bone placed at the wanted pole vector location
            bpy.ops.armature.duplicate()
            #rename ik bone            
            bpy.context.selected_editable_bones[0].name = bpy.context.selected_editable_bones[0].name.replace(".temp.pointer.rig.001",".temp.pole.rig")
            tempIKPoleBoneN = bpy.context.selected_editable_bones[0].name
            #set parent to tempIKPolePointerN
            armature.edit_bones[tempIKPoleBoneN].parent = armature.edit_bones[tempIKPolePointerN]

            #place temp ik pole correctly in edit mode and return if the limb chain is straight
            isStraight = IKLimbUtils.PolePosition(self, context, baseBoneN, poleBoneN, targetBoneN, tempIKPoleBoneN, tempIKPolePointerN)
            
            #duplicate ikPoleBone to get tempIKPoleBoneN used to get the desired motion for the ikPole
            bpy.ops.armature.duplicate()
            bpy.context.selected_editable_bones[0].name = bpy.context.selected_editable_bones[0].name.replace(".temp.pole.rig.001",".pole.rig")
            ikPoleBoneN = bpy.context.selected_editable_bones[0].name
            #remove parent
            armature.edit_bones[ikPoleBoneN].parent = None            

            #snap tail of selectedPoleBoneN to ikTargetBoneN head's position
            poleBoneOldLength = armature.edit_bones[poleBoneN].length
            armature.edit_bones[poleBoneN].tail = armature.edit_bones[ikTargetBoneN].head
            poleBoneNewLength = armature.edit_bones[poleBoneN].length
            poleBoneLengthFactor = poleBoneOldLength/poleBoneNewLength

            #to keep poleBone's custom shape visual size in case snapping it's tail onto targetBone's head changed poleBone's length
            poleBoneP.custom_shape_scale *= poleBoneLengthFactor

            baseBoneB = armature.edit_bones[baseBoneN]
            ikTargetBoneB = armature.edit_bones[ikTargetBoneN]
            tempIKPoleBoneB = armature.edit_bones[tempIKPoleBoneN]
            poleBoneB = armature.edit_bones[poleBoneN]

            poleAngle = IKLimbUtils.PoleAngleRadian (self, context, baseBoneB, ikTargetBoneB, tempIKPoleBoneB, poleBoneB)

            #force pose mode
            bpy.ops.object.mode_set(mode='POSE')
            #change rig bones' display to square, rotation mode to euler YZX and adds copy transform constraint to copy the base armature's animation.
            ikTargetBoneP = obj.pose.bones[ikTargetBoneN]
            ikTargetBoneP.custom_shape = bpy.data.objects["RotF_Square"]
            armature.bones[ikTargetBoneN].show_wire = True
            copyTransforms = ikTargetBoneP.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = obj
            copyTransforms.subtarget = targetBoneN

            if stretchIK:
                #change rig bones' display to square, rotation mode to euler YZX and adds copy transform constraint to copy the base armature's animation.
                baseStretchP = obj.pose.bones[baseStretchN]
                baseStretchP.custom_shape = bpy.data.objects["RotF_Square"]
                baseStretchP.ik_stretch = 0.001

                #change rig bones' display to square, rotation mode to euler YZX and adds copy transform constraint to copy the base armature's animation.
                poleStretchP = obj.pose.bones[poleStretchN]
                poleStretchP.custom_shape = bpy.data.objects["RotF_Square"]
                poleStretchP.ik_stretch = 0.001
            
            #change rig bones' display to square, rotation mode to euler YZX and adds copy transform constraint to copy the base armature's animation.
            ikPoleBoneP = obj.pose.bones[ikPoleBoneN]
            ikPoleBoneP.custom_shape = bpy.data.objects["RotF_Locator"]
            armature.bones[ikPoleBoneP.name].show_wire = True
            ikPoleBoneP.rotation_mode = poleBoneP.rotation_mode
            copyTransforms = ikPoleBoneP.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = obj
            copyTransforms.subtarget = ikPoleBoneP.name.replace(".pole.rig",".temp.pole.rig")

            #constrain tempIKPolePointer to stay between the base bone and the target bone pointing towards the pole bone
            tempIKPolePointerP = obj.pose.bones[tempIKPolePointerN]
            #copy location of base bone
            copyLocation = tempIKPolePointerP.constraints.new('COPY_LOCATION')
            copyLocation.target = obj
            copyLocation.subtarget = baseBoneN
            #copy a fraction of the location of target bone
            copyLocation = tempIKPolePointerP.constraints.new('COPY_LOCATION')
            copyLocation.target = obj
            copyLocation.subtarget = targetBoneN
            baseToPole = baseBoneP.bone.head_local - poleBoneP.bone.head_local #distance between baseBone and poleBone
            poleToTarget = poleBoneP.bone.head_local - targetBoneP.bone.head_local #distance between poleBone and targetBone
            copyLocation.influence = baseToPole.length/(baseToPole.length + poleToTarget.length)
            #point towards pole bone
            pointerIK = tempIKPolePointerP.constraints.new('IK')
            pointerIK.target = obj
            pointerIK.subtarget = poleBoneN

            #only adds ikTargetBoneN to selection since ikPoleBone is already selected
            armature.bones[tempIKPoleBoneN].select = True
            armature.bones[ikTargetBoneN].select = True
            #remove tempIKPoleBoneN from selection to prevent baking it
            armature.bones[tempIKPoleBoneN].select = False
            
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
                            if ikTargetBoneP.rotation_mode == 'QUATERNION':
                                bonePChannelsToBake[ikTargetBoneP] = channelsList + quaternionWXYZList
                                
                            else:
                                bonePChannelsToBake[ikTargetBoneP] = channelsList + eulerXYZList
                            
                            targetBoneDataPath = targetBoneP.path_from_id()
                            for i in range(3):
                                fcurve = action.fcurves.find(targetBoneDataPath + ".scale",index=i)
                                if fcurve:
                                    if i == 0: #if scale X channel
                                        bonePChannelsToBake[ikTargetBoneP].append(Channel.scaleX)
                                    if i == 1: #if scale Y channel
                                        bonePChannelsToBake[ikTargetBoneP].append(Channel.scaleY)
                                    if i == 2: #if scale Z channel
                                        bonePChannelsToBake[ikTargetBoneP].append(Channel.scaleZ)

                            bonePChannelsToBake[ikPoleBoneP] = channelsList
                        DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)

                    StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack
                    obj.animation_data.action = initialAction
                StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
                #------------------------------------------------------------------------------------------------------------------------------------
            
            StateUtility.RemoveConstraintsOfSelectedPoseBones()

            if stretchIK:
                #adds ik constraint to selectedPoleBoneN
                ikBone = obj.pose.bones[poleStretchN]
            else :
                #adds ik constraint to selectedPoleBoneN
                ikBone = obj.pose.bones[poleBoneN]

            ik = ikBone.constraints.new('IK')
            ik.target = obj
            ik.subtarget = ikTargetBoneN
            ik.pole_target = obj
            ik.pole_subtarget = ikPoleBoneN
            ik.pole_angle = -math.pi/2 #-90°
            ik.pole_angle = poleAngle
            ik.chain_count = 2

            #selectedTargetBone follow ikTargetBone transforms
            copyRotation = targetBoneP.constraints.new('COPY_ROTATION')
            copyRotation.target = obj
            copyRotation.subtarget = ikTargetBoneN

            copyScale = targetBoneP.constraints.new('COPY_SCALE')
            copyScale.target = obj
            copyScale.subtarget = ikTargetBoneN

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
            armature.bones[baseBoneN].select = True

            armature.bones[tempIKPoleBoneN].select = True

            if obj.animation_data:
                #clear all key frames of selected bones
                StateUtility.KeyframeClear()

            #deselect all to prevent baking bones that were left selected
            bpy.ops.pose.select_all(action='DESELECT')

            #remove tempIKPoleBoneN
            StateUtility.SetEditMode()
            try:
                armature.edit_bones.remove(armature.edit_bones[tempIKPoleBoneN])
                armature.edit_bones.remove(armature.edit_bones[tempIKPolePointerN])
            except:
                print(tempIKPoleBoneN)
            #return to pose mode
            bpy.ops.object.mode_set(mode='POSE')


            if isStraight:
                bendAmount = 0.001
                defaultAxisIndex = bpy.context.scene.rotf_ik_default_pole_axis
                if stretchIK:
                    boneToBend = poleStretchP
                else:
                    boneToBend = poleBoneP
                if defaultAxisIndex == "+X":
                    boneToBend.rotation_quaternion.z = bendAmount
                    boneToBend.rotation_euler.z = bendAmount
                if defaultAxisIndex ==  "-X":
                    boneToBend.rotation_quaternion.z = -bendAmount
                    boneToBend.rotation_euler.z = -bendAmount
                if defaultAxisIndex ==  "+Z":
                    boneToBend.rotation_quaternion.x = -bendAmount
                    boneToBend.rotation_euler.x = -bendAmount
                if defaultAxisIndex ==  "-Z":
                    boneToBend.rotation_quaternion.x = bendAmount
                    boneToBend.rotation_euler.x = bendAmount


            unusedLayer = obj.unusedRigBonesLayer

            #move non relevant bones to unused layer
            bonesToMove = [targetBoneN, poleBoneN, baseBoneN]
            if stretchIK:
                bonesToMove.extend([baseStretchN, poleStretchN])

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
            armature.bones[targetBoneN.replace(".rig",".IK.rig")].select = True
