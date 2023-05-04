import bpy
from . import bl_info
from bpy.types import (AddonPreferences,Operator)
from bpy.props import (BoolProperty,StringProperty)
import urllib.request
import rna_keymap_ui
import ssl
import platform
qolversionsDict={}
qolurlsDict={}
ssl_context = None
#detect whether mac or windows

if platform.system() != "Windows":
    try:
        ssl_context = ssl._create_unverified_context()
    except:
        ssl_context = None
try:
    with urllib.request.urlopen("https://www.ricoholmes.com/extraneous/qol/QOL_Versions.txt",context=ssl_context) as response:
        qolversionData=response.read()
    qolversions=qolversionData.decode("utf-8").splitlines()
    
    for line in qolversions:
        addon_name=line.split(",")[0]
        addon_version=tuple([int(x) for x in line.split(",")[1].split(".")])
        qolversionsDict[addon_name]=addon_version
    
    for line in qolversions:
        addon_name=line.split(",")[0]
        addon_url=line.split(",")[2]
        qolurlsDict[addon_name]=addon_url
except:
    print("Could not connect to QOL_HUB server. Please check your internet connection.\n Note: If you are on a Mac, we are investigating solutions. In the meantime the Version control facility of HUB will be unavailable.")


def compare_versions(version1, version2):
    for p1, p2 in zip(version1, version2):
        if p1 < p2:
            return 1
        elif p1 > p2:
            return 0
    return -1

def updateAvailable():
    if not qolversionsDict:
        return False
    if not qolurlsDict:
        return False
    for addon_name in qolurlsDict:
        if addon_name in bpy.context.preferences.addons:
            if qolurlsDict[addon_name].startswith("http"):
                if checkAddonVersion(addon_name)[3]==1:
                    return True
    return False

def checkAddonVersion(addon_name):
    addon = bpy.context.preferences.addons[addon_name]
    module = __import__(addon.module)
    addon_version = module.bl_info["version"]
    if not qolversionsDict:
        return(False,addon_version,"",0)

    website_version = qolversionsDict[addon_name]
    if compare_versions(addon_version,website_version)==1:
        return(True,addon_version,website_version,1)
    elif compare_versions(addon_version,website_version)==-1:
        return(False,addon_version,website_version,-1)
    else:
        return(True,addon_version,website_version,0)

class QOL_OT_SiteLink(Operator):
    bl_idname = "wm.qol_sitelink"
    bl_label = "BlenderMarket_Page"
    bl_description = "Visit the tool page on BlenderMarket"
    bl_options = {'REGISTER', 'UNDO'}
    url: StringProperty(name="URL", default="https://blendermarket.com/creators/qoltools")
    def execute(self,context):
        bpy.ops.wm.url_open(url=self.url)
        return {'FINISHED'}

class QOL_Pie_preferences(AddonPreferences):
    bl_idname = __package__
    showLabels: BoolProperty(
        name = "Show Section Labels",
        description = "Whether to show the labels for each lower section of the pie menu",
        default = True,
        )
    showIcons: BoolProperty(
        name = "Show Section Icons",
        description = "Whether to show the icons",
        default = True,
        )


    def draw(self, context):
        box = self.layout.box()
        column = box.column(align=True)
        row = column.row()
        row.label(text="Keymap:")
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.user

        for keymap in ['Screen Editing']:
            km = kc.keymaps.get(keymap)
            column = box.column(align=True)
            row = column.row()
            row.label(text=keymap)
            for kmi in km.keymap_items:
                if kmi.idname == "wm.call_menu_pie":
                    column = box.column(align=True)
                    row = column.row()
                    rna_keymap_ui.draw_kmi([], kc, km, kmi, row, 0)
            box.separator()

        self.layout.separator()        

        box = self.layout.box()
        box.label(text="Show:")
        row = box.row(align=True)
        row.prop(self,"showLabels",text="Section Labels")
        row = box.row(align=True)  
        row.prop(self,"showIcons",text="Section Icons")
        box.separator()

        self.layout.separator()

        QolAddons = []
        for addon in bpy.context.preferences.addons:
            if addon.module.startswith("QOL_"):
                QolAddons.append(addon.module)
        box = self.layout.box()
        box.label(text="QOL Addons installed:")
        box.separator()
        for addon in QolAddons:
            row = box.box().row(align=True)
            row.scale_y = 0.6
            row.alert = checkAddonVersion(addon)[0]
            row.label(text=addon)
            row.label(text=("installed: "+ str(checkAddonVersion(addon)[1])))
            
            if qolurlsDict:
                row.label(text=("latest: "+ str(checkAddonVersion(addon)[2])))
                if qolurlsDict[addon].startswith("http"):
                    if checkAddonVersion(addon)[3]==0:
                        row.label(text="PUSH!")
                        row.label(text="",icon="ERROR")
                    elif checkAddonVersion(addon)[3]==1:
                        row.label(text="Update available ->")
                        siteLink = row.operator("wm.qol_sitelink",text="",icon="ERROR")
                        siteLink.url=qolurlsDict[addon]
                    else:
                        row.label(text="")
                        siteLink = row.operator("wm.qol_sitelink",text="",icon="URL")
                        siteLink.url=qolurlsDict[addon]
                else:
                    if checkAddonVersion(addon)[3]==0:
                        row.label(text="PUSH!")
                        row.label(text="",icon="ERROR")
                    else:
                        row.label(text=qolurlsDict[addon])
                        row.label(text="",icon="MODIFIER")
            else:
                row.label(text="Could not connect to QOL_HUB server")

