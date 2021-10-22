#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

bl_info = {
    "name" : "RigOnTheFly",
    "author" : "Dypsloom",
    "description" : "",
    "blender" : (2, 80, 5),
    "version" : (1, 0, 1),
    "location" : "View3D",
    "warning" : "",
    "category" : "Animation & Rig"
}

import bpy

from . OffsetKeysOperator import OffsetKeysOperator
from . DypsloomBakeOperator import DypsloomBakeOperator
from . PolygonShapesUtilityOperator import PolygonShapesUtilityOperator
from . AutoBoneOrientOperator import AutoBoneOrientOperator
from . RigOnSkeletonOperator import RigOnSkeletonOperator
from . RigProxyOperator import RigProxyOperator
from . BakeProxyOperator import BakeProxyOperator
from . BakeOnSkeletonOperator import BakeOnSkeletonOperator
from . BakeOrientOnSkeletonOperator import BakeOrientOnSkeletonOperator
from . ControllerSizePlusOperator import ControllerSizePlusOperator
from . ControllerSizeMinusOperator import ControllerSizeMinusOperator
from . KeyRangeOperator import KeyRangeOperator
from . IKLimbOperator import IKLimbOperator
from . IKLimbNoPoleOperator import IKLimbNoPoleOperator
from . IKLimbPoleAngleOperator import IKLimbPoleAngleOperator
from . FKLimbOperator import FKLimbOperator
from . RotationModeOperator import RotationModeOperator
from . InheritRotationOffOperator import InheritRotationOffOperator
from . InheritRotationOnOperator import InheritRotationOnOperator
from . InheritScaleOffOperator import InheritScaleOffOperator
from . InheritScaleOnOperator import InheritScaleOnOperator
from . RotationDistributionOperator import RotationDistributionOperator
from . ApplyDistributionOperator import ApplyDistributionOperator
from . AddTwistOperator import AddTwistOperator
from . RemoveTwistOperator import RemoveTwistOperator
from . WorldPositionOperator import WorldPositionOperator
from . RemoveWorldTransformsOperator import RemoveWorldTransformsOperator
from . IKChainOperator import IKChainOperator
from . AimWorldOperator import AimWorldOperator
from . StretchWorldOperator import StretchWorldOperator
from . AimOffsetOperator import AimOffsetOperator
from . AimChainOperator import AimChainOperator
from . StretchChainOperator import StretchChainOperator
from . LocalAimChainOperator import LocalAimChainOperator
from . LocalStretchChainOperator import LocalStretchChainOperator
from . RemoveLocalAimChainOperator import RemoveLocalAimChainOperator
from . RemoveAimSpaceOperator import RemoveAimSpaceOperator
from . ParentSpaceOperator import ParentSpaceOperator
from . ParentSpaceCopyOperator import ParentSpaceCopyOperator
from . RestoreSelectedChildrenOperator import RestoreSelectedChildrenOperator
from . RestoreSiblingsPerObjectOperator import RestoreSiblingsPerObjectOperator
from . AddExtraBoneOperator import AddExtraBoneOperator
from . DeleteBonesOperator import DeleteBonesOperator
from . CenterOfMassOperator import CenterOfMassOperator
from . TranslationInertiaOperator import TranslationInertiaOperator
from . RotationInertiaOperator import RotationInertiaOperator
from . ScaleInertiaOperator import ScaleInertiaOperator
from . RigOnTheFly import ROTF_PT_RigOnTheFly, ROTF_PT_RigBake, ROTF_PT_BoneLayers, ROTF_PT_Settings, ROTF_PT_Keyframes, ROTF_PT_IKFKSwitch, ROTF_PT_RotationScaleTool, ROTF_PT_ExtraBone, ROTF_PT_SpaceSwitch, ROTF_PT_AimSpace, ROTF_PT_InertiaOnTransforms, RotationModeMenu, RestoreParentMenu

classes = (
    OffsetKeysOperator,
    DypsloomBakeOperator,
    PolygonShapesUtilityOperator,
    AutoBoneOrientOperator,
    RigOnSkeletonOperator, 
    RigProxyOperator,
    BakeProxyOperator,
    BakeOnSkeletonOperator,
    BakeOrientOnSkeletonOperator,
    ControllerSizePlusOperator, 
    ControllerSizeMinusOperator, 
    KeyRangeOperator, 
    IKLimbOperator, 
    IKLimbNoPoleOperator,
    IKLimbPoleAngleOperator, 
    FKLimbOperator, 
    RotationModeOperator,
    InheritRotationOffOperator, 
    InheritScaleOffOperator, 
    InheritRotationOnOperator, 
    InheritScaleOnOperator,
    RotationDistributionOperator,
    ApplyDistributionOperator,
    AddTwistOperator,
    RemoveTwistOperator,
    WorldPositionOperator,
    RemoveWorldTransformsOperator,
    IKChainOperator,
    AimWorldOperator,
    StretchWorldOperator,
    AimOffsetOperator,
    AimChainOperator,
    StretchChainOperator,
    LocalAimChainOperator,
    LocalStretchChainOperator,
    RemoveLocalAimChainOperator,
    RemoveAimSpaceOperator, 
    ParentSpaceOperator, 
    ParentSpaceCopyOperator,
    RestoreSelectedChildrenOperator, 
    RestoreSiblingsPerObjectOperator,
    AddExtraBoneOperator, 
    DeleteBonesOperator,
    CenterOfMassOperator, 
    TranslationInertiaOperator, 
    RotationInertiaOperator, 
    ScaleInertiaOperator, 
    ROTF_PT_RigOnTheFly,
    ROTF_PT_RigBake,
    ROTF_PT_BoneLayers,
    ROTF_PT_Settings,
    ROTF_PT_Keyframes,
    ROTF_PT_IKFKSwitch,
    ROTF_PT_RotationScaleTool,
    ROTF_PT_ExtraBone,
    ROTF_PT_SpaceSwitch,
    ROTF_PT_AimSpace,
    ROTF_PT_InertiaOnTransforms,
    RotationModeMenu,
    RestoreParentMenu
)

register, unregister = bpy.utils.register_classes_factory(classes)