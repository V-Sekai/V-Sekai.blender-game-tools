#########################################
#######       Rig On The Fly      #######
####### Copyright © 2024 Dypsloom #######
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

class IKStretchConstraint:

    def __init__(self):
        print('IK Stretch Constraint')

    def CreateIKStretchConstraint(ikSettingsList):
        ikTargetPBoneList = list()

        bonesToBakeInfo = SetupIKStretchControllers(ikSettingsList)
        
        for ikSettings in ikSettingsList:
            ikTargetPBoneList.append(ikSettings.ikTargetPBone)
        
        rotfBake.Bake(bonesToBakeInfo)
        
        SetupIKStretchBehaviour(ikSettingsList)
        
        return ikTargetPBoneList

    def CreateConstraint(self, obj, constraintInfoList):
        ikSettingsList = list()
        errorMessageList = list()
        for constraintInfo in constraintInfoList:

            targetBoneN = constraintInfo['bone_list'][0]
            if obj.data.bones.get(targetBoneN) == None: #check if target bone exists. if not, skips
                errorMessageList.append("IK Stretch Constraint|Bone not found: " + obj.name + "[" + targetBoneN + "]")
                continue

            targetPBone = obj.pose.bones[targetBoneN]

            bool_list = constraintInfo['bool_list']
            distributeRotation = bool_list[0]

            string_list = constraintInfo['string_list']
            ikStretchType = string_list[0]

            int_list = constraintInfo['int_list']
            chainLength = int_list[0]

            ikSettings = IKStretchSettings()
            ikSettings.targetPBone = targetPBone
            ikSettings.ikStretchType = ikStretchType
            ikSettings.chainLength = int(chainLength)
            ikSettings.distributeRotation = distributeRotation

            ikSettingsList.append(ikSettings)

        IKStretchConstraint.CreateIKStretchConstraint(ikSettingsList)

        if errorMessageList:
            return errorMessageList

class IKStretchSettings:
    def __init__(self): 
        self.targetPBone = None #pose bone
        self.chainLength = None #int
        #self.maintainVolume = None #bool
        #self.chainScale = None #bool
        #self.inheritScale = None #bool
        self.distributeRotation = None #bool
        self.ikStretchType = None #string

        self.obj = None
        self.bones = None
        self.poseBones = None
        self.editBones = None

        self.targetBoneN = None

        self.ikTargetBoneN = None
        self.ikTargetPBone = None
        self.ikTargetEBone = None

        self.boneNChainList = None
        self.pboneChainList = None
        self.eboneChainList = None

        self.boneNAimChainList = None
        self.pboneAimChainList = None
        self.eboneAimChainList = None

        self.boneNOffsetChainList = None
        self.pboneOffsetChainList = None
        self.eboneOffsetChainList = None

        self.boneNTempChainList = None
        self.pboneTempChainList = None
        self.eboneTempChainList = None

        self.boneNIKBase = None
        self.pboneIKBase = None
        self.eboneIKBase = None

        self.boneNRotHelperChainList = None
        self.pboneRotHelperChainList = None
        self.eboneRotHelperChainList = None

        self.IKBaseBoneLengthFactor = float()

