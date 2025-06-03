#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
import math
import mathutils
from . import duplicateBone
from . import boneCollections
from . import removeConstraints
from . import rigState
from . import importControllerShapes
from . import rotfBake

class IKLimbConstraint:

    def __init__(self):
        print('IK Limb Constraint')

    def CreateIKLimbConstraint(ikSettingsList):
        ikTargetPBoneList = list()

        bonesToBakeInfo = SetupIKControllers(ikSettingsList)

        for ikSettings in ikSettingsList:
            ikTargetPBoneList.append(ikSettings.ikTargetPBone)
        
        rotfBake.Bake(bonesToBakeInfo)
        
        SetupIKBehaviour(ikSettingsList)

        return ikTargetPBoneList

    def CreateConstraint(self, obj, constraintInfoList):
        ikSettingsList = list()
        errorMessageList = list()
        for constraintInfo in constraintInfoList:

            targetBoneN = constraintInfo['bone_list'][0]
            if obj.data.bones.get(targetBoneN) == None: #check if target bone exists. if not, skips
                errorMessageList.append("IK Constraint|Bone not found: " + obj.name + "[" + targetBoneN + "]")
                continue

            targetPBone = obj.pose.bones[targetBoneN]

            bool_list = constraintInfo['bool_list']
            poleVector = bool_list[0]

            string_list = constraintInfo['string_list']
            ikStretchType = string_list[0]
            defaultAxisIndex = string_list[1]

            int_list = constraintInfo['int_list']
            chainLength = int_list[0]

            ikSettings = IKSettings()
            ikSettings.targetPBone = targetPBone
            ikSettings.ikStretchType = ikStretchType
            ikSettings.poleVector = poleVector
            ikSettings.defaultAxisIndex = defaultAxisIndex
            ikSettings.chainLength = int(chainLength)

            ikSettingsList.append(ikSettings)

        IKLimbConstraint.CreateIKLimbConstraint(ikSettingsList)

        if errorMessageList:
            return errorMessageList

class IKSettings:
    def __init__(self): 
        self.targetPBone = None #pose bone
        self.chainLength = None #int
        self.ikStretchType = None #string
        self.poleVector = None #boolean
        self.defaultAxisIndex = None #string

        self.isStraight = False
        self.mainAxisIsY = True
        self.axisToBend = None
        self.bendSign = None
        self.constrainedBoneAxisToBend = None
        self.constrainedBoneSign = None
        self.poleAngle = float()

        self.obj = None
        self.bones = None
        self.poseBones = None
        self.editBones = None

        self.targetBoneN = None

        self.ikChainBaseBoneN = None
        self.ikChainBasePBone = None
        self.ikChainBaseEBone = None

        self.ikTargetBoneN = None
        self.ikTargetPBone = None
        self.ikTargetEBone = None

        self.ikPoleBoneN = None
        self.ikPolePBone = None
        self.ikPoleEBone = None

        self.chainAxisBoneN = None
        self.chainAxisPBone = None
        self.chainAxisEBone = None

        self.poleAngleOffsetBoneN = None
        self.poleAngleOffsetPBone = None
        self.poleAngleOffsetEBone = None

        self.poleAngleFlipped = False

        self.tempPoleBoneN = None
        self.tempPolePBone = None
        self.tempPoleEBone = None

        self.tempPointerBoneN = None
        self.tempPointerPBone = None
        self.tempPointerEBone = None

        self.boneNChainList = None
        self.pboneChainList = None
        self.eboneChainList = None

        self.offsetBoneNStretchChainList = None
        self.offsetPBoneStretchChainList = None
        self.offsetEBoneStretchChainList = None

        self.boneNStretchChainList = None
        self.pboneStretchChainList = None
        self.eboneStretchChainList = None

        self.tempBoneNStretchChainList = None
        self.tempPBoneStretchChainList = None
        self.tempEBoneStretchChainList = None

        self.offsetBoneN =  None
        self.offsetPBone =  None
        self.offsetEBone =  None

        self.refConstrainedBoneN = None
        self.refConstrainedPBone = None
        self.refConstrainedEBone = None

        self.constrainedBoneN = None
        self.constrainedPBone = None
        self.constrainedEBone = None

        self.tempConstrainedBoneN = None
        self.tempConstrainedPBone = None
        self.tempConstrainedEBone = None

        self.constrainedBoneLengthFactor = float()

