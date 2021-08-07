#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils

class RemoveTwistUtils:

    def RemoveTwist (self, context):

        obj = bpy.context.object

        #armature set to pose mode
        bpy.ops.object.mode_set(mode='POSE')

        bonesToUntwist = list()

        #list pose bones that are diven by the selected controller bones that are not the active controller
        for pbone in bpy.context.selected_pose_bones:
            
            boneName = pbone.name

            baseBoneN = str()
            tempBaseBoneN = str()
            
            #possible suffixes for bone name extensions
            suffixToDelete = ["IK","parent", "child", "world", "top", "rig", "parentCopy", "aimOffset"]
            boneNSplit = boneName.split(".")

            #loop over each word split by '.' in the bone name
            previousMatch = False
            first = True
            for word in boneNSplit:
                match = False
                
                #check if one of the suffixes matches the word 
                for suffix in suffixToDelete:
                    if word == suffix:
                        match = True

                #if match remember word in case next word does not match 
                if match:
                    tempBaseBoneN = tempBaseBoneN + "."+ word
                    previousMatch = True
                else:
                    #if previous was a match use the temp words that was cached 
                    if previousMatch:
                        baseBoneN = baseBoneN + tempBaseBoneN
                        previousMatch = False
                        tempBaseBoneN = str()
                    
                    #the first word does not start with a '.' but the others do
                    if first:
                        baseBoneN = baseBoneN + word
                    else:
                        baseBoneN = baseBoneN +"."+ word

                first = False

            twistPbone = obj.pose.bones[baseBoneN]
            bonesToUntwist.append(twistPbone)

        for pbone in bonesToUntwist:
            for constraint in pbone.constraints:
                if constraint.name == "Copy Y Rotation":
                    pbone.constraints.remove(constraint)