def SetupIKStretchControllers(ikSettingsList):
    #adds chain bones to their respective ikSettings depending on the chainLength value
    for ikSettings in ikSettingsList:
        pboneTarget = ikSettings.targetPBone
        ikSettings.targetBoneN = pboneTarget.name
        ikSettings.obj = pboneTarget.id_data
        
        ikSettings.boneNChainList = list()
        ikSettings.pboneChainList = list()
        for i, pbone in zip(range(ikSettings.chainLength), pboneTarget.parent_recursive):
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
        newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("StretchIK.", [ikSettings.targetEBone])
        ikSettings.ikTargetBoneN = newBoneNames[0]
        ikSettings.ikTargetEBone = newEditBones[0]

        #remove parent of IK target
        ikSettings.ikTargetEBone.parent = None

        #add the chain bones to ikSettings.eboneChainList
        ikSettings.eboneChainList = list()
        for boneName in ikSettings.boneNChainList:
            ikSettings.eboneChainList.append(ikSettings.editBones[boneName])

        #add IK base bone
        newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBones("BaseIK.", [ikSettings.eboneChainList[-1]])
        ikSettings.boneNIKBase = newBoneNames[0]
        ikSettings.eboneIKBase = newEditBones[0]

        #add AimIK bones, they are duplicates of the bone chain
        newBones, eboneAimChainList, boneNAimChainList = duplicateBone.DuplicateBones("AimIK.", ikSettings.eboneChainList)
        ikSettings.boneNAimChainList = boneNAimChainList
        ikSettings.eboneAimChainList = eboneAimChainList

        #add AimIK Offset bones, they are duplicates of the bone chain
        newBones, eboneOffsetChainList, boneNOffsetChainList = duplicateBone.DuplicateBones("AimIKOffset.", ikSettings.eboneChainList)
        ikSettings.boneNOffsetChainList = boneNOffsetChainList
        ikSettings.eboneOffsetChainList = eboneOffsetChainList

        for eboneAimChain, eboneOffsetChain in zip(ikSettings.eboneAimChainList, ikSettings.eboneOffsetChainList):
            eboneAimChain.parent = ikSettings.eboneIKBase
            eboneOffsetChain.parent = eboneAimChain

        #snap tail of the Aim chain to the bone it will be aiming at to avoid
        for eboneChain, eboneAimChain in zip([ikSettings.targetEBone]+ikSettings.eboneChainList[:-1], ikSettings.eboneAimChainList):
            eboneAimChain.tail = eboneChain.head

        #add AimIK temp bones, to get rotation from, are duplicates of the aimIK bone chain
        newBones, eboneTempChainList, boneNTempChainList = duplicateBone.DuplicateBones("Temp", ikSettings.eboneAimChainList)
        ikSettings.boneNTempChainList = boneNTempChainList
        ikSettings.eboneTempChainList = eboneTempChainList
        for ebone, eboneTemp in zip(ikSettings.eboneChainList, eboneTempChainList):
            eboneTemp.parent = ebone

        #add AimIK rotation helper bones, to get helper with rotation distribution along the chain, are duplicates of the aimIK bone chain
        newBones, eboneRotHelperChainList, boneNRotHelperChainList = duplicateBone.DuplicateBones("RotHelper", ikSettings.eboneAimChainList)
        ikSettings.boneNRotHelperChainList = boneNRotHelperChainList
        ikSettings.eboneRotHelperChainList = eboneRotHelperChainList
        for eboneRotHelper in eboneRotHelperChainList:
            eboneRotHelper.parent = ikSettings.ikTargetEBone
        
        #snap tail of IK base bone to ikTargetEBone head's position
        constrainedBoneOldLength = ikSettings.eboneIKBase.length
        ikSettings.eboneIKBase.tail = ikSettings.ikTargetEBone.head
        constrainedBoneNewLength = ikSettings.eboneIKBase.length
        ikSettings.IKBaseBoneLengthFactor = constrainedBoneOldLength/constrainedBoneNewLength

    bpy.context.object.data.use_mirror_x = mirrorX
    
    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')
    
    bonesToBakeInfo = dict()
    for ikSettings in ikSettingsList:
        #prepare the oldPBoneList and newPBoneList (the duplicated bones) to assign the appropriate bone groups along with tagging them as rotf bones
        poseBones = ikSettings.obj.pose.bones
        pboneTarget = poseBones[ikSettings.targetBoneN]
        pboneIKTarget = poseBones[ikSettings.ikTargetBoneN]
        pboneIKBase = poseBones[ikSettings.boneNIKBase]
        
        ikSettings.targetPBone = pboneTarget
        ikSettings.ikTargetPBone = pboneIKTarget
        ikSettings.pboneIKBase = pboneIKBase

        pboneChainList = list()
        pboneAimChainList = list()
        pboneOffsetChainList = list()
        pboneTempChainList = list()
        pboneRotHelperChainList = list()

        for boneN, boneNAim, boneNAimOffset, boneNTemp, boneNRotHelper in zip(ikSettings.boneNChainList, 
                                                                              ikSettings.boneNAimChainList, 
                                                                              ikSettings.boneNOffsetChainList, 
                                                                              ikSettings.boneNTempChainList, 
                                                                              ikSettings.boneNRotHelperChainList):
            pboneChainList.append(poseBones[boneN])
            pboneAimChainList.append(poseBones[boneNAim])
            pboneOffsetChainList.append(poseBones[boneNAimOffset])
            pboneTempChainList.append(poseBones[boneNTemp])
            pboneRotHelperChainList.append(poseBones[boneNRotHelper])

        ikSettings.pboneChainList = pboneChainList
        ikSettings.pboneAimChainList = pboneAimChainList
        ikSettings.pboneOffsetChainList = pboneOffsetChainList   
        ikSettings.pboneTempChainList = pboneTempChainList
        ikSettings.pboneRotHelperChainList = pboneRotHelperChainList

        oldPBoneList = list()
        newPboneList = list()

        oldPBoneList.append(pboneTarget)
        newPboneList.append(pboneIKTarget)

        oldPBoneList.append(pboneChainList[-1])
        newPboneList.append(pboneIKBase)

        oldPBoneList.extend(pboneChainList)
        newPboneList.extend(pboneAimChainList)

        oldPBoneList.extend(pboneChainList)
        newPboneList.extend(pboneOffsetChainList)

        oldPBoneList.extend(pboneChainList)
        newPboneList.extend(pboneRotHelperChainList)

        duplicateBone.AssignPoseBoneGroups(oldPBoneList, newPboneList)

        #set up IK Target
        copyTransforms = pboneIKTarget.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " RotF"
        copyTransforms.target = ikSettings.obj
        copyTransforms.subtarget = pboneTarget.name

        bonesToBakeInfo[pboneIKTarget] = [pboneTarget]

        #set up Offset Chain
        for pbone, pboneOffsetIK in zip(pboneChainList, pboneOffsetChainList):
            pboneOffsetIK.bone.show_wire = False

            #if ikSettings.inheritScale:
            if ikSettings.ikStretchType == "Location":
                pboneOffsetIK.bone.inherit_scale = 'NONE'
            else:
                pboneOffsetIK.bone.inherit_scale = 'FULL'

            #constraint the IK target to the target bone
            copyTransforms = pboneOffsetIK.constraints.new('COPY_TRANSFORMS')
            copyTransforms.name += " RotF"
            copyTransforms.target = ikSettings.obj
            copyTransforms.subtarget = pbone.name

            #prepare bake info for the ik target pose bone
            bonesToBakeInfo[pboneOffsetIK] = [pboneTarget]
        
        #set up Aim Chain
        for pbone, pboneAimIK, pboneTemp, pboneAimTarget in zip(pboneChainList, pboneAimChainList, pboneTempChainList, [pboneTarget]+pboneChainList[:-1]):
            pboneAimIK.bone.show_wire = False
            #have the aimIK chain bones look at bones up the chain and constrain their location to the chain bone

            #constraint the chainAimIK bones position to their corresponding chain bones
            copyLocation = pboneAimIK.constraints.new('COPY_TRANSFORMS')
            copyLocation.name += " RotF"
            copyLocation.target = ikSettings.obj
            copyLocation.subtarget = pboneTemp.name

            #have the chainAimIK bones aim up the chain
            if ikSettings.ikStretchType == "Location":
                copyLocation = pboneAimIK.constraints.new('DAMPED_TRACK')
                copyLocation.name += " RotF"
                copyLocation.target = ikSettings.obj
                copyLocation.subtarget = pboneAimTarget.name
            else:
                copyLocation = pboneAimIK.constraints.new('STRETCH_TO')
                copyLocation.name += " RotF"
                copyLocation.target = ikSettings.obj
                copyLocation.subtarget = pboneAimTarget.name
            
            bonesToBakeInfo[pboneAimIK] = [pboneTarget]

            #set custom shape scale relative to target chain
            pboneAimIK.custom_shape_scale_xyz = pbone.custom_shape_scale_xyz * (pbone.bone.length/pboneAimIK.bone.length)
        
        #set up constraints for Rotation Helper bones
        for pboneTemp, pboneRotHelper in zip(pboneTempChainList, pboneRotHelperChainList):
            copyRotation = pboneRotHelper.constraints.new('COPY_ROTATION')
            copyRotation.name += " RotF"
            copyRotation.target = ikSettings.obj
            copyRotation.subtarget = pboneTemp.name

            bonesToBakeInfo[pboneRotHelper] = [pboneTarget]

        #set up constraints for IKBase bone
        pboneIKBase = ikSettings.pboneIKBase
        pboneIKBase.bone.show_wire = False

        bonesToBakeInfo[pboneIKBase] = list()
        for pbone in [ikSettings.ikTargetPBone]+ikSettings.pboneAimChainList:
            bonesToBakeInfo[pboneIKBase].append(pbone)
        
        #constraint the IK base to the target bone
        copyLocation = pboneIKBase.constraints.new('COPY_LOCATION')
        copyLocation.name += " RotF"
        copyLocation.target = ikSettings.obj
        copyLocation.subtarget = ikSettings.pboneChainList[-1].name
        #add a stretch to constraint to the IK base
        stretchTo = pboneIKBase.constraints.new('STRETCH_TO')
        stretchTo.name += " RotF"
        stretchTo.target = ikSettings.obj
        stretchTo.subtarget = ikSettings.ikTargetBoneN
        stretchTo.rest_length = pboneIKBase.bone.length
        #if not ikSettings.maintainVolume:
        if ikSettings.ikStretchType != "Keep Volume":
            stretchTo.volume = 'NO_VOLUME'

        #assign controller shape to ikTargetBoneP
        pboneThatNeedCustomShapeList = [pboneIKTarget, pboneIKBase]+pboneAimChainList
        aimIK_customShape = bpy.context.scene.rotf_ikTarget_customShape
        for pbone in pboneThatNeedCustomShapeList:
            if aimIK_customShape == None:
                importControllerShapes.ImportControllerShapes(["RotF_Square"])
                pbone.custom_shape = bpy.data.objects['RotF_Square']
            else:
                pbone.custom_shape = bpy.data.objects[aimIK_customShape.name]
            
        #to IKBase bone's custom shape visual size
        pboneIKBase.custom_shape_scale_xyz *= ikSettings.IKBaseBoneLengthFactor * 2

    return bonesToBakeInfo

