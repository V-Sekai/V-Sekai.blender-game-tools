bl_info = {
    "name": "QOL PolyPal",
    "author": "Rico Holmes",
    "version": (2, 0, 0),
    "blender": (3, 3, 0),
    "location": "View3D > Add > Mesh > QOL PolyPal",
    "description": "Draws a polygon on the fly",
    "warning": "",
    "wiki_url": "",
    }

import bpy
from . prefs import *
from . import classes

def qolPolyTools_menu_func(self, context):
    self.layout.operator("qol.cutproject", icon='MOD_BOOLEAN')
    self.layout.operator("qol.ngoncleaner", icon='MOD_TRIANGULATE')

def qolpolydraw_menu_func(self, context):
    self.layout.operator("qol.polypaldraw", icon='STICKY_UVS_VERT')
    self.layout.operator("qol.polypalrectangle", icon='MESH_PLANE')
    self.layout.operator("qol.polypalcircle", icon='MESH_CIRCLE')

  

registerable_classes = (
    classes.QOL_PolyPal_Preferences,
    classes.QOL_OT_PolyPalDraw,
    classes.QOL_CutProject,
    classes.QOL_OT_PolyPalRectangle,
    classes.QOL_OT_PolyPalCircle,
    classes.QOL_OT_NGonCleaner,
    classes.QOL_OT_WeldSilhouette,
    )
def register():
    for cls in registerable_classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.prepend(qolpolydraw_menu_func)
    bpy.types.VIEW3D_MT_object_context_menu.append(qolPolyTools_menu_func)
    prefs = QOLPolyPal_get_preferences(bpy.context)
    if prefs.nPanel:
        bpy.utils.register_class(classes.QOL_PT_PolyPalNPanel)
    
def unregister():
    for cls in registerable_classes:
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.remove(qolpolydraw_menu_func)
    bpy.types.VIEW3D_MT_object_context_menu.remove(qolPolyTools_menu_func)
    prefs = QOLPolyPal_get_preferences(bpy.context)
    if prefs.nPanel:
        bpy.utils.unregister_class(classes.QOL_PT_PolyPalNPanel)

if __name__ == "__main__":
    register()






