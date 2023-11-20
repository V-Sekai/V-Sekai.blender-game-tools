#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
import math
import mathutils
from . import duplicateBone
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
            ikStretch = string_list[0]
            defaultAxisIndex = string_list[1]

            int_list = constraintInfo['int_list']
            chainLength = int_list[0]

            ikSettings = IKSettings()
            ikSettings.targetPBone = targetPBone
            ikSettings.ikStretch = ikStretch
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
        self.ikStretch = None #string
        self.poleVector = None #boolean
        self.defaultAxisIndex = None #string

        self.isStraight = False
        self.poleAngle = float()

        self.obj = None
        self.bones = None
        self.poseBones = None
        self.editBones = None

        self.targetBoneN = None

        self.ikTargetBoneN = None
        self.ikTargetPBone = None
        self.ikTargetEBone = None

        self.ikPoleBoneN = None
        self.ikPolePBone = None
        self.ikPoleEBone = None

        self.tempPoleBoneN = None
        self.tempPolePBone = None
        self.tempPoleEBone = None

        self.tempPointerBoneN = None
        self.tempPointerPBone = None
        self.tempPointerEBone = None

        self.boneNChainList = None
        self.pboneChainList = None
        self.eboneChainList = None

        self.boneNStretchChainList = None
        self.pboneStretchChainList = None
        self.eboneStretchChainList = None

        self.constrainedBoneN = None
        self.constrainedPBone = None
        self.constrainedEBone = None

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
    bpy.context.object.data.use_mirror_x = False

    #duplicate the needed bones
    for ikSettings in ikSettingsList:
        ikSettings.editBones = ikSettings.obj.data.edit_bones
        ikSettings.targetEBone = ikSettings.editBones[ikSettings.targetBoneN]
        newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBone("IK.", [ikSettings.targetEBone])
        ikSettings.ikTargetBoneN = newBoneNames[0]
        ikSettings.ikTargetEBone = newEditBones[0]

        #remove parent of IK target
        ikSettings.ikTargetEBone.parent = None

        ikSettings.eboneChainList = list()
        for boneName in ikSettings.boneNChainList:
            ikSettings.eboneChainList.append(ikSettings.editBones[boneName])
        #if stretchIK is not None, duplicate the bones that will be part of the stretch chain and disconnect the target bone and the eboneChainList
        if ikSettings.ikStretch != "None":
            newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBone("IKStretch.", ikSettings.eboneChainList)
            ikSettings.boneNStretchChainList = newBoneNames #assign the duplicated bone chain to the ikSettings' boneStretchChainList
            ikSettings.eboneStretchChainList = newEditBones

            #parent bones from eboneStretchChainList so that they form a single hierarchycal chain
            for i in range(len(ikSettings.eboneStretchChainList)-1):
                ikSettings.eboneStretchChainList[i].parent = ikSettings.eboneStretchChainList[i+1]

            ikSettings.constrainedBoneN = ikSettings.boneNStretchChainList[0]
            ikSettings.constrainedEBone = ikSettings.eboneStretchChainList[0]

            #disconnect the target bone and chain bones so that they can translate while stretching
            ikSettings.targetEBone.use_connect = False
            for ebone in ikSettings.eboneChainList:
                ebone.use_connect = False

        else:
            ikSettings.constrainedBoneN = ikSettings.boneNChainList[0]
            ikSettings.constrainedEBone = ikSettings.editBones[ikSettings.constrainedBoneN]

        if ikSettings.poleVector:
            newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBone("Pole.", [ikSettings.targetEBone])
            ikSettings.ikPoleBoneN = newBoneNames[0]
            ikSettings.ikPoleEBone = newEditBones[0]

            ikSettings.ikPoleEBone.parent = None
            
            #place temp ik pole correctly in edit mode
            ikSettings.isStraight = PolePosition(ikSettings)
            
            newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBone("TempPole.", [ikSettings.targetEBone])
            ikSettings.tempPoleBoneN = newBoneNames[0]
            ikSettings.tempPoleEBone = newEditBones[0]
            ikSettings.tempPoleEBone.parent = ikSettings.eboneChainList[-1] #base bone
            ikSettings.tempPoleEBone.matrix = ikSettings.ikPoleEBone.matrix

            ikSettings.poleAngle = PoleAngleRadian(ikSettings)

        #snap tail of constrainedEBone to ikTargetEBone head's position
        constrainedBoneOldLength = ikSettings.constrainedEBone.length
        ikSettings.constrainedEBone.tail = ikSettings.ikTargetEBone.head
        constrainedBoneNewLength = ikSettings.constrainedEBone.length
        ikSettings.constrainedBoneLengthFactor = constrainedBoneOldLength/constrainedBoneNewLength

    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    bonesToBake = dict()
    bonesToBakeInfo = dict()
    for ikSettings in ikSettingsList:
        #prepare the oldPBoneList and newPBoneList (duplicated bones) to assign the appropriate bone groups along with tagging them as rotf bones
        ikSettings.poseBones = ikSettings.obj.pose.bones
        ikSettings.ikTargetPBone = ikSettings.obj.pose.bones[ikSettings.ikTargetBoneN]
        oldPBoneList = [ikSettings.targetPBone]
        newPboneList = [ikSettings.ikTargetPBone]

        if ikSettings.poleVector:
            ikSettings.ikPolePBone = ikSettings.obj.pose.bones[ikSettings.ikPoleBoneN]
            oldPBoneList.extend([ikSettings.targetPBone])
            newPboneList.extend([ikSettings.ikPolePBone])

        if ikSettings.ikStretch != "None":
            ikSettings.pboneStretchChainList = list()
            for boneN in ikSettings.boneNStretchChainList:
                ikSettings.pboneStretchChainList.append(ikSettings.poseBones[boneN])

            for pbone, pboneStretch in zip(ikSettings.pboneChainList, ikSettings.pboneStretchChainList):
                bonesToBakeInfo[pboneStretch] = [
                    [pbone, rotfBake.Channel.locationXYZ, rotfBake.Channel.locationXYZ],
                    [pbone, rotfBake.Channel.rotationQE, rotfBake.Channel.rotationQE],
                    [pbone, rotfBake.Channel.scaleXYZ, rotfBake.Channel.scaleXYZ],
                    ]
            
            oldPBoneList.extend(ikSettings.pboneChainList)
            newPboneList.extend(ikSettings.pboneStretchChainList)

        duplicateBone.AssignPoseBoneGroups(oldPBoneList, newPboneList)

        #assign constrainedPBone for later use
        ikSettings.constrainedPBone = ikSettings.poseBones[ikSettings.constrainedBoneN]
    
        #change rig bones' display to square, rotation mode to euler YZX and adds copy transform constraint to copy the base armature's animation.
        ikTargetBoneP = ikSettings.ikTargetPBone
        ikTargetBoneP.bone.show_wire = True
        copyTransforms = ikTargetBoneP.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " RotF"
        copyTransforms.target = ikSettings.obj
        copyTransforms.subtarget = ikSettings.targetPBone.name

        #prepare bake info for the ik target pose bone
        bonesToBakeInfo[ikTargetBoneP] = [
            [targetPBone, rotfBake.Channel.locationRotationQE, rotfBake.Channel.locationRotationQE],
            [targetPBone, rotfBake.Channel.scaleXYZ, rotfBake.Channel.scaleXYZ],
            ]
        for pbone in ikSettings.pboneChainList:
            bonesToBakeInfo[ikTargetBoneP].append([pbone, rotfBake.Channel.allChannels, rotfBake.Channel.locationXYZ + rotfBake.Channel.scaleXYZ])

        #assign controller shape to ikTargetBoneP
        ikTarget_customShape = bpy.context.scene.rotf_ikTarget_customShape
        if ikTarget_customShape == None:
            importControllerShapes.ImportControllerShapes(["RotF_Square"])
            ikTargetBoneP.custom_shape = bpy.data.objects['RotF_Square']
        else:
            ikTargetBoneP.custom_shape = bpy.data.objects[ikTarget_customShape.name]

        if ikSettings.ikStretch != "None":
            #assign controller shape to pboneStretchChainList
            stretchChain_customShape = bpy.context.scene.rotf_ikTarget_customShape
            if stretchChain_customShape == None:
                importControllerShapes.ImportControllerShapes(["RotF_Square"])
                customShape = bpy.data.objects['RotF_Square']
            else:
                customShape = bpy.data.objects[stretchChain_customShape.name]

            for pboneStretch, pbone in zip(ikSettings.pboneStretchChainList, ikSettings.pboneChainList):
                pboneStretch.custom_shape = customShape
                pboneStretch.bone.show_wire = True
                pboneStretch.ik_stretch = 0.001

                copyTransforms = pboneStretch.constraints.new('COPY_TRANSFORMS')
                copyTransforms.name += " RotF"
                copyTransforms.target = ikSettings.obj
                copyTransforms.subtarget = pbone.name
            
        #to keep poleBone's custom shape visual size in case snapping it's tail onto targetBone's head changed poleBone's length
        ikSettings.constrainedPBone.custom_shape_scale_xyz *= ikSettings.constrainedBoneLengthFactor

        if ikSettings.poleVector:
            #change rig bones' display to crosshair and adds copy transform constraint to copy the base armature's animation.
            ikPoleBoneP = ikSettings.ikPolePBone
            ikPoleBoneP.bone.show_wire = True
            copyTransforms = ikPoleBoneP.constraints.new('COPY_TRANSFORMS')
            copyTransforms.name += " RotF"
            copyTransforms.target = ikSettings.obj
            copyTransforms.subtarget = ikSettings.tempPoleBoneN

            poleVector_customShape = bpy.context.scene.rotf_poleVector_customShape
            if poleVector_customShape == None:
                importControllerShapes.ImportControllerShapes(["RotF_Locator"])
                ikPoleBoneP.custom_shape = bpy.data.objects['RotF_Locator']
            else:
                ikPoleBoneP.custom_shape = bpy.data.objects[poleVector_customShape.name]
            
            ikPoleBoneP.custom_shape_scale_xyz *= 0.5

            bonesToBakeInfo[ikPoleBoneP] = [
                    [targetPBone, rotfBake.Channel.locationXYZ, rotfBake.Channel.locationXYZ]]
            for pbone in ikSettings.pboneChainList:
                bonesToBakeInfo[ikPoleBoneP].append([pbone, rotfBake.Channel.allChannels, rotfBake.Channel.locationXYZ])
    
    return bonesToBakeInfo