def SetupIKControllers(ikSettingsList):
    #adds chain bones to their respective ikSettings depending on the chainLength value
    for ikSettings in ikSettingsList:
        targetPBone = ikSettings.targetPBone
        ikSettings.targetBoneN = targetPBone.name
        ikSettings.obj = targetPBone.id_data
        
        ikSettings.boneNChainList = list()
        ikSettings.pboneChainList = list()
        for i, pbone in zip(range(ikSettings.chainLength), targetPBone.parent_recursive):
            ikSettings.pboneChainList.append(pbone)
            ikSettings.boneNChainList.append(pbone.name)

    #force edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    mirrorX = bpy.context.object.data.use_mirror_x
    bpy.context.object.data.use_mirror_x = False

    #duplicate the needed bones
    for ikSettings in ikSettingsList:
        ikSettings.editBones = ikSettings.obj.data.edit_bones
        ikSettings.targetEBone = ikSettings.editBones[ikSettings.targetBoneN]
        
        #add IK target bone
        newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("IK.", [ikSettings.targetEBone])
        ikSettings.ikTargetBoneN = newBoneNames[0]
        ikSettings.ikTargetEBone = newEditBones[0]

        #remove parent of IK target
        ikSettings.ikTargetEBone.parent = None

        ikSettings.eboneChainList = list()
        for boneName in ikSettings.boneNChainList:
            ikSettings.eboneChainList.append(ikSettings.editBones[boneName])
        #if stretchIK is not None, duplicate the bones that will be part of the stretch chain and disconnect the target bone and the eboneChainList
        if ikSettings.ikStretchType != "None":

            newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("IKStretch.", ikSettings.eboneChainList)
            ikSettings.boneNStretchChainList = newBoneNames #assign the duplicated bone chain to the ikSettings' boneStretchChainList
            ikSettings.eboneStretchChainList = newEditBones

            #parent bones from eboneStretchChainList so that they form a single hierarchycal chain
            for i in range(len(ikSettings.eboneStretchChainList)-1):
                ikSettings.eboneStretchChainList[i].parent = ikSettings.eboneStretchChainList[i+1]

            newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("OffsetIKStretch.", ikSettings.eboneChainList)
            ikSettings.offsetBoneNStretchChainList = newBoneNames #assign the duplicated bone chain to the ikSettings' offsetBoneStretchChainList
            ikSettings.offsetEBoneStretchChainList = newEditBones

            #parent the offset stretch bones to their corresponding stretch bones
            for stretchEBone, offsetStretchEBone in zip(ikSettings.eboneStretchChainList, ikSettings.offsetEBoneStretchChainList):
                offsetStretchEBone.parent = stretchEBone

            #have the Y axis of bones from the stretch chain list point up the chain so that it is compatible with how IK stretch functions in Blender
            tailTargetEBoneList = [ikSettings.targetEBone] + ikSettings.eboneChainList[:-1]
            for ebone, tailTargetEBone in zip(ikSettings.eboneStretchChainList, tailTargetEBoneList):
                ebone.tail = tailTargetEBone.head

            #duplicate the stretch chain bones to be help transfer FK motion to the stretch chain
            newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("Temp", ikSettings.eboneStretchChainList)
            ikSettings.tempBoneNStretchChainList = newBoneNames #assign the duplicated bone chain to the ikSettings' offsetBoneStretchChainList
            ikSettings.tempEBoneStretchChainList = newEditBones

            #parent the tempStretch bones to their correspoding chain bones
            for tempStretchEBone, ebone in zip(ikSettings.tempEBoneStretchChainList, ikSettings.eboneChainList):
                tempStretchEBone.parent = ebone

            ikSettings.constrainedBoneN = ikSettings.boneNStretchChainList[0]
            ikSettings.constrainedEBone = ikSettings.eboneStretchChainList[0]

            ikSettings.ikChainBaseBoneN = ikSettings.boneNStretchChainList[-1]
            ikSettings.ikChainBaseEBone = ikSettings.eboneStretchChainList[-1]

            #disconnect the target bone and chain bones so that they can translate while stretching
            ikSettings.targetEBone.use_connect = False
            for ebone in ikSettings.eboneChainList:
                ebone.use_connect = False

        else:
            ikSettings.refConstrainedBoneN = ikSettings.boneNChainList[0]
            ikSettings.refConstrainedEBone = ikSettings.editBones[ikSettings.refConstrainedBoneN]

            ikSettings.ikChainBaseBoneN = ikSettings.boneNChainList[-1]
            ikSettings.ikChainBaseEBone = ikSettings.eboneChainList[-1]

            #add constrained bone
            newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("IKConstrained.", [ikSettings.refConstrainedEBone])
            ikSettings.constrainedBoneN = newBoneNames[0]
            ikSettings.constrainedEBone = newEditBones[0]

            #add offset bone and parent it to the constrained bone
            newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("IKOffset.", [ikSettings.refConstrainedEBone])
            ikSettings.offsetBoneN = newBoneNames[0]
            ikSettings.offsetEBone = newEditBones[0]
            ikSettings.offsetEBone.parent = ikSettings.constrainedEBone

            #snap tail of constrainedEBone to ikTargetEBone head's position
            constrainedBoneOldLength = ikSettings.constrainedEBone.length
            ikSettings.constrainedEBone.tail = ikSettings.ikTargetEBone.head
            constrainedBoneNewLength = ikSettings.constrainedEBone.length
            ikSettings.constrainedBoneLengthFactor = constrainedBoneOldLength/constrainedBoneNewLength

            #add temp version of the constrained bone for motion transfer
            newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("Temp", [ikSettings.constrainedEBone])
            ikSettings.tempConstrainedBoneN = newBoneNames[0]
            ikSettings.tempConstrainedEBone = newEditBones[0]
            ikSettings.tempConstrainedEBone.parent = ikSettings.targetEBone.parent


        if ikSettings.poleVector:
            A, C, AB, AC, proj, start_end_norm = PolePosition(ikSettings)
            
            # Project an arrow from AC projection point to point B
            #check if hierarchy chain forms a straight line, 
            isStraight, axisVector, vectorSign = IsLimbStraight(ikSettings, AB , AC)
            if isStraight:
                arrow_vec = axisVector * vectorSign
                ikSettings.axisToBend = FindAxisToBend(ikSettings, axisVector, AC) #findAxisToBend() also finds if mainAxisIsY

                #will not add a pole vector if the chain is both straigh and the main axis down the chain hierarchy is not the Y axis
                if ikSettings.mainAxisIsY == False:
                    ikSettings.poleVector = False
            else :
                proj_vec  = start_end_norm * proj
                arrow_vec = AB - proj_vec
        
        if ikSettings.poleVector:
            arrow_vec = arrow_vec.normalized()
            # Place pole target at a reasonable distance from the chain
            arrow_vec *= AC.length/2
            final_vec = arrow_vec + (A+C)*0.5

            arrow_vec, final_vec, isStraight

            arrow_vec, final_vec, ikSettings.isStraight

            #add ik pole bone
            newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("IKPole.", [ikSettings.targetEBone])
            ikSettings.ikPoleBoneN = newBoneNames[0]
            ikSettings.ikPoleEBone = newEditBones[0]

            ikSettings.ikPoleEBone.parent = None
            
            #place ik pole correctly in edit mode
            ikSettings.ikPoleEBone.head = final_vec
            ikSettings.ikPoleEBone.tail = final_vec + arrow_vec
            ikSettings.ikPoleEBone.length = ikSettings.ikTargetEBone.length #AC.length *0.5
            ikSettings.ikPoleEBone.roll = 0.0

            baseEBone = ikSettings.ikChainBaseEBone

            newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("TempPoleAngleOffset.", [baseEBone])
            ikSettings.poleAngleOffsetBoneN = newBoneNames[0]
            ikSettings.poleAngleOffsetEBone = newEditBones[0]
            ikSettings.poleAngleOffsetEBone.parent = baseEBone #base bone
            ikSettings.poleAngleOffsetEBone.matrix = PoleAngleOffsetMatrix(ikSettings)
            
            newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("TempChainAxis.", [baseEBone])
            ikSettings.chainAxisBoneN = newBoneNames[0]
            ikSettings.chainAxisEBone = newEditBones[0]
            ikSettings.chainAxisEBone.parent = None
            ikSettings.chainAxisEBone.tail = ikSettings.targetEBone.head
            #get the roll of chainAxis so that it's X axis points towards the ik pole
            ikSettings.chainAxisEBone.roll = ChainAxisRoll(ikSettings)

            newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("TempPole.", [ikSettings.targetEBone])
            ikSettings.tempPoleBoneN = newBoneNames[0]
            ikSettings.tempPoleEBone = newEditBones[0]
            ikSettings.tempPoleEBone.parent = ikSettings.chainAxisEBone #chain axis bone
            ikSettings.tempPoleEBone.matrix = ikSettings.ikPoleEBone.matrix

            ikSettings.poleAngle = PoleAngleRadian(ikSettings)

    bpy.context.object.data.use_mirror_x = mirrorX
    
    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    #bonesToBake = dict()
    bonesToBakeInfo = dict()
    for ikSettings in ikSettingsList:
        #prepare the oldPBoneList and newPBoneList (duplicated bones) to assign the appropriate bone groups along with tagging them as rotf bones
        ikSettings.poseBones = ikSettings.obj.pose.bones
        ikSettings.ikTargetPBone = ikSettings.poseBones[ikSettings.ikTargetBoneN]
        oldPBoneList = [ikSettings.targetPBone]
        newPboneList = [ikSettings.ikTargetPBone]

        if ikSettings.poleVector:
            ikSettings.ikPolePBone = ikSettings.obj.pose.bones[ikSettings.ikPoleBoneN]
            oldPBoneList.extend([ikSettings.targetPBone])
            newPboneList.extend([ikSettings.ikPolePBone])

        if ikSettings.ikStretchType != "None":
            ikSettings.pboneStretchChainList = list()
            ikSettings.tempPBoneStretchChainList = list()
            ikSettings.offsetPBoneStretchChainList = list()

            for stretchBoneN, tempStretchBoneN, offsetStretchBoneN in zip(
                ikSettings.boneNStretchChainList, 
                ikSettings.tempBoneNStretchChainList, 
                ikSettings.offsetBoneNStretchChainList
                ):

                ikSettings.pboneStretchChainList.append(ikSettings.poseBones[stretchBoneN])
                ikSettings.tempPBoneStretchChainList.append(ikSettings.poseBones[tempStretchBoneN])
                ikSettings.offsetPBoneStretchChainList.append(ikSettings.poseBones[offsetStretchBoneN])

            for pbone, pboneStretch, tempPBoneStretch in zip(ikSettings.pboneChainList, ikSettings.pboneStretchChainList, ikSettings.tempPBoneStretchChainList):
                #constrain stretch bones to the tempStretch bones
                copyTransforms = pboneStretch.constraints.new('COPY_TRANSFORMS')
                copyTransforms.name += " RotF"
                copyTransforms.target = ikSettings.obj
                copyTransforms.subtarget = tempPBoneStretch.name

                bonesToBakeInfo[pboneStretch] = [pbone]
            
            oldPBoneList.extend(ikSettings.pboneChainList + ikSettings.pboneChainList)
            newPboneList.extend(ikSettings.pboneStretchChainList + ikSettings.offsetPBoneStretchChainList)

        else:
            ikSettings.offsetPBone = ikSettings.poseBones[ikSettings.offsetBoneN]
            ikSettings.refConstrainedPBone = ikSettings.poseBones[ikSettings.refConstrainedBoneN]
            ikSettings.tempConstrainedPBone = ikSettings.poseBones[ikSettings.tempConstrainedBoneN]
            ikSettings.constrainedPBone = ikSettings.poseBones[ikSettings.constrainedBoneN]

            oldPBoneList.extend([ikSettings.targetPBone.parent, ikSettings.targetPBone.parent])
            newPboneList.extend([ikSettings.offsetPBone, ikSettings.constrainedPBone])

            #constrain constrainedPBone to tempconstrainedPBone so that it follows the same motion
            copyTransforms = ikSettings.constrainedPBone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.name += " RotF"
            copyTransforms.target = ikSettings.obj
            copyTransforms.subtarget = ikSettings.tempConstrainedBoneN
        
        #change rig bones' display to square, rotation mode to euler YZX and adds copy transform constraint to copy the base armature's animation.
        ikTargetPBone = ikSettings.ikTargetPBone
        ikTargetPBone.bone.show_wire = False
        copyTransforms = ikTargetPBone.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " RotF"
        copyTransforms.target = ikSettings.obj
        copyTransforms.subtarget = ikSettings.targetBoneN

        #assign constrainedPBone for later use
        ikSettings.constrainedPBone = ikSettings.poseBones[ikSettings.constrainedBoneN]
        duplicateBone.AssignPoseBoneGroups(oldPBoneList, newPboneList)

        #prepare bake info for the ik target pose bone
        targetPBone = ikSettings.targetPBone
        ikTargetPBone = ikSettings.ikTargetPBone
        bonesToBakeInfo[ikTargetPBone] = [targetPBone]
        bonesToBakeInfo[ikSettings.constrainedPBone] = [targetPBone]
        for pbone in ikSettings.pboneChainList:
            bonesToBakeInfo[ikTargetPBone].append(pbone)

        #assign controller shape to ikTargetBoneP
        ikTarget_customShape = bpy.context.scene.rotf_ikTarget_customShape
        if ikTarget_customShape == None:
            importControllerShapes.ImportControllerShapes(["RotF_Square"])
            ikTargetPBone.custom_shape = bpy.data.objects['RotF_Square']
        else:
            ikTargetPBone.custom_shape = bpy.data.objects[ikTarget_customShape.name]

        if ikSettings.ikStretchType != "None":
            #assign controller shape to pboneStretchChainList
            stretchChain_customShape = bpy.context.scene.rotf_ikTarget_customShape
            if stretchChain_customShape == None:
                importControllerShapes.ImportControllerShapes(["RotF_Square"])
                customShape = bpy.data.objects['RotF_Square']
            else:
                customShape = bpy.data.objects[stretchChain_customShape.name]

            #ikSettings.constrainedPBone.ik_stretch = 0.001
            for pboneStretch, pbone in zip(ikSettings.pboneStretchChainList, ikSettings.pboneChainList):
                pboneStretch.custom_shape = customShape
                pboneStretch.bone.show_wire = False
                pboneStretch.ik_stretch = 0.001

                pboneStretch.bone.inherit_scale = 'NONE'

                #copyTransforms = pboneStretch.constraints.new('COPY_TRANSFORMS')
                #copyTransforms.name += " RotF"
                #copyTransforms.target = ikSettings.obj
                #copyTransforms.subtarget = pbone.name

            #make sure offsetStretch bones are fully inheriting transforms from it's parent
            for pbone in ikSettings.offsetPBoneStretchChainList + ikSettings.tempPBoneStretchChainList:
                pbone.bone.use_local_location = True
                pbone.bone.use_inherit_rotation = True
                pbone.bone.inherit_scale = 'FULL'
        else:
            #constrain the offset bone to the parent of the target bone
            copyTransforms = ikSettings.offsetPBone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.name += " RotF"
            copyTransforms.target = ikSettings.obj
            copyTransforms.subtarget = ikSettings.refConstrainedBoneN

            #to keep constrained's custom shape visual size in case snapping it's tail onto targetBone's head changed poleBone's length
            ikSettings.constrainedPBone.custom_shape_scale_xyz *= ikSettings.constrainedBoneLengthFactor

            bonesToBakeInfo[ikSettings.offsetPBone] = [ikSettings.refConstrainedPBone]

        if ikSettings.poleVector:
            #change rig bones' display to crosshair and adds copy transform constraint to copy the base armature's animation.
            chainAxisPBone = ikSettings.obj.pose.bones[ikSettings.chainAxisBoneN]
            copyLocation = chainAxisPBone.constraints.new('COPY_LOCATION')
            copyLocation.target = ikSettings.obj
            copyLocation.subtarget = ikSettings.boneNChainList[-1]

            stretchTo = chainAxisPBone.constraints.new('STRETCH_TO')
            stretchTo.target = ikSettings.obj
            stretchTo.subtarget = ikSettings.targetBoneN
            stretchTo.rest_length = chainAxisPBone.bone.length

            lockedTrack = chainAxisPBone.constraints.new('LOCKED_TRACK')
            lockedTrack.target = ikSettings.obj
            lockedTrack.subtarget = ikSettings.poleAngleOffsetBoneN
            lockedTrack.head_tail = 1
            lockedTrack.track_axis = 'TRACK_X'
            lockedTrack.lock_axis = 'LOCK_Y'


            ikPolePBone = ikSettings.ikPolePBone
            ikPolePBone.bone.show_wire = False
            copyTransforms = ikPolePBone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.name += " RotF"
            copyTransforms.target = ikSettings.obj
            copyTransforms.subtarget = ikSettings.tempPoleBoneN

            poleVector_customShape = bpy.context.scene.rotf_poleVector_customShape
            if poleVector_customShape == None:
                importControllerShapes.ImportControllerShapes(["RotF_Locator"])
                ikPolePBone.custom_shape = bpy.data.objects['RotF_Locator']
            else:
                ikPolePBone.custom_shape = bpy.data.objects[poleVector_customShape.name]
            
            ikPolePBone.custom_shape_scale_xyz *= 0.5

            bonesToBakeInfo[ikPolePBone] = [targetPBone]
            for pbone in ikSettings.pboneChainList:
                bonesToBakeInfo[ikPolePBone].append(pbone)

    return bonesToBakeInfo

