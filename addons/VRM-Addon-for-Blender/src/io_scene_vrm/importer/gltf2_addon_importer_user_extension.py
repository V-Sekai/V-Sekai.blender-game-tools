import secrets
import string
from collections.abc import Sequence
from typing import Optional

from bpy.types import Image

from ..common.logging import get_logger

logger = get_logger(__name__)


class Gltf2AddonImporterUserExtension:
    current_import_id: Optional[str] = None

    @classmethod
    def update_current_import_id(cls) -> str:
        import_id = "BlenderVrmAddonImport" + (
            "".join(secrets.choice(string.digits) for _ in range(10))
        )
        cls.current_import_id = import_id
        return import_id

    @classmethod
    def clear_current_import_id(cls) -> None:
        cls.current_import_id = None

    # https://github.com/KhronosGroup/glTF-Blender-IO/blob/6f9d0d9fc1bb30e2b0bb019342ffe86bd67358fc/addons/io_scene_gltf2/blender/imp/gltf2_blender_image.py#L51
    def gather_import_image_after_hook(
        self, image: object, bpy_image: object, gltf_importer: object
    ) -> None:
        if self.current_import_id is None:
            return

        if not isinstance(bpy_image, Image):
            logger.warning(
                "gather_import_image_after_hook: "
                + "bpy_image is not a Image but {type(bpy_image)}"
            )
            return

        images = getattr(getattr(gltf_importer, "data", None), "images", None)
        if not isinstance(images, Sequence):
            logger.warning(
                "gather_import_image_after_hook: "
                + f"gltf_importer is unexpected structure: {gltf_importer}"
            )
            return

        if image not in images:
            logger.warning(f"gather_import_image_after_hook: {image} not in {images}")
            return

        index = images.index(image)

        bpy_image[self.current_import_id] = index
