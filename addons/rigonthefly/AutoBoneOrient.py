#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from mathutils import Matrix, Euler, Vector
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils
from . PolygonShapesUtility import PolygonShapes

class AutoBoneOrientUtils:

    def AutoBoneOrient(self, context):
        PolygonShapes.AddControllerShapes() #add conrtoller shapes to the scene
        
        activeObject = bpy.context.active_object #set aside the active object as a variable
        armature = activeObject.data #set aside the active object's armature as a variable
        #bones list needed
        baseBonesNList = list()
        orientChildrenNList = list()
        orientBonesNList = list()
        orientRigBonesNList = list()

        #list visible layers
        originalLayers = list()
        layersToTurnOff = list()
        for layer in range(32):
            if activeObject.data.layers[layer] == True:
                originalLayers.append(layer)
            else: 
                armature.layers[layer] = True
                layersToTurnOff.append(layer)

        #
        baseLayer = activeObject.baseBonesLayer
        rigLayer = activeObject.rigBonesLayer        
        unorientedLayer = activeObject.notOrientedBonesLayer
        translatorLayer = activeObject.translatorBonesLayer
        
        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        for boneP in bpy.context.selected_pose_bones:
            boneP.bone.select = False
        for layer in range(32):
            if layer in layersToTurnOff:
                armature.layers[layer] = False

        #set armature baseLayer from the Layer Settings to visible
        armature.layers[baseLayer] = True
        
        #select all base armature bones
        bpy.ops.pose.select_all(action='SELECT')

        StateUtility.MoveBonesToLayer(baseLayer)

        #hide originally visible layers
        for layer in range(32):
            if layer != baseLayer:
                activeObject.data.layers[layer] = False

        #set armature layers rigLayer unorientedLayer translatorLayer from the Layer Settings to visible
        armature.layers[rigLayer] = True
        armature.layers[unorientedLayer] = True
        armature.layers[translatorLayer] = True 

        #add selected bones' names to bones lists
        selectedPBones = bpy.context.selected_pose_bones.copy()
        selectedPBones.sort(key = lambda x:len(x.parent_recursive))
        for boneP in selectedPBones:
            boneN = boneP.name
            baseBonesNList.append(boneN)
            boneN = StateUtility.LeftRightSuffix(boneN)
            orientChildrenNList.append(boneN + ".orient.child")
            orientBonesNList.append(boneN + ".orient")
            orientRigBonesNList.append(boneN + ".orient.rig")

        #set to edit mode
        StateUtility.SetEditMode()

        #disconnect base bones from their parents
        for boneN in baseBonesNList:
            armature.edit_bones[boneN].use_connect = False

        #set to pose mode
        bpy.ops.object.mode_set(mode='POSE')

        StateUtility.PoseBoneGroups() #add pose bones groups

        StateUtility.DuplicateBones(activeObject, ".orient.child") #duplicate selected bones and selects them instead
        
        #set to edit mode
        StateUtility.SetEditMode()

        #duplicate .orient. Duplicated bones are selected from this operation
        bpy.ops.armature.duplicate()

        #change duplicated bones' names to ".orient.parent"
        for boneE in bpy.context.selected_bones:
            boneE.name = boneE.name.replace(".child.001", "")
        
        #orient the dupliacted bones to work better with Blender's constraints
        AutoBoneOrientUtils.OrientBones(armature, orientBonesNList)

        #duplicate ".orient.parent". Duplicated bones are selected from this operation
        bpy.ops.armature.duplicate()

        #change duplicated bones' names to ".orient.rig"
        for boneE in bpy.context.selected_bones:
            boneE.name = boneE.name.replace(".orient.001", ".orient.rig")

        #Now that ".orient" and ".orient.parent" bones exist in the scene, the ".orient" are temporarly set as parent of the ".orient.parent" for transfering animation data through constraints baking
        for boneN in orientBonesNList:
            boneE = armature.edit_bones[boneN]
            boneE.parent = armature.edit_bones[boneN +".child"]

        #ALL NEEDED BONES CHAINS ARE NOW CREATED

        #MAKE ORIENT AND ORIENT BONES MIRROR
        activeObject.data.use_mirror_x = True
        
        for i, baseBoneN in enumerate(baseBonesNList):
            boneN = StateUtility.LeftRightSuffix(baseBoneN)
            if "R." in boneN:
                orientBoneN = boneN + ".orient"
                orientRigN = boneN + ".orient.rig"

                orientBoneE = armature.edit_bones[orientBoneN]
                orientRigE = armature.edit_bones[orientRigN]

                orientBoneE.roll = orientBoneE.roll
                orientRigE.roll = orientRigE.roll

        #ADD CONSTRAINT FOR TRANSFERING ANIMATION DATA FROM BASE BONES TO RIG BONES

        #set to pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #deselect all
        bpy.ops.pose.select_all(action='DESELECT')
        
        for i, baseBoneN in enumerate(baseBonesNList):
            #find relevant names
            boneN = StateUtility.LeftRightSuffix(baseBoneN)
            orientChildN = boneN + ".orient.child"
            orientBoneN = boneN + ".orient"
            orientRigN = boneN + ".orient.rig"
            #from the names, find the pose bones
            orientChildP = activeObject.pose.bones[orientChildN]
            orientRigP = activeObject.pose.bones[orientRigN]
            
            #add bones to their corresponding layer
            armature.bones[baseBoneN].layers[unorientedLayer] = True
            armature.bones[orientChildN].layers[translatorLayer] = True
            armature.bones[orientRigN].layers[rigLayer] = True

            #remove bones from the 1st layer
            armature.bones[baseBoneN].layers[baseLayer] = False
            armature.bones[orientChildN].layers[baseLayer] = False
            armature.bones[orientRigN].layers[baseLayer] = False
            
            #disable deform on all bones except the base bone
            armature.bones[orientChildN].use_deform = False
            armature.bones[orientBoneN].use_deform = False
            armature.bones[orientRigN].use_deform = False

            #change display of ".orient.rig" to a circle and rotation mode to YZX
            orientRigP.custom_shape = bpy.data.objects["RotF_Circle"]
            armature.bones[orientRigN].show_wire = True
            #orientRigP.rotation_mode = 'YZX'

            #for the first two bones of the hierarchy have the controller size bigger
            if i < 2:
                objDimensions = (activeObject.dimensions[0] + activeObject.dimensions[1] + activeObject.dimensions[2])/3
                objWorldScaleV = activeObject.matrix_world.to_scale()
                objWorldScale = (objWorldScaleV[0] + objWorldScaleV[1] + objWorldScaleV[2])/3
                objSize = objDimensions / objWorldScale
                sizeMultiplyer = objSize / orientRigP.length
                orientRigP.custom_shape_scale *= sizeMultiplyer/(2*(i+3))

            #have the ".orient" bone follow the base bone using a copy transform constraint
            orientChildConstraint = orientChildP.constraints.new('COPY_TRANSFORMS')
            orientChildConstraint.target = activeObject
            orientChildConstraint.subtarget = baseBoneN

            #have the ".orient.rig" bone follow the ".orient.parent" bones using a copy transform constraint
            orientRigConstraint = orientRigP.constraints.new('COPY_TRANSFORMS')
            orientRigConstraint.target = activeObject
            orientRigConstraint.subtarget = orientBoneN

            #add ".orient.rig" to selection
            armature.bones[orientRigN].select = True
        
        if activeObject.animation_data: #check if active object has an action to bake
            #bake animation on selection and remove constraints
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
                    #quaternionWXYZList = [Channel.quaternionW, Channel.quaternionX, Channel.quaternionY, Channel.quaternionZ]
                    eulerXYZList = [Channel.eulerX, Channel.eulerY, Channel.eulerZ]
                    scaleXYZList = [Channel.scaleX, Channel.scaleY, Channel.scaleZ]

                    for i, boneN in enumerate(orientRigBonesNList):
                        boneP = obj.pose.bones[boneN]
                        baseBoneN = baseBonesNList[i]
                        channelsList = list()
                        
                        bonePDataPath = boneP.path_from_id()
                        targetBoneDataPath = bonePDataPath.replace(boneN, baseBoneN) #bonePDataPath.replace(".orient.rig","")

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
                                channelsList.extend(scaleXYZList)
                                StateUtility.GetFramePointFromFCurve(fcurve, frames)

                        bonePChannelsToBake[boneP] = channelsList
                    DypsloomBakeUtils.DypsloomBake(obj, action, frames, bonePChannelsToBake)

                StateUtility.RestoreTracksState(obj, tracksStateDict, soloTrack, activeActionBlendMode) #remove the bakeTrack

                obj.animation_data.action = initialAction
            StateUtility.RestoreActionState(ActionInitialState, objectActionsDictionary) #return objects' actions to tweak mode if it was their initial state
            #------------------------------------------------------------------------------------------------------------------------------------

        StateUtility.RemoveConstraintsOfSelectedPoseBones()

        #remove copy transform on "orient.child"
        for orientChildN in orientChildrenNList:
            orientChildP = activeObject.pose.bones[orientChildN]

            while orientChildP.constraints:
                orientChildP.constraints.remove(orientChildP.constraints[0])

        #FLIP PARENT RELATION BETWEEN CHILD BONES AND ORIENT BONES
        #set to edit mode
        StateUtility.SetEditMode()

        for i, orientChildN in enumerate(orientChildrenNList):

            baseBoneN = baseBonesNList[i] #orientChildN.replace(".orient.child","")
            orientBoneN = orientChildN.replace(".child","")

            if armature.edit_bones[baseBoneN].parent:
                baseParentBoneN = armature.edit_bones[baseBoneN].parent.name
                orientBoneParentN = baseParentBoneN +".orient"
                if armature.edit_bones.get(orientBoneParentN):
                    armature.edit_bones[orientBoneN].parent = armature.edit_bones[orientBoneParentN] #set orientBone parent to be the ".orient" equivalent of the base base bone's parent
                else:
                    armature.edit_bones[orientBoneN].parent = armature.edit_bones[baseParentBoneN]
            else:
                armature.edit_bones[orientBoneN].parent = None #remove parent from orient bone
            
            armature.edit_bones[orientChildN].parent = armature.edit_bones[orientBoneN] #make ".orient" bone parent of ".orient.child"

        #REVERSE CONSTRAINTS SO THAT BASE BONES TO FOLLOW RIG BONES MOTION

        #set to pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #deselect all
        bpy.ops.pose.select_all(action='DESELECT')

        #
        for i, baseBoneN in enumerate(baseBonesNList):
            #find relevant names
            orientChildN = orientChildrenNList[i] #baseBoneN + ".orient.child"
            orientBoneN = orientBonesNList[i] #baseBoneN + ".orient"
            orientRigN = orientRigBonesNList[i] #baseBoneN + ".orient.rig"
            #from the names, find the pose bones
            baseBoneP = activeObject.pose.bones[baseBoneN]
            #orientChildP = activeObject.pose.bones[orientChildN]
            orientBoneP = activeObject.pose.bones[orientBoneN]
            #orientRigP = activeObject.pose.bones[orientRigN]

            #have the ".orient" bone follow the base bone using a copy transform constraint
            orientConstraint = orientBoneP.constraints.new('COPY_TRANSFORMS')
            orientConstraint.target = activeObject
            orientConstraint.subtarget = orientRigN

            #have the ".orient" bone follow the base bone using a copy transform constraint
            baseConstraint = baseBoneP.constraints.new('COPY_TRANSFORMS')
            baseConstraint.target = activeObject
            baseConstraint.subtarget = orientChildN

            #add ".orient.child" and ".orient.rig" to selection
            armature.bones[baseBoneN].select = True
            armature.bones[orientBoneN].select = True
            armature.bones[orientChildN].select = True

        if activeObject.animation_data:
            #clear all key frames of selected bones
            StateUtility.KeyframeClear()

        #set armature layers 1, 4 and 5 to hidden
        armature.layers[baseLayer] = False
        armature.layers[unorientedLayer] = False
        armature.layers[translatorLayer] = False
        
    @staticmethod
    def OrientBones(armature, bonesNamesToOrient):
        parent_correction_inv = Matrix()

        #orient duplicated bones to be compatible with Rig on the Fly tools
        for boneN in bonesNamesToOrient:

            orientBone = armature.edit_bones[boneN]

            from bpy_extras.io_utils import axis_conversion
            
            #if parent_correction_inv:
            #    orientBone.pre_matrix = parent_correction_inv @ (orientBone.pre_matrix if orientBone.pre_matrix else Matrix())

            correction_matrix = Matrix()

            # find best orientation to align baseBone with
            bone_children = tuple(child for child in orientBone.children)
            if len(bone_children) == 0:
                # no children, inherit the correction from parent (if possible)
                correction_matrix = parent_correction_inv
                #if orientBone.parent:
                #    correction_matrix = parent_correction_inv.inverted() if parent_correction_inv else None
            else:
                # else find how best to rotate the baseBone to align the Y axis with the children
                best_axis = (1, 0, 0)
                if len(bone_children) == 1:
                    childMatrix = bone_children[0].matrix
                    orientBoneMatrix = orientBone.matrix                    
                    orientBoneMatrixInv = orientBoneMatrix.inverted()                    
                    vec= orientBoneMatrixInv @ childMatrix                    
                    vec= vec.to_translation()

                    best_axis = Vector((0, 0, 1 if vec[2] >= 0 else -1))
                    if abs(vec[0]) > abs(vec[1]):
                        if abs(vec[0]) > abs(vec[2]):
                            best_axis = Vector((1 if vec[0] >= 0 else -1, 0, 0))
                    elif abs(vec[1]) > abs(vec[2]):
                        best_axis = Vector((0, 1 if vec[1] >= 0 else -1, 0))
                else:
                    # get the child directions once because they may be checked several times
                    child_locs = list()
                    for child in bone_children:
                        childMatrix = child.matrix
                        orientBoneMatrix = orientBone.matrix                    
                        orientBoneMatrixInv = orientBoneMatrix.inverted()                        
                        vec= orientBoneMatrixInv @ childMatrix                        
                        vec= vec.to_translation()
                        child_locs.append(vec)
                    child_locs = tuple(loc.normalized() for loc in child_locs if loc.magnitude > 0.0)

                    # I'm not sure which one I like better...                
                    best_angle = -1.0
                    for vec in child_locs:

                        test_axis = Vector((0, 0, 1 if vec[2] >= 0 else -1))
                        if abs(vec[0]) > abs(vec[1]):
                            if abs(vec[0]) > abs(vec[2]):
                                test_axis = Vector((1 if vec[0] >= 0 else -1, 0, 0))
                        elif abs(vec[1]) > abs(vec[2]):
                            test_axis = Vector((0, 1 if vec[1] >= 0 else -1, 0))

                        # find max angle to children
                        max_angle = 1.0
                        for loc in child_locs:
                            max_angle = min(max_angle, test_axis.dot(loc))

                        # is it better than the last one?
                        if best_angle < max_angle:
                            best_angle = max_angle
                            best_axis = test_axis                

                # convert best_axis to axis string
                to_up = 'Z' if best_axis[2] >= 0 else '-Z'
                if abs(best_axis[0]) > abs(best_axis[1]):
                    if abs(best_axis[0]) > abs(best_axis[2]):
                        to_up = 'X' if best_axis[0] >= 0 else '-X'
                elif abs(best_axis[1]) > abs(best_axis[2]):
                    to_up = 'Y' if best_axis[1] >= 0 else '-Y'
                to_forward = 'X' if to_up not in {'X', '-X'} else 'Y'

                # Build correction matrix
                #if (to_up, to_forward) != ('Y', 'X'):
                correction_matrix = axis_conversion(from_forward='X',
                                                    from_up='Y',
                                                    to_forward=to_forward,
                                                    to_up=to_up,
                                                    ).to_4x4()
                            
            orientBone.matrix = orientBone.matrix @ correction_matrix
            parent_correction_inv = correction_matrix

        #now the orient bones are well oriented!
