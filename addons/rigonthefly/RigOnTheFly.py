#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy

def startFrameUpdate(self, context):
    obj = context.object
    if obj == None:
        return
    if obj.startFrame > obj.endFrame:
        obj.endFrame = obj.startFrame


def endFrameUpdate(self, context):
    obj = context.object
    if obj == None:
        return
    if obj.startFrame > obj.endFrame:
        obj.startFrame = obj.endFrame


def smartRangeStartUpdate(self, context):
    scene = context.scene
    if scene == None:
        return
    if scene.smartRangeStart > scene.smartRangeEnd:
        scene.smartRangeEnd = scene.smartRangeStart


def smartRangeEndUpdate(self, context):
    scene = context.scene
    if scene == None:
        return
    if scene.smartRangeStart > scene.smartRangeEnd:
        scene.smartRangeStart = scene.smartRangeEnd


def LayerIsOccupied(self, context, value):
    obj = context.object
    if obj == None:
        return
    return value == obj.baseBonesLayer or value == obj.rigBonesLayer or value == obj.unusedRigBonesLayer or value == obj.notOrientedBonesLayer or value == obj.translatorBonesLayer


def UpdateLayer(self, context, value, name):
    obj = context.object
    if obj == None:
        return
    newValue = value + (-1 if LayerIsOccupied(self, context, value+1) else 1)

    if value == obj.baseBonesLayer and name != "baseBonesLayer":
        obj.baseBonesLayer = newValue
    if value == obj.rigBonesLayer and name != "rigBonesLayer":
        obj.rigBonesLayer = newValue
    if value == obj.unusedRigBonesLayer and name != "unusedRigBonesLayer":
        obj.unusedRigBonesLayer = newValue
    if value == obj.notOrientedBonesLayer and name != "notOrientedBonesLayer":
        obj.notOrientedBonesLayer = newValue
    if value == obj.translatorBonesLayer and name != "translatorBonesLayer":
        obj.translatorBonesLayer = newValue


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


def update_TranslatorBonesLayer(self, context):
    UpdateLayer(self, context, context.object.translatorBonesLayer,
                "translatorBonesLayer")


# bpy.boneSelection will store bone in order of selection
bpy.boneSelection = []


def select():
    # function inspired by Alfonso Serra's Curve Tool's Object selection Order
    if bpy.context.mode == "POSE":
        selectionLength = len(bpy.context.selected_pose_bones)

        if selectionLength == 0:
            bpy.boneSelection = []
        else:
            if selectionLength == 1:
                bpy.boneSelection = []
                bpy.boneSelection.append(bpy.context.selected_pose_bones[0])
            elif selectionLength > len(bpy.boneSelection):
                for selectedPBone in bpy.context.selected_pose_bones:
                    if (selectedPBone in bpy.boneSelection) == False:
                        bpy.boneSelection.append(selectedPBone)

            elif selectionLength < len(bpy.boneSelection):
                for pbone in bpy.boneSelection:
                    if (pbone in bpy.context.selected_pose_bones) == False:
                        bpy.boneSelection.remove(pbone)


bpy.types.Object.aimDistance = bpy.props.FloatProperty(
    name="aimDistance", default=1, min=0)

bpy.types.Object.startFrame = bpy.props.IntProperty(
    name="startFrame", default=1, update=startFrameUpdate)
bpy.types.Object.endFrame = bpy.props.IntProperty(
    name="endFrame", default=100, update=endFrameUpdate)
bpy.types.Object.inertia = bpy.props.FloatProperty(
    name="inertia", default=0.2, min=0, max=1)

bpy.types.Scene.orientRig = bpy.props.BoolProperty(
    name="orientRig", description="Turn this option ON before rigging if the armature's bones are not oriented appropriately for Blender", default=False)

bpy.types.Scene.smartChannels = bpy.props.BoolProperty(
    name="smartChannels", description="When checked ON, any baking will result in keys only on used transform channels, instead of keys on all transform channels. Ideal when working with animation layers", default=False)
bpy.types.Scene.smartFrames = bpy.props.BoolProperty(
    name="smartFrames", description="When checked ON, any baking will result in keys only on frames where they were previously, instead of keys every frame. Ideal for the basic posing phase", default=False)

bpy.types.Scene.smartRangeStart = bpy.props.IntProperty(
    name="smartRangeStart", default=1, update=smartRangeStartUpdate)
bpy.types.Scene.smartRangeEnd = bpy.props.IntProperty(
    name="smartRangeEnd", default=10, update=smartRangeEndUpdate)
