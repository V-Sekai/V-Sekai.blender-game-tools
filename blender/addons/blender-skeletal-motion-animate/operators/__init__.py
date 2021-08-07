if "bpy" not in locals():
    import bpy
    from . import detector
    from . import actor
    from . import info
    from . import retargeting
else:
    import importlib

    importlib.reload(detector)
    importlib.reload(actor)
    importlib.reload(info)
    importlib.reload(retargeting)
