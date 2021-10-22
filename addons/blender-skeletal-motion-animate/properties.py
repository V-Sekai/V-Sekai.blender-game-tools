from bpy.types import Scene, Object
from bpy.props import IntProperty, StringProperty, EnumProperty, BoolProperty, FloatProperty, CollectionProperty, PointerProperty

from .core import animation_lists, state_manager, retargeting
from .panels import retargeting as retargeting_ui


def register():
    Scene.rsl_scene_scaling = FloatProperty(
        name='Scene Scaling',
        description="This allows you to scale the position of props and trackers."
                    "\nUseful to align their positions with armatures",
        default=1,
        precision=3,
        step=1
    )
    Scene.rsl_reset_scene_on_stop = BoolProperty(
        name='Reset Scene on Stop',
        description='This will reset the location and position of animated objects to the state of before starting the receiver',
        default=True
    )

    # Retargeting
    Scene.rsl_retargeting_armature_source = PointerProperty(
        name='Source',
        description='Select the armature with the animation that you want to retarget',
        type=Object,
        poll=retargeting.poll_source_armatures,
        update=retargeting.clear_bone_list
    )
    Scene.rsl_retargeting_armature_target = PointerProperty(
        name='Target',
        description='Select the armature that should receive the animation',
        type=Object,
        poll=retargeting.poll_target_armatures,
        update=retargeting.clear_bone_list
    )
    Scene.rsl_retargeting_auto_scaling = BoolProperty(
        name='Auto Scale',
        description='This will scale the source armature to fit the height of the target armature.'
                    '\nBoth armatures have to be in T-pose for this to work correctly',
        default=True
    )
    Scene.rsl_retargeting_use_pose = EnumProperty(
        name="Use Pose",
        description='Select which pose of the source and target armature to use to retarget the animation.'
                    '\nBoth armatures should be in the same pose before retargeting',
        items=[
            ("REST", "Rest", "Select this to use the rest pose during retargeting."),
            ("CURRENT", "Current", "Select this to use the current pose during retargeting.")
        ]
    )
    Scene.rsl_retargeting_bone_list = CollectionProperty(
        type=retargeting_ui.BoneListItem
    )
    Scene.rsl_retargeting_bone_list_index = IntProperty(
        name="Index for the retargeting bone list",
        default=0
    )