bpy.types.Scene.smartRangeStep = bpy.props.IntProperty(
    name="smartRangeStep", default=1, min=1)

bpy.types.Scene.offsetValue = bpy.props.FloatProperty(
    name="offsetValue", default=1.0)

bpy.types.Scene.ikStretch = bpy.props.BoolProperty(
    name="ikStretch", description="When checked ON, enables stretching for IK and IK no P", default=False)

bpy.types.Scene.rotf_ik_default_pole_axis = bpy.props.EnumProperty(
    name="",
    description="Axis used for setting the Pole Vector if Limb is Straight",
    items=[
        ('+X', "+X", "", 1),
        ('-X', "- X", "", 2),
        ('+Z', "+Z", "", 3),
        ('-Z', "- Z", "", 4)
        ]
    )

bpy.types.Scene.selectionOrder = bpy.props.StringProperty(
    name="selectionOrder", description="string list of selected pose bones in order of selection", default="")

bpy.types.Object.baseBonesLayer = bpy.props.IntProperty(
    name="baseBonesLayer", description="Where bones that are directly driven by rig bones are sent to", default=0, min=0, max=31, update=update_BaseBoneslayer)
bpy.types.Object.rigBonesLayer = bpy.props.IntProperty(
    name="rigBonesLayer", description="Where rig bones used for animation are sent to", default=1, min=0, max=31, update=update_RigBoneslayer)
bpy.types.Object.unusedRigBonesLayer = bpy.props.IntProperty(
    name="unusedRigBonesLayer", description="Where temporarly unused rig bones are sent to", default=2, min=0, max=31, update=update_UnusedRigBonesLayer)
bpy.types.Object.notOrientedBonesLayer = bpy.props.IntProperty(
    name="notOrientedBonesLayer", description="Where not-oriented bones are sent to", default=3, min=0, max=31, update=update_NotOrientedBonesLayer)
bpy.types.Object.translatorBonesLayer = bpy.props.IntProperty(
    name="translatorBonesLayer", description="Where bones used to translate rig bones motion to not-oriented bones are sent to", default=4, min=0, max=31, update=update_TranslatorBonesLayer)


bpy.types.Object.aimAxis = bpy.props.EnumProperty(
    name="",
    description="Axis used for World Aim & Stretch Aim",
    items=[
        ('+Y', "+Y", "", 1),
        ('-Y', "- Y", "", 2),
        ('+X', "+X", "", 3),
        ('-X', "- X", "", 4),
        ('+Z', "+Z", "", 5),
        ('-Z', "- Z", "", 6)
    ])


class RigOnTheFlyBase:
    bl_category = "Rig on the Fly"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def DisplayCondition(self, context):
        obj = bpy.context.object
        if obj:
            if obj.type == 'ARMATURE':
                self.bl_options = {'DEFAULT_CLOSED'}
                return True
        else:
            #self.bl_options= {'HIDE_HEADER'}
            return False

    def Header(self, context):
        return True
        """
        obj = bpy.context.object
        if obj.type == 'ARMATURE':
            self.bl_options= {'DEFAULT_CLOSED'}
            return True
        else:
            self.bl_options= {'HIDE_HEADER'}
            return False
        """

class ROTF_PT_RigOnTheFly(RigOnTheFlyBase, bpy.types.Panel):
    bl_idname = "DYPSLOOM_PT_RigOnTheFly"
    bl_label = "Rig on the Fly : v 1.0.1"  # tab name

    def __init__(self):
        select()

    def draw(self, context):
        obj = bpy.context.object
        notArmature = False
        if obj:
            if not obj.type == 'ARMATURE':
                notArmature = True
        else:
            notArmature = True

        if notArmature:
            layout = self.layout
            row = layout.row(align=True)
            row.scale_y = 1.5
            row.label(text="   Select an Armature", icon='ERROR')

            self.drawCondition = False
            return


