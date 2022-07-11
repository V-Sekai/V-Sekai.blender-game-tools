#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

if "bpy" not in locals():
    import bpy
    from . import icon_manager
    from . import duplicateBone
    from . import baseControllerShape
    from . import proxy
    from . import orient
    from . import extraBone
    from . import rootMotion
    from . import rotationModeAndRelations
    from . import rotationDistribution
    from . import ikLimb
    from . import fkLimb
    from . import worldSpace
    from . import aimSpace
    from . import aimOffsetSpace
    from . import parentSpace
    from . import parentOffsetSpace
    from . import reverseHierarchySpace
    from . import simpleCopyTransforms
    from . import simpleConstraints
    from . import removeConstraints
    from . import keyRange
    from . import rigState
    from . import importControllerShapes
    from . import constraintLibrary
    from . import rotfBake
    from . import bakeRig
    from . import singleFramePose
else:
    import importlib

    importlib.reload(icon_manager)
    importlib.reload(duplicateBone)
    importlib.reload(baseControllerShape)
    importlib.reload(proxy)
    importlib.reload(orient)
    importlib.reload(extraBone)
    importlib.reload(rootMotion)
    importlib.reload(rotationModeAndRelations)
    importlib.reload(rotationDistribution)
    importlib.reload(ikLimb)
    importlib.reload(fkLimb)
    importlib.reload(worldSpace)
    importlib.reload(aimSpace)
    importlib.reload(aimOffsetSpace)
    importlib.reload(parentSpace)
    importlib.reload(parentOffsetSpace)
    importlib.reload(reverseHierarchySpace)
    importlib.reload(simpleCopyTransforms)
    importlib.reload(simpleConstraints)
    importlib.reload(removeConstraints)
    importlib.reload(keyRange)
    importlib.reload(rigState)
    importlib.reload(importControllerShapes)
    importlib.reload(constraintLibrary)
    importlib.reload(rotfBake)
    importlib.reload(bakeRig)
    importlib.reload(singleFramePose)