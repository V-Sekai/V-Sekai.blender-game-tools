#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import os
import bpy
import numpy
import json
from json import JSONEncoder
from mathutils import Matrix, Euler, Vector
from bpy.props import StringProperty
from . import constraintLibrary
from . import rotationModeAndRelations

main_dir = os.path.dirname(__file__)
delete_files_on_startup_file = os.path.join(main_dir, "delete_files_on_startup.txt")


class RigStatesManager():
    def __init__(self,  type="__RigStatesManager__", rigStates=dict()):
        self.type = type
        self.rigStates = rigStates
        self.stringTest = StringProperty(default='')
    def ToJSON(self):
        return self.__dict__
    def AddConstraint(self, objectName, constraint):
        if objectName not in self.rigStates:
            self.rigStates[objectName] = RigState()
        self.rigStates[objectName].constraints.append(constraint)
    
    def RemoveConstraint(self, objectName, constraint):
        if objectName not in self.rigStates:
            return
        self.rigStates[objectName].constraints.remove(constraint)

class RigState():
    def __init__(self, type="__RigState__", constraints=list()):
        self.type = type
        self.constraints = constraints
        #self.bonesState list()
    def ToJSON(self):
        return self.__dict__
    def ApplyConstraints(self):
        for constraint in self.constraints:
            constraint.Apply()

