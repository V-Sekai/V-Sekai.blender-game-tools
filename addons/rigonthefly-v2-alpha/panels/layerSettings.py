import bpy

from .main import ToolPanel, separator
from ..operators import info
from ..core.icon_manager import Icons

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
    name="unusedRigBonesLayer", description="Where temporarly unused rig bones are sent to", default=1, min=0, max=31, update=update_UnusedRigBonesLayer)
bpy.types.Object.notOrientedBonesLayer = bpy.props.IntProperty(
    name="notOrientedBonesLayer", description="Where not-oriented bones are sent to", default=2, min=0, max=31, update=update_NotOrientedBonesLayer)


class LayerSettingsPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rsl_layerSettings'
    bl_label = 'Layer Settings'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        #if not self.DisplayCondition(context):
        #    return

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

            col = layout.column(align=True)

            col.enabled = toRig

            col.prop(obj, "baseBonesLayer", text="Base Bones")
            col.prop(obj, "unusedRigBonesLayer", text="Unused Controllers")

            col = layout.column(align=True)

            col.enabled = toRig

            col.label(text="Orient Rig Only")
            col.prop(obj, "notOrientedBonesLayer", text="Unoriented Bones")