def SetupIKBehaviour(ikSettingsList):
    for ikSettings in ikSettingsList:
        removeConstraints.RemoveAllRotFConstraints([ikSettings.constrainedPBone])
        if ikSettings.poleVector:
            removeConstraints.RemoveAllRotFConstraints([ikSettings.ikTargetPBone, ikSettings.ikPolePBone])
        else:
            removeConstraints.RemoveAllRotFConstraints([ikSettings.ikTargetPBone])
        if ikSettings.ikStretchType != "None":
            removeConstraints.RemoveAllRotFConstraints(ikSettings.pboneStretchChainList)
        else:
            removeConstraints.RemoveAllRotFConstraints([ikSettings.offsetPBone])

        ikConstraint = ikSettings.constrainedPBone.constraints.new('IK')
        ikConstraint.name += " RotF"
        ikConstraint.target = ikSettings.obj
        ikConstraint.subtarget = ikSettings.ikTargetBoneN
        if ikSettings.poleVector:
            ikConstraint.pole_target = ikSettings.obj
            ikConstraint.pole_subtarget = ikSettings.ikPoleBoneN
            #ik.pole_angle = -math.pi/2 #-90°
            ikConstraint.pole_angle = ikSettings.poleAngle
        ikConstraint.chain_count = ikSettings.chainLength #2

        #selectedTargetBone follow ikTargetBone rotation
        copyTransforms = ikSettings.targetPBone.constraints.new('COPY_ROTATION')
        copyTransforms.name += " RotF"
        copyTransforms.target = ikSettings.obj
        copyTransforms.subtarget = ikSettings.ikTargetBoneN

        #selectedTargetBone follow ikTargetBone scale
        copyTransforms = ikSettings.targetPBone.constraints.new('COPY_SCALE')
        copyTransforms.name += " RotF"
        copyTransforms.target = ikSettings.obj
        copyTransforms.subtarget = ikSettings.ikTargetBoneN
        
        if ikSettings.ikStretchType != "None":
            for pbone, boneNStretch, offsetboneNStretch in zip(ikSettings.pboneChainList, ikSettings.boneNStretchChainList, ikSettings.offsetBoneNStretchChainList):
                #boneP copy rotation of offsetStretchBone
                copyRotation = pbone.constraints.new('COPY_ROTATION')
                copyRotation.name += " RotF"
                copyRotation.target = ikSettings.obj
                copyRotation.subtarget = offsetboneNStretch

                if ikSettings.ikStretchType == "Scale":
                    #bone copy Y scale of offsetStretchBone
                    copyScale = pbone.constraints.new('COPY_SCALE')
                    copyScale.name += " RotF"
                    copyScale.target = ikSettings.obj
                    copyScale.subtarget = offsetboneNStretch

                    #find which axis should be used for scaling 
                    pboneStretchY = ikSettings.poseBones[boneNStretch].y_axis
                    
                    dotX = pbone.x_axis.dot(pboneStretchY)
                    dotY = pbone.y_axis.dot(pboneStretchY)
                    dotZ = pbone.z_axis.dot(pboneStretchY)

                    absoluteDotProductList = [abs(dotX), abs(dotY), abs(dotZ)]
                    mostParrallelAxis = max(absoluteDotProductList)

                    #turn off copy scale of the axis that are not parrallel the the StretchBone's Y axis
                    for i, absoluteDotProduct in enumerate(absoluteDotProductList):
                        if absoluteDotProduct != mostParrallelAxis:
                            if i == 0:
                                copyScale.use_x = False
                            if i == 1:
                                copyScale.use_y = False
                            if i == 2:
                                copyScale.use_z = False

                #copy location of poleStretchP
                copyLocation = pbone.constraints.new('COPY_LOCATION')
                copyLocation.name += " RotF"
                copyLocation.target = ikSettings.obj
                copyLocation.subtarget = offsetboneNStretch

            copyLocation = ikSettings.targetPBone.constraints.new('COPY_LOCATION')
            copyLocation.name += " RotF"
            copyLocation.target = ikSettings.obj
            copyLocation.subtarget = ikSettings.ikTargetBoneN
            
        else:
            #constrain the first bone of the chain to the offset bone
            copyTransforms = ikSettings.refConstrainedPBone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.name += " RotF"
            copyTransforms.target = ikSettings.obj
            copyTransforms.subtarget = ikSettings.offsetBoneN

    #remove tempPoleBone
    bpy.ops.object.mode_set(mode='EDIT')
    for ikSettings in ikSettingsList:
        if ikSettings.tempPoleBoneN:
            tempPoleEBone = ikSettings.editBones.get(ikSettings.tempPoleBoneN) #switching from pose mode to edit mode lost the pointer to ikSettings.tempPoleEBone that's why ikSettings.editBones[ikSettings.tempPoleBoneN] is used instead
            poleAngleOffsetEBone = ikSettings.editBones.get(ikSettings.poleAngleOffsetBoneN)
            chainAxisEBone = ikSettings.editBones.get(ikSettings.chainAxisBoneN)
            if tempPoleEBone: 
                ikSettings.editBones.remove(tempPoleEBone)
            if poleAngleOffsetEBone:
                ikSettings.editBones.remove(poleAngleOffsetEBone)
            if chainAxisEBone:
                ikSettings.editBones.remove(chainAxisEBone)
        if ikSettings.tempConstrainedBoneN:
            tempConstrainedEBone = ikSettings.editBones.get(ikSettings.tempConstrainedBoneN)
            if tempConstrainedEBone:
                ikSettings.editBones.remove(tempConstrainedEBone)
        if ikSettings.tempBoneNStretchChainList:
            for tempBoneNStretch in ikSettings.tempBoneNStretchChainList:
                tempEBoneStretch = ikSettings.editBones.get(tempBoneNStretch)
                if tempEBoneStretch:
                    ikSettings.editBones.remove(tempEBoneStretch)

    #return to pose mode
    bpy.ops.object.mode_set(mode='POSE')
    
    for ikSettings in ikSettingsList:
        if ikSettings.isStraight and ikSettings.mainAxisIsY: #bend the chain if it is straight
            bendAmount = 0.001
            #defaultAxisIndex = bpy.context.scene.rotf_bend_ik_default_pole_axis
            
            pboneToBendList = list()
            if ikSettings.ikStretchType == "None":
                pboneToBendList = ikSettings.pboneChainList[:-1] #except the base pose bone
            else:
                pboneToBendList = ikSettings.pboneStretchChainList[:-1] #except the base stretch pose bone
            
            #bend the constrainedPBone
            constrainedPBone = ikSettings.constrainedPBone
            constrainedAxisToBend = ikSettings.constrainedBoneAxisToBend
            bendSign = ikSettings.constrainedBoneSign
            if "X" in constrainedAxisToBend:
                if constrainedPBone.y_axis.dot(pboneToBendList[-1].y_axis) < 0:
                    if constrainedPBone.x_axis.dot(pboneToBendList[-1].x_axis) < 0:
                        bendSign *= -1
                constrainedPBone.rotation_quaternion.x = bendAmount * bendSign * -1
                constrainedPBone.rotation_euler.x = bendAmount * bendSign * -1
            
            #if "Y" in constrainedAxisToBend:
            #    print("Y")
            #    constrainedPBone.rotation_quaternion.y = bendAmount
            #    constrainedPBone.rotation_euler.y = bendAmount

            if "Z" in constrainedAxisToBend:
                if constrainedPBone.y_axis.dot(pboneToBendList[-1].y_axis) < 0:
                    bendSign*= -1
                    if constrainedPBone.z_axis.dot(pboneToBendList[-1].z_axis) < 0:
                        bendSign*= -1
                constrainedPBone.rotation_quaternion.z = bendAmount * bendSign
                constrainedPBone.rotation_euler.z = bendAmount * bendSign
            
            #bend the rest of the chain
            axisToBend = ikSettings.axisToBend
            bendSign = ikSettings.bendSign
            for pboneToBend in pboneToBendList:
                if axisToBend == "X":
                    pboneToBend.rotation_quaternion.x = bendAmount * bendSign * -1
                    pboneToBend.rotation_euler.x = bendAmount * bendSign * -1

                #if axisToBend == "Y":
                #    pboneToBend.rotation_quaternion.y = bendAmount
                #    pboneToBend.rotation_euler.y = bendAmount

                if axisToBend == "Z":
                    pboneToBend.rotation_quaternion.z = bendAmount * bendSign
                    pboneToBend.rotation_euler.z = bendAmount * bendSign

        #move non relevant bones to unused layer
        pboneToHideList = [ikSettings.targetPBone]

        secondaryFKPBoneList = list()
        print(ikSettings.pboneChainList[0])
        #if ikSettings.chainLength == 2: #if chain length is two hide the constrained bone
        #    secondaryFKPBoneList.append(ikSettings.constrainedPBone)

        if ikSettings.ikStretchType != "None":
            secondaryFKPBoneList.extend(ikSettings.pboneStretchChainList[:-1])
            pboneToHideList.extend(ikSettings.pboneChainList)
            pboneToHideList.extend(ikSettings.offsetPBoneStretchChainList)
        else:
            secondaryFKPBoneList.extend(ikSettings.pboneChainList[1:-1])
            secondaryFKPBoneList.append(ikSettings.constrainedPBone)
            pboneToHideList.extend(ikSettings.pboneChainList[:-1])
            pboneToHideList.append(ikSettings.offsetPBone)
            
        if ikSettings.poleVector:
            if ikSettings.ikStretchType != "None":
                pboneToHideList.append(ikSettings.pboneStretchChainList[-1])
            else:
                pboneToHideList.append(ikSettings.pboneChainList[-1])
        
        pboneToHideList.extend(secondaryFKPBoneList)

        appVersion = bpy.app.version
        if appVersion[0] == 4:

            for pbone in pboneToHideList:
                pbone.bone.inherit_scale = 'NONE'
                #if using IK on orient bone it's driven bone needs to have it's inherit scale truned off as well for apprpriate behaviour
                pointerOrient = pbone.bone.rotf_pointer_list.get('Orient')
                if pointerOrient:
                    ikSettings.poseBones[pointerOrient['bone_name']].bone.inherit_scale = 'NONE'

                boneCollections.AddBoneToCollections(pbone.bone, [boneCollections.RotFHiddenFKColName, boneCollections.RotFUnusedColName])

                #Keep stretch chain bones that should stay in the unnused
                boneCollections.UnassignBoneFromCollections(pbone.bone, [boneCollections.RotFAnimationColName])

                #hide bones
                pbone.bone.hide = True

            for pbone in secondaryFKPBoneList:
                boneCollections.AddBoneToCollections(pbone.bone, [boneCollections.RotFSecondaryFKColName])
                                                                  
        elif appVersion[0] == 3:
            unusedLayer = ikSettings.obj.unusedRigBonesLayer
            for pbone in pboneToHideList:
                pbone.bone.inherit_scale = 'NONE'
                #if using IK on orient bone it's driven bone needs to have it's inherit scale truned off as well for opprpriate behaviour
                pointerOrient = pbone.bone.rotf_pointer_list.get('Orient')
                if pointerOrient:
                    ikSettings.poseBones[pointerOrient['bone_name']].bone.inherit_scale = 'NONE'
            
                bone = pbone.bone
                bone.layers[unusedLayer]=True
                for layer in range(32):
                    if layer != unusedLayer:
                        bone.layers[layer]=False
        
        if ikSettings.ikStretchType != "None":
            #make sure offsetStretch bones are fully inheriting transforms from it's parent
            for offsetStretchPBone in ikSettings.offsetPBoneStretchChainList:
                offsetStretchPBone.bone.use_local_location = True
                offsetStretchPBone.bone.use_inherit_rotation = True
                offsetStretchPBone.bone.inherit_scale = 'FULL'

        #add IK tag and the target bone's name to the ik target bone's rotf_pointer_list for when to remove the ik constraint
        newPointer = ikSettings.ikTargetPBone.bone.rotf_pointer_list.add()
        newPointer.name = "IK"
        newPointer.armature_object = ikSettings.obj
        newPointer.bone_name = ikSettings.targetBoneN

        if ikSettings.poleVector:
            newPointer = ikSettings.ikPolePBone.bone.rotf_pointer_list.add()
            newPointer.name = "IK"
            newPointer.armature_object = ikSettings.obj
            newPointer.bone_name = ikSettings.targetBoneN

        rigState.AddConstraint(
                ikSettings.obj,
                "IK Limb|" + ikSettings.targetBoneN,
                "IK Limb|" + ikSettings.targetBoneN + "|length:" + str(ikSettings.chainLength) + "|stretch:" + str(ikSettings.ikStretchType) + "|pole:" + str(ikSettings.poleVector),
                "IK Limb",
                [ikSettings.targetBoneN],
                [ikSettings.poleVector],
                [ikSettings.ikStretchType, ikSettings.defaultAxisIndex],
                [ikSettings.chainLength],
                [0.0] #is not used
                )

