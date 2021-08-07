#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
import math
from . Utility import StateUtility

class IKLimbPoleAngleUtils:

    def GetNextAngle (currentAngle):
        pole_angle0 = 0 #0°
        pole_angle90 = math.pi/2 #90°
        pole_angle180 = math.pi #180°
        pole_angle270 = -math.pi/2 #-90°

        if currentAngle < pole_angle0 + math.pi/4 and currentAngle > pole_angle0 - math.pi/4:
            return pole_angle270

        if currentAngle < pole_angle90 + math.pi/4 and currentAngle > pole_angle90 - math.pi/4:
            return pole_angle0

        if abs(currentAngle) > pole_angle180 - math.pi/4:
            return pole_angle90

        if currentAngle < pole_angle270 + math.pi/4 and currentAngle > pole_angle270 - math.pi/4:
            return pole_angle180

        return pole_angle0

    def IKLimbPoleAngle (self, context):
        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #add bone name to selectedBonesN to have it's generated IK controller selected at the end of the script
        selectedBonesN = list()
        for bone in bpy.context.selected_pose_bones:
            selectedBonesN.append(bone.name)

        for selectedIKBone in selectedBonesN:
            
            selectedFKBone = selectedIKBone.replace(".IK.rig",".rig")
            #find the rig bone with IK constraints
            FKBone = bpy.context.object.pose.bones[selectedFKBone].parent.name

            currentAngle = bpy.context.object.pose.bones[FKBone].constraints['IK'].pole_angle

            nextAngle = IKLimbPoleAngleUtils.GetNextAngle(currentAngle)

            bpy.context.object.pose.bones[FKBone].constraints['IK'].pole_angle = nextAngle