def SetupIKStretchBehaviour(ikSettingsList):
    for ikSettings in ikSettingsList:
        pboneIKBase = ikSettings.pboneIKBase
        pboneIKTarget = ikSettings.ikTargetPBone
        pboneAimChainList = ikSettings.pboneAimChainList 
        pboneOffsetChainList = ikSettings.pboneOffsetChainList 
        pboneRotHelperChainList = ikSettings.pboneRotHelperChainList

        removeConstraints.RemoveAllRotFConstraints([pboneIKBase, pboneIKTarget] 
                                                   + pboneAimChainList 
                                                   + pboneOffsetChainList 
                                                   + pboneRotHelperChainList)
        
        #setup the aim constraint to the IKBase bone aiming at the IKTarget bone
        stretchTo = ikSettings.pboneIKBase.constraints.new('STRETCH_TO')
        stretchTo.name += " RotF"
        stretchTo.target = ikSettings.obj
        stretchTo.subtarget = ikSettings.ikTargetBoneN
        stretchTo.rest_length = ikSettings.pboneIKBase.bone.length
        #if not ikSettings.maintainVolume:
        if ikSettings.ikStretchType != "Keep Volume":
            stretchTo.volume = 'NO_VOLUME'

        aimTargetBoneNList = [ikSettings.ikTargetBoneN] + ikSettings.boneNAimChainList[:-1]
        
        #set up the aim chain
        chainLength = float(ikSettings.chainLength)
        for i, (pboneAim, aimTargetBoneN, pboneRotHelper) in enumerate(zip(pboneAimChainList, aimTargetBoneNList, pboneRotHelperChainList)):
            if ikSettings.distributeRotation:
                #add rotation constraint so that the rotation gets distributed between the IKBase and the IKTarget
                copyRotation = pboneAim.constraints.new("COPY_ROTATION")
                copyRotation.name += " RotF"
                copyRotation.target = ikSettings.obj
                copyRotation.subtarget = pboneRotHelper.name #ikSettings.ikTargetBoneN
                copyRotation.influence = (chainLength-i-1)/chainLength #the closer the bone is to the IKTarget bone the more it copies IKTarget bone's rotation

            #add aim constraints to the AimIK bones aiming up the chain
            #if ikSettings.chainScale:
            if ikSettings.ikStretchType == "Location":
                aimConstraint = pboneAim.constraints.new("DAMPED_TRACK")
                aimConstraint.name += " RotF"
                aimConstraint.target = ikSettings.obj
                aimConstraint.subtarget = aimTargetBoneN
                
            else:
                stretchTo = pboneAim.constraints.new("STRETCH_TO")
                stretchTo.name += " RotF"
                stretchTo.target = ikSettings.obj
                stretchTo.subtarget = aimTargetBoneN
                stretchTo.rest_length = pboneAim.bone.length#math.dist(ikSettings.obj.pose.bones[aimTargetBoneN].bone.head_local, pboneAim.bone.head_local)
                if ikSettings.ikStretchType != "Keep Volume":
                    stretchTo.volume = 'NO_VOLUME'

        #have the bone chain constrained to the aim chain bones
        pboneList = [ikSettings.targetPBone] + ikSettings.pboneChainList
        offsetBoneNList = [ikSettings.ikTargetBoneN] + ikSettings.boneNOffsetChainList
        for pboneAim, aimBoneN in zip(pboneList, offsetBoneNList):
            copyTransforms = pboneAim.constraints.new("COPY_TRANSFORMS")
            copyTransforms.name += " RotF"
            copyTransforms.target = ikSettings.obj
            copyTransforms.subtarget = aimBoneN

            #remove pbone's inherit scale to prevent unexpected shearing when removing IK Stretch
            pboneAim.bone.inherit_scale = 'NONE'
        
        #move non relevant bones to unused layer
        appVersion = bpy.app.version
        if appVersion[0] == 4:
            pboneToMoveList = [ikSettings.targetPBone] + ikSettings.pboneChainList + ikSettings.pboneOffsetChainList + ikSettings.pboneRotHelperChainList
            for pboneAim in pboneToMoveList:

                boneCollections.AddBoneToCollections(pboneAim.bone, [boneCollections.RotFUnusedColName])

                #Keep stretch chain bones that should stay in the unnused
                boneCollections.UnassignBoneFromCollections(pboneAim.bone, [boneCollections.RotFAnimationColName])

                #hide bones
                pboneAim.bone.hide = True

        elif appVersion[0] == 3:
            pboneToMoveList = [ikSettings.targetPBone] + ikSettings.pboneChainList
            unusedLayer = ikSettings.obj.unusedRigBonesLayer
            for pboneAim in pboneToMoveList:            
                bone = pboneAim.bone
                bone.layers[unusedLayer]=True
                for layer in range(32):
                    if layer != unusedLayer:
                        bone.layers[layer]=False
        
        #add IKStretch tag and the target bone's name to the ik target aim chain list and ik base bones' rotf_pointer_list for when to remove the ikStretch constraint
        for pboneAim in [ikSettings.ikTargetPBone, ikSettings.pboneIKBase] + ikSettings.pboneAimChainList:
            newPointer = pboneAim.bone.rotf_pointer_list.add()
            newPointer.name = "IK_STRETCH"
            newPointer.armature_object = ikSettings.obj
            newPointer.bone_name = ikSettings.targetBoneN

        
        #force pose mode
        bpy.ops.object.mode_set(mode='EDIT')
        #Reparent the Temp bone to be used as rotation distribution helper bones
        editBones = ikSettings.obj.data.edit_bones
        #boneNIKTarget = ikSettings.ikTargetBoneN
        #eboneIKTarget = editBones[boneNIKTarget]

        """if ikSettings.distributeRotation:
            for boneNTemp in ikSettings.boneNTempChainList:
                eboneTemp = editBones[boneNTemp]
                eboneTemp.parent = eboneIKTarget
        else:"""
        for boneNTemp in ikSettings.boneNTempChainList:
            eboneTemp = editBones[boneNTemp]
            editBones.remove(eboneTemp)

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        rigState.AddConstraint(
                ikSettings.obj,
                "IK Stretch|" + ikSettings.targetBoneN,
                "IK Stretch|" + ikSettings.targetBoneN + "|length:" + str(ikSettings.chainLength) + "|stretch:" + str(ikSettings.ikStretchType),
                "IK Stretch",
                [ikSettings.targetBoneN],
                [ikSettings.distributeRotation], #is not used
                [""], #is not used
                [ikSettings.chainLength],
                [0.0] #is not used
                )

