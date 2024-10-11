import bpy

from bl_xr import intersection_checks, root

import os
import platform
import traceback

stop_checking_mode = False
MODE_CHECK_INTERVAL = 0.5  # seconds
FB_COLLECTION_NAME = "Freebird's Stuff"

_prev_mode = None


def set_mode(mode):  # EDIT or OBJECT
    from freebird.utils import log

    ob = bpy.context.view_layer.objects.active

    try:
        if ob:
            bpy.ops.object.mode_set(mode=mode)
            bpy.ops.ed.undo_push(message=f"{mode} mode")
            log.debug(f"CREATED UNDO FOR MODE SWITCH: {mode}")
            return True
    except:
        log.warn(f"Can't set {mode} for the active object {ob}")

    return False


def enable_bounds_check():
    intersection_checks.add("BOUNDS_ON_MAIN_TRIGGER")


def disable_bounds_check():
    if "BOUNDS_ON_MAIN_TRIGGER" in intersection_checks:
        intersection_checks.remove("BOUNDS_ON_MAIN_TRIGGER")


def set_viewport_mirror_state(state):
    area = next(area for area in bpy.data.screens["Layout"].areas if area.type == "VIEW_3D")
    space = next(space for space in area.spaces if space.type == "VIEW_3D")
    space.mirror_xr_session = state


def link_to_configured_collection(ob):
    scene = bpy.context.scene
    collection = getattr(scene, "freebird_draw_collection", None) or scene.collection

    for prev_coll in ob.users_collection:
        prev_coll.objects.unlink(ob)

    collection.objects.link(ob)


def get_freebird_collection():
    if FB_COLLECTION_NAME not in bpy.data.collections:
        c = bpy.data.collections.new(FB_COLLECTION_NAME)
        bpy.context.scene.collection.children.link(c)

    return bpy.data.collections[FB_COLLECTION_NAME]


def is_cycles_rendering():
    area = next(area for area in bpy.context.screen.areas if area.type == "VIEW_3D")
    space = next(space for space in area.spaces if space.type == "VIEW_3D")
    return space.shading.type == "RENDERED" and bpy.context.scene.render.engine == "CYCLES"


def get_device_info(include_version=True):
    import gpu

    ram_total = get_system_ram() / 1024**3

    gpu_info = [gpu.platform.vendor_get(), gpu.platform.renderer_get()]
    os_info = platform.system()

    if include_version:
        gpu_info.append(gpu.platform.version_get())
        os_info = [os_info, platform.version()]

    return {
        "gpu": gpu_info,
        "cpu": get_processor_name(),
        "ram": f"{ram_total:.1f}",
        "os": os_info,
    }


def get_system_ram():
    import os
    from freebird.utils import log

    try:
        total_mem = 0

        if platform.system() == "Windows":
            process = os.popen("wmic memorychip get capacity")
            result = process.read()
            process.close()
            for m in result.splitlines()[1:-1]:
                if not m:
                    continue

                total_mem += int(m)

        return total_mem
    except:
        log.error(traceback.format_exc())
        return 0


# from https://github.com/easydiffusion/easydiffusion/blob/dfb26ed7812d34e4e23cbf4c2b4fcac2ead70780/ui/easydiffusion/device_manager.py#L239
def get_processor_name():
    from freebird.utils import log

    try:
        import subprocess
        import re
        import os

        if platform.system() == "Windows":
            process = os.popen("wmic cpu get name")
            result = process.read()
            process.close()
            for m in result.splitlines()[1:-1]:
                if m:
                    return m
        elif platform.system() == "Darwin":
            os.environ["PATH"] = os.environ["PATH"] + os.pathsep + "/usr/sbin"
            command = "sysctl -n machdep.cpu.brand_string"
            return subprocess.check_output(command, shell=True).decode().strip()
        elif platform.system() == "Linux":
            command = "cat /proc/cpuinfo"
            all_info = subprocess.check_output(command, shell=True).decode().strip()
            for line in all_info.split("\n"):
                if "model name" in line:
                    return re.sub(".*model name.*:", "", line, 1).strip()
    except:
        log.error(traceback.format_exc())
        return "cpu"


def _check_mode():
    global _prev_mode

    if stop_checking_mode:
        return

    ob = bpy.context.view_layer.objects.active
    if ob is None:
        return MODE_CHECK_INTERVAL

    curr_mode = ob.mode
    if curr_mode != _prev_mode:
        _prev_mode = curr_mode

        root.dispatch_event("bl.mode_change", curr_mode)

    return MODE_CHECK_INTERVAL


def watch_for_blender_mode_changes():
    if not bpy.app.background:
        bpy.app.timers.register(_check_mode, persistent=True)


class RestartBlenderOperator(bpy.types.Operator):
    bl_idname = "wm.restart_blender"
    bl_label = "Restart Blender"

    def invoke(self, context, event):
        import bpy, os, subprocess

        blender_exe = bpy.app.binary_path
        head, _ = os.path.split(blender_exe)
        blender_launcher = os.path.join(head, "blender-launcher")
        subprocess.run([blender_launcher, "--python-expr", "import bpy; bpy.ops.wm.recover_last_session()"])
        bpy.ops.wm.quit_blender()

        return {"FINISHED"}


bpy.utils.register_class(RestartBlenderOperator)
