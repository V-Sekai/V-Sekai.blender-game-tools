import bpy

addon_keymaps = []

def register_keymap():
    '''Register Keymap for Move Along View'''
    addon = bpy.context.window_manager.keyconfigs.addon
    km = addon.keymaps.new(name = "3D View", space_type = "VIEW_3D")

    kmi = km.keymap_items.new("view3d.move_along_view", "Y", "PRESS", alt = True)
    kmi.active = True
    addon_keymaps.append(km)

def unregister_keymap():
    '''Unregister Keymap for Move Along View'''
    wm = bpy.context.window_manager
    for km in addon_keymaps:
        for kmi in km.keymap_items:
            km.keymap_items.remove(kmi)
        wm.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()
