import time
from typing import Optional

import bpy
from bpy.app.handlers import persistent
from bpy.types import Mesh

from ...common.logging import get_logger
from ..extension import get_material_extension
from . import migration
from .ops import VRM_OT_refresh_mtoon1_outline

logger = get_logger(__name__)


previous_object_material_state: list[list[Optional[tuple[str, bool, bool]]]] = []


def update_mtoon1_outline() -> Optional[float]:
    context = bpy.context

    compare_start_time = time.perf_counter()

    # Optimize appropriately.
    has_auto_smooth = tuple(bpy.app.version) < (4, 1)
    object_material_state = [
        [
            (
                material_slot.material.name,
                get_material_extension(
                    material_slot.material
                ).mtoon1.get_enabled_in_material(material_slot.material),
                has_auto_smooth and obj.data.use_auto_smooth,
            )
            if material_slot.material
            else None
            for material_slot in obj.material_slots
        ]
        for obj in context.blend_data.objects
        if isinstance(obj.data, Mesh)
    ]
    not_changed = object_material_state == previous_object_material_state

    compare_end_time = time.perf_counter()

    logger.debug(
        "The duration to determine material updates is %.9f seconds",
        compare_end_time - compare_start_time,
    )

    if not_changed:
        return None
    previous_object_material_state.clear()
    previous_object_material_state.extend(object_material_state)

    VRM_OT_refresh_mtoon1_outline.refresh(bpy.context, create_modifier=False)
    return None


def trigger_update_mtoon1_outline() -> None:
    if bpy.app.version < (3, 3):
        return
    if bpy.app.timers.is_registered(update_mtoon1_outline):
        return
    bpy.app.timers.register(update_mtoon1_outline, first_interval=0.2)


@persistent
def save_pre(_unused: object) -> None:
    update_mtoon1_outline()


@persistent
def depsgraph_update_pre(_unused: object) -> None:
    trigger_update_mtoon1_outline()


@persistent
def load_post(_unsed: object) -> None:
    migration.state.material_blender_4_2_warning_shown = False
