import bpy

import os
from os import path
import threading
import requests
import json
import tempfile
import shutil
import time
from uuid import uuid4

from .settings_manager import settings
from .utils import clear_folder, unzip, get_device_info, log

# draws ideas from https://github.com/CGCookie/blender-addon-updater

needs_update = False
curr_version = None
curr_commit = None
latest_available_version = None
latest_available_commit = None

update_installing_state = None
update_checking_state = None
update_error = None

UPDATE_INFO = {
    "main": {
        "download_url": "https://freebirdxr.com/releases/freebird-beta.zip",
        "changelog_url": "https://freebirdxr.com/releases/changelog-beta",
    },
    "release": {
        "download_url": "https://freebirdxr.com/releases/freebird.zip",
        "changelog_url": "https://freebirdxr.com/releases/changelog",
    },
}
VERSION_URL = "https://freebirdxr.com/ops/check-update"

MIN_UPDATE_CHECK_INTERVAL = 10  # seconds

last_update_check_time = 0  # seconds


def _do_check_update(ref, install_update):
    global needs_update
    global curr_version, curr_commit, latest_available_version, latest_available_commit
    global update_checking_state

    try:
        update_checking_state = "CHECKING"
        log.info("Checking for an update..")

        fb_dir = path.join(path.expanduser("~"), ".freebird")
        os.makedirs(fb_dir, exist_ok=True)

        version_file = path.join(path.dirname(__file__), "..", "version.json")
        license_file = path.join(fb_dir, ".license")
        version_file = path.abspath(version_file)
        license_file = path.abspath(license_file)

        with open(version_file, "r") as f:
            version_info = json.load(f)
            curr_version = tuple(version_info["version"])
            curr_commit = version_info["commit"]

        if path.exists(license_file):
            with open(license_file, "r") as f:
                license_num = f.read()
                license_num = license_num.strip()
        else:
            license_num = str(uuid4())
            with open(license_file, "w") as f:
                f.write(license_num)

        update_branch = get_update_branch()
        data = {
            "license_num": license_num,
            "update_branch": update_branch,
            "version": ".".join([str(v) for v in curr_version]),
            "commit": curr_commit,
            "ref": ref,
            "licensed_device": get_device_info(include_version=False),
        }
        res = requests.post(VERSION_URL, json=data, timeout=5)
        res = res.json()
        latest_available_version = tuple(res["version"])
        latest_available_commit = res["commit"]

        log.info(
            f"latest version: {latest_available_version}, latest commit: {latest_available_commit}, curr version: {curr_version}, curr commit: {curr_commit}"
        )

        version_different = latest_available_version[:3] > curr_version[:3]
        hash_different = latest_available_commit != curr_commit

        if version_different:
            log.warning("Freebird XR needs to be updated!")
            needs_update = True

        update_checking_state = None

        if (version_different or hash_different) and (settings["app.update.auto_update"] or install_update):
            log.warning("Auto-updating Freebird XR..")
            download_and_install()
    except Exception as e:
        log.exception(f"Error while checking for an update to Freebird: {e}")
    finally:
        update_checking_state = None


def check_update(ref="bl_start", install_update=False):
    global last_update_check_time

    if bpy.app.background:
        return

    if time.time() < last_update_check_time + MIN_UPDATE_CHECK_INTERVAL:
        log.error("Throttling update check. Too frequent!")
        return

    thread = threading.Thread(target=_do_check_update, kwargs={"ref": ref, "install_update": install_update})
    thread.daemon = True
    thread.start()

    last_update_check_time = time.time()


def get_download_info():
    update_branch = get_update_branch()
    return UPDATE_INFO[update_branch]


def get_update_branch():
    return "main" if settings["app.update.early_access"] else "release"


def download_and_install():
    global update_installing_state, update_error

    # download
    update_installing_state = "DOWNLOADING"
    update_error = None

    tmp_filepath = path.join(tempfile.gettempdir(), "freebird.zip")
    unzip_dirpath = path.join(tempfile.gettempdir(), "freebird_update")

    with open(tmp_filepath, "wb") as tmp:
        download_url = get_download_info()["download_url"] + f"?t={time.time()}"

        try:
            res = requests.get(download_url)
            res.raise_for_status()
        except Exception as e:
            fail_with_message("download", str(e))
            raise e

        try:
            tmp.write(res.content)
        except Exception as e:
            fail_with_message("download", str(e))
            raise e

    # install addon
    update_installing_state = "INSTALLING"

    try:
        curr_dir = path.join(path.dirname(__file__), "..")
        curr_dir = path.abspath(curr_dir)
        unzip(tmp_filepath, outdir=unzip_dirpath)
        clear_folder(curr_dir)
        shutil.copytree(src=unzip_dirpath, dst=curr_dir, dirs_exist_ok=True)
    except Exception as e:
        fail_with_message("download", str(e))
        raise e

    update_installing_state = "INSTALLED"


def fail_with_message(action, msg):
    global update_error, update_installing_state

    update_error = f"Oops! Could not {action} the update for Freebird. Error message: {msg}"
    update_installing_state = "ERROR"


class ApplyUpdateOperator(bpy.types.Operator):
    bl_idname = "freebird.apply_update"
    bl_label = "Freebird Apply Update"

    def invoke(self, context, event):
        if update_installing_state is not None and update_installing_state != "ERROR":
            return {"FINISHED"}

        thread = threading.Thread(target=download_and_install)
        thread.daemon = True
        thread.start()

        return {"FINISHED"}


bpy.utils.register_class(ApplyUpdateOperator)


class CheckForUpdateOperator(bpy.types.Operator):
    bl_idname = "freebird.check_update"
    bl_label = "Freebird Check Update"

    def invoke(self, context, event):
        global update_checking_state

        if update_checking_state is not None:
            return {"FINISHED"}

        check_update(install_update=True)

        return {"FINISHED"}


bpy.utils.register_class(CheckForUpdateOperator)