class ROTF_PT_RigBake(RigOnTheFlyBase, bpy.types.Panel):
    bl_parent_id = "DYPSLOOM_PT_RigOnTheFly"
    bl_label = "1. Rig & Bake"

    def draw_header(self, context):
        if not self.Header(context):
            return

        layout = self.layout
        row = layout.row(align=True)
        row.label(icon='ARMATURE_DATA')

    def draw(self, context):

        # Conditions------------------------------------------------------------------------------------
        scene = context.scene
        if scene == None:
            return

        obj = bpy.context.object
        if not self.DisplayCondition(context):
            return

        armature = obj.data

        rigSkeleton = False
        bakeRig = False
        orientRig = False
        bakeOrient = False
        rigProxy = False
        bakeProxy = False

        isRigged = False

        if obj.proxy or obj.override_library:
            rigProxy = True
        else:
            for bone in armature.bones:
                if ".orient." in bone.name:
                    bakeOrient = True
                    bakeRig = True
                    isRigged = True
                    break
                elif ".proxy." in bone.name:
                    bakeProxy = True
                    isRigged = True
                    break
                elif ".rig" in bone.name:
                    bakeRig = True
                    isRigged = True
                    break
            if not isRigged:
                rigSkeleton = True
                orientRig = True

        # Panels---------------------------------------------------------------------------------------
        layout = self.layout
        rowSizeY = 1.4

        row = layout.row(align=True)
        row.scale_y = rowSizeY

        row.prop(scene, "orientRig", text="Orient Rig")

        row = layout.row(align=True)
        row.scale_y = rowSizeY

        subRow = row.row(align=True)
        subRow.operator('view3d.rig_on_skeleton_operator',
                        text="Rig Skeleton", icon='ARMATURE_DATA')
        subRow.enabled = rigSkeleton

        subRow = row.row(align=True)
        subRow.operator('view3d.bake_on_skeleton_operator',
                        text="Bake Rig", icon='OUTLINER_OB_ARMATURE')
        subRow.enabled = bakeRig

        row = layout.row(align=True)
        row.scale_y = rowSizeY

        row = layout.row(align=True)
        row.scale_y = rowSizeY

        subRow = row.row(align=True)
        subRow.operator('view3d.rig_proxy_operator',
                        text="Rig Proxy", icon='ARMATURE_DATA')
        subRow.enabled = rigProxy

        subRow = row.row(align=True)
        subRow.operator('view3d.bake_proxy_operator',
                        text="Bake Proxy", icon='OUTLINER_OB_ARMATURE')
        subRow.enabled = bakeProxy


class ROTF_PT_BoneLayers(RigOnTheFlyBase, bpy.types.Panel):
    bl_parent_id = "DYPSLOOM_PT_RigOnTheFly"
    bl_label = "2. Rig Layers Settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):

        if not self.Header(context):
            return

        layout = self.layout
        row = layout.row(align=True)
        row.label(icon='RENDERLAYERS')

    def draw(self, context):

        if not self.DisplayCondition(context):
            return

        layout = self.layout
        obj = context.object
        if obj.type == 'ARMATURE':
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
        col.prop(obj, "rigBonesLayer", text="Controllers")
        col.prop(obj, "unusedRigBonesLayer", text="Unused Controllers")

        col = layout.column(align=True)

        col.enabled = toRig

        col.label(text="Orient Rig Only")
        col.prop(obj, "notOrientedBonesLayer", text="Unoriented Bones")
        col.prop(obj, "translatorBonesLayer", text="Translator Bones")


class ROTF_PT_Settings(RigOnTheFlyBase, bpy.types.Panel):
    bl_parent_id = "DYPSLOOM_PT_RigOnTheFly"
    bl_label = "3. Settings"

    def draw_header(self, context):

        if not self.Header(context):
            return
        layout = self.layout
        row = layout.row(align=True)
        row.label(icon='PREFERENCES')

    def draw(self, context):
        layout = self.layout

        scene = context.scene
        if scene == None:
            return

        if not self.DisplayCondition(context):
            return

        row = layout.row(align=True)
        row.operator('view3d.controller_size_minus_operator',
                     text="-")  # , icon='ZOOM_OUT')
        row.operator('view3d.controller_size_plus_operator',
                     text="+")  # , icon='ZOOM_IN')
        row = row.row(align=True)
        row.scale_x = 1.3
        row.label(text="Controller Size")

        col = layout.column(align=True)
        col.scale_y = 1.3
        col.label(text="Smart Bake Options")
        col.prop(scene, "smartChannels", text="Smart Channels")
        row = col.row(align=True)
        row.prop(scene, "smartFrames", text="Smart Frames")

        row = layout.row()
        row.operator('view3d.polygon_shapes_operator',
                     text="Controller Shapes", icon='MESH_UVSPHERE')


