#########################################
#######       Rig On The Fly      #######
####### Copyright © 2022 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import math
import bpy
from . import rotfBake

def KeyAsActive():
    bpy.ops.object.mode_set(mode='POSE') #force pose mode
    scene = bpy.context.scene

    activePBone = bpy.context.active_pose_bone
    activePath = activePBone.path_from_id() #active bone's fcurve path
    activeObj = activePBone.id_data #pbone's object
    activeAction = activeObj.animation_data.action #current action

    #look through the active bone's keys to find the frames to key
    framesToKeyList = list()
    for transformType, axis in [[".location", 3],[".rotation_quaternion", 4],[".rotation_euler",3],[".scale",3]]:
        for axe in range(axis):
            fcurve = activeAction.fcurves.find(activePath + transformType,index=axe)
                
            if fcurve:
                if fcurve.keyframe_points:
                    for point in fcurve.keyframe_points:
                        if scene.rotf_selected_keys:
                            if point.select_control_point: #check if control points are selected
                                frameValue = point.co[0]
                                if frameValue not in framesToKeyList: #add frame coordinate to the framesToKeyList it has not yet been added
                                    framesToKeyList.append(frameValue)
                        else:
                            frameValue = point.co[0]
                            if frameValue not in framesToKeyList: #add frame coordinate to the framesToKeyList it has not yet been added
                                framesToKeyList.append(frameValue)

    pbonesToKeyList = bpy.context.selected_pose_bones
    pbonesToKeyList.remove(activePBone)
    for pbone in pbonesToKeyList:
        #check the options to see which channel types should be keyed
        channelssToKeyList = list()
        if scene.rotf_key_location:
            channelssToKeyList.append(["location", 3])
        if scene.rotf_key_rotation:
            if pbone.rotation_mode == 'QUATERNION':
                channelssToKeyList.append(["rotation_quaternion", 4])
            else:
                channelssToKeyList.append(["rotation_euler", 3])
        if scene.rotf_key_scale:
            channelssToKeyList.append(["scale", 3])

        channelsList = list() #list of channels to key
        for f in framesToKeyList:
            for prop_type, numberOfChannels in channelssToKeyList:
                if scene.rotf_key_available:
                    obj = pbone.id_data
                    if obj.animation_data.action:
                        action = obj.animation_data.action
                        dataPath = pbone.path_from_id()
                        for arr_idx in range(numberOfChannels):
                            fcurve = action.fcurves.find(dataPath + "." + prop_type,index=arr_idx)
                            if fcurve:
                                pbone.keyframe_insert(prop_type, index=arr_idx, frame=f, group=pbone.name, options=set())

                else:
                    pbone.keyframe_insert(prop_type, index=-1, frame=f, group=pbone.name, options=set())
