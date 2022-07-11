#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . import rigState
from . import bakeRig

def Setup(objectList):
    frame = bpy.context.scene.frame_current
    for obj in objectList:
        animData = obj.animation_data

        #SAVE RIG STATE
        rigStateDict = rigState.RigStateSerializer.SerializeRigState()
        obj.rotf_sfp_rig_state = str(rigStateDict)

        #copy pose
        pboneMatrixList = dict()
        for pbone in obj.pose.bones:
            pboneMatrixList[pbone] = pbone.matrix
        
        #save nla state
        nla_state = obj.rotf_sfp_nla_state.add()
        if animData.action:
            nla_state.action_name = animData.action.name
        else:
            nla_state.action_name = ""
        nla_state.action_extrapolation = animData.action_extrapolation
        nla_state.action_blend_type = animData.action_blend_type
        nla_state.action_influence = animData.action_influence

        nla_tracks_mute_string = str() 
        for track in animData.nla_tracks:
            if track.mute:
                nla_tracks_mute_string += "1"
            else:
                nla_tracks_mute_string += "0"

                #track.mute = True #mute all tracks
        nla_state.nla_tracks_mute = nla_tracks_mute_string

        #SETUP SINGLE FRAME ACTION

        #create single frame pose action
        action = bpy.data.actions.new(obj.name +' SFP')
        animData.action = action

        #active track extrapolation "Nothing" 
        animData.action_extrapolation = 'NOTHING'
        animData.action_blend_type = 'REPLACE'
        animData.action_influence = 1

        #paste pose in case adding the single frame pose action changed it
        for pbone in pboneMatrixList:
            pbone.matrix = pboneMatrixList[pbone]

        #key current pose
        for pbone in obj.pose.bones:
            bone_name = pbone.name
            for prop_type in ["location","rotation_euler","scale"]:
                prop_values = list()

                if prop_type == "location":
                    prop_values = [value for value in pbone.location]
                if prop_type == "rotation_euler":
                    prop_values = [value for value in pbone.rotation_euler]
                if prop_type == "scale":
                    prop_values = [value for value in pbone.scale]

                for index, value in enumerate(prop_values):
                    data_path = 'pose.bones["' + bone_name + '"].' + prop_type
                    fcurve = action.fcurves.new(data_path, index=index, action_group=pbone.name)
                    fcurve.keyframe_points.add(1)

                    fcurve.keyframe_points[0].co.x = frame
                    fcurve.keyframe_points[0].co.y = value

            prop_values = [value for value in pbone.rotation_quaternion]
            for index, value in enumerate(prop_values):
                fcurve = action.fcurves.new('pose.bones["'+bone_name+'"].'+"rotation_quaternion", index=index, action_group=pbone.name)
                fcurve.keyframe_points.add(1)
                
                fcurve.keyframe_points[0].co.x = frame
                fcurve.keyframe_points[0].co.y = value

def SaveSFPRigState(obj):
    while obj.rotf_sfp_rig_state: #reset the single frame pose rig state
        obj.rotf_sfp_rig_state = ""

    for constraint in obj.rotf_rig_state: #have the single frame pose rig state save the initial rig state
        sfp_constraint = obj.rotf_sfp_rig_state.add()
        sfp_constraint.name = constraint.name
        sfp_constraint.full_name = constraint.full_name
        sfp_constraint.constraint_type = constraint.constraint_type
        
        for bone in constraint.bone_list:
            boneProperty = sfp_constraint.bone_list.add()
            boneProperty.name = bone.name

        for value in constraint.bool_list:
            boolProperty = sfp_constraint.bool_list.add()
            boolProperty.value = value['value']
        
        for string in constraint.string_list:
            stringProperty = sfp_constraint.string_list.add()
            stringProperty.string = string['string']
        
        for int in constraint.int_list:
            intProperty = sfp_constraint.int_list.add()
            intProperty.int = int['int']
        
        for float in constraint.float_list:
            floatProperty = sfp_constraint.float_list.add()
            floatProperty.float = float['float']

def Apply(objectList):
    frame = bpy.context.scene.frame_current
    bakeRig.BakeRig(objectList)
    for obj in objectList:
        #RETURN TO INITIAL RIG STATE
        sfpRigState = eval(obj.rotf_sfp_rig_state)
        rigState.RigStateSerializer.DeserializeRigState(sfpRigState)

        #set aside animData and sfpAction for later use
        animData = obj.animation_data
        sfpAction = animData.action

        #COPY POSE
        pboneMatrixList = dict()
        for pbone in obj.pose.bones:
            pboneMatrixList[pbone] = pbone.matrix.copy()

        #RETURN TO INITIAL NLA STATE
        nlaState = obj.rotf_sfp_nla_state['']

        actionName = nlaState.action_name    
        action = bpy.data.actions[actionName]
        animData.action = action

        animData.action_extrapolation = nlaState.action_extrapolation
        animData.action_blend_type = nlaState.action_blend_type
        animData.action_influence = nlaState.action_influence

        #return nla tracks to initial mute state
        for i, track in zip(nlaState.nla_tracks_mute, animData.nla_tracks):
            if i == "0":
                track.mute = False
            if i == "1":
                track.mute = True

        #PASTE POSE
        for pbone in pboneMatrixList:
            pbone.matrix = pboneMatrixList[pbone]

        #list visible bones to key
        visibleLayers = list()
        for i, layer in enumerate(obj.data.layers):
            if layer:
                visibleLayers.append(i)

        #key current pose     
        for pbone in obj.pose.bones:
            bone = pbone.bone
            boneName = bone.name

            #check if bone is in a visible layer
            pboneIsInVisibleLayer = False
            for i in visibleLayers:
                if bone.layers[i]:
                    pboneIsInVisibleLayer = True

            if pboneIsInVisibleLayer and not bone.hide: #check if bone is visible
                #key current pose
                rotation_data_path = "rotation_"+pbone.rotation_mode.lower()
                for prop_type in ["location", rotation_data_path,"scale"]:
                    pbone.keyframe_insert(prop_type, index=-1, frame=bpy.context.scene.frame_current, group=boneName, options=set())

        #delete sfp action
        bpy.data.actions.remove(sfpAction)

        obj.rotf_sfp_rig_state = ""
        obj.rotf_sfp_nla_state.remove(0)