def SetupIKBehaviour(ikSettingsList):
    for ikSettings in ikSettingsList:
        if ikSettings.poleVector:
            removeConstraints.RemoveAllRotFConstraints([ikSettings.ikTargetPBone, ikSettings.ikPolePBone])
        else:
            removeConstraints.RemoveAllRotFConstraints([ikSettings.ikTargetPBone])
        if ikSettings.ikStretch != "None":
            removeConstraints.RemoveAllRotFConstraints(ikSettings.pboneStretchChainList)

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
        
        if ikSettings.ikStretch != "None":
            for pbone, boneNStretch in zip(ikSettings.pboneChainList, ikSettings.boneNStretchChainList):
                #baseBoneP copy rotation of baseStretchP
                copyRotation = pbone.constraints.new('COPY_ROTATION')
                copyRotation.name += " RotF"
                copyRotation.target = ikSettings.obj
                copyRotation.subtarget = boneNStretch

                if ikSettings.ikStretch == "Scale":
                    #baseBoneP copy Y scale of baseStretchP
                    copyScale = pbone.constraints.new('COPY_SCALE')
                    copyScale.name += " RotF"
                    copyScale.target = ikSettings.obj
                    copyScale.subtarget = boneNStretch
                    copyScale.use_x = False
                    copyScale.use_z = False

                #poleBoneP copy location of poleStretchP
                copyLocation = pbone.constraints.new('COPY_LOCATION')
                copyLocation.name += " RotF"
                copyLocation.target = ikSettings.obj
                copyLocation.subtarget = boneNStretch

            if ikSettings.ikStretch != "None":
                copyLocation = ikSettings.targetPBone.constraints.new('COPY_LOCATION')
                copyLocation.name += " RotF"
                copyLocation.target = ikSettings.obj
                copyLocation.subtarget = ikSettings.ikTargetBoneN

    #remove tempPoleBone
    bpy.ops.object.mode_set(mode='EDIT')
    for ikSettings in ikSettingsList:
        if ikSettings.tempPoleBoneN:
            tempPoleEBone = ikSettings.editBones.get(ikSettings.tempPoleBoneN) #switching from pose mode to edit mode lost the pointer to ikSettings.tempPoleEBone that's why ikSettings.editBones[ikSettings.tempPoleBoneN] is used instead
            if tempPoleEBone: 
                ikSettings.editBones.remove(tempPoleEBone)

    #return to pose mode
    bpy.ops.object.mode_set(mode='POSE')

    for ikSettings in ikSettingsList:
        if ikSettings.isStraight: #bend the chain if it is straight
            bendAmount = 0.001
            defaultAxisIndex = bpy.context.scene.rotf_ik_default_pole_axis
            pboneToBendList = list()
            if ikSettings.ikStretch == "None":
                pboneToBendList = ikSettings.pboneChainList[:-1] #except the base pose bone
            else:
                pboneToBendList = ikSettings.pboneStretchChainList[:-1] #except the base stretch pose bone
            for pboneToBend in pboneToBendList:
                if defaultAxisIndex == "+X":
                    pboneToBend.rotation_quaternion.z = bendAmount
                    pboneToBend.rotation_euler.z = bendAmount
                if defaultAxisIndex ==  "-X":
                    pboneToBend.rotation_quaternion.z = -bendAmount
                    pboneToBend.rotation_euler.z = -bendAmount
                if defaultAxisIndex ==  "+Z":
                    pboneToBend.rotation_quaternion.x = -bendAmount
                    pboneToBend.rotation_euler.x = -bendAmount
                if defaultAxisIndex ==  "-Z":
                    pboneToBend.rotation_quaternion.x = bendAmount
                    pboneToBend.rotation_euler.x = bendAmount
        
        #move non relevant bones to unused layer
        unusedLayer = ikSettings.obj.unusedRigBonesLayer
        pboneToMoveList = [ikSettings.targetPBone]
        if ikSettings.chainLength == 2: #if chain length is two hide the constrained bone
            pboneToMoveList.append(ikSettings.constrainedPBone)
        
        if ikSettings.poleVector:
            if ikSettings.ikStretch != "None":
                pboneToMoveList.extend(ikSettings.pboneChainList)
            
            if ikSettings.poleVector:
                if ikSettings.ikStretch != "None":
                    pboneToMoveList.append(ikSettings.pboneStretchChainList[-1])
                else:
                    pboneToMoveList.append(ikSettings.pboneChainList[-1])
                        
        for pbone in pboneToMoveList:
            pbone.bone.use_inherit_scale = False

        for pbone in pboneToMoveList:
            bone = pbone.bone
            bone.layers[unusedLayer]=True
            for layer in range(32):
                if layer != unusedLayer:
                    bone.layers[layer]=False

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
                "IK Limb|" + ikSettings.targetBoneN + "|length:" + str(ikSettings.chainLength) + "|stretch:" + str(ikSettings.ikStretch) + "|pole:" + str(ikSettings.poleVector),
                "IK Limb",
                [ikSettings.targetBoneN],
                [ikSettings.poleVector],
                [ikSettings.ikStretch, ikSettings.defaultAxisIndex],
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
    A = ikSettings.eboneChainList[-1].head #base edit bone of the ik chain
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

    # Project an arrow from AC projection point to point B
    isStraight, axisVector =  IsLimbStraight(ikSettings, AB , AC)
    if isStraight :
        arrow_vec = axisVector
    else :
        proj_vec  = start_end_norm * proj
        arrow_vec = AB - proj_vec
    
    arrow_vec = arrow_vec.normalized()

    # Place pole target at a reasonable distance from the chain
    arrow_vec *= AC.length/2
    final_vec = arrow_vec + (A+C)*0.5

    # place pole target bone in the scene pointed to Z+        
    ikSettings.ikPoleEBone.head = final_vec
    ikSettings.ikPoleEBone.tail = final_vec + arrow_vec
    ikSettings.ikPoleEBone.length = ikSettings.ikTargetEBone.length #AC.length *0.5
    ikSettings.ikPoleEBone.roll = 0.0

    """ikSettings.tempPointerEBone.head = (A+C)*0.5
    ikSettings.tempPointerEBone.tail = final_vec
    ikSettings.tempPointerEBone.roll = 0"""

    return isStraight

