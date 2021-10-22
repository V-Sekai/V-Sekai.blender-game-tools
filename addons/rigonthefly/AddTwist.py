#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . DypsloomBake import DypsloomBakeUtils

class AddTwistUtils:

    def AddTwist (self, context):

        obj = bpy.context.object
        armature = obj.data

        #armature set to pose mode
        bpy.ops.object.mode_set(mode='POSE')

        bonesToTwist = list()
        activePBone = bpy.context.active_pose_bone

        #list pose bones that are diven by the selected controller bones that are not the active controller
        for pbone in bpy.boneSelection:
            
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

            #set aside the active .rig controller and base bone version of the selected controllers
            if pbone == activePBone:
                twistTargetBoneN = baseBoneN + ".rig"
            else:
                twistPbone = obj.pose.bones[baseBoneN]
                bonesToTwist.append(twistPbone)

        #add copy rotation constraints using only the Y axis and using the YZX euler rotation order and have the influence of the constraint increase down the bonesToTwist list
        for i in range(len(bonesToTwist)):
            twistPbone = bonesToTwist[i]

            hasTwistConstraint = False

            for constraint in twistPbone.constraints:
                if constraint.name == "Copy Y Rotation":
                    hasTwistConstraint = True

            if not hasTwistConstraint:
                copyYRotation = twistPbone.constraints.new('COPY_ROTATION')
                copyYRotation.name = "Copy Y Rotation"
                copyYRotation.target = obj
                copyYRotation.subtarget = twistTargetBoneN

                copyYRotation.euler_order = 'YZX'

                copyYRotation.use_x = False
                copyYRotation.use_z = False

                copyYRotation.target_space = 'LOCAL_WITH_PARENT'
                copyYRotation.owner_space = 'LOCAL_WITH_PARENT'

                copyYRotation.influence = (i+1)/(len(bonesToTwist)+1)

        bpy.ops.pose.select_all(action='DESELECT')
        armature.bones[activePBone.name].select = True


