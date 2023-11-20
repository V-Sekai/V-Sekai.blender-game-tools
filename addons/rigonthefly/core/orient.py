#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

from os import name
import bpy
from mathutils import Matrix, Vector
from . import duplicateBone
from . import removeConstraints
from . import rigState
from . import importControllerShapes
from . import rotfBake

class OrientConstraint:

    def __init__(self):
        print('Orient Constraint')

    def CreateOrientConstraint(orientSettings):

        bonesToBakeInfo = SetupOrientControllers(orientSettings)
        rotfBake.Bake(bonesToBakeInfo)

        SetupOrientBehaviour(orientSettings)

    def CreateConstraint(self, obj, constraintInfoList):
        errorMessageList = list()
        for constraintInfo in constraintInfoList:
            orientSettings = OrientSettings()
            boneNList = list()
            for boneN in constraintInfo['bone_list']:
                if obj.data.bones.get(boneN) == None:
                    errorMessageList.append("Orient Constraint|Bone not found: " + obj.name + "[" + boneN + "]")
                    continue
                boneNList.append(boneN)

            orientSettings.obj = obj
            orientSettings.boneNList = boneNList

            OrientConstraint.CreateOrientConstraint(orientSettings)

        if errorMessageList:
            return errorMessageList

class OrientSettings:
    def __init__(self):
        self.obj = None
        self.boneNList = list()
        self.orientBoneNList = list()        

def SetupOrientControllers(orientSettings):
    obj = orientSettings.obj
    boneNList = orientSettings.boneNList

    #force edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.context.object.data.use_mirror_x = False

    editBones = obj.data.edit_bones

    eboneList = list()
    for boneN in boneNList:
        ebone = editBones[boneN]
        ebone.use_connect = False
        eboneList.append(ebone)

    newBones, newEditBones, newBoneNames = duplicateBone.DuplicateBone("Orient.", eboneList)
    orientEboneList = newEditBones
    orientSettings.orientBoneNList = newBoneNames
    for ebone, orientEBone in zip(eboneList, orientEboneList):
        if ebone.parent:
            boneNParent = ebone.parent.name
            orientBoneNParent = "Orient." + boneNParent
            orientEBoneParent = editBones.get(orientBoneNParent)
            if orientEBoneParent:
                orientEBone.parent = orientEBoneParent
            else:
                orientEBone.parent = editBones.get(boneNParent)


    #orient the dupliacted bones to work better with Blender's constraints
    OrientBones(obj.data, newBoneNames)

    #mirror oriented bones so that they work correctly in mirror mode
    bpy.context.object.data.use_mirror_x = True
    for ebone in newEditBones:
        ebone.roll = ebone.roll
    bpy.context.object.data.use_mirror_x = False

    #go to pose mode to setup constraints to transfer motion from base hierarchy onto orient hierarchy
    bpy.ops.object.mode_set(mode='POSE')

    poseBones = obj.pose.bones
    baseLayer = obj.notOrientedBonesLayer

    bonesToBakeInfo = dict()

    pboneList = list()
    orientPBoneList = list()

    for boneN, orientBoneN in zip(orientSettings.boneNList, orientSettings.orientBoneNList):
        pbone = poseBones[boneN]
        orientPBone = poseBones[orientBoneN]

        pboneList.append(pbone)
        orientPBoneList.append(orientPBone)
        
        #constrain orient bones to temp bones
        orientPBone = poseBones[orientBoneN]
        orientCopyTransforms = orientPBone.constraints.new('COPY_TRANSFORMS')
        orientCopyTransforms.name += " RotF"
        orientCopyTransforms.target = obj
        orientCopyTransforms.subtarget = boneN #tempBoneN
        orientCopyTransforms.target_space = 'LOCAL_OWNER_ORIENT'
        orientCopyTransforms.owner_space = 'LOCAL'

        bonesToBakeInfo[orientPBone] = [
            [pbone, rotfBake.Channel.locationXYZ, rotfBake.Channel.locationXYZ],
            [pbone, rotfBake.Channel.rotationQE, rotfBake.Channel.rotationQE],
            [pbone, rotfBake.Channel.scaleXYZ, rotfBake.Channel.scaleXYZ],
            ]


        #ASSIGN BONE LAYERS
        for layer in range(32):
            #set orient bone to the same layer as the base bone
            orientPBone.bone.layers[layer] = pbone.bone.layers[layer]

        #add base bone to their appropriate layer
        pbone.bone.layers[baseLayer] = True

        for layer in range(32):
            #remove base bone form all layers except base layer
            if layer != baseLayer:
                pbone.bone.layers[layer] = False


        #ASSIGN CONTROLLER SHAPE
        #assign controller shape to orient bone
        orient_customShape = bpy.context.scene.rotf_orient_customShape
        if orient_customShape == None:
            importControllerShapes.ImportControllerShapes(["RotF_Circle"])
            orientPBone.custom_shape = bpy.data.objects['RotF_Circle']
        else:
            orientPBone.custom_shape = bpy.data.objects[orient_customShape.name]

        #add Orient tag and the base bone's name to the orient bone's rotf_pointer_list for when to remove the ik constraint
        newPointer = orientPBone.bone.rotf_pointer_list.add()
        newPointer.name = "Orient"
        newPointer.armature_object = obj
        newPointer.bone_name = boneN

    duplicateBone.AssignPoseBoneGroups(pboneList, orientPBoneList)
    return bonesToBakeInfo