def AveragePointOfChain(ikSettings):
    eboneList = ikSettings.eboneChainList[:-1] #make a new list ignoring the base bone
    pointList = list()
    for ebone in eboneList:
        pointList.append(ebone.head)

    vectorPoint = mathutils.Vector((0.0, 0.0, 0.0))

    for vector in pointList:
        vectorPoint += vector
    vectorPoint /= len(pointList)

    return vectorPoint

def PolePosition(ikSettings):
    ########################################
    # Create and place IK pole target bone #
    #          by Marco Giordano           #
    ########################################

    # Get points to define the plane on which to put the pole target
    A = ikSettings.ikChainBaseEBone.head #base edit bone of the ik chain
    B = AveragePointOfChain(ikSettings)
    C = ikSettings.ikTargetEBone.head

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

    return A, C, AB, AC, proj, start_end_norm

def IsLimbStraight(ikSettings, AB, AC):
    chainEbone = ikSettings.eboneChainList[0]
    straightnessThreshold = 0.9999 # Maximum 1
    normalized_dot_product = AB.normalized() @ AC.normalized()
    if abs(normalized_dot_product) < straightnessThreshold :
        ikSettings.isStraight = False
        return False, chainEbone.x_axis, 1

    defaultAxisIndex = ikSettings.defaultAxisIndex
    # default axis defined in the properties file.
    axisVector =  chainEbone.x_axis
    if "X" in defaultAxisIndex:
        axisVector = chainEbone.x_axis
    #if "Y" in defaultAxisIndex:
    #    axisVector = chainEbone.y_axis
    if "Z" in defaultAxisIndex:
        axisVector = chainEbone.z_axis
    
    vectorSign = 1
    if "-" in defaultAxisIndex:
        vectorSign = -1

    ikSettings.isStraight = True
    return True, axisVector, vectorSign

