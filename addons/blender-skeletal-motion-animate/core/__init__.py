if "bpy" not in locals():
    import bpy
    from . import animation_lists
    from . import utils
    from . import state_manager
    from . import icon_manager
    from . import retargeting
    from . import detection_manager
else:
    import importlib

    importlib.reload(animation_lists)
    importlib.reload(utils)
    importlib.reload(state_manager)
    importlib.reload(icon_manager)
    importlib.reload(retargeting)
    importlib.reload(detection_manager)
