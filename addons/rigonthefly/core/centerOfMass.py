#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . import duplicateBone
from . import removeConstraints
from . import extraBone
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

def SetupCenterOfMassController(obj, targetBoneNList):
    #find scale offset to apply to the driver's expression
    scaleVector = obj.matrix_world.to_scale()
    scaleAverage = (scaleVector[0]+scaleVector[1]+scaleVector[2])/3
    scaleOffset = str(int(1/scaleAverage))

    CoMboneN = extraBone.CreateBone(obj, prefix="CoM")
    CoMpbone = obj.pose.bones[CoMboneN]
    #scale the size of the pose bone's custom shape relative to the average dimensions of the armature
    CoMpbone.custom_shape_scale_xyz *= ((obj.dimensions.x + obj.dimensions.y + obj.dimensions.z)/3)*0.1
    
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

    #assign custom shape to CoM bone
    newBone_customShape = bpy.context.scene.rotf_centerOfMass_customShape
    if newBone_customShape == None:
        importControllerShapes.ImportControllerShapes(["RotF_Sphere"])
        CoMpbone.custom_shape = bpy.data.objects['RotF_Sphere']
    else:
        CoMpbone.custom_shape = bpy.data.objects[newBone_customShape.name]
        
    CoMpbone.bone.show_wire=False

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
    
    obj.data.bones.active = CoMpbone.bone
    return CoMboneN

def CenterOfMass():
    obj = bpy.context.object
    boneNList = list()
    for pbone in bpy.context.selected_pose_bones:
        if pbone.id_data == obj:
            boneNList.append(pbone.name)

    SetupCenterOfMassController(obj, boneNList)

def AddToCenterOfMass():
    #Adds selected bones to the active center of mass bone list of influence

    #save CoM bone's name, custom shape, custom shape transforms and color
    CoMPBone = bpy.context.active_pose_bone
    obj = CoMPBone.id_data
    CoMBoneN = CoMPBone.name

    CoMCustomShape = CoMPBone.custom_shape
    CoMCustomShapeTranslation = CoMPBone.custom_shape_translation
    CoMCustomShapeRotation = CoMPBone.custom_shape_rotation_euler
    CoMCustomShapeScale = CoMPBone.custom_shape_scale_xyz
    
    appVersion = bpy.app.version
    if appVersion[0] == 4:
        CoMBoneColor = CoMPBone.bone.color.palette
        CoMPBoneColor = CoMPBone.color.palette

    #save original list of target bones influencing the CoM bone
    targetBoneNDict = dict()

    #get driver fCurve from name of the CoM bone
    for fCurve in obj.animation_data.drivers:
        if 'pose.bones["'+ CoMPBone.name +'"].location' == fCurve.data_path:
            fCurveDriver = fCurve.array_index
            break

    #find the driver's bone target and add it to targetBoneNList
    for i in range(len(obj.animation_data.drivers[fCurveDriver].driver.variables)):
        #get target bone name if i is even
        if i % 2 == 0: 
            variable = obj.animation_data.drivers[fCurveDriver].driver.variables[i]
            targetBoneN = variable.targets[0].bone_target

        #get target bone's weight if i is odd
        else: 
            weight = CoMPBone[targetBoneN +" Weight"]
            targetBoneNDict[targetBoneN] = weight

    for pbone in bpy.context.selected_pose_bones:
        if obj == pbone.id_data and pbone != CoMPBone and not pbone.name in targetBoneNDict:
            targetBoneNDict[pbone.name] = float(100) #default weight

    #remove center of mass bone to create a new one that includes the other selected bones
    RemoveCenterOfMass()

    #CoMBoneN is a new CoM bone
    newCoMBoneN = SetupCenterOfMassController(obj, targetBoneNDict)

    newCoMPBone = obj.pose.bones[newCoMBoneN] #we are not using CoMPBone because it got deleted during RemoveCenterOfMass()
    newCoMPBone.name = CoMBoneN #rename the new Center of Mass bone to be the same as the initial Center of Mass.

    newCoMPBone.custom_shape = CoMCustomShape
    newCoMPBone.custom_shape_translation = CoMCustomShapeTranslation
    newCoMPBone.custom_shape_rotation_euler = CoMCustomShapeRotation
    newCoMPBone.custom_shape_scale_xyz = CoMCustomShapeScale
    
    appVersion = bpy.app.version
    if appVersion[0] == 4:
        newCoMPBone.bone.color.palette = CoMBoneColor
        newCoMPBone.color.palette = CoMPBoneColor

    #set the recorded weight to the newly created CoM
    for targetBoneN in targetBoneNDict:
        newCoMPBone[targetBoneN +" Weight"] = targetBoneNDict[targetBoneN]

