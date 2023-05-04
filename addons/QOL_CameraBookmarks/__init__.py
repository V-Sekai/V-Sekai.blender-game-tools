bl_info = {
    "name": "QOL Camera Bookmarks",
    "author": "Rico Holmes",
    "version": (1, 5, 0),
    "blender": (3, 0, 0),
    "location": "View3D",
    "description": "A panel for creating camera bookmarks",
    "warning": "",
    "wiki_url": "",
    "category": "Interface",
}

import bpy,os,math

from bpy.props import (EnumProperty,FloatProperty,BoolProperty,IntProperty)
from bpy.types import (AddonPreferences,)
from .prefs import *
bpy.utils.register_class(QOL_CamBM_preferences)
from .functions import *

####################################################################################################  

class QOLBM_DataSet(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Test Property", default="Unknown")
    location: bpy.props.FloatVectorProperty(name="Test Property")
    rotation_euler: bpy.props.FloatVectorProperty(name="Test Property",subtype="EULER")
    scale: bpy.props.FloatVectorProperty(name="Test Property")
    passepartout_alpha: bpy.props.FloatProperty(name="Test Property")
    angle_x: bpy.props.FloatProperty(name="Test Property")
    angle_y: bpy.props.FloatProperty(name="Test Property")
    clip_start: bpy.props.FloatProperty(name="Test Property")
    clip_end: bpy.props.FloatProperty(name="Test Property")
    lens: bpy.props.FloatProperty(name="Test Property")
    sensor_width: bpy.props.FloatProperty(name="Test Property")
    sensor_height: bpy.props.FloatProperty(name="Test Property")
    ortho_scale: bpy.props.FloatProperty(name="Test Property")
    shift_x: bpy.props.FloatProperty(name="Test Property")
    shift_y: bpy.props.FloatProperty(name="Test Property")

class QOLVP_DataSet(bpy.types.PropertyGroup):
    view_perspective: bpy.props.StringProperty(name="Test Property", default="Unknown")
    view_camera_zoom: bpy.props.FloatProperty(name="Test Property")
    view_location: bpy.props.FloatVectorProperty(name="Test Property")
    view_rotation: bpy.props.FloatVectorProperty(name="Test Property",size=4,subtype="QUATERNION")
    view_distance: bpy.props.FloatProperty(name="Test Property")

####################################################################################################


class QOL_OT_SetVP(bpy.types.Operator):
    """Create new VIEWPORT bookmark from current position"""
    bl_idname = "wm.qol_setvpbm"
    bl_label = "Add Persp BM"

    @classmethod
    def poll(cls, context):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                return area.spaces[0].region_3d.view_perspective != "CAMERA"
    def execute(self, context):
        setVP(self,context)
        return {'FINISHED'}

class QOL_OT_SetBM(bpy.types.Operator):
    bl_idname = "wm.qol_setbm"
    bl_label = "add new item"

    @classmethod
    def poll(cls, context):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                return area.spaces[0].region_3d.view_perspective == "CAMERA"

    def execute(self, context):
        setBM(self,context)
        return {'FINISHED'}

class QOL_OT_DelBM(bpy.types.Operator):
    bl_idname = "qol.delbm"
    bl_label = "delete bookmark"
    BMIndex: IntProperty(default=0)

    def execute(self, context):
        bpy.context.scene.QOL_BM_DataSets.remove(self.BMIndex)
        return {'FINISHED'}

class QOL_OT_DelVP(bpy.types.Operator):
    bl_idname = "qol.delvpbm"
    bl_label = "delete bookmark"
    BMIndex: IntProperty(default=0)


    def execute(self, context):
        bpy.context.scene.QOL_VP_DataSets.remove(self.BMIndex)
        return {'FINISHED'}

class QOL_OT_UpdateVP(bpy.types.Operator):
    bl_idname = "qol.updatevpbm"
    bl_label = "update bookmark"
    BMIndex: IntProperty(default=0)
    @classmethod
    def poll(cls, context):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                return area.spaces[0].region_3d.view_perspective != "CAMERA"
    def execute(self, context):
        updateVP(self,context,self.BMIndex)
        return {'FINISHED'}

class QOL_OT_UpdateBM(bpy.types.Operator):
    bl_idname = "qol.updatebm"
    bl_label = "update bookmark"
    BMIndex: IntProperty(default=0)
    @classmethod
    def poll(cls, context):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                return area.spaces[0].region_3d.view_perspective == "CAMERA"        
    def execute(self, context):
        updateBM(self,context,self.BMIndex)
        return {'FINISHED'}


class QOL_OT_GetVP(bpy.types.Operator):
    """Restore vieport view from bookmark"""
    bl_idname = "wm.qol_getvpbm"
    bl_label = "retrieve bookmark"
    BMIndex: IntProperty(default=0)
    def execute(self, context):
        ApplyVP(self,context,self.BMIndex)
        return {'FINISHED'}
class QOL_OT_GetBM(bpy.types.Operator):
    """Restore camera view from bookmark"""
    bl_idname = "qol.getbm"
    bl_label = "retrieve bookmark"
    BMIndex: IntProperty(default=0)
    def execute(self, context):
        ApplyBM(self,context,self.BMIndex)
        return {'FINISHED'}

class QOL_OT_CYCLEBM(bpy.types.Operator):
    """Cycle through bookmarks"""
    bl_idname = "wm.qol_cyclebm"
    bl_label = "QOL 'Mini Bookmarks' button\nCTRL click to set new bookmark"
    BMIndex: IntProperty(default=0)

    def invoke(self, context,event):   
        vp = context.region_data
        if event.ctrl:
            if vp.view_perspective == "CAMERA": setBM(self,context)
            else: setVP(self,context)
        else:
            BMCount = len(context.scene.QOL_BM_DataSets)
            VPCount = len(context.scene.QOL_VP_DataSets)
            if self.BMIndex >= (BMCount+VPCount): self.BMIndex = 0
            if self.BMIndex < BMCount: ApplyBM(self,context,self.BMIndex)
            elif self.BMIndex < (BMCount+VPCount):    ApplyVP(self,context,(self.BMIndex-BMCount))
            # else: pass
            self.BMIndex += 1
        return {'FINISHED'}

    def execute(self, context):
        BMCount = len(context.scene.QOL_BM_DataSets)
        VPCount = len(context.scene.QOL_VP_DataSets)
        if self.BMIndex >= (BMCount+VPCount): self.BMIndex = 0
        if self.BMIndex < BMCount: ApplyBM(context,self.BMIndex)
        elif self.BMIndex < (BMCount+VPCount):    ApplyVP(context,(self.BMIndex-BMCount))
        # else: pass
        self.BMIndex += 1
        return {'FINISHED'}

class QOL_PT_CameraBookmarks(bpy.types.Panel):
    """Camera Bookmarks Manager"""
    panelPrefs = bpy.context.preferences.addons['QOL_CameraBookmarks'].preferences
    bl_idname = "QOL_PT_camerabookmarks"
    bl_label = "QOL Camera Bookmarks"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    if panelPrefs.paneltype == "properties":
        bl_category = "Tool"
    if panelPrefs.paneltype == "npanel": 
        bl_category = "View"  

    def draw(self, context):
        isCamView = False
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                if area.spaces[0].region_3d.view_perspective == "CAMERA":
                    isCamView = True
        BM = context.scene.QOL_BM_DataSets
        BM_Count = len(BM)
        layout = self.layout
        row = layout.row()
        if isCamView:   row.operator("wm.qol_setbm",icon="BOOKMARKS",text="Create Bookmark")
        else:   row.operator("wm.qol_setvpbm",icon="BOOKMARKS",text="Create Bookmark")

        i=0
        while i < BM_Count:
            row = layout.row()
            BMButtn = row.operator("qol.getbm",icon="BOOKMARKS",text="")
            row.prop(BM[i],"name",text="")
            op_update = row.operator("qol.updatebm",icon="INDIRECT_ONLY_ON",text="")
            op_del=row.operator("qol.delbm",icon="CANCEL",text="")
            BMButtn.BMIndex=op_update.BMIndex=op_del.BMIndex=i
            i+=1

        BM = context.scene.QOL_VP_DataSets
        BM_Count = len(BM)
        i=0
        while i < BM_Count:
            row = layout.row()
            BMButtn = row.operator("wm.qol_getvpbm",icon="BOOKMARKS",text="")
            row.prop(BM[i],"name",text="")
            op_update = row.operator("qol.updatevpbm",icon="INDIRECT_ONLY_ON",text="")
            op_del=row.operator("qol.delvpbm",icon="CANCEL",text="")
            BMButtn.BMIndex=i
            op_update.BMIndex=i
            op_del.BMIndex=i
            i+=1

    def execute(self, context):
        return {'FINISHED'}



def topdraw(self,context):
 for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        self.layout.operator(QOL_OT_CYCLEBM.bl_idname,text="",icon="BOOKMARKS")
        break


classes = [
QOLBM_DataSet,
QOLVP_DataSet,
QOL_OT_UpdateBM,
QOL_OT_UpdateVP,
QOL_OT_DelBM,
QOL_OT_DelVP,
QOL_OT_SetBM,
QOL_OT_SetVP,
QOL_OT_GetBM,
QOL_OT_GetVP,
QOL_PT_CameraBookmarks,
QOL_OT_CYCLEBM,
]


def register():
    for c in classes:   bpy.utils.register_class(c)
    bpy.types.Scene.QOL_BM_DataSets = bpy.props.CollectionProperty(type=QOLBM_DataSet)
    bpy.types.Scene.QOL_VP_DataSets = bpy.props.CollectionProperty(type=QOLVP_DataSet)
    bpy.types.VIEW3D_HT_header.append(topdraw)
def unregister():
    for c in classes:   bpy.utils.unregister_class(c)
    bpy.types.VIEW3D_HT_header.remove(topdraw)

if __name__ == "__main__":
    register()