class ROTF_PT_Keyframes(RigOnTheFlyBase, bpy.types.Panel):
    bl_parent_id = "DYPSLOOM_PT_RigOnTheFly"
    bl_label = "4. Keyframes"

    def draw_header(self, context):
        if not self.Header(context):
            return
        layout = self.layout
        row = layout.row(align=True)
        row.label(icon='DECORATE_KEYFRAME')

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        if scene == None:
            return
        if not self.DisplayCondition(context):
            return

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('view3d.key_range_operator',
                     text="Key Range", icon='KEYFRAME_HLT')
        row.prop(scene, "smartRangeStep", text="Step")
        row = col.row(align=True)
        row.prop(scene, "smartRangeStart", text="Start")
        row.prop(scene, "smartRangeEnd", text="End")

        row = layout.row(align=True)
        row.operator('view3d.offset_keys_operator',
                     text="Offset Keys", icon='NEXT_KEYFRAME')
        row.prop(scene, "offsetValue", text="Offset")


class ROTF_PT_IKFKSwitch(RigOnTheFlyBase, bpy.types.Panel):
    bl_parent_id = "DYPSLOOM_PT_RigOnTheFly"
    bl_label = "5. IK FK Switch"

    def draw_header(self, context):
        if not self.Header(context):
            return
        layout = self.layout
        row = layout.row(align=True)
        row.label(icon='CON_KINEMATIC')

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        if scene == None:
            return
        if not self.DisplayCondition(context):
            return

        hasIK = False
        if bpy.context.mode == 'POSE':
            for pbone in bpy.context.selected_pose_bones:
                if ".IK." in pbone.name:
                    hasIK = True
                else:
                    continue

        row = layout.row(align=True)
        row.scale_y = 1.3
        #row.scale_x = 0.1
        #row.label(text=(""))  # offset for ikStretch boolean box
        row.prop(scene, "ikStretch", text="IK Stretch")
        subrow = row.row(align=True)
        subrow.scale_x = 0.8
        subrow.label(text="If Straight")
        subrow.prop(scene,"rotf_ik_default_pole_axis")

        row = layout.row(align=True)
        col = row.column(align=True)
        col.operator('view3d.ik_limb_operator',
                     text="IK", icon='CON_KINEMATIC')
        col.operator('view3d.ik_limb_no_pole_operator',
                     text="IK no P", icon='CON_KINEMATIC')
        col.enabled = not hasIK

        col = row.column(align=True)
        col.scale_y = 2.0
        col.operator('view3d.fk_limb_operator', text="FK", icon='CON_ROTLIKE')
        col.enabled = hasIK

class ROTF_PT_RotationScaleTool(RigOnTheFlyBase, bpy.types.Panel):
    bl_parent_id = "DYPSLOOM_PT_RigOnTheFly"
    bl_label = "6. Rotation and Scale Tools"

    def draw_header(self, context):
        if not self.Header(context):
            return
        layout = self.layout
        row = layout.row(align=True)
        row.label(icon='ORIENTATION_GIMBAL')

    def draw(self, context):
        if not self.DisplayCondition(context):
            return

        topBone = False
        canDistribute = False
        canAddTwist = False
        if bpy.context.mode == 'POSE':
            for pbone in bpy.context.selected_pose_bones:
                if ".top." in pbone.name:
                    topBone = True
                    break
            if len(bpy.context.selected_pose_bones) > 1:
                canAddTwist = True

            if len(bpy.context.selected_pose_bones) > 2 and not topBone:
                canDistribute = True

        layout = self.layout
        layout.menu(RotationModeMenu.bl_idname, icon='ORIENTATION_GIMBAL')

        row = layout.row(align=True)
        subRow = row.row()
        subRow.operator('view3d.add_twist_operator', text="Add Twist")
        subRow.enabled = canAddTwist
        row.operator('view3d.remove_twist_operator', text='Remove Twist')

        row = layout.row(align=True)
        subRow = row.row()
        subRow.operator('view3d.rotation_distribution_operator',
                        text="Distribute", icon='STRANDS')
        subRow.enabled = canDistribute
        subRow = row.row()
        subRow.operator('view3d.apply_distribution_operator',
                        text="Apply", icon='MOD_THICKNESS')
        subRow.enabled = topBone

        row = layout.row(align=True)
        row.operator('view3d.inherit_rotation_on_operator', text="On")
        row.operator('view3d.inherit_rotation_off_operator', text="Off")
        row = row.row(align=True)
        row.scale_x = 1.4
        row.label(text="Inherit Rotation")

        row = layout.row(align=True)
        row.operator('view3d.inherit_scale_on_operator', text="On")
        row.operator('view3d.inherit_scale_off_operator', text="Off")
        row = row.row(align=True)
        row.scale_x = 1.4
        row.label(text="Inherit Scale")


