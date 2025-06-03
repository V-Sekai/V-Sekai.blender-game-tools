#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

from decimal import Clamped
import bpy
import math

def Dynamics(transformType, pboneList):
    context = bpy.context
    scene = context.scene

    frameStart = scene.rotf_dynamics_start
    frameEnd = scene.rotf_dynamics_end + 1
    frameRange = list(range(frameStart, frameEnd))

    keyDynamics(frameRange, transformType, pboneList)

def keyDynamics(frameRange, transformType, pboneList):
    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    #save current frame to return to it by the end of the script
    scene = bpy.context.scene

    for pbone in pboneList:
        if pbone.id_data.animation_data == None:
            continue
        if pbone.id_data.animation_data.action == None:
            continue
        action = pbone.id_data.animation_data.action
        
        fcurvesList = findFCurves(action, transformType, pbone)

        t = 1/scene.render.fps

        for fcurve in fcurvesList:
            newKeyframesList = findNewKeyframesList(fcurve, frameRange, t)

            #make the newKeyframesList new values converge to the initial value of the end frame
            newKeyframesList = convergeToEndFrame(fcurve, newKeyframesList)

            for f, newValue in newKeyframesList:
                fcurve.keyframe_points.insert(f, newValue)

            fcurve.update()

def findFCurves(action, transformType, pbone):
    fcurvesList = list()
    dataPath = pbone.path_from_id()
    if transformType == "selection": #add only the selected fcurves to fcurveList
        for fcurve in action.fcurves:
            if fcurve.select:
                fcurvesList.append(fcurve)

    else: 
        if transformType == "rotation": #find the right rotation mode datapath
            dataPath += "." + transformType + pbone.rotation_mode.lower()
            if pbone.rotation_mode.lower() == "quaternion":
                arr_idx = 4
            else:
                arr_idx = 3
        else:
            dataPath += "." + transformType #find the right datapath
            arr_idx = 3

        for i in range(arr_idx): #add the fcurves from the dataPath to fcurvesList
            fcurve = action.fcurves.find(dataPath, index =i)
            if fcurve:
                fcurvesList.append(fcurve)
    
    return fcurvesList

def findNewKeyframesList(fcurve, frameRange, t):
    #dynamics taken from this video https://www.youtube.com/watch?v=KPoeNZZ6H4s
    newKeyframesList = list()
    
    scene = bpy.context.scene

    f = scene.rotf_frequency
    z = scene.rotf_damping
    r = scene.rotf_response

    k1 = z/(math.pi*f)
    k2 = 1/((2*math.pi*f)*(2*math.pi*f))
    k3 = r*z/(2*math.pi*f)

    firstFrame = frameRange[0]
    xp = fcurve.evaluate(firstFrame-1)
    x = fcurve.evaluate(firstFrame)

    y = x
    yd = (x - xp)/t

    for f in frameRange:
        y = y + t * yd

        k2_stable = max(k2, 1.1 * (t*t/4 + t*k1/2)) #clamp k2 to guarantee stability
        xd = (x - xp)/t
        yd = yd + t * (x + k3*xd - y - k1*yd)/k2_stable
        
        newKeyframesList.append([f, y])

        xp = fcurve.evaluate(f)
        x = fcurve.evaluate(f+1)

    return newKeyframesList

def convergeToEndFrame(fcurve, newKeyframesList):
    scene = bpy.context.scene
    blendFrame = scene.rotf_blend_frame

    for i, fy in enumerate(newKeyframesList):
        f = fy[0]
        y = fy[1]

        if f == blendFrame:
            startBlendIndex = i

        if f >= blendFrame:
            x = fcurve.evaluate(f) #current frame value
            y = y #new frame value from newKeyframesList
            blendFactor=(i - startBlendIndex)/(len(newKeyframesList)- 1 - startBlendIndex) #blend factor
            blendFactor=easeInOutQuad(blendFactor)
            blendedY = (blendFactor * x) + ((1-blendFactor) * y) #lerp blend
            newKeyframesList[i] = [f, blendedY]

    return newKeyframesList

def easeInOutQuad (x):
    if x < 0.5:
        return 2 * x * x
    else:
        return 1 - pow(-2 * x + 2, 2) / 2
