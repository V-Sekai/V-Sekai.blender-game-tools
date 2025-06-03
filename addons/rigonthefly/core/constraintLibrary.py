#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy

from . import orient
from . import extraBone
from . import centerOfMass
from . import rootMotion
from . import rotationDistribution
from . import ikLimb
from . import ikStretch
from . import worldSpace
from . import aimSpace
from . import aimOffsetSpace
from . import parentSpace
from . import parentOffsetSpace
from . import reverseHierarchySpace
from . import simpleCopyTransforms
from . import simpleAim
from importlib import reload
reload(orient)
reload(extraBone)
reload(centerOfMass)
reload(rootMotion)
reload(ikLimb)
reload(ikStretch)
reload(worldSpace)
reload(aimSpace)
reload(aimOffsetSpace)
reload(parentSpace)
reload(parentOffsetSpace)
reload(reverseHierarchySpace)
reload(simpleCopyTransforms)
reload(simpleAim)

class ConstraintLibrary:
    constraintCreators = dict()
    constraintCreators["Orient"] = orient.OrientConstraint()
    constraintCreators["Center of Gravity"] = centerOfMass.CenterOfMassConstraint()
    constraintCreators["Root Motion"] = rootMotion.RootMotionConstraint()
    constraintCreators["Rotation Distribution"] = rotationDistribution.RotationDistributionConstraint()
    constraintCreators["IK Limb"] = ikLimb.IKLimbConstraint()
    constraintCreators["IK Stretch"] = ikStretch.IKStretchConstraint()
    constraintCreators["World Space"] = worldSpace.WorldSpaceConstraint()
    constraintCreators["Aim Space"] = aimSpace.AimSpaceConstraint()
    constraintCreators["Aim Offset Space"] = aimOffsetSpace.AimOffsetSpaceConstraint()
    constraintCreators["Parent Space"] = parentSpace.ParentSpaceConstraint()
    constraintCreators["Parent Offset Space"] = parentOffsetSpace.ParentOffsetSpaceConstraint()
    constraintCreators["Reverse Hierarchy Space"] = reverseHierarchySpace.ReverseHierarchySpaceConstraint()
    constraintCreators["Simple Copy Transforms"] = simpleCopyTransforms.SimpleCopyTransformsConstraint()
    constraintCreators["Simple Aim"] = simpleAim.SimpleAimConstraint()


    def CreateConstraint(constraintInfoList):
        obj = bpy.context.object
        errorMessageList = None
        if constraintInfoList:
            constraintType = constraintInfoList[0]['constraint_type'] #constraint type from the first element of constraintInfoList because they should all have the same constraint type
            #print(constraintType)
            constraintCreators = ConstraintLibrary.constraintCreators
            #for constraint in constraintInfoList:
            #    print(constraint['full_name'])
            if constraintType not in constraintCreators :
                message = "constraint Type '"+constraintType+"' not supported"
                return [{'WARNING'}, message]

            constraintCreator = constraintCreators[constraintType]
            errorMessageList = constraintCreator.CreateConstraint(obj, constraintInfoList)
        return errorMessageList