def IKStretch():
    scene = bpy.context.scene

    ikStretchType = scene.rotf_stretch_ik_stretch_type
    chainLength = scene.rotf_stretch_ik_chain_length
    #maintainVolume = scene.rotf_ik_stretch_maintain_volume
    #inheritScale = scene.rotf_ik_stretch_chain_inherit_scale
    #chainScale = scene.rotf_ik_stretch_chain_scale
    distributeRotation = scene.rotf_stretch_ik_distribute_rotation
    
    pboneList = bpy.context.selected_pose_bones
    #add bone name to selectedBonesN to have it's generated IK controller selected at the end of the script
    ikSettingsList = list()
    for pbone in pboneList:
        if len(pbone.parent_recursive) < chainLength:
            return [{'WARNING'}, "not enough parents"]

        ikSettings = IKStretchSettings()
        ikSettings.targetPBone = pbone
        ikSettings.chainLength = chainLength
        ikSettings.ikStretchType = ikStretchType
        ikSettings.distributeRotation = distributeRotation

        ikSettingsList.append(ikSettings)
        
    ikPBoneTargetList = IKStretchConstraint.CreateIKStretchConstraint(ikSettingsList)
        
    #end script with new ik handles selected
    for ikTargetPBone in ikPBoneTargetList:
        ikTargetPBone.bone.select = True