def FindAxisToBend(ikSettings, axisVector, AC):
    #first bone of the chain
    ebone = ikSettings.eboneChainList[0]
    boneAxisList = [ebone.x_axis, ebone.y_axis, ebone.z_axis]
    axisNameList = ["X", "Y", "Z"]
    axisToBendList = ["X", "Y", "Z"]

    #axisToBend is perpendicular to both axisVector and the axis most parallel to AC
    dotX = ebone.x_axis.dot(AC)
    dotY = ebone.y_axis.dot(AC)
    dotZ = ebone.z_axis.dot(AC)
    if abs(dotX) > abs(dotY) or abs(dotZ) > abs(dotY):
        axisToBend = str()
        ikSettings.mainAxisIsY = False
        return axisToBend

    #find if Y axis is point in the same direction as vector AC, if not set bendSign to -1
    ikSettings.bendSign = 1 if dotY > 0 else -1

    defaultAxisIndex = ikSettings.defaultAxisIndex
    for i, axisName in enumerate(axisNameList):
        if axisName in defaultAxisIndex:
            poleAxisIndex = i

    if "X" in ikSettings.defaultAxisIndex:
        axisToBend = "Z"
        axisToBendIndex = 2
    else:
        axisToBend = "X"
        axisToBendIndex = 0

    constrainedEBone = ikSettings.constrainedEBone
    constrainedBoneAxisList = [constrainedEBone.x_axis, constrainedEBone.y_axis, constrainedEBone.z_axis]

    previousDotProduct = 0
    boneAxisToBend = boneAxisList[axisToBendIndex]

    for i, constrainedBoneAxis in enumerate(constrainedBoneAxisList):
        dotProduct = constrainedBoneAxis.dot(boneAxisToBend)
        absoluteDotProduct = abs(dotProduct)
        if absoluteDotProduct > previousDotProduct:
            previousDotProduct = absoluteDotProduct
            ikSettings.constrainedBoneAxisToBend = axisNameList[i]
            ikSettings.constrainedBoneSign = dotProduct/absoluteDotProduct
    
    if "-" in defaultAxisIndex:
        ikSettings.bendSign *= -1
        ikSettings.constrainedBoneSign *= -1

    return axisToBend