def RemoveFromCenterOfMass():
    #Removes selected bones from affecting the active center of mass bone

    #save CoM bone's name, custom shape, custom shape transforms and color
    CoMPBone = bpy.context.active_pose_bone
    obj = CoMPBone.id_data
    CoMBoneN = CoMPBone.name

    CoMCustomShape = CoMPBone.custom_shape
    CoMCustomShapeTranslation = CoMPBone.custom_shape_translation
    CoMCustomShapeRotation = CoMPBone.custom_shape_rotation_euler
    CoMCustomShapeScale = CoMPBone.custom_shape_scale_xyz
    
    appVersion = bpy.app.version
    if appVersion[0] == 4:
        CoMBoneColor = CoMPBone.bone.color.palette
        CoMPBoneColor = CoMPBone.color.palette

    #save original list of target bones influencing the CoM bone
    targetBoneNDict = dict()

    #get driver fCurve from name of the CoM bone
    for fCurve in obj.animation_data.drivers:
        if 'pose.bones["'+ CoMPBone.name +'"].location' == fCurve.data_path:
            fCurveDriver = fCurve.array_index
            break

    #find the driver's bone target and add it to targetBoneNList
    for i in range(len(obj.animation_data.drivers[fCurveDriver].driver.variables)):
        #get target bone name if i is even
        if i % 2 == 0: 
            variable = obj.animation_data.drivers[fCurveDriver].driver.variables[i]
            targetBoneN = variable.targets[0].bone_target

        #get target bone's weight if i is odd
        else: 
            weight = CoMPBone[targetBoneN +" Weight"]
            targetBoneNDict[targetBoneN] = weight

    #remove selected bones from targetBoneNDict
    for pbone in bpy.context.selected_pose_bones:
        if pbone.name in targetBoneNDict:
            del targetBoneNDict[pbone.name]

    #remove center of mass bone to create a new one that includes the other selected bones
    RemoveCenterOfMass()

    #CoMBoneN is a new CoM bone
    newCoMBoneN = SetupCenterOfMassController(obj, targetBoneNDict)

    newCoMPBone = obj.pose.bones[newCoMBoneN] #we are not using CoMPBone because it got deleted during RemoveCenterOfMass()
    newCoMPBone.name = CoMBoneN #rename the new Center of Mass bone to be the same as the initial Center of Mass.

    newCoMPBone.custom_shape = CoMCustomShape
    newCoMPBone.custom_shape_translation = CoMCustomShapeTranslation
    newCoMPBone.custom_shape_rotation_euler = CoMCustomShapeRotation
    newCoMPBone.custom_shape_scale_xyz = CoMCustomShapeScale
    
    appVersion = bpy.app.version
    if appVersion[0] == 4:
        newCoMPBone.bone.color.palette = CoMBoneColor
        newCoMPBone.color.palette = CoMPBoneColor

    #set the recorded weight to the newly created CoM
    for targetBoneN in targetBoneNDict:
        newCoMPBone[targetBoneN +" Weight"] = targetBoneNDict[targetBoneN]

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

            #remove the driver's fCurves
            for fCurve in obj.animation_data.drivers:
                if 'pose.bones["'+ boneN +'"].location' == fCurve.data_path:
                    obj.animation_data.drivers.remove(fCurve)

        rotfBake.KeyframeClear(pboneList) #remove keyframes for all bones in pboneList

    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    mirrorX = bpy.context.object.data.use_mirror_x
    bpy.context.object.data.use_mirror_x = False

    for obj in centerOfMassDict:
        boneNList = centerOfMassDict[obj]

        for boneN in boneNList:
            armature = obj.data
            ebone = armature.edit_bones.get(boneN)
            if ebone:
                armature.edit_bones.remove(ebone)
    
    bpy.context.object.data.use_mirror_x = mirrorX

    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')

    for obj in centerOfMassDict:
        boneNList = centerOfMassDict[obj]
        pboneList = list()
        for boneN in boneNList:
            rigState.RemoveConstraint(obj, "Center of Gravity|"+ boneN) #remove center of mass constraint from the object's rig state