def IsLimbStraight(ikSettings, AB, AC):
    straightnessThreshold = 0.9999 # Maximum 1
    normalized_dot_product = AB.normalized() @ AC.normalized()
    if abs(normalized_dot_product) < straightnessThreshold :
        ikSettings.isStraight = False
        return False, ikSettings.ikPoleEBone.x_axis

    defaultAxisIndex = ikSettings.defaultAxisIndex
    # default axis defined in the properties file.
    axisVector =  ikSettings.ikPoleEBone.x_axis
    if defaultAxisIndex == "+X":
        axisVector = ikSettings.ikPoleEBone.x_axis
    if defaultAxisIndex ==  "-X":
        axisVector = -ikSettings.ikPoleEBone.x_axis
    if defaultAxisIndex ==  "+Z":
        axisVector = ikSettings.ikPoleEBone.z_axis
    if defaultAxisIndex ==  "-Z":
        axisVector = -ikSettings.ikPoleEBone.z_axis

    ikSettings.isStraight = True
    return True, axisVector

def Signed_angle (vector_u, vector_v, normal):
    ##############
    # Pole Angle #
    # by Jerryno #
    ##############

    # Normal specifies orientation
    angle = vector_u.angle(vector_v)
    if vector_u.cross(vector_v).angle(normal) < 1:
        angle = -angle
    return angle