class RigStateSerializer():

    def SerializeConstraints(obj):

        constraintsDict = dict()

        objRigState = obj.rotf_rig_state

        for constraint in objRigState:
            constraintInfoDict = dict()

            constraintInfoDict["full_name"] = constraint["full_name"]
            constraintInfoDict["constraint_type"] = constraint["constraint_type"]
            
            boneNameList = list()
            for i in range(len(constraint["bone_list"])):
                boneNameList.append(constraint['bone_list'][i]["name"])

            boolValueList = list()
            for i in range(len(constraint["bool_list"])):
                boolValueList.append(constraint['bool_list'][i]["value"])

            stringList = list()
            for i in range(len(constraint["string_list"])):
                stringList.append(constraint['string_list'][i]["string"])

            intList = list()
            for i in range(len(constraint["int_list"])):
                intList.append(constraint['int_list'][i]["int"])

            floatList = list()
            for i in range(len(constraint["float_list"])):
                floatList.append(constraint['float_list'][i]["float"])
            
            constraintInfoDict["bone_list"] = boneNameList
            constraintInfoDict["bool_list"] = boolValueList
            constraintInfoDict["string_list"] = stringList
            constraintInfoDict["int_list"] = intList
            constraintInfoDict["float_list"] = floatList

            constraintsDict[constraint["name"]] = constraintInfoDict
        return constraintsDict

    def SerializeBoneGroups(obj):
        boneGroupsDict = dict()
        boneGroupsDict["group_name"] = list()
        boneGroupsDict["group_color_set"] = list()
        if len(obj.pose.bone_groups):
            for boneGroup in obj.pose.bone_groups:
                boneGroupsDict["group_name"].append(boneGroup.name)
                boneGroupsDict["group_color_set"].append(boneGroup.color_set)

        return boneGroupsDict

    def SerializeBoneStates(obj):
        boneStatesDict = dict()

        for pbone in obj.pose.bones:
            boneDict = dict()

            boneDict["rotation_mode"] = pbone.rotation_mode
            boneDict["use_inherit_rotation"] = pbone.bone.use_inherit_rotation
            boneDict["use_inherit_scale"] = pbone.bone.use_inherit_scale

            
            if pbone.bone_group:
                boneDict["bone_group"] = pbone.bone_group.name
            else:
                boneDict["bone_group"] = ""

            if pbone.custom_shape:
                boneDict["custom_shape"] = pbone.custom_shape.name
                boneDict["custom_shape_scale"] = [pbone.custom_shape_scale_xyz[0], pbone.custom_shape_scale_xyz[1], pbone.custom_shape_scale_xyz[2]]
                if pbone.custom_shape_transform:
                    boneDict["custom_shape_transform"] = pbone.custom_shape_transform.name
                else:
                    boneDict["custom_shape_transform"] = ""
            else:
                boneDict["custom_shape"] = ""
                boneDict["custom_shape_scale"] = ""

            layerList = list()
            layerInt = 0X0
            for layer in pbone.bone.layers:
                layerList.append(layer)
                layerInt = (layerInt << 1) + (1 if layer else 0)
            boneDict["layers"] = '{:032b}'.format(layerInt)

            if pbone.bone.is_rotf and pbone.keys():
                keyList = pbone.keys()
                boneDict["center_of_mass"] = list()
                for influenceKey in keyList:
                    boneDict["center_of_mass"].append([influenceKey, pbone[influenceKey]])

            boneStatesDict[pbone.name] = boneDict

        return boneStatesDict
    
    def SerializeRigState():
        obj = bpy.context.object #active object

        rigStateDict = dict()

        rigStateDict["constraints"] = RigStateSerializer.SerializeConstraints(obj)
        rigStateDict["bone_groups"] = RigStateSerializer.SerializeBoneGroups(obj)
        rigStateDict["bone_states"] = RigStateSerializer.SerializeBoneStates(obj)
        return rigStateDict

    def DeserializeRigState(rigStateDict):
        obj = bpy.context.object
        objectRigState = obj.rotf_rig_state

        constraints = rigStateDict["constraints"]
        boneGroups = rigStateDict["bone_groups"]
        boneStates = rigStateDict["bone_states"]

        constraintsLoadedResult = dict()
        constraintsLoadedResult['Success'] = True
        constraintsLoadedResult['Result'] = list()

        if constraints:
            constraintInfoList = list() #list of successive constraint infos using the same constraint type
            previousConstraintType = None
            for constraintName, constraintInfo in constraints.items():
                #check if constraint is already in object's rotf_rig_state before adding it
                if constraintName not in objectRigState:
                    if constraintInfo['constraint_type'] == previousConstraintType: #check if current constraint type is the same as previousConstraintType
                        constraintInfoList.append(constraintInfo)
                    elif len(constraintInfoList) > 0:
                        CreateConstraint(constraintsLoadedResult,constraintInfoList)
                        constraintInfoList = [constraintInfo]
                    else:
                        constraintInfoList = [constraintInfo]

                    previousConstraintType = constraintInfo['constraint_type']            
            
            #go through the last constraint of the constraints list
            #check if constraint is already in object's rotf_rig_state before adding it
            if constraintName not in objectRigState:
                if constraintInfo['constraint_type'] != previousConstraintType: #check if current constraint type is not the same as previousConstraintType
                    CreateConstraint(constraintsLoadedResult,constraintInfoList)
                    constraintInfoList = [constraintInfo]
            CreateConstraint(constraintsLoadedResult,constraintInfoList)

        #if len(errorMessageList) > 0:
        #    return [{'WARNING'}, errorMessageList]
        
        LoadBoneGroups(boneGroups)

        LoadBoneStates(constraintsLoadedResult,boneStates)

        constraintsLoadedResult['Success']
                
        #if not constraintsLoadedResult['Success'] :
        return constraintsLoadedResult

def CreateConstraint(constraintsLoadedResult,constraintInfoList):
    print("Creating Constraint")
    result = constraintLibrary.ConstraintLibrary.CreateConstraint(constraintInfoList)
    print(result)
    if result != None:
        constraintsLoadedResult['Success'] = False
        constraintsLoadedResult['Result'].extend(result)
        print(constraintsLoadedResult['Result'])

def AddConstraint(obj, name, fullName, constraintType, boneList, boolList, stringList, intList, floatList):
    constraint = obj.rotf_rig_state.add()
    constraint.name = name
    constraint.full_name = fullName
    constraint.constraint_type = constraintType
    
    for boneName in boneList:
        boneProperty = constraint.bone_list.add()
        boneProperty.name = boneName

    for value in boolList:
        boolProperty = constraint.bool_list.add()
        boolProperty.value = value
    
    for string in stringList:
        stringProperty = constraint.string_list.add()
        stringProperty.string = string
    
    for int in intList:
        intProperty = constraint.int_list.add()
        intProperty.int = int
    
    for float in floatList:
        floatProperty = constraint.float_list.add()
        floatProperty.float = float

