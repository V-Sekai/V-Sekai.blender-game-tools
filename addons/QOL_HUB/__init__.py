bl_info = {
    "name": "QOL HUB",
    "author": "Rico Holmes",
    "version": (1, 0, 7),
    "blender": (3, 4, 0),
    "description": "Quickly access QOL tools",
    "warning": "",
    "wiki_url": "",
    "category": "Interface",
    }

import bpy,os
import addon_utils
from bpy.types import (Menu,Operator)
from bpy.props import (StringProperty)
from .prefs import *
from . import preview_defs
ICONS = {
    "Contiguous": "Contiguous.png",
    "FillHole": "FillHole.png",
    "Flip": "Flip.png",
    "GridCut": "GridCut.png",
    "QuickBool": "QuickBool.png",
    "RingArray": "RingArray.png",
    "SameSize": "SameSize.png",
    "SameVtxCount": "SameVtxCount.png",
    "SnapOffCopy": "SnapOffCopy.png",
    "GroundObjects": "GroundObjects.png",
    "OriginToBase": "OriginToBase.png",
    "MatchOrigins": "MatchOrigins.png",
    "Primitives": "Primitives.png",
    "ExportSelected": "ExportSelected.png",
    "MaterialsPanel": "MaterialsPanel.png",
    "QOL_NewPen": "NewPen.png",
    "QOL_Subdivide": "Subdivide.png",
    "QOL_HandlesVector": "HandlesVector.png",
    "QOL_HandlesFree": "HandlesFree.png",
    "QOL_HandlesAligned": "HandlesAligned.png",
    "QOL_HandlesAuto": "HandlesAuto.png",
    "QOL_Fillet": "Fillet.png",
    "QOL_Chamfer": "Chamfer.png",
    "QOL_UnFillet": "UnFillet.png",
    "QOL_PolyPalDraw": "PolyPalDraw.png",
    "QOL_PolyPalRectangle": "PolyPalRectangle.png",
    "QOL_PolyPalCircle": "PolyPalCircle.png",
    "QOL_CutProject": "CutProject.png",
    }
icons_dict = bpy.utils.previews.new()
icons_dir = os.path.join(os.path.dirname(__file__), "icons")
for icon_id, icon_file in ICONS.items():
    icons_dict.load(icon_id, os.path.join(icons_dir, icon_file), 'IMAGE')

class QOL_OT_Unavailable(Operator):
    bl_idname = "wm.qol_unavailable"
    bl_label = "Not installed or not enabled"
    bl_description = "Not installed or not enabled"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.report({'INFO'}, "Not installed or unavailable")
        return {'FINISHED'}

class QOL_OT_BreakoutWindow(Operator):
    bl_idname = "wm.qol_breakoutwindow"   
    bl_label = "Breakout Window"
    bl_description = "Breakout a new window of this type"
    bl_options = {'REGISTER', 'UNDO'} 
    windowType: StringProperty(name="Window Type", default="GeometryNodeTree")
    def execute(self,context):
        bpy.ops.wm.window_new()
        bpy.context.area.ui_type = self.windowType
        return {'FINISHED'}


class QOL_OT_PiePrefs(Operator):
    bl_idname = "wm.qol_pieprefs"
    bl_label = "QOL Pie Preferences"
    bl_description = "QOL Pie Preferences access directly from the pie menu"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.screen.userpref_show()
        bpy.context.preferences.active_section = 'ADDONS'
        bpy.data.window_managers["WinMan"].addon_search = "QOL HUB"
        return {'FINISHED'}

