#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . import rigState
from . import importControllerShapes
from mathutils import Matrix, Vector

class RootMotionConstraint:

    def __init__(self):
        print('Root Motion Constraint')

    def CreateRootMotionConstraint(objList):
        
        SetupRootMotionControllers(objList)

    def CreateConstraint(self, obj, constraintInfoList):
        #errorMessageList = list()

        RootMotionConstraint.CreateRootMotionConstraint([obj])

        #if errorMessageList:
        #    return errorMessageList

def SetupRootMotionControllers(objList):
    objBoneNList = list()
    for obj in objList:
        #force edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        armature = obj.data

        #create new bone
        objEBone = armature.edit_bones.new("Root_Motion")
        
        objEBone.use_deform = False
        objEBone.tail = (0,1,0) #tail position
        
        objDimensions = (obj.dimensions[0] + obj.dimensions[1] + obj.dimensions[2])/3
        objWorldScaleV = obj.matrix_world.to_scale()
        objWorldScale = (objWorldScaleV[0] + objWorldScaleV[1] + objWorldScaleV[2])/3
        objSize = objDimensions / objWorldScale
        sizeMultiplyer = objSize / objEBone.length
        objEBone.length = sizeMultiplyer/3

        objBoneN = objEBone.name
        objBoneNList.append(objBoneN)

        for ebone in armature.edit_bones:
            if ebone.parent == None:
                ebone.parent = objEBone

    for obj, objBoneN in zip(objList, objBoneNList):
        #set pose mode
        bpy.ops.object.mode_set(mode='POSE')

        appVersion = bpy.app.version
        if appVersion[0] == 4:
            #assign to objBone a color and the same rotation mode as the armature's object
            objPBone = obj.pose.bones[objBoneN]
            objPBone.bone.color.palette = 'THEME11'
            objPBone.rotation_mode = obj.rotation_mode

        elif appVersion[0] == 3:
            #add pose bone group
            objToBoneGroup = obj.pose.bone_groups.get('RigOnTheFly Object Motion')
            if objToBoneGroup == None:
                objToBoneGroup = obj.pose.bone_groups.new(name="RigOnTheFly Object Motion")
                objToBoneGroup.color_set = 'THEME11'

            #assign to objBone a bone group, custom shape and the same rotation mode as the armature's object
            objPBone = obj.pose.bones[objBoneN]
            objPBone.rotation_mode = obj.rotation_mode
            objPBone.bone_group = objToBoneGroup

        RootMotion_customShape = bpy.context.scene.rotf_rootMotion_customShape
        if RootMotion_customShape == None:
            importControllerShapes.ImportControllerShapes(["RotF_Square"])
            objPBone.custom_shape = bpy.data.objects['RotF_Square']
        else:
            objPBone.custom_shape = bpy.data.objects[RootMotion_customShape.name]

        objPBone.custom_shape_rotation_euler[0] = 1.5708 #rotate custom shape 90 degrees on the X axis

        if obj.animation_data:
            TransferObjectMotionToBone(obj, objPBone)

        objPBone.bone.is_rotf = True #mark as a Rig on the Fly Bone

        #add bone pointer to object bone to mark it as a Root bone
        newPointer = objPBone.bone.rotf_pointer_list.add()
        newPointer.name = "ROOT"
        newPointer.armature_object = obj
        newPointer.bone_name = objPBone.name

        rigState.AddConstraint(
        obj,
        "Root Motion|",
        "Root Motion|",
        "Root Motion",
        [""], #is not used
        [True], #is not used
        [""], #is not used
        [0], #is not used
        [0.0] #is not used
        )