class RemoveIKStretchInfo:
    def __init__(self):
        self.object = None
        self.targetBoneN = str()
        self.constraint = None
        self.ikTargetBoneN = str()
        self.baseIKBoneN = str()
        self.aimChainBoneNList = list()

def RemoveIKStretchSpace():
    print("start removing Stretch IK")
    removeIKStretchInfoList = list()
    targetBoneNList = list()

    for pbone in bpy.context.selected_pose_bones:
        if "IK_STRETCH" in pbone.bone.rotf_pointer_list:
            obj = pbone.id_data
            targetBoneN = pbone.bone.rotf_pointer_list['IK_STRETCH'].bone_name
            #ikTargetBone = obj.pose.bones[targetBoneN].bone
            print("found target bone with IK Stretch pointer")
            print(targetBoneN)
            if targetBoneN not in targetBoneNList:
                targetBoneNList.append(targetBoneN)
                removeIKStretchInfo = RemoveIKStretchInfo()
                removeIKStretchInfo.object = obj
                removeIKStretchInfo.targetBoneN = targetBoneN

                removeIKStretchInfoList.append(removeIKStretchInfo)

    RemoveIKStretch(removeIKStretchInfoList)

    #end with only the aim space bones selected
    bpy.ops.pose.select_all(action='DESELECT')
    for removeAimInfo in removeIKStretchInfoList:
        pbone = removeAimInfo.object.pose.bones[removeAimInfo.targetBoneN]
        pbone.bone.select = True