def PoleAngleRadian (ikSettings):
    ##############
    # Pole Angle #
    # by Jerryno #
    ##############
    baseEBone = ikSettings.eboneChainList[-1]
    AC = ikSettings.ikTargetEBone.head - baseEBone.head
    AP = ikSettings.ikPoleEBone.head - baseEBone.head
    pole_normal = AC.cross(AP)
    projected_pole_axis = pole_normal.cross(baseEBone.tail - baseEBone.head)

    if baseEBone.x_axis == projected_pole_axis.normalized(): 
        return 0
    return Signed_angle(baseEBone.x_axis, projected_pole_axis, baseEBone.tail - baseEBone.head)

def IKLimb():
    scene = bpy.context.scene

    ikStretch = scene.rotf_ik_stretch  
    poleVector = scene.rotf_pole_vector
    defaultAxisIndex = scene.rotf_ik_default_pole_axis
    chainLength = scene.rotf_ik_chain_length
    
    pboneList = bpy.context.selected_pose_bones
    #add bone name to selectedBonesN to have it's generated IK controller selected at the end of the script
    ikSettingsList = list()
    for pbone in pboneList:
        if len(pbone.parent_recursive) < chainLength:
            return [{'WARNING'}, "not enough parents"]

        ikSettings = IKSettings()
        ikSettings.targetPBone = pbone
        ikSettings.ikStretch = ikStretch
        ikSettings.poleVector = poleVector
        ikSettings.defaultAxisIndex = defaultAxisIndex
        ikSettings.chainLength = chainLength

        ikSettingsList.append(ikSettings)
        
    ikPBoneTargetList = IKLimbConstraint.CreateIKLimbConstraint(ikSettingsList)
        
    #end script with new ik handles selected
    for ikTargetPBone in ikPBoneTargetList:
        ikTargetPBone.bone.select = True



   
