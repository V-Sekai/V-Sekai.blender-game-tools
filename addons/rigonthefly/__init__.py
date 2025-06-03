#########################################
#######       Rig On The Fly      #######
####### Copyright © 2024 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

# Important plugin info for Blender
bl_info = {
    'name': 'Rig On The Fly 2.0',
    'author': 'Dypsloom',
    'category': 'Animation',
    'location': 'View 3D > Tool Shelf > Rig On The Fly 2.0',
    'description': '',
    'version': (2, 0, 8),
    'blender': (4, 2, 0)
}

# If first startup of this plugin, load all modules normally
# If reloading the plugin, use importlib to reload modules
# This lets you do adjustments to the plugin on the fly without having to restart Blender


import sys

if "bpy" not in locals():
    import bpy
    from . import core
    from . import panels
    from . import operators
    from . import properties
else:
    import importlib
    importlib.reload(core)
    importlib.reload(panels)
    importlib.reload(operators)
    importlib.reload(properties)


# List of all buttons and panels
classes = [  # These panels will always be loaded, all panel ui should go in here
    operators.controllerShapeSettings.ControllerSizeMinusOperator,
    operators.controllerShapeSettings.ControllerSizePlusOperator,
    operators.boneCollections.UnhideAllBonesOperator,
    operators.boneCollections.ShowROTFCollectionOperator,
    operators.boneCollections.HideROTFCollectionOperator,
    operators.armatureTools.BaseControllerShapeOperator,
    operators.armatureTools.ProxyOperator,
    operators.armatureTools.RemoveProxyOperator,
    operators.armatureTools.OrientOperator,
    operators.armatureTools.AddBoneOperator,
    operators.armatureTools.RootMotionOperator,
    operators.armatureTools.RemoveRootMotionOperator,
    operators.centerOfMass.CenterOfMassOperator,
    operators.centerOfMass.AddToCenterOfMassOperator,
    operators.centerOfMass.RemoveFromCenterOfMassOperator,
    operators.centerOfMass.RemoveCenterOfMassOperator,
    operators.rotationScaleTools.RotationModeAndRelationsOperator,
    operators.rotationScaleTools.InheritRotationOperator,
    operators.rotationScaleTools.InheritScaleOperator,
    operators.rotationScaleTools.RotationDistributionOperator,
    operators.rotationScaleTools.ApplyRotationDistributionOperator,
    operators.ikfkSwitch.IKLimbOperator,
    operators.ikfkSwitch.FKLimbOperator,
    operators.ikfkSwitch.IKStretchOperator,
    operators.ikfkSwitch.RemoveIKStretchOperator,
    operators.worldSpace.WorldSpaceOperator,
    operators.worldSpace.RemoveWorldSpaceOperator,
    operators.aimSpace.AimSpaceOperator,
    operators.aimSpace.AimOffsetSpaceOperator,
    operators.aimSpace.RemoveAimSpaceOperator,
    operators.parentSpace.ParentSpaceOperator,
    operators.parentSpace.ParentCopySpaceOperator,
    operators.parentSpace.ParentOffsetSpaceOperator,
    operators.parentSpace.RemoveParentSpaceOperator,
    operators.parentSpace.RemoveParentSpaceSiblingsOperator,
    operators.reverseHierarchySpace.ReverseHierarchySpaceOperator,
    operators.reverseHierarchySpace.RestoreHierarchySpaceOperator,
    operators.simpleConstraints.SimpleCopyTransformsOperator,
    operators.simpleConstraints.SimpleAimOperator,
    operators.simpleConstraints.RemoveSimpleConstraintsOperator,
    operators.simpleConstraints.BakeSimpleConstraintsOperator,
    operators.keyframeTools.KeyRangeOperator,
    operators.keyframeTools.OffsetKeysOperator,
    operators.keyframeTools.KeyAsActiveOperator,
    operators.dynamics.DynamicsOperator,
    operators.rigState.SaveRigStateOperator,
    operators.rigState.LoadFilePathOperator,
    operators.rigState.LoadRigStateOperator,
    operators.rigState.RefreshFilePathOperator,
    operators.rigState.BakeRigOperator,
    operators.singleFramePose.SetUpSingleFramePoseOperator,
    operators.singleFramePose.ApplySingleFramePoseOperator,

    panels.bakeSettings.BakeSettingsPanel,
    panels.controllerShapeSettings.ControllerShapeSettingsPanel,
    panels.layerSettings.LayerSettingsPanel,
    panels.layerSettings.DATA_UL_bone_collections, #Test
    panels.armatureTools.ArmatureToolsPanel,
    panels.armatureTools.ArmatureTools_CS_Panel,
    panels.centerOfMass.CenterOfMassPanel,
    panels.centerOfMass.CenterOfMass_CS_Panel,
    panels.rotationScaleTools.RotationScaleToolsPanel,
    panels.rotationScaleTools.RotationModeAndRelations_MT_Panel,
    panels.rotationScaleTools.RotationScaleTools_CS_Panel,
    panels.ikfkSwitch.IKFKSwitchPanel,
    panels.ikfkSwitch.IKFKSwitch_CS_Panel,
    panels.spaceSwitch.SpaceSwitchPanel,
    panels.spaceSwitch.SpaceSwitch_CS_Panel,
    panels.simpleConstraints.SimpleConstraintsPanel,
    panels.keyframeTools.KeyframeToolsPanel,
    panels.dynamics.DynamicsPanel,
    panels.rigState.RigStatePanel,
    panels.singleFramePose.SingleFramePosePanel,
    panels.info.InfoPanel,

    properties.RigStateFilePaths,
    properties.BonePointer,
    properties.BoneProperty,
    properties.BoolPropertyGroup,
    properties.StringPropertyGroup,
    properties.IntPropertyGroup,
    properties.FloatPropertyGroup,
    properties.Constraint,
    properties.NLAState
]

# register and unregister all classes
def register():
    print("\n### Loading Rig On The Fly 2 ...")

    # Register classes
    for cls in classes:
        bpy.utils.register_class(cls)

    # Register all custom propreties
    properties.register()

    # Load custom icons
    core.icon_manager.load_icons()

    print("### Loaded Rig On The Fly 2 successfully!\n")


def unregister():
    print("### Unloading Rig On The Fly 2 ...")

    # Unregister all classes
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass

    # Unload all custom icons
    core.icon_manager.unload_icons()

    print("### Unloaded Rig On The Fly 2 successfully!\n")


if __name__ == '__main__':
    register()