def Signed_angle (vector_u, vector_v, normal):
    ##############
    # Pole Angle #
    # by Jerryno #
    ##############

    # Normal specifies orientation
    angle = vector_u.angle(vector_v)

    crossProduct = vector_u.cross(vector_v)
    if crossProduct.magnitude > 0:
        if crossProduct.angle(normal) < 1:
            angle = -angle
    return angle

def PoleAngleOffsetMatrix(ikSettings):
    baseEBone = ikSettings.ikChainBaseEBone
    poleAngleOffsetEBone = ikSettings.poleAngleOffsetEBone

    AC = ikSettings.ikTargetEBone.head - baseEBone.head
    AP = ikSettings.ikPoleEBone.head - baseEBone.head
    pole_normal = AC.cross(AP)
    projected_pole_axis = pole_normal.cross(baseEBone.tail - baseEBone.head)

    rotationAxis = poleAngleOffsetEBone.y_axis.cross(projected_pole_axis)

    rotation = math.radians(90)
    axisVector = rotationAxis @ baseEBone.matrix.to_3x3()
    rotation_matrix = mathutils.Matrix.Rotation(rotation, 4, axisVector)
    poleAngleOffsetEBone.matrix = baseEBone.matrix @ rotation_matrix

    #turn tempPoleBone's by 180 degrees if it's tail/Y axis is pointing away from the ik pole vector
    if poleAngleOffsetEBone.y_axis.dot(ikSettings.ikPoleEBone.y_axis) < 0:
        rotation = math.radians(180)
        axisVector = poleAngleOffsetEBone.x_axis @ poleAngleOffsetEBone.matrix.to_3x3()
        rotation_matrix = mathutils.Matrix.Rotation(rotation, 4, axisVector)
        poleAngleOffsetEBone.matrix = poleAngleOffsetEBone.matrix @ rotation_matrix

        ikSettings.poleAngleFlipped = True

    return poleAngleOffsetEBone.matrix

