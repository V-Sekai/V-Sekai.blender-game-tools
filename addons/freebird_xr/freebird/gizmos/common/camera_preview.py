import bpy
import gpu

from bl_xr import xr_session
from bl_xr import Node, Bounds
from bl_xr.consts import VEC_ZERO

from freebird.utils import desktop_viewport, log

from mathutils import Vector


class CameraPreview(Node):
    "Shows a preview of the view from the given camera"

    TEXTURE_SIZE = 512

    def __init__(self, camera, **kwargs):
        super().__init__(**kwargs)

        self.camera = camera

        self.space = desktop_viewport.get_space()
        self.region = desktop_viewport.get_region()
        self.intersects = None

        self.offscreen = None
        self._texture = None

        self.aspect_ratio = 1

        self.draw_handler = None

    def start_preview(self):
        if not bpy.app.background:
            self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_camera, (), "WINDOW", "POST_PIXEL")

            # offscreen.draw_view3d() fails to run in XR's draw handler, I don't know why.
            # Works properly only in a desktop draw handler.

            # force a draw call on the desktop
            cam = next((ob for ob in bpy.context.scene.objects if getattr(ob, "type", None) == "CAMERA"), None)
            if cam:
                cam.location += Vector((0, 0, 0))
                bpy.context.view_layer.update()

            log.info(f"started camera preview")

    def stop_preview(self):
        if self.draw_handler:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, "WINDOW")
            self.draw_handler = None

            log.info(f"stopped camera preview")

    def draw_camera(self):
        if not xr_session.is_running:
            return

        try:
            self.camera.__class__  # skip invalid references (e.g. deleted targets)
        except:
            return

        if self.offscreen is None:
            self.offscreen = gpu.types.GPUOffScreen(self.TEXTURE_SIZE, self.TEXTURE_SIZE)
            self._texture = self.offscreen.texture_color

        if self.camera is None:
            if bpy.context.scene.camera is not None:
                self.camera = bpy.context.scene.camera
            else:
                return

        context = bpy.context
        scene = context.scene

        view_matrix = self.camera.matrix_world.inverted()

        frame = self.camera.data.view_frame(scene=bpy.context.scene)
        view_width = abs(frame[0].x - frame[2].x)
        view_height = abs(frame[0].y - frame[1].y)
        self.aspect_ratio = view_width / view_height

        W = int(self.TEXTURE_SIZE * self.aspect_ratio)
        H = int(self.TEXTURE_SIZE)

        projection_matrix = self.camera.calc_matrix_camera(context.evaluated_depsgraph_get(), x=W, y=H)

        self.offscreen.draw_view3d(scene, context.view_layer, self.space, self.region, view_matrix, projection_matrix)

    @property
    def bounds_local(self) -> Bounds:
        return Bounds(VEC_ZERO, Vector((self.aspect_ratio, 1, 0)))
