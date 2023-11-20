#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . import duplicateBone
from . import removeConstraints
from . import rigState
from . import importControllerShapes
from . import rotfBake

class CenterOfMassConstraint:

    def __init__(self):
        print('Center of Mass Constraint')

    def CreateCenterOfMassConstraint(obj, targetBoneNList):
                
        SetupCenterOfMassController(obj, targetBoneNList)

    def CreateConstraint(self, obj, constraintInfoList):
        targetBoneNList = list()
        errorMessageList = list()
        for constraintInfo in constraintInfoList:
            for targetBoneN in constraintInfo['bone_list']:
                if obj.data.bones.get(targetBoneN) == None: #check if target bone exists. if not, skips
                    errorMessageList.append("Center of Mass Constraint|Bone not found: " + obj.name + "[" + targetBoneN + "]")
                    continue
                else:
                    targetBoneNList.append(targetBoneN)

            CenterOfMassConstraint.CreateCenterOfMassConstraint(obj, targetBoneNList)

        if errorMessageList:
            return errorMessageList

def AddBone():
    obj = bpy.context.object
    CreateBone(obj, prefix="Extra")
    
def CreateBone(obj, prefix):
    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.context.object.data.use_mirror_x = False

    obj = bpy.context.object
    armature = obj.data

    newBoneN = ExtraBoneName(obj, prefix, 1)

    newEBone = armature.edit_bones.new(newBoneN)
    newEBone.use_deform = False
    newEBone.tail = (0,0,1) #tail position

    #find the matrix coordinates of the armature object
    objectMatrix = obj.matrix_world
    #invert armature's matrix to find where global(0,0,0) is in relation to the armature's position/roation
    objectMatrixInvert= objectMatrix.copy()
    objectMatrixInvert.invert()
    #set aim bone position to global (0,0,0) with axis following world's
    newEBone.matrix = objectMatrixInvert

    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    #select new extra bone to change it's custom shape and viewport display
    armature.bones[newBoneN].select = True
    newPBone = obj.pose.bones[newBoneN]
    #assign controller shape to worldPbone
    newBone_customShape = bpy.context.scene.rotf_extraBone_customShape
    if newBone_customShape == None:
        importControllerShapes.ImportControllerShapes(["RotF_Locator"])
        newPBone.custom_shape = bpy.data.objects['RotF_Locator']
    else:
        newPBone.custom_shape = bpy.data.objects[newBone_customShape.name]
        
    newPBone.bone.show_wire=True

    newPBone.bone.is_rotf = True #mark newPBone as a rotf bone
    return newPBone.name

def ExtraBoneName(obj, prefix, count):
    boneName = prefix+str(count)

    if obj.data.bones.get(boneName)==None:
        return boneName
    else:
        return ExtraBoneName(obj, prefix, count+1)

def SetupCenterOfMassController(obj, targetBoneNList):
    #find scale offset to apply to the driver's expression
    scaleVector = obj.matrix_world.to_scale()
    scaleAverage = (scaleVector[0]+scaleVector[1]+scaleVector[2])/3
    scaleOffset = str(int(1/scaleAverage))

    CoMboneN = CreateBone(obj, prefix="CoM")
    CoMpbone = obj.pose.bones[CoMboneN]
    
    for i in range(len(targetBoneNList)): #use bones in targetBoneNList to prepare the expresion that will drive CoM bone's location axis
        if i==0 :
            topVar = "("+"l" + str(i) + "*" + "w" + str(i)+ ") "
            totalWeightVar = "w" + str(i)
        else :
            topVar += "+("+ "l" + str(i) + "*" + "w" + str(i) + ") "
            totalWeightVar += "+w" + str(i)

    for i, boneN in enumerate(targetBoneNList):
        weightN = boneN + " Weight"
        #for each bone in pbone list, add to CoM bone a custom float property that goes from 0.001 to 100            
        CoMpbone[weightN] = float(100)
        #CoMpbone["center_of_mass_influence"].update({weightN: {"min":0.001, "max":100.0, "soft_min":0.0, "soft_max":100.0}})

        #for each location axis of CoM bone, add a driver
        for locIndex in range(3):
            transformType = str()
            if locIndex == 0:
                transformType = 'LOC_X'
            if locIndex == 1:
                transformType = 'LOC_Y'
            if locIndex == 2:
                transformType = 'LOC_Z'

            driver = obj.driver_add('pose.bones["' + CoMpbone.name +'"].location',locIndex).driver #add driver to one of CoM location axis

            #location variable of pbone in world space
            locVar = driver.variables.new()
            locVar.type = 'TRANSFORMS'
            locVar.name = "l" + str(i)
            locVar.targets[0].id = obj
            locVar.targets[0].bone_target = boneN
            locVar.targets[0].transform_type = transformType

            #weight variable from CoM bone's custom property
            weightVar = driver.variables.new()
            weightVar.name = "w" + str(i)
            weightVar.targets[0].id = obj
            weightVar.targets[0].data_path = 'pose.bones["' + CoMpbone.name +'"]["'+ weightN +'"]'

            driver.expression = scaleOffset +"*(" + topVar + ")/(" + totalWeightVar + ")" #assign expression using topVar and totalWeightVar prepared earlier

    newBone_customShape = bpy.context.scene.rotf_centerOfMass_customShape
    if newBone_customShape == None:
        importControllerShapes.ImportControllerShapes(["RotF_Sphere"])
        CoMpbone.custom_shape = bpy.data.objects['RotF_Sphere']
    else:
        CoMpbone.custom_shape = bpy.data.objects[newBone_customShape.name]
        
    CoMpbone.bone.show_wire=True

    rigState.AddConstraint(
                obj,
                "Center of Gravity|" + CoMboneN,
                "Center of Gravity|" + "|".join(targetBoneNList),
                "Center of Gravity",
                targetBoneNList,
                [True], #is not used
                [""], #is not  used
                [0], #is not used
                [0.0] #is not used
                )

def CenterOfMass():
    obj = bpy.context.object
    boneNList = list()
    for pbone in bpy.context.selected_pose_bones:
        if pbone.id_data == obj:
            boneNList.append(pbone.name)

    SetupCenterOfMassController(obj, boneNList)

def RemoveCenterOfMass():
    centerOfMassDict = dict()
    for pbone in bpy.context.selected_pose_bones:
        if pbone.bone.is_rotf and pbone.keys():
            if pbone.id_data not in centerOfMassDict:
                centerOfMassDict[pbone.id_data] = [pbone.name]
            else:
                centerOfMassDict[pbone.id_data].append(pbone.name)

    DeleteCenterOfMassControllers(centerOfMassDict)

def DeleteCenterOfMassControllers(centerOfMassDict):
    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')

    for obj in centerOfMassDict:
        boneNList = centerOfMassDict[obj]
        pboneList = list()
        for boneN in boneNList:
            pboneList.append(obj.pose.bones[boneN])

        rotfBake.KeyframeClear(pboneList) #remove keyframes for all bones in pboneList

    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.context.object.data.use_mirror_x = False

    for obj in centerOfMassDict:
        boneNList = centerOfMassDict[obj]

        for boneN in boneNList:
            armature = obj.data
            ebone = armature.edit_bones.get(boneN)
            if ebone:
                armature.edit_bones.remove(ebone)
    
    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')

    for obj in centerOfMassDict:
        boneNList = centerOfMassDict[obj]
        pboneList = list()
        for boneN in boneNList:
            rigState.RemoveConstraint(obj, "Center of Gravity|"+ boneN) #remove center of mass constraint from the object's rig state