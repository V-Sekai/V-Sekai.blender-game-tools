#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

if "bpy" not in locals():
    import bpy
    from . import main
    from . import bakeSettings
    from . import controllerShapeSettings
    from . import layerSettings
    from . import armatureTools
    from . import centerOfMass
    from . import rotationScaleTools
    from . import ikfkSwitch
    from . import spaceSwitch
    from . import simpleConstraints
    from . import keyframeTools
    from . import dynamics
    from . import rigState
    from . import singleFramePose
    from . import info
else:
    import importlib

    importlib.reload(main)
    importlib.reload(bakeSettings)
    importlib.reload(controllerShapeSettings)
    importlib.reload(layerSettings)
    importlib.reload(armatureTools)
    importlib.reload(centerOfMass)
    importlib.reload(rotationScaleTools)
    importlib.reload(ikfkSwitch)
    importlib.reload(spaceSwitch)
    importlib.reload(simpleConstraints)
    importlib.reload(keyframeTools)
    importlib.reload(dynamics)
    importlib.reload(rigState)
    importlib.reload(singleFramePose)
    importlib.reload(info)