def ChainAxisRoll(ikSettings):
    chainAxisEBone = ikSettings.chainAxisEBone
    ikPoleEBone = ikSettings.ikPoleEBone
    # Calculate the projection of the vector onto the plane perpendicular to the matrix's Y-axis
    desiredAxis = ikPoleEBone.head - chainAxisEBone.head
    projection = desiredAxis - desiredAxis.dot(chainAxisEBone.y_axis) * chainAxisEBone.y_axis
    angle = projection.angle(chainAxisEBone.x_axis)
    chainAxisEBone.align_roll(projection)
    return chainAxisEBone.roll - math.radians(90)

def PoleAngleRadian(ikSettings):
    ##############
    # Pole Angle #
    # by Jerryno #
    ##############
    baseEBone = ikSettings.ikChainBaseEBone
    AC = ikSettings.ikTargetEBone.head - baseEBone.head
    AP = ikSettings.ikPoleEBone.head - baseEBone.head
    pole_normal = AC.cross(AP)
    projected_pole_axis = pole_normal.cross(baseEBone.tail - baseEBone.head)

    #print("FIND POLE ANGLE")

    #if bone chain forms a straight line
    """if baseEBone.x_axis == projected_pole_axis.normalized() or projected_pole_axis.magnitude < 0.0001:
        defaultAxisIndex = ikSettings.defaultAxisIndex
        # default axis defined in the properties file.
        poleAngle = 0
        if "X" in defaultAxisIndex:
            poleAngle = 0
        if "Y" in defaultAxisIndex:
            poleAngle = 90
        if "Z" in defaultAxisIndex:
            poleAngle = 90
        
        if "-" in defaultAxisIndex:
            poleAngle -= 180
        return poleAngle"""
    
    poleAngle = Signed_angle(baseEBone.x_axis, projected_pole_axis, baseEBone.tail - baseEBone.head)
    #print(poleAngle)
    #if poleAngleOffset Bone needed to be flipped, flip the pole angle as well
    if ikSettings.poleAngleFlipped:
        #print("flipped")
        if poleAngle > 0:
            poleAngle -= math.radians(180)
            #print(poleAngle)
        else:
            poleAngle += math.radians(180)
            #print(poleAngle)
    return poleAngle

