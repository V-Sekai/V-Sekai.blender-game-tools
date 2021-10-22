if "bpy" not in locals():
    import bpy
    from . import main
    from . import retargeting
    from . import info
else:
    import importlib

    importlib.reload(main)
    importlib.reload(retargeting)
    importlib.reload(info)