def RemoveConstraint(obj, name):
    for i, constraint in enumerate(obj.rotf_rig_state):
        if constraint.name == name:
            obj.rotf_rig_state.remove(i)
            return

def SaveRigState(file_path):

    rigState = RigStateSerializer.SerializeRigState()
    jsonString = json.dumps(rigState, indent=4)

    with open(file_path, 'w', encoding="utf8") as outfile:
        outfile.write(jsonString)
        #json.dump(jsonString, outfile, ensure_ascii=False, indent=4)

    return file_path

def LoadRigState(file_path):

    with open(file_path) as json_file:
        rigStateDict = json.load(json_file)

    result = RigStateSerializer.DeserializeRigState(rigStateDict)
    return result

def LoadBoneGroups(boneGroups):
    obj = bpy.context.object
    
    for groupName, colorSet in zip(boneGroups['group_name'], boneGroups["group_color_set"]):
        if groupName not in obj.pose.bone_groups:
            boneGroup = obj.pose.bone_groups.new(name = groupName)
            boneGroup.color_set = colorSet

def LoadBoneStates(constraintsLoadedResult, boneStates):
    missingBoneList = list()
    obj = bpy.context.object

    boneNamesDict = dict()
    boneNamesDict[obj] = list()
    RotationModeAndRelationsDict = dict()
    RotationModeAndRelationsDict[obj] = list()
    inheritRotationDict = dict()
    inheritRotationDict[obj] = list()
    inheritScaleDict = dict()
    inheritScaleDict[obj] = list()

    for boneName in boneStates:
        rotation_mode = boneStates[boneName]['rotation_mode']
        use_inherit_rotation = boneStates[boneName]['use_inherit_rotation']
        use_inherit_scale = boneStates[boneName]['use_inherit_scale']
        bone_group_name = boneStates[boneName]['bone_group']
        custom_shape_name = boneStates[boneName]['custom_shape']
        custom_shape_scale_xyz = boneStates[boneName]['custom_shape_scale']
        layers = boneStates[boneName]['layers']
        centerOfMassInfluence = boneStates[boneName].get('center_of_mass')
    
        pbone = obj.pose.bones.get(boneName)
        if pbone:
            if pbone.rotation_mode != rotation_mode or pbone.bone.use_inherit_rotation != use_inherit_rotation or pbone.bone.use_inherit_scale != use_inherit_scale:
                boneNamesDict[obj].append(pbone.name)
                RotationModeAndRelationsDict[obj].append(rotation_mode)
                inheritRotationDict[obj].append(use_inherit_rotation)
                inheritScaleDict[obj].append(use_inherit_scale)

            if bone_group_name != "":
                pbone.bone_group = obj.pose.bone_groups[bone_group_name]
            if custom_shape_name != "":
                pbone.custom_shape = bpy.data.objects[custom_shape_name]
            if custom_shape_scale_xyz != "":
                pbone.custom_shape_scale_xyz = Vector(numpy.array(custom_shape_scale_xyz)) #convert list into vector 3
            for layerIndex, inLayer in enumerate(layers):
                if inLayer == "0":
                    pbone.bone.layers[layerIndex] = False
                if inLayer == "1":
                    pbone.bone.layers[layerIndex] = True

            if centerOfMassInfluence:
                for influenceKeyValuePair in centerOfMassInfluence:
                    key = influenceKeyValuePair[0]
                    value = influenceKeyValuePair[1]
                    pbone[key] = value
        else:
            missingBoneList.append(boneName)

    rotationModeAndRelations.ChangeRotationAndScaleMode(boneNamesDict, RotationModeAndRelationsDict, inheritRotationDict, inheritScaleDict)

    if missingBoneList:
        constraintsLoadedResult['Success'] = False
        message = "Bone State|Bone not found: "+ ", ".join(missingBoneList)
        print(message)
        return [message]