def SetupOrientBehaviour(orientSettings):
    obj = orientSettings.obj
    boneNList = orientSettings.boneNList

    poseBones = obj.pose.bones

    orientPBoneList = list()
    for orientBoneN in orientSettings.orientBoneNList:
        orientPBone = poseBones[orientBoneN]
        orientPBoneList.append(orientPBone)
    
    removeConstraints.RemoveAllRotFConstraints(orientPBoneList)

    for boneN, orientBoneN in zip(orientSettings.boneNList, orientSettings.orientBoneNList):
        pbone = poseBones[boneN]
        
        #constrain base bones to orient bones
        copyTransforms = pbone.constraints.new('COPY_TRANSFORMS')
        copyTransforms.name += " RotF"
        copyTransforms.target = obj
        copyTransforms.subtarget = orientBoneN
        copyTransforms.target_space = 'LOCAL_OWNER_ORIENT'
        copyTransforms.owner_space = 'LOCAL'
    
    boneNListString = "|".join(orientSettings.boneNList)

    rigState.AddConstraint(
        orientSettings.obj,
        "Orient|" + boneNListString,
        "Orient|" + boneNListString,
        "Orient",
        orientSettings.boneNList,
        [True], #is not used
        [""], #is not  used
        [0], #is not used
        [0.0] #is not used
        )

def Orient():
    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')
    for obj in bpy.context.selected_objects:

        boneNList = list()

        #list visible bones to key
        visibleLayers = list()
        for i, layer in enumerate(obj.data.layers):
            if layer:
                visibleLayers.append(i)

        for pbone in obj.pose.bones:
            bone = pbone.bone
            boneName = bone.name

            #check if bone is in a visible layer
            pboneIsInVisibleLayer = False
            for i in visibleLayers:
                if bone.layers[i]:
                    pboneIsInVisibleLayer = True
                    break

            if pboneIsInVisibleLayer and not bone.hide: #check if bone is visible
                boneNList.append(boneName)

        if len(boneNList) > 1:
            orientSettings = OrientSettings()
            orientSettings.obj = obj
            orientSettings.boneNList = boneNList

            OrientConstraint.CreateOrientConstraint(orientSettings)

def OrientBones(armature, bonesNamesToOrient):
        parent_correction_inv = Matrix()

        #orient duplicated bones to be compatible with Rig on the Fly tools
        for boneN in bonesNamesToOrient:

            ebone = armature.edit_bones[boneN]

            from bpy_extras.io_utils import axis_conversion
            
            #if parent_correction_inv:
            #    orientBone.pre_matrix = parent_correction_inv @ (orientBone.pre_matrix if orientBone.pre_matrix else Matrix())

            correction_matrix = Matrix()

            # find best orientation to align baseBone with
            bone_children = tuple(child for child in ebone.children)
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
                    orientBoneMatrix = ebone.matrix                    
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
                        orientBoneMatrix = ebone.matrix                    
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
                            
            ebone.matrix = ebone.matrix @ correction_matrix
            parent_correction_inv = correction_matrix

        #now the orient bones are well oriented!