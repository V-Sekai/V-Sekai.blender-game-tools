#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel

class DypsloomBakeUtils:

    @staticmethod
    def DypsloomBake(obj, action, frames, selectedPBones):
        iter = DypsloomBakeUtils.DypsloomBake_iter(obj, action, selectedPBones)
        iter.send(None)

        scene = bpy.context.scene
        frame_back = scene.frame_current

        try:
            for frame in frames:
                scene.frame_set(frame)
                bpy.context.view_layer.update()
                iter.send(frame)
            scene.frame_set(frame_back)
            return iter.send(None)
        except StopIteration: pass

    @staticmethod
    def DypsloomBake_iter(obj, action, selectedPBones):
        """
        def pose_frame_info(obj, selectedPBones):
            matrix = {}
            for pbone in selectedPBones:
                name = pbone.name
                # Get the final transform of the bone in its own local space...
                matrix[name] = obj.convert_space(pose_bone=pbone, matrix=pbone.matrix,
                                                    from_space='POSE', to_space='LOCAL')
            return matrix
        """
        pose_info = []

        while True:
            # Caller is responsible for setting the frame and updating the scene.
            frame = yield None

            # Signal we're done!
            if frame is None:
                break

            #for frame in frames:
            #bpy.context.scene.frame_set(frame)

            matrix = {}
            for pbone in selectedPBones:
                name = pbone.name
                if not pbone.bone.select:
                    continue
                # Get the final transform of the bone in its own local space...
                matrix[name] = obj.convert_space(pose_bone=pbone, matrix=pbone.matrix,
                                                    from_space='POSE', to_space='LOCAL')
            pose_info.append((frame, matrix))

            #pose_info.append((frame, *pose_frame_info(obj, selectedPBones)))

        # Clean (store initial data)
        clean_orig_data = {fcu: {p.co[1] for p in fcu.keyframe_points} for fcu in action.fcurves}

        # Apply transformations to action

        # pose

        def store_keyframe(bone_name, prop_type, fc_array_index, frame, value):
            fc_data_path = 'pose.bones["' + bone_name + '"].' + prop_type
            fc_key = (fc_data_path, fc_array_index)
            if not keyframes.get(fc_key):
                keyframes[fc_key] = []
            keyframes[fc_key].extend((frame, value))


        #For selected pose bones
        for pbone in selectedPBones:
            name = pbone.name

            if bpy.context.scene.smartChannels:
                channelsToBake = selectedPBones[pbone]
            else:
                channelsToBake = [
                    Channel.locationX, 
                    Channel.locationY, 
                    Channel.locationZ, 
                    Channel.quaternionW,
                    Channel.quaternionX,
                    Channel.quaternionY,
                    Channel.quaternionZ,
                    Channel.eulerX,
                    Channel.eulerY,
                    Channel.eulerZ,
                    Channel.scaleX,
                    Channel.scaleY,
                    Channel.scaleZ
                    ]
            
            # Create compatible eulers, quats.
            euler_prev = None
            quat_prev = None
            keyframes = {}

            #store keyframe values for each transform
            for (f, matrix) in pose_info:
                #bpy.context.scene.frame_set(f)
                pbone.matrix_basis = matrix[name].copy()
                
                for arr_idx, value in enumerate(pbone.location):
                    if arr_idx == 0 and Channel.locationX not in channelsToBake: #skip loop if no Channel.locationX found
                        continue
                    if arr_idx == 1 and Channel.locationY not in channelsToBake: #skip loop if no Channel.locationY found
                        continue
                    if arr_idx == 2 and Channel.locationZ not in channelsToBake: #skip loop if no Channel.locationZ found
                        continue
                    store_keyframe(pbone.name, "location", arr_idx, f, value)
                
                rotation_mode = pbone.rotation_mode
                if rotation_mode == 'QUATERNION':
                    if quat_prev is not None:
                        quat = pbone.rotation_quaternion.copy()
                        quat.make_compatible(quat_prev)
                        pbone.rotation_quaternion = quat
                        quat_prev = quat
                        del quat
                    else:
                        quat_prev = pbone.rotation_quaternion.copy()

                    for arr_idx, value in enumerate(pbone.rotation_quaternion):
                        if arr_idx == 0 and Channel.quaternionW not in channelsToBake: #skip loop if no Channel.quaternionW found
                            continue
                        if arr_idx == 1 and Channel.quaternionX not in channelsToBake: #skip loop if no Channel.quaternionX found
                            continue
                        if arr_idx == 2 and Channel.quaternionY not in channelsToBake: #skip loop if no Channel.quaternionY found
                            continue
                        if arr_idx == 3 and Channel.quaternionZ not in channelsToBake: #skip loop if no Channel.quaternionZ found
                            continue
                        store_keyframe(pbone.name, "rotation_quaternion", arr_idx, f, value)

                elif rotation_mode == 'AXIS_ANGLE':
                    for arr_idx, value in enumerate(pbone.rotation_axis_angle):
                        store_keyframe(pbone.name, "rotation_axis_angle", arr_idx, f, value)

                else:  # euler, XYZ, ZXY etc
                    if euler_prev is not None:
                        euler = pbone.rotation_euler.copy()
                        euler.make_compatible(euler_prev)
                        pbone.rotation_euler = euler
                        euler_prev = euler
                        del euler
                    else:
                        euler_prev = pbone.rotation_euler.copy()

                    for arr_idx, value in enumerate(pbone.rotation_euler):
                        if arr_idx == 0 and Channel.eulerX not in channelsToBake: #skip loop if no Channel.eulerX found
                            continue
                        if arr_idx == 1 and Channel.eulerY not in channelsToBake: #skip loop if no Channel.eulerY found
                            continue
                        if arr_idx == 2 and Channel.eulerZ not in channelsToBake: #skip loop if no Channel.eulerZ found
                            continue
                        store_keyframe(pbone.name, "rotation_euler", arr_idx, f, value)

                for arr_idx, value in enumerate(pbone.scale):
                    if arr_idx == 0 and Channel.scaleX not in channelsToBake: #skip loop if no Channel.scaleX found
                        continue
                    if arr_idx == 1 and Channel.scaleY not in channelsToBake: #skip loop if no Channel.scaleY found
                        continue
                    if arr_idx == 2 and Channel.scaleZ not in channelsToBake: #skip loop if no Channel.scaleZ found
                        continue
                    store_keyframe(pbone.name, "scale", arr_idx, f, value)
                

            # Add all keyframe points to the fcurves at once and set their coordinates them after
            # (best performance, inserting keyframes with pbone.keyframe_insert() is about 3 times slower)
            for fc_key, key_values in keyframes.items():
                
                data_path, index = fc_key
                fcurve = action.fcurves.find(data_path=data_path, index=index)
                if fcurve == None:
                    fcurve = action.fcurves.new(data_path, index=index, action_group=pbone.name)

                keyframePointsInterpolationDict = dict() #set aside keyframe point's interpolation's types
                for point in fcurve.keyframe_points:
                    framePoint = point.co[0]
                    interpolation = point.interpolation
                    leftHandle = point.handle_left_type
                    righHandle = point.handle_right_type
                    keyframePointsInterpolationDict[framePoint] = [interpolation, leftHandle, righHandle]
                    if interpolation != 'BEZIER':
                        print("not bezier")
                        print(interpolation)
                
                num_keys = len(key_values) // 2
                keys_to_add = num_keys - len(fcurve.keyframe_points) #find how many keyframe points need to be added
                if keys_to_add > 0: #if the number of keyframe points to add is positive
                    fcurve.keyframe_points.add(keys_to_add) #add the needed keyframe points
                
                if keys_to_add < 0: #if the number of keyframe points to add is negative
                    
                    for point in fcurve.keyframe_points:
                        fcurve.keyframe_points.remove(point) #remove keyframe point
                        
                        if len(fcurve.keyframe_points) == num_keys: #stop removing keyframe points if the amount is equal to the amount needed
                            break
                
                fcurve.keyframe_points.foreach_set('co', key_values)
                
                
                #reset keyframe point to bezier autoclamped
                for point in fcurve.keyframe_points:
                    pointFrame = point.co[0]
                    if pointFrame in keyframePointsInterpolationDict.keys():
                        point.interpolation = keyframePointsInterpolationDict[pointFrame][0]
                        point.handle_left_type = keyframePointsInterpolationDict[pointFrame][1]
                        point.handle_right_type = keyframePointsInterpolationDict[pointFrame][2]

                    else:
                        point.interpolation = 'BEZIER'
                        point.handle_left_type = 'AUTO_CLAMPED'
                        point.handle_right_type = 'AUTO_CLAMPED'

                fcurve.update()

        # Clean

        for fcu in action.fcurves:
            fcu_orig_data = clean_orig_data.get(fcu, set())

            keyframe_points = fcu.keyframe_points
            i = 1
            while i < len(keyframe_points) - 1:
                val = keyframe_points[i].co[1]

                if val in fcu_orig_data:
                    i += 1
                    continue

                val_prev = keyframe_points[i - 1].co[1]
                val_next = keyframe_points[i + 1].co[1]

                if abs(val - val_prev) + abs(val - val_next) < 0.0001:
                    keyframe_points.remove(keyframe_points[i])
                else:
                    i += 1


    @staticmethod
    def AllTranformsChannels(action, frames, targetBoneDataPath, channelsList):
        
        locationXYZList = [Channel.locationX, Channel.locationY, Channel.locationZ]
        rotationQEList = [Channel.quaternionW, Channel.quaternionX, Channel.quaternionY, Channel.quaternionZ, Channel.eulerX, Channel.eulerY, Channel.eulerZ]
        scaleXYZList = [Channel.scaleX, Channel.scaleY, Channel.scaleZ]

        #looking for translation channels
        for i in range(3):
            fcurve = action.fcurves.find(targetBoneDataPath + ".location",index=i)
            if fcurve:
                channelsList.extend(locationXYZList)
                StateUtility.GetFramePointFromFCurve(fcurve, frames)
        #looking for quaternion channels
        for i in range(4):
            fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_quaternion",index=i)
            if fcurve:
                channelsList.extend(rotationQEList)
                StateUtility.GetFramePointFromFCurve(fcurve, frames)
        #looking for euler channels
        for i in range(3):
            fcurve = action.fcurves.find(targetBoneDataPath + ".rotation_euler",index=i)
            if fcurve:
                channelsList.extend(rotationQEList)
                StateUtility.GetFramePointFromFCurve(fcurve, frames)
        #looking for scale channels
        for i in range(3):
            fcurve = action.fcurves.find(targetBoneDataPath + ".scale",index=i)
            if fcurve:
                channelsList.extend(scaleXYZList)
                StateUtility.GetFramePointFromFCurve(fcurve, frames)
    
    