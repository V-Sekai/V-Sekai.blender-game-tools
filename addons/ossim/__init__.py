import sys
import importlib

bl_info = {
    "name": "Ossim",
    "description": "Bakes rigidbody and cloth simulations to armature.",
    "author": "Peter Gubin  http://thewarpgames.com/petergubin",
    "version": (1, 4, 2),
    "blender": (2, 91, 0),
    "location": "3D View > Tools panel",
    "warning": "",
    "wiki_url": "https://blendermarket.com/products/ossim",
    "tracker_url": "",
    "category": "Physics"}

modulesNames = ['panels.panel_generator', 'operators.op_armature_generator', 'operators.op_autokeyframe']

modulesFullNames = {}
for currentModuleName in modulesNames:
    if 'DEBUG_MODE' in sys.argv:
        modulesFullNames[currentModuleName] = ('{}'.format(currentModuleName))
    else:
        modulesFullNames[currentModuleName] = ('{}.{}'.format(__name__, currentModuleName))

for currentModuleFullName in modulesFullNames.values():
    if currentModuleFullName in sys.modules:
        importlib.reload(sys.modules[currentModuleFullName])
        print("Importing module: " + currentModuleFullName)
    else:
        globals()[currentModuleFullName] = importlib.import_module(currentModuleFullName)
        setattr(globals()[currentModuleFullName], 'modulesNames', modulesFullNames)


def register():
    for currentModuleName in modulesFullNames.values():
        if currentModuleName in sys.modules:
            if hasattr(sys.modules[currentModuleName], 'register'):
                print("Module register: " + currentModuleFullName)

                sys.modules[currentModuleName].register()


def unregister():
    for currentModuleName in modulesFullNames.values():
        if currentModuleName in sys.modules:
            if hasattr(sys.modules[currentModuleName], 'unregister'):
                sys.modules[currentModuleName].unregister()


if __name__ == "__main__":
    register()
