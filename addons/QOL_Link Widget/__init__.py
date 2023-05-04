#setup bl_info
bl_info = {
    "name": "QOL Link Widget",
    "author": "Rico Holmes",
    "version": (1, 0, 9),
    "blender": (3, 0, 0),
    "location": "View3D",
    "description": "Show linked objects indicator in topbar",
    "warning": "",
    "wiki_url": "",
    "category": "Interface",
    }

import bpy,os
from bpy.types import (Operator,Menu)
from .prefs import *


import bpy.utils.previews
icons_dict = bpy.utils.previews.new()
icons_dir = os.path.join(os.path.dirname(__file__), "icons")
icons_dict.load("QOL_LinkFound", os.path.join(icons_dir, "Link_Found.png"), 'IMAGE')
icons_dict.load("QOL_LinkFound_Mono", os.path.join(icons_dir, "Link_Found_Mono.png"), 'IMAGE')
icons_dict.load("QOL_LinkNone", os.path.join(icons_dir, "Link_None.png"), 'IMAGE')

class QOL_MT_ActionsPopup(Menu):
    bl_label = "QOL Link Widget"
    bl_idname = "QOL_MT_linkindicator_popup"
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        layout.operator("object.break_links",text="Break Links")
        row = layout.row()
        layout.operator("qol.select_linked",text="Select Linked")
        row = layout.row()
        layout.operator("object.linkalltoactive",text="Link All to Active")

class QOL_OT_LinkWidget(Operator):
    """CLICK: UNLINK data to make unique\nSHIFT: LINK data to active object\nALT: Select linked objects connected to active\nCTRL+SHIFT freeze Scale\nCTRL: Select ALL linked objects in scene"""
    bl_idname = "object.linkindicator"
    bl_label = "QOL Link Widget"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def invoke(self, context, event):
        if event.shift and not event.ctrl and not event.alt:
            bpy.ops.object.make_links_data(type='OBDATA')
            self.report({'INFO'}, "Linked data to active object")
            
        elif event.alt and not event.ctrl and not event.shift:
            bpy.ops.qol.select_linked()

        elif event.ctrl and event.shift and not event.alt:
            bpy.ops.qol.select_linked()
            bpy.ops.object.make_single_user(object=True, obdata=True)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            bpy.ops.object.make_links_data(type='OBDATA')

        elif event.ctrl and not event.shift and not event.alt:
            stepper = 0
            for obj in bpy.data.objects:
                if obj.data is not None and obj.data.users > 1 and obj.name in context.view_layer.objects:
                    obj.select_set(True)
                if obj.data is not None and obj.data.users > 1 and obj.name not in context.view_layer.objects:
                    stepper += 1

            self.report({'INFO'}, "Selected all linked objects in scene" if stepper == 0 else "Selected all linked objects in scene, except {} objects NOT visible or in view layer".format(stepper))

        else:
            return self.execute(context)

        return {'FINISHED'}


    def execute(self, context):
        li_prefs = RHLinkWidget_get_preferences(bpy.context)
        if li_prefs.popupEnabled:
            bpy.ops.wm.call_menu(name=QOL_MT_ActionsPopup.bl_idname)
        else:
            obj = context.active_object
            if obj.data.users > 1:
                bpy.ops.object.make_single_user(object=True, obdata=True)

        return {'FINISHED'}

class QOL_OT_SelectLinked(Operator):
    """Select linked objects connected to active"""
    bl_idname = "qol.select_linked"
    bl_label = "Select Linked"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        allSelected = bpy.context.selected_objects
        initialCount = len(allSelected)
        for uX in bpy.data.objects:
            if uX.data == obj.data and uX.name in context.view_layer.objects:
                uX.select_set(True)
        afterOpSelected = bpy.context.selected_objects
        afterCount = len(afterOpSelected)
        if afterCount == initialCount:
            self.report({'INFO'}, "No linked objects found")
        else:
            amountAdded = afterCount - initialCount
            self.report({'INFO'}, "Selected {} linked objects".format(amountAdded))
        return {'FINISHED'}

class QOL_OT_Breaklinks(Operator):
    """Break all links to this object"""
    bl_idname = "object.break_links"
    bl_label = "Break Links"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        bpy.ops.object.make_single_user(object=True, obdata=True)
        bpy.ops.object.make_local(type='ALL')
        return {'FINISHED'}

class QOL_OT_LinkAlltoActive(Operator):
    """Link all selected objects to active"""
    bl_idname = "object.linkalltoactive"
    bl_label = "Link All to Active"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        bpy.ops.object.make_links_data(type='OBDATA')
        return {'FINISHED'}

def topbarIcon(self,context):
    li_prefs = RHLinkWidget_get_preferences(bpy.context)
    obj = context.active_object
    if len(context.selected_objects) > 0:
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                if obj is not None:
                    if obj.data is not None and obj.data.users > 1 and obj in bpy.context.selected_objects:
                        if li_prefs.paneltype == 'Colored':
                            self.layout.operator("object.linkindicator",text = str(obj.data.users) ,icon_value=icons_dict["QOL_LinkFound"].icon_id)
                        else:
                            self.layout.operator("object.linkindicator",text = str(obj.data.users) ,icon_value=icons_dict["QOL_LinkFound_Mono"].icon_id)
                    else:
                        self.layout.operator("object.linkindicator",text = "0",icon_value=icons_dict["QOL_LinkNone"].icon_id)
                    break
                else:
                    self.layout.operator("object.linkindicator",text = "0",icon_value=icons_dict["QOL_LinkNone"].icon_id)
                break
    else:
        self.layout.operator("object.linkindicator",text = "0",icon_value=icons_dict["QOL_LinkNone"].icon_id)

classes = [
        RH_LinkWidget_preferences,
        QOL_OT_LinkWidget,
        QOL_OT_SelectLinked,
        QOL_MT_ActionsPopup,
        QOL_OT_Breaklinks,
        QOL_OT_LinkAlltoActive,
        ]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_HT_header.append(topbarIcon)
    

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_HT_header.remove(topbarIcon)
    bpy.utils.previews.remove(icons_dict)

if __name__ == "__main__":
    register()