def IKLimb():
    scene = bpy.context.scene

    ikStretchType = scene.rotf_bend_ik_stretch_type  
    poleVector = scene.rotf_bend_ik_pole_vector
    defaultAxisIndex = scene.rotf_bend_ik_default_pole_axis
    chainLength = scene.rotf_bend_ik_chain_length
    
    pboneList = bpy.context.selected_pose_bones
    #add bone name to selectedBonesN to have it's generated IK controller selected at the end of the script
    ikSettingsList = list()
    for pbone in pboneList:
        if len(pbone.parent_recursive) < chainLength:
            return [{'WARNING'}, "not enough parents"]

        ikSettings = IKSettings()
        ikSettings.targetPBone = pbone
        ikSettings.ikStretchType = ikStretchType
        ikSettings.poleVector = poleVector
        ikSettings.defaultAxisIndex = defaultAxisIndex
        ikSettings.chainLength = chainLength

        ikSettingsList.append(ikSettings)
        
    ikPBoneTargetList = IKLimbConstraint.CreateIKLimbConstraint(ikSettingsList)
        
    #end script with new ik handles selected
    for ikTargetPBone in ikPBoneTargetList:
        ikTargetPBone.bone.select = True

    for ikSettings in ikSettingsList:
        if ikSettings.mainAxisIsY == False:
            return [{'WARNING'}, "No Pole added, Y axis is not main axis of chain"]



   