def TransferObjectMotionToBone(obj, objPBone):
    actionList = ObjectActionList(obj) #list all actions used by the object. Current action and actions in it's NLA strips
    #print("transferring object motion to bone")
    boneDataPath = objPBone.path_from_id()
    for action in actionList:
        #copy the armature's object motion to the new bone
        for transformType in ["location","rotation_euler","rotation_quaternion","scale"]:
            index = int()
            if transformType == "rotation_quaternion":
                index = 4
            else:
                index = 3
                
            for i in range(index):
                objFCurve = action.fcurves.find(transformType,index=i)
                #print(objFCurve)
                if not objFCurve:
                    continue
                else:
                    data_path = boneDataPath+"."+transformType
                    fcurve = action.fcurves.find(data_path, index=i)
                    
                    if fcurve == None:
                        fcurve = action.fcurves.new(data_path, index=i, action_group=objPBone.name)
                        
                    num_keys = len(objFCurve.keyframe_points)
                    keys_to_add = num_keys - len(fcurve.keyframe_points) #find how many keyframe points need to be added
                    fcurve.keyframe_points.add(keys_to_add) #add the needed keyframe points
                    
                    for key in range(num_keys):
                        fcurve.keyframe_points[key].co = objFCurve.keyframe_points[key].co
                        #print(data_path)
                        #print(i)
                        #if transformType == "location" and obj.delta_scale != Vector((1,1,1)):

                        
                        fcurve.keyframe_points[key].handle_left = objFCurve.keyframe_points[key].handle_left
                        #print(fcurve.keyframe_points[key].handle_left)
                        
                        fcurve.keyframe_points[key].handle_right = objFCurve.keyframe_points[key].handle_right
                        #print(fcurve.keyframe_points[key].handle_right)
                #remove fcurve on armature object
                action.fcurves.remove(objFCurve)

    #zero armature's object transforms
    obj.location = (0,0,0)
    obj.rotation_euler = (0,0,0)
    obj.rotation_quaternion = (1,0,0,0)
    obj.scale = (1,1,1)

def RootMotion():
    objList = list()
    for obj in bpy.context.selected_objects:
        if obj.type == 'ARMATURE':
            objList.append(obj)

            if obj.delta_location != Vector((0,0,0)) or obj.delta_rotation_euler!= Vector((0,0,0)) or obj.delta_rotation_quaternion!= Vector((0,0,0,0)) or obj.delta_scale != Vector((1,1,1)):
                errorMessage = "Objects uses delta transforms, result will be unnexpected"

    SetupRootMotionControllers(objList)
    return errorMessage

def RemoveRootMotion():
    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')
    
    objList = list()
    rootBoneNList = list()
    for rootPBone in bpy.context.selected_pose_bones:
        if 'ROOT' in rootPBone.bone.rotf_pointer_list:
            obj = rootPBone.id_data
            objList.append(obj)
            rootBoneNList.append(rootPBone.name)

            rootBoneDataPath = rootPBone.path_from_id()
            
            actionList = ObjectActionList(obj) #list all actions used by the object. Current action and actions in it's NLA strips

            for action in actionList:
                #copy the armature's object motion to the new bone
                for transformType in ["location","rotation_euler","rotation_quaternion","scale"]:
                    index = int()
                    if transformType == "rotation_quaternion":
                        index = 4
                    else:
                        index = 3
                        
                    for i in range(index):
                        data_path = rootBoneDataPath+"."+transformType
                        fcurve = action.fcurves.find(data_path, index=i)
                        if not fcurve:
                            continue
                        else:
                            objFCurve = action.fcurves.find(transformType,index=i)
                            
                            if objFCurve == None:
                                objFCurve = action.fcurves.new(transformType, index=i, action_group="Object Transforms")
                                
                            num_keys = len(fcurve.keyframe_points)
                            keys_to_add = num_keys - len(objFCurve.keyframe_points) #find how many keyframe points need to be added
                            objFCurve.keyframe_points.add(keys_to_add) #add the needed keyframe points
                            
                            for key in range(num_keys):
                                objFCurve.keyframe_points[key].co = fcurve.keyframe_points[key].co
                                objFCurve.keyframe_points[key].handle_left = fcurve.keyframe_points[key].handle_left
                                objFCurve.keyframe_points[key].handle_right = fcurve.keyframe_points[key].handle_right
                        
                        #remove fcurve on armature object
                        action.fcurves.remove(fcurve)

    #set to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    for obj, rootBoneN in zip(objList, rootBoneNList):
        ebones = obj.data.edit_bones
        rootEBone = ebones.get(rootBoneN)
        if rootEBone:
            ebones.remove(rootEBone)

    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')

    for obj in objList:
        rigState.RemoveConstraint(obj, "Root Motion|")

def ObjectActionList(obj):
    #list all actions used by the object. Current action and actions in it's NLA strips
    actionList = list()
    #initialAction = None
    if obj.animation_data.action:
        actionList.append(obj.animation_data.action)
        
    for nlaTrack in obj.animation_data.nla_tracks: #go through object's nla tracks
        for actionStrip in nlaTrack.strips: #go through the strips in it's nla tracks
            action = actionStrip.action
            if action not in actionList: #if action used in strips of the nla tracks are not yet in actionList
                actionList.append(action) #add the action name to actionList

    return actionList