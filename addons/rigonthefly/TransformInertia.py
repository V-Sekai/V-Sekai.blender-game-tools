#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
import mathutils
from . Utility import StateUtility


class TransformDataUtils:
    @staticmethod
    def SetTranslation(bone, newValue):
        bone.location = newValue

    @staticmethod
    def GetTranslation(bone):
        return bone.location.copy()

    @staticmethod
    def SetRotation(bone, newValue):
        bone.rotation_euler = mathutils.Euler(newValue)

    @staticmethod
    def GetRotation(bone):
        euler = bone.rotation_euler.copy()
        rotationVector = mathutils.Vector([euler.x, euler.y, euler.z])
        return rotationVector
    
    @staticmethod
    def SetScale(bone, newValue):
        bone.scale = newValue

    @staticmethod
    def GetScale(bone):
        return bone.scale.copy()

class TransformInertiaUtils:        

    def TransformInertia(self, context, inertia, frameRange, keyingSet, getTransformData, setTransformData):
        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #save current frame to return to it by the end of the script
        currentFrame = bpy.context.scene.frame_current

        for bone in bpy.context.selected_pose_bones:
            for frame in frameRange:
                bpy.context.scene.frame_set(frame)
                bpy.ops.anim.keyframe_insert_menu(type=keyingSet)
                
            for frame in frameRange:
                #sets current frame to be 2 frame before current frameRange to get previous transform values 
                bpy.context.scene.frame_set(frame-2)
                valueM2 = getTransformData(bone)


                #sets current frame to 1 frame before current frameRange to get previous transform values
                bpy.context.scene.frame_set(frame-1)
                valueM1 = getTransformData(bone)

                #sets current frame
                bpy.context.scene.frame_set(frame)

                #axisValue = (X0 - (2*XM1 -XM2))*I + 2*XM1 -XM2
                value0 = getTransformData(bone)
                #change current frame transform to work with inertia
                newValue = (value0 - (2 * valueM1 - valueM2)) * (1 - inertia) + 2 * valueM1 - valueM2

                setTransformData(bone,newValue)

                bpy.ops.anim.keyframe_insert_menu(type= keyingSet)

        #return to initial frame
        bpy.context.scene.frame_set(currentFrame)