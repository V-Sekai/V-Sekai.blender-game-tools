bl_info = {
    "name": "QOL_PolyCount Widget",
    "author": "QOL",
    "version": (1, 0, 5),
    "blender": (3, 00, 0),
    "description": "Counts the number of polygons in the selected objects",
    "category": "Interface",    
    }

import bpy
from bpy.types import Operator
from bpy.props import *
from .prefs import *


class QOL_PolyHudSwitcher(Operator):
    bl_idname = "object.qol_polyhudswitcher"
    bl_label = "Poly Hud Switcher"
    bl_description = "Switches between the poly counter and the poly counter hud"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.context.space_data.overlay.show_stats = not bpy.context.space_data.overlay.show_stats
        return {'FINISHED'}


def TopBarWidget(self,context):
    pcwprefs = bpy.context.preferences.addons[__package__].preferences
    obj = context.active_object
    polyCount = 0
    if obj is not None:
        if context.mode == 'OBJECT' and obj.type == 'MESH' and obj is not None :
            if len(context.selected_objects) > 0:
                #create a list of all selected objects
                allSelectedObjects = bpy.context.selected_objects.copy()
                #remove all objects that have data linked to another object in the list
                for obj in allSelectedObjects:
                    if obj.data is not None and obj.data.users > 1:
                        for obj2 in bpy.data.objects:
                            if obj2.data == obj.data and obj2 != obj:
                                if obj2 in allSelectedObjects:
                                    allSelectedObjects.remove(obj2)

                for obj in allSelectedObjects:
                    dg = bpy.context.evaluated_depsgraph_get()
                    currobj = obj.evaluated_get(dg)
                    if hasattr(currobj.data, "polygons"):
                        if pcwprefs.mod_eval:
                            polyCount += sum([(len(p.vertices) - 2) for p in currobj.data.polygons])
                        else:
                            polyCount += sum([(len(p.vertices) - 2) for p in obj.data.polygons])
                       
    if polyCount > 1000000:
        polyCountString = pcwprefs.polylabel + str(round(polyCount/1000000,2)) + "M"
    elif polyCount > 1000:
        polyCountString = pcwprefs.polylabel + str(round(polyCount/1000,2)) + "K"
    else:
        polyCountString = pcwprefs.polylabel + str(polyCount)

    if context.mode == 'EDIT_MESH':
        polyCountString = "EDITING"

    
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            if obj is not None:
                self.layout.operator("object.qol_polyhudswitcher",emboss=False, text = polyCountString)
                break
            else:
                self.layout.operator("object.qol_polyhudswitcher",emboss=False, text = (pcwprefs.polylabel + "0"))
                break

def register():
    bpy.utils.register_class(RH_PolyCountWidget_preferences)
    bpy.utils.register_class(QOL_PolyHudSwitcher)
    if bpy.context.preferences.addons[__package__].preferences.header_left:
        bpy.types.VIEW3D_HT_tool_header.prepend(TopBarWidget)
    else:
        bpy.types.VIEW3D_HT_tool_header.append(TopBarWidget)

def unregister():
    bpy.utils.unregister_class(RH_PolyCountWidget_preferences)
    bpy.utils.unregister_class(QOL_PolyHudSwitcher)
    bpy.types.VIEW3D_HT_tool_header.remove(TopBarWidget)

if __name__ == "__main__":
    register()