def RemoveIKStretch(removeIKStretchInfoList):
    bonesToBakeInfo = dict()
    boneNToRemoveDict = dict()
    pboneKeyframeClearList = list()

    for removeIKStretchInfo in removeIKStretchInfoList:
        obj = removeIKStretchInfo.object
        armature = obj.data
        ikTargetBoneN = removeIKStretchInfo.targetBoneN

        targetPBone = obj.pose.bones[ikTargetBoneN]

        #list the bones to remove and bones to bake

        #find ikbase as it will help find the rest of the bones to remove and bones to bake
        for i, pbone in enumerate(targetPBone.parent_recursive):
            boneN = pbone.name

            ikbasePBone = obj.pose.bones.get("BaseIK."+boneN)

            if ikbasePBone:
                pbonesToRemoveList = list()
                pbonesToRemoveList.append(ikbasePBone)

                #get IKTarget control
                constraint = ikbasePBone.constraints.get("Stretch To RotF")
                ikTargetBoneN = constraint.subtarget
                ikTargetPBone = obj.pose.bones[ikTargetBoneN]

                pbonesToRemoveList.append(ikTargetPBone)
                #get aimChain controls
                for aimChainPBone in ikbasePBone.children_recursive:
                    pbonesToRemoveList.append(aimChainPBone)

                #get RotHelper controls
                for childPBone in ikTargetPBone.children:
                    if "RotHelper" in childPBone.name:
                        pbonesToRemoveList.append(childPBone)

                #add pbonesToRemoveList to pboneKeyframeClearList
                pboneKeyframeClearList.extend(pbonesToRemoveList)

                for pboneToBake in [targetPBone] + targetPBone.parent_recursive[:i+1]:
                    bonesToBakeInfo[pboneToBake] = list()
                    for pboneToRemove in pbonesToRemoveList:
                        bonesToBakeInfo[pboneToBake].append(pboneToRemove)

                    appVersion = bpy.app.version
                    if appVersion[0] == 4:
                        pboneToBake.bone.hide = False
                        boneCollections.UnassignBoneFromCollections(pboneToBake.bone, [boneCollections.RotFUnusedColName])

                    if appVersion[0] == 3:
                        for layer in range(32):
                            pboneToBake.bone.layers[layer] = armature.bones[ikTargetBoneN].layers[layer]
                break
    
    if bpy.context.scene.rotf_no_bake_on_remove == False:
        rotfBake.Bake(bonesToBakeInfo)
    removeConstraints.RemoveAllRotFConstraints(bonesToBakeInfo)

    rotfBake.KeyframeClear(pboneKeyframeClearList)

    for pbone in pboneKeyframeClearList:
        armature = pbone.id_data.data
        if armature in boneNToRemoveDict:
            boneNToRemoveDict[armature].append(pbone.name)
        else:
            boneNToRemoveDict[armature] = [pbone.name]

    #force edit mode to remove IK bones
    bpy.ops.object.mode_set(mode='EDIT')
    for armature in boneNToRemoveDict:
        for boneN in boneNToRemoveDict[armature]:
            try:
                armature.edit_bones.remove(armature.edit_bones[boneN])
            except:
                print(boneN)

    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    appVersion = bpy.app.version
    if appVersion[0] == 4:
        boneCollections.RemoveEmptyBoneCollection(armature) #for some reason it has to be in Pose mode to work otherwise in Edit mode collections are considered empty

    for removeIKStretchInfo in removeIKStretchInfoList:
        rigState.RemoveConstraint(obj, "IK Limb|"+ removeIKStretchInfo.targetBoneN)