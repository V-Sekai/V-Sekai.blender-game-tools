import time
from typing import Optional

import bpy
from bpy.app.handlers import persistent
from mathutils import Vector

from ...common.logging import get_logger
from .property_group import Vrm1ExpressionPropertyGroup, Vrm1LookAtPropertyGroup

logger = get_logger(__name__)


@persistent
def frame_change_pre(_dummy: object) -> None:
    Vrm1ExpressionPropertyGroup.frame_change_post_shape_key_updates.clear()


@persistent
def frame_change_post(_dummy: object) -> None:
    for (
        shape_key_name,
        key_block_name,
    ), value in Vrm1ExpressionPropertyGroup.frame_change_post_shape_key_updates.items():
        shape_key = bpy.data.shape_keys.get(shape_key_name)
        if not shape_key:
            continue
        key_blocks = shape_key.key_blocks
        if not key_blocks:
            continue
        key_block = key_blocks.get(key_block_name)
        if not key_block:
            continue
        key_block.value = value
    Vrm1ExpressionPropertyGroup.frame_change_post_shape_key_updates.clear()


def update_look_at_preview() -> Optional[float]:
    compare_start_time = time.perf_counter()

    # ここは最適化の必要がある
    changed = any(
        True
        for ext in [armature.vrm_addon_extension for armature in bpy.data.armatures]
        if ext.is_vrm1()
        and ext.vrm1.look_at.enable_preview
        and ext.vrm1.look_at.preview_target_bpy_object
        and (
            Vector(ext.vrm1.look_at.previous_preview_target_bpy_object_location)
            - ext.vrm1.look_at.preview_target_bpy_object.location
        ).length_squared
        > 0
    )

    compare_end_time = time.perf_counter()

    # logger.debug(
    #     "The duration to determine look at preview updates is "
    #     + f"{compare_end_time - compare_start_time:.9f} seconds"
    # )

    if not changed:
        return None

    Vrm1LookAtPropertyGroup.update_all_previews(bpy.context)
    return None


@persistent
def save_pre(_dummy: object) -> None:
    update_look_at_preview()


def trigger_update_look_at_preview() -> None:
    if bpy.app.timers.is_registered(update_look_at_preview):
        return
    bpy.app.timers.register(update_look_at_preview, first_interval=0.2)


@persistent
def depsgraph_update_pre(_dummy: object) -> None:
    trigger_update_look_at_preview()
