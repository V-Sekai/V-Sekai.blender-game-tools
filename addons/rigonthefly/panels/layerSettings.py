import bpy

from .main import ToolPanel, separator
from ..operators import info
from ..core.icon_manager import Icons
from ..core import boneCollections
from bpy.types import UIList

def LayerIsOccupied(self, context, value):
    obj = context.object
    if obj == None:
        return
    return value == obj.baseBonesLayer or value == obj.unusedRigBonesLayer or value == obj.notOrientedBonesLayer


def UpdateLayer(self, context, value, name):
    obj = context.object
    if obj == None:
        return
    newValue = value + (-1 if LayerIsOccupied(self, context, value+1) else 1)

    if value == obj.baseBonesLayer and name != "baseBonesLayer":
        obj.baseBonesLayer = newValue
    if value == obj.unusedRigBonesLayer and name != "unusedRigBonesLayer":
        obj.unusedRigBonesLayer = newValue
    if value == obj.notOrientedBonesLayer and name != "notOrientedBonesLayer":
        obj.notOrientedBonesLayer = newValue


def update_BaseBoneslayer(self, context):
    UpdateLayer(self, context, context.object.baseBonesLayer, "baseBonesLayer")


def update_RigBoneslayer(self, context):
    UpdateLayer(self, context, context.object.rigBonesLayer, "rigBonesLayer")


def update_UnusedRigBonesLayer(self, context):
    UpdateLayer(self, context, context.object.unusedRigBonesLayer,
                "unusedRigBonesLayer")


def update_NotOrientedBonesLayer(self, context):
    UpdateLayer(self, context, context.object.notOrientedBonesLayer,
                "notOrientedBonesLayer")

bpy.types.Object.baseBonesLayer = bpy.props.IntProperty(
    name="baseBonesLayer", description="Where bones that are directly driven by rig bones are sent to", default=0, min=0, max=31, update=update_BaseBoneslayer)
bpy.types.Object.unusedRigBonesLayer = bpy.props.IntProperty(
    name="unusedRigBonesLayer", description="Where temporarily unused rig bones are sent to", default=1, min=0, max=31, update=update_UnusedRigBonesLayer)
bpy.types.Object.notOrientedBonesLayer = bpy.props.IntProperty(
    name="notOrientedBonesLayer", description="Where not-oriented bones are sent to", default=2, min=0, max=31, update=update_NotOrientedBonesLayer)


class LayerSettingsPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rsl_layerSettings'
    bl_label = 'Bone Layers/Collections'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        appVersion = bpy.app.version
        #if not self.DisplayCondition(context):
        layout = self.layout
        obj = context.object
        if obj and obj.type == 'ARMATURE':
            armature = obj.data

            toRig = True

            for bone in armature.bones:
                if ".orient." in bone.name:
                    toRig = False
                    break
                elif ".proxy.rig" in bone.name:
                    toRig = False
                    break
                elif ".rig" in bone.name:
                    toRig = False
                    break
            
            if appVersion[0] == 4:
                col = layout.column(align=False)
                col.enabled = toRig

                #Unhide all Bones
                row = col.row(align=True)
                row.label(text="Unhide All")
                row.operator('rotf.unhide_all_bones', text="", icon='VIS_SEL_11')

                #Hide Bones in Hidden
                row = col.row(align=True)
                row.label(text="RotF Hidden")

                boneCollectionName = boneCollections.RotFUnusedColName
                row.enabled = bool(armature.collections.get(boneCollectionName))
                
                show_Hidden = row.operator('rotf.show_rotf_collection', text="", icon='VIS_SEL_11')
                show_Hidden.collectionName = boneCollectionName
                hide_Hidden = row.operator('rotf.hide_rotf_collection', text="", icon='VIS_SEL_00')
                hide_Hidden.collectionName = boneCollectionName

                #Show / Hide Bones in Unoriented
                row = col.row(align=True)
                row.label(text="RotF Hidden Unoriented")

                boneCollectionName = boneCollections.RotFUnoritentedColName
                row.enabled = bool(armature.collections.get(boneCollectionName))
                
                show_FKHidden = row.operator('rotf.show_rotf_collection', text="", icon='VIS_SEL_11')
                show_FKHidden.collectionName = boneCollectionName
                hide_FKHidden = row.operator('rotf.hide_rotf_collection', text="", icon='VIS_SEL_00')
                hide_FKHidden.collectionName = boneCollectionName
                
                #Show/Hide Bones in FK
                row = col.row(align=True)
                row.label(text="RotF Hidden FK")

                boneCollectionName = boneCollections.RotFHiddenFKColName
                row.enabled = bool(armature.collections.get(boneCollectionName))
                
                show_FKHidden = row.operator('rotf.show_rotf_collection', text="", icon='VIS_SEL_11')
                show_FKHidden.collectionName = boneCollectionName
                hide_FKHidden = row.operator('rotf.hide_rotf_collection', text="", icon='VIS_SEL_00')
                hide_FKHidden.collectionName = boneCollectionName
                
                
                #Show/Hide Rotation Distribution
                row = col.row(align=True)
                row.label(text="RotF Hidden Rotation Distribution")

                boneCollectionName = boneCollections.RotFHiddenRotDistColName
                row.enabled = bool(armature.collections.get(boneCollectionName))
                
                show_RotDistHidden = row.operator('rotf.show_rotf_collection', text="", icon='VIS_SEL_11')
                show_RotDistHidden.collectionName = boneCollectionName
                hide_RotDistHidden = row.operator('rotf.hide_rotf_collection', text="", icon='VIS_SEL_00')
                hide_RotDistHidden.collectionName = boneCollectionName
                
            elif appVersion[0] == 3:
                col = layout.column(align=True)

                col.enabled = toRig

                col.prop(obj, "baseBonesLayer", text="Base Bones")
                col.prop(obj, "unusedRigBonesLayer", text="Unused Controllers")

                col = layout.column(align=True)

                col.enabled = toRig

                col.label(text="Orient Rig Only")
                col.prop(obj, "notOrientedBonesLayer", text="Unoriented Bones")

#Overrides Armature's Bone Collections' Property widow with one that includes hide/unhide bones in collection
class DATA_UL_bone_collections(UIList):
    def draw_item(self, _context, layout, armature, bcoll, _icon, _active_data, _active_propname, _index):
        active_bone = armature.edit_bones.active or armature.bones.active
        has_active_bone = active_bone and bcoll.name in active_bone.collections
    
        layout.prop(bcoll, "name", text="", emboss=False,
                    icon='DOT' if has_active_bone else 'BLANK1')

        if armature.override_library:
            icon = 'LIBRARY_DATA_OVERRIDE' if bcoll.is_local_override else 'BLANK1'
            layout.prop(
                bcoll,
                "is_local_override",
                text="",
                emboss=False,
                icon=icon)

        boneCollectionName = bcoll.name

        show_RotDistHidden = layout.operator('rotf.show_rotf_collection', text="", icon='VIS_SEL_11')
        show_RotDistHidden.collectionName = boneCollectionName

        hide_RotDistHidden = layout.operator('rotf.hide_rotf_collection', text="", icon='VIS_SEL_00')
        hide_RotDistHidden.collectionName = boneCollectionName

        layout.prop(bcoll, "is_visible", text="", emboss=False,
                    icon='HIDE_OFF' if bcoll.is_visible else 'HIDE_ON')

        
        