class QOL_MT_Pie(Menu):
    bl_idname = "QOL_MT_Pie"
    bl_label = "QOL Pie"

    def draw(self, context):
        prefs = bpy.context.preferences.addons["QOL_HUB"].preferences
        if updateAvailable():   self.bl_label = "QOL Pie (Update Available)"
        layout = self.layout
        pie = layout.menu_pie()
        
        menuMode = "HUB"

        # order of draw: West, East, South, North, Northwest, Northeast Southwest Southeast
        if "QOL_PenPal" in bpy.context.preferences.addons:
            # pie.operator("wm.call_menu_pie", text="PenPal", icon='NONE').name = 'QOL_MT_PenPalPie'
            if bpy.context.active_object is not None:
                if bpy.context.mode == 'EDIT_CURVE':
                    menuMode = "PenPal"

        if menuMode == "PenPal":
            #West    
            pie.operator("qol.plotbezier", text="Create New Curve", icon_value=icons_dict["QOL_NewPen"].icon_id)
            #East
            pie.separator()
            #South
            pie.operator("qol.make_mesh", text="Make Poly Mesh")
            #North
            pie.operator("curve.cyclic_toggle", text="Toggle Cyclic")
            #Northwest
            NorthWestBox = pie.column().box()
            NorthWestBox.emboss = 'RADIAL_MENU'
            NorthWestBox.scale_y = 1.2
            NorthWestBox.scale_x = 1.4
            NorthWestSubItem = NorthWestBox.column()
            NorthWestSubItem.operator("qol.bezier_modal_fillet", text="Fillet",icon_value=icons_dict["QOL_Fillet"].icon_id).cornering_style = "Round"
            NorthWestSubItem.operator("qol.bezier_modal_fillet", text="Chamfer",icon_value=icons_dict["QOL_Chamfer"].icon_id).cornering_style = "Chamfer"
            NorthWestSubItem.operator("qol.unfillet", text="Un-Fillet",icon_value=icons_dict["QOL_UnFillet"].icon_id)
            NorthWestSubItem.operator("qol.bezier_modal_subdivide", text="Subdivide",icon_value=icons_dict["QOL_Subdivide"].icon_id)
            #Northeast
            pie.operator("qol.origin_to_start", text="Pivot To Start")
            #Southwest
            SouthWestBox = pie.column().box()
            SouthWestBox.emboss = 'RADIAL_MENU'
            SouthWestBox.scale_x = 1.4
            SouthWestBox.scale_y = 1.2
            SouthWestSubItem = SouthWestBox.column()
            SouthWestSubItem.operator("curve.handle_type_set", text="Vector", icon_value=icons_dict["QOL_HandlesVector"].icon_id).type='VECTOR'
            SouthWestSubItem.operator("curve.handle_type_set", text="Aligned",icon_value=icons_dict["QOL_HandlesAligned"].icon_id).type='ALIGNED'
            SouthWestSubItem.operator("curve.handle_type_set", text="Free",icon_value=icons_dict["QOL_HandlesFree"].icon_id).type='FREE_ALIGN'
            SouthWestSubItem.operator("curve.handle_type_set", text="Auto",icon_value=icons_dict["QOL_HandlesAuto"].icon_id).type='AUTOMATIC'
            #Southeast
            pie.separator()


        #---------------------------------------------------------------------------------------------
        else:
            # West
            if "QOL_PenPal" in bpy.context.preferences.addons:
                pie.operator("qol.plotbezier", text="Create New Curve", icon_value=icons_dict["QOL_NewPen"].icon_id)
            # elif "QOL_PrimitivesPopup" in bpy.context.preferences.addons:
                # pie.operator("wm.call_menu_pie", text="Primitives", icon='NONE').name = 'QOL_MT_PrimsPie'
            else:
                westBox = pie.column().box()
                westBox.emboss = 'RADIAL_MENU'
                westBox.scale_y = 1.2
                westBox.scale_x = 1.2
                westPieSubItem = westBox.column()
                westPieSubItem.operator("wm.qol_unavailable",text="New PenPal curve", icon_value=icons_dict["QOL_NewPen"].icon_id)
                westPieSubItem.enabled = False
                # op.enabled = False
            
            #---------------------------------------------------------------------------------------------
            #East
            if "QOL_PolyPal" in bpy.context.preferences.addons:
                op = pie.operator("qol.polypaldraw", text="New PolyPal Poly", 
                             icon_value=icons_dict["QOL_PolyPalDraw"].icon_id
                             )
                op.directCreate = True
            else:
                eastBox = pie.column().box()
                eastBox.emboss = 'RADIAL_MENU'
                eastBox.scale_y = 1.2
                eastBox.scale_x = 1.2
                # EastSubItem = eastBox.column()
                EastSubItem = eastBox.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=False, align=True)
                if "QOL_ExportSelected" in bpy.context.preferences.addons:
                    if prefs.showIcons:
                        EastSubItem.operator("qol.exportfile", text="ExportSelected",icon_value=icons_dict["ExportSelected"].icon_id)
                    else:
                        EastSubItem.operator("qol.exportfile", text="ExportSelected")
                else:
                    EastSubItem.emboss = 'NONE'
                    EastSubItem.operator("wm.qol_unavailable",text="ExportSelected")
            #---------------------------------------------------------------------------------------------
            # South
            southBox = pie.column().box()
            southBox.emboss = 'RADIAL_MENU'
            southBox.scale_y = 1.2
            SouthSubItem = southBox.column()
            if prefs.showLabels:
                SouthSubItem.label(text=":: Placement")
            if prefs.showIcons:
                southBox.scale_x = 1.2
            if "QOL_GroundObjects" in bpy.context.preferences.addons:
                if prefs.showIcons:
                    SouthSubItem.operator("object.ground_objects",text="GroundObjects",icon_value=icons_dict["GroundObjects"].icon_id)
                else:
                    SouthSubItem.operator("object.ground_objects",text="GroundObjects")
            else:
                SouthSubItem.emboss = 'NONE'
                SouthSubItem.operator("wm.qol_unavailable",text="GroundObjects")

            if "QOL_OriginToBase" in bpy.context.preferences.addons:
                if prefs.showIcons:
                    SouthSubItem.operator("object.qol_origintobase",text="OriginToBase",icon_value=icons_dict["OriginToBase"].icon_id)
                else:
                    SouthSubItem.operator("object.qol_origintobase",text="OriginToBase")
            else:
                SouthSubItem.emboss = 'NONE'
                SouthSubItem.operator("wm.qol_unavailable",text="OriginToBase")
            
            if "QOL_MatchOrigin" in bpy.context.preferences.addons:
                if prefs.showIcons:
                    SouthSubItem.operator("object.qol_matchorigin",text="MatchOrigin",icon_value=icons_dict["MatchOrigins"].icon_id)
                else:
                    SouthSubItem.operator("object.qol_matchorigin",text="MatchOrigin")
            else:
                SouthSubItem.emboss = 'NONE'
                SouthSubItem.operator("wm.qol_unavailable",text="MatchOrigin")
            #---------------------------------------------------------------------------------------------
            # North
            northBox = pie.column().box()
            northBox.emboss = 'RADIAL_MENU'
            northBox.scale_y = 1
            NorthSubItem = northBox.column()
            NewBreakoutWindow = NorthSubItem.operator("wm.qol_breakoutwindow", text="Graph Editor", icon='GRAPH')
            NewBreakoutWindow.windowType = "FCURVES"
            NewBreakoutWindow = NorthSubItem.operator("wm.qol_breakoutwindow", text="GeoNodes", icon='GEOMETRY_NODES')
            NewBreakoutWindow.windowType = "GeometryNodeTree"
            NewBreakoutWindow = NorthSubItem.operator("wm.qol_breakoutwindow", text="ShaderNodes", icon='SHADING_RENDERED')
            NewBreakoutWindow.windowType = "ShaderNodeTree"
            NorthSubItem.separator()
            NorthSubItem.scale_y = 1.6
            addon_name = "QOL_MaterialsPanel"
            if addon_name in bpy.context.preferences.addons:
                addon = bpy.context.preferences.addons[addon_name]
                module = __import__(addon.module)
                addon_version = module.bl_info["version"]
                if compare_versions(addon_version, (2, 0, 0)) >= 0:
                    if prefs.showIcons:
                        northBox.scale_x = 1.2
                        NorthSubItem.operator("rh.matpanelpopup",text="Materials Popup",icon_value=icons_dict["MaterialsPanel"].icon_id)
                    else:
                        NorthSubItem.operator("rh.matpanelpopup",text="Materials Popup")
            
            # NorthSubItem.label(text="Update Available", icon='ERROR')
            # NorthSubItem.alert = True
            #---------------------------------------------------------------------------------------------
            # NorthWest
            NorthWestBox = pie.column().box()
            NorthWestBox.emboss = 'RADIAL_MENU'
            NorthWestBox.scale_y = 1.2
            NorthWestBox.scale_x = 1.2
            NorthWestSubItem = NorthWestBox.column()
            if "QOL_QuickBool" in bpy.context.preferences.addons:
                if prefs.showIcons:
                    NorthWestSubItem.operator("object.rhtools_quickboolchop", text="QuickBool",icon_value=icons_dict["QuickBool"].icon_id)
                else:
                    NorthWestSubItem.operator("object.rhtools_quickboolchop", text="QuickBool")
            else:
                NorthWestSubItem.emboss = 'NONE'
                NorthWestSubItem.operator("wm.qol_unavailable",text="QuickBool")

            if "QOL_RingArray" in bpy.context.preferences.addons:
                if prefs.showIcons:
                    NorthWestSubItem.operator("wm.qol_ringarray", text="RingArray",icon_value=icons_dict["RingArray"].icon_id)
                else:
                    NorthWestSubItem.operator("wm.qol_ringarray", text="RingArray")
            else:
                NorthWestSubItem.emboss = 'NONE'
                NorthWestSubItem.operator("wm.qol_unavailable",text="RingArray")
            
            if "QOL_GridCut" in bpy.context.preferences.addons:
                if prefs.showIcons:
                    NorthWestSubItem.operator("object.qol_grid_cut", text="GridCut",icon_value=icons_dict["GridCut"].icon_id)
                else:
                    NorthWestSubItem.operator("object.qol_grid_cut", text="GridCut")
            else:
                NorthWestSubItem.emboss = 'NONE'
                NorthWestSubItem.operator("wm.qol_unavailable",text="GridCut")
            #---------------------------------------------------------------------------------------------
            # NorthEast
            if "QOL_PolyPal" in bpy.context.preferences.addons:
                NorthEastBox = pie.column().box()
                NorthEastBox.emboss = 'RADIAL_MENU'
                NorthEastBox.scale_y = 1.2
                if prefs.showIcons:
                    NorthEastBox.scale_x = 1.4
                NorthEastSubItem = NorthEastBox.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=False, align=True)
                if prefs.showLabels:
                    NorthEastSubItem.label(text=":: PolyPal Tools")
                    NorthEastSubItem.separator()
                if prefs.showIcons:
                    NorthEastSubItem.operator("qol.polypalrectangle", text="Rectangle",icon_value=icons_dict["QOL_PolyPalRectangle"].icon_id)
                else:
                    NorthEastSubItem.operator("qol.polypalrectangle", text="Rectangle")
                if prefs.showIcons:
                    NorthEastSubItem.operator("qol.cutproject", text="CutProject",icon_value=icons_dict["QOL_CutProject"].icon_id)
                else:
                    NorthEastSubItem.operator("qol.cutproject", text="CutProject")
                if prefs.showIcons:
                    NorthEastSubItem.operator("qol.polypalcircle", text="Circle",icon_value=icons_dict["QOL_PolyPalCircle"].icon_id)
                else:
                    NorthEastSubItem.operator("qol.polypalcircle", text="Circle")
                if prefs.showIcons:
                    NorthEastSubItem.operator("qol.weldsilhouette", text="Weld silhouette",icon_value=icons_dict["QOL_CutProject"].icon_id)
                else:
                    NorthEastSubItem.operator("qol.weldsilhouette", text="Weldsilhouette")

                if prefs.showIcons:
                    op = NorthEastSubItem.operator("qol.polypaldraw", text="Edit",icon_value=icons_dict["QOL_PolyPalDraw"].icon_id)
                    op.directCreate = False
                else:
                    op = NorthEastSubItem.operator("qol.polypaldraw", text="Edit")
                    op.directCreate = False

                if prefs.showIcons:
                    NorthEastSubItem.operator("qol.ngoncleaner", text="NGon Cleaner",icon='MOD_TRIANGULATE')
                else:
                    NorthEastSubItem.operator("qol.ngoncleaner", text="NGon Cleaner")



            else:
                NorthEastBox = pie.column().box()
                NorthEastBox.emboss = 'RADIAL_MENU'
                NorthEastBox.scale_y = 1.2
                NorthEastBox.scale_x = 1.2
                NorthEastSubItem = NorthEastBox.column()
                NorthEastSubItem.operator("wm.qol_pieprefs", text="Prefs", icon='PREFERENCES')

            #---------------------------------------------------------------------------------------------
            # SouthWest
            SouthWestBox = pie.column().box()
            SouthWestBox.emboss = 'RADIAL_MENU'
            SouthWestBox.scale_y = 1.2
            if prefs.showIcons:
                SouthWestBox.scale_x = 1.2
            SouthWestSubItem = SouthWestBox.column()
            if prefs.showLabels:
                SouthWestSubItem.label(text=":: Selections")
            if "QOL_SelSameVtxCount" in bpy.context.preferences.addons:
                if prefs.showIcons:
                    SouthWestSubItem.operator("object.selsamevtx", text="Same vtx count",icon_value=icons_dict["SameVtxCount"].icon_id)
                else:
                    SouthWestSubItem.operator("object.selsamevtx", text="Same vtx count")
            else:
                SouthWestSubItem.emboss = 'NONE'
                SouthWestSubItem.operator("wm.qol_unavailable",text="Same vtx count")

            if "QOL_SelectSameSize" in bpy.context.preferences.addons:
                if prefs.showIcons:
                    SouthWestSubItem.operator("object.selectsamesize", text="Same size",icon_value=icons_dict["SameSize"].icon_id)
                else:
                    SouthWestSubItem.operator("object.selectsamesize", text="Same size")
            else:
                SouthWestSubItem.emboss = 'NONE'
                SouthWestSubItem.operator("wm.qol_unavailable",text="Same size")

            if "QOL_Select_Contiguous" in bpy.context.preferences.addons:
                if prefs.showIcons:
                    SouthWestSubItem.operator("qol.selectcontiguous", text="Contiguous Edges",icon_value=icons_dict["Contiguous"].icon_id)
                else:
                    SouthWestSubItem.operator("qol.selectcontiguous", text="Contiguous Edges")
            else:
                SouthWestSubItem.emboss = 'NONE'
                SouthWestSubItem.operator("wm.qol_unavailable",text="Contiguous Edges")
            #---------------------------------------------------------------------------------------------
            # SouthEast
            SouthEastBox = pie.column().box()
            SouthEastBox.emboss = 'RADIAL_MENU'
            SouthEastBox.scale_y = 1.2
            if prefs.showIcons:
                SouthEastBox.scale_x = 1.2
            # SouthEastSubItem = SouthEastBox.column()
            SouthEastSubItem = SouthEastBox.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=False, align=True)
            if prefs.showLabels:
                SouthEastSubItem.label(text=":: MeshEdit")
                SouthEastSubItem.separator()
            if "QOL_FlipFaces" in bpy.context.preferences.addons:
                if prefs.showIcons:
                    SouthEastSubItem.operator("object.qol_flipfaces", text="Flip Faces",icon_value=icons_dict["Flip"].icon_id)
                else:
                    SouthEastSubItem.operator("object.qol_flipfaces", text="Flip Faces")
            else:
                SouthEastSubItem.emboss = 'NONE'
                SouthEastSubItem.operator("wm.qol_unavailable",text="Flip Faces")

            if "QOL_HoleFiller" in bpy.context.preferences.addons:
                if prefs.showIcons:
                    SouthEastSubItem.operator("mesh.qol_holefiller", text="Hole Filler",icon_value=icons_dict["FillHole"].icon_id)
                else:
                    SouthEastSubItem.operator("mesh.qol_holefiller", text="Hole Filler")
            else:
                SouthEastSubItem.emboss = 'NONE'
                SouthEastSubItem.operator("wm.qol_unavailable",text="Hole Filler")

            if "QOL_SnapOffCopy" in bpy.context.preferences.addons:
                if prefs.showIcons:
                    SouthEastSubItem.operator("object.qol_snapoffcopy", text="SnapOffCopy",icon_value=icons_dict["SnapOffCopy"].icon_id)
                else:
                    SouthEastSubItem.operator("object.qol_snapoffcopy", text="SnapOffCopy")
            else:
                SouthEastSubItem.emboss = 'NONE'
                SouthEastSubItem.operator("wm.qol_unavailable",text="SnapOffCopy")
            if "QOL_PolyPal" in bpy.context.preferences.addons:
                if prefs.showIcons:
                    SouthEastSubItem.operator("qol.cutproject", text="CutProject",icon_value=icons_dict["QOL_CutProject"].icon_id)
                else:
                    SouthEastSubItem.operator("qol.cutproject", text="CutProject")
            else:
                SouthEastSubItem.emboss = 'NONE'
                SouthEastSubItem.operator("wm.qol_unavailable",text="CutProject")
            


classes = [
        QOL_Pie_preferences,
        QOL_OT_PiePrefs,
        QOL_OT_SiteLink,
        QOL_MT_Pie,
        QOL_OT_BreakoutWindow,
        QOL_OT_Unavailable,
        ]
addon_keymaps = []

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    #keymap
    wm = bpy.context.window_manager
    # km = wm.keyconfigs.addon.keymaps.new(name='Screen Editing', space_type='VIEW_3D')
    km = wm.keyconfigs.addon.keymaps.new(name='Screen Editing', space_type='EMPTY')
    kmi = km.keymap_items.new("wm.call_menu_pie", 'BUTTON4MOUSE', 'PRESS')
    kmi.properties.name = "QOL_MT_Pie"
    addon_keymaps.append((km, kmi))
    

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

if __name__ == "__main__":
    register()