class RotationModeMenu(bpy.types.Menu):
    bl_label = "   Rotation Mode"
    bl_idname = "ROTF_MT_rotationModeMenu"

    def draw(self, context):
        layout = self.layout

        layout.operator('view3d.rotation_mode_operator',
                        text="Quaternion").rotationMode = 'QUATERNION'
        layout.operator('view3d.rotation_mode_operator',
                        text="XYZ").rotationMode = 'XYZ'
        layout.operator('view3d.rotation_mode_operator',
                        text="XZY").rotationMode = 'XZY'
        layout.operator('view3d.rotation_mode_operator',
                        text="YXZ").rotationMode = 'YXZ'
        layout.operator('view3d.rotation_mode_operator',
                        text="YZX (default)").rotationMode = 'YZX'
        layout.operator('view3d.rotation_mode_operator',
                        text="ZXY").rotationMode = 'ZXY'
        layout.operator('view3d.rotation_mode_operator',
                        text="ZYX").rotationMode = 'ZYX'


class ROTF_PT_ExtraBone(RigOnTheFlyBase, bpy.types.Panel):
    bl_parent_id = "DYPSLOOM_PT_RigOnTheFly"
    bl_label = "7. Extra Controller"

    def draw_header(self, context):
        if not self.Header(context):
            return
        layout = self.layout
        row = layout.row(align=True)
        row.label(icon='EMPTY_AXIS')

    def draw(self, context):
        if not self.DisplayCondition(context):
            return

        layout = self.layout

        canDelete = False
        canCenterOfMass = False
        if bpy.context.selected_pose_bones:
            canDelete = True
            if len(bpy.context.selected_pose_bones) > 1:
                canCenterOfMass = True

        row = layout.row(align=True)
        row.operator('view3d.add_extra_bone_operator',
                     text="Add", icon='EMPTY_AXIS')
        subRow = row.row()
        subRow.operator('view3d.delete_bones_operator',
                        text="Delete", icon='SORTBYEXT')
        subRow.enabled = canDelete

        col = layout.column(align=True)
        col.operator('view3d.center_of_mass_operator',
                     text="Center of Mass", icon='TRACKER')
        col.enabled = canCenterOfMass


class ROTF_PT_SpaceSwitch(RigOnTheFlyBase, bpy.types.Panel):
    bl_parent_id = "DYPSLOOM_PT_RigOnTheFly"
    bl_label = "8. Space Switch"

    def draw_header(self, context):
        if not self.Header(context):
            return
        layout = self.layout
        row = layout.row(align=True)
        row.label(icon='ORIENTATION_GLOBAL')

    def draw(self, context):
        if not self.DisplayCondition(context):
            return

        canWorldBone = True
        worldBone = False
        childBone = False
        parentBone = False
        if bpy.context.mode == 'POSE':
            for pbone in bpy.context.selected_pose_bones:
                if ".top." in pbone.name:
                    canWorldBone = False
                if ".world." in pbone.name:
                    canWorldBone = False
                    worldBone = True
                if ".child." in pbone.name:
                    childBone = True
            if len(bpy.context.selected_pose_bones) > 1:
                parentBone = True

        layout = self.layout

        col = layout.column(align=True)
        col.label(text="World Space")
        row = col.row(align=True)
        subRow = row.row()
        subRow.operator('view3d.world_position_operator',
                        text="World Transforms", icon='ORIENTATION_GLOBAL')
        subRow.enabled = canWorldBone
        subRow = row.row()
        subRow.operator('view3d.remove_world_transforms_operator',
                        text="Remove World", icon='OBJECT_ORIGIN')
        subRow.enabled = worldBone

        col = layout.column(align=True)
        col.label(text="Parent Space")
        row = col.row(align=True)
        row.operator('view3d.parent_space_operator',
                     text="Parent", icon='PIVOT_ACTIVE')
        row.operator('view3d.parent_space_copy_operator',
                     text="Parent to Copy", icon='PIVOT_INDIVIDUAL')
        row.enabled = parentBone

        #layout.menu(RestoreParentMenu.bl_idname, icon='PIVOT_MEDIAN')
        row = col.row(align=True)
        row.operator('view3d.restore_selected_children_operator',
                     text="Restore Child")
        row.operator('view3d.restore_siblings_per_object_operator',
                     text="Restore Siblings")
        row.enabled = childBone


