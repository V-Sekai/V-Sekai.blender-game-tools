#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy

def RemoveAllRotFConstraints(pboneList):
    #force pose mode
    bpy.ops.object.mode_set(mode='POSE')

    for pbone in pboneList:
        obj = pbone.id_data

        rotfConstraints = list()
        for constraint in pbone.constraints:
            if "RotF" in constraint.name:
                rotfConstraints.append(constraint)

        #if there is no animation data on the object, keeptransform from the constraint
        if not obj.animation_data:
            # Get the matrix in world space.
            #bone = context.pose_bone
            mat = obj.matrix_world @ pbone.matrix
        for constraint in rotfConstraints:
            constraint.influence = 0.0
        #set matrix
        if not obj.animation_data:
            pbone.matrix = obj.matrix_world.inverted() @ mat

        while rotfConstraints:
            pbone.constraints.remove(rotfConstraints[0])
            rotfConstraints.remove(rotfConstraints[0])