class RestoreParentMenu(bpy.types.Menu):
    bl_label = "Restore Parent"
    bl_idname = "ROTF_MT_restoreParentMenu"

    def draw(self, context):
        layout = self.layout

        layout.operator('view3d.restore_selected_children_operator',
                        text="Selected .child.rig")
        layout.operator('view3d.restore_siblings_per_object_operator',
                        text="All related .child.rig")
        #layout.operator('view3d.restore_selected_children_operator', text="All .child.rig under selected parent")


class ROTF_PT_AimSpace(RigOnTheFlyBase, bpy.types.Panel):
    bl_parent_id = "DYPSLOOM_PT_RigOnTheFly"
    bl_label = "9. Aim Space"

    def draw_header(self, context):
        if not self.Header(context):
            return
        layout = self.layout
        row = layout.row(align=True)
        row.label(icon='CON_TRACKTO')

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene == None:
            return
        obj = context.object

        if not self.DisplayCondition(context):
            return

        aimBone = False
        canAimBone = True
        canStretchBone = True
        canAimChain = False
        canLocalAimChain = False
        if bpy.context.mode == 'POSE':
            for pbone in bpy.context.selected_pose_bones:
                if ".top." in pbone.name:
                    canStretchBone = False
                if ".aim." in pbone.name:
                    aimBone = True
                    canAimBone = False
                for constraint in pbone.constraints:
                    if constraint.type == 'STRETCH_TO' or constraint.type == 'IK' or constraint.type == 'DAMPED_TRACK':
                        canAimBone = False
        if bpy.context.selected_pose_bones:
            if len(bpy.context.selected_pose_bones) > 1:
                canLocalAimChain= True
                if canAimBone:
                    canAimChain = True

        col = layout.column(align=True)
        row = col.row(align=True)
        subRow = row.row()
        subRow.operator('view3d.aim_world_operator',
                        text="World Aim", icon='CON_TRACKTO')
        subRow.enabled = canAimBone
        subRow = row.row()
        subRow.operator('view3d.stretch_world_operator',
                        text="World Stretch", icon='CON_STRETCHTO')
        subRow.enabled = canStretchBone

        row = col.row(align=True)
        row.prop(obj, "aimAxis")
        row.scale_x = 2.5
        row.prop(obj, "aimDistance", text="Distance", icon='CON_DISTLIMIT')

        row = layout.row(align=True)
        row.operator('view3d.aim_offset_operator',
                     text="Aim Offset", icon='CON_LOCKTRACK')
        row.enabled = canAimBone

        row = layout.row(align=True)
        row.operator('view3d.aim_chain_operator',
                     text="Aim Chain", icon='CON_CHILDOF')
        row.operator('view3d.stretch_chain_operator',
                     text="Stretch Chain", icon='CON_CHILDOF')
        row.enabled = canAimChain

        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator('view3d.remove_aim_space_operator',
                     text="Remove Aim", icon='CON_SHRINKWRAP')
        row.enabled = aimBone

        col = layout.column(align=True)
        col.label(text = "Simple Constraints")
        row = col.row(align=True)
        row.operator('view3d.local_aim_chain_operator',
                     text="Aim Chain", icon='CON_CHILDOF')
        row.operator('view3d.local_stretch_chain_operator',
                     text="Stretch Chain", icon='CON_CHILDOF')
        row.enabled = canLocalAimChain

        col.operator('view3d.remove_local_aim_chain_operator',
                    text="Remove Local Aim", icon='CON_SHRINKWRAP')

class ROTF_PT_InertiaOnTransforms(RigOnTheFlyBase, bpy.types.Panel):
    bl_parent_id = "DYPSLOOM_PT_RigOnTheFly"
    bl_label = "10. Inertia On Transforms"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        if not self.Header(context):
            return
        layout = self.layout
        row = layout.row(align=True)
        row.label(icon='IPO_ELASTIC')

    def draw(self, context):
        layout = self.layout
        obj = context.object
        if not self.DisplayCondition(context):
            return

        col = layout.column(align=True)

        row = col.row(align=True)
        row.prop(obj, "startFrame", text="Start")
        row.prop(obj, "endFrame", text="End")

        row = col.row(align=True)
        row.prop(obj, "inertia", text="Inertia Value", icon='IPO_ELASTIC')

        row = col.row(align=True)
        row.operator('view3d.translation_inertia_operator',
                     text="Loc", icon='CON_LOCLIMIT')
        row.operator('view3d.rotation_inertia_operator',
                     text="Rot", icon='CON_ROTLIMIT')
        row.operator('view3d.scale_inertia_operator',
                     text="Scale", icon='CON_SIZELIMIT')

