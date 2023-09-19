"""
Copyright (C) 2022 Adobe.
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# file: toolkit/manager.py
# brief: SRE toolkit operations manager
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import sys
import os
import time
import zipfile
import shutil
import stat
import pathlib
import subprocess
import traceback


from ..utils import SUBSTANCE_Utils
from ..common import (
    Code_Response,
    TOOLKIT_VERSION_FILE,
    TOOLKIT_UNINSTALL_TIME,
    TOOLKIT_EXT,
    TOOLKIT_NAME,
    SRE_DIR,
    SRE_BIN
)


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


class SRE_ToolkitManager():
    def __init__(self):
        self.process = None
        self.version = None
        self.toolkit_dir = SRE_DIR
        self.toolkit_bin = SRE_BIN
        _home = pathlib.Path.home()
        self.toolkit_path = os.path.join(_home, self.toolkit_dir)

    # Version
    def version_get(self):
        if self.version is None:
            _path = os.path.join(self.toolkit_path, TOOLKIT_VERSION_FILE)
            if os.path.exists(_path):
                try:
                    with open(_path, 'r') as _f:
                        self.version = _f.read()
                except Exception:
                    return (Code_Response.toolkit_version_get_error, None)
            else:
                return (Code_Response.toolkit_version_not_found_error, None)
        return (Code_Response.success, self.version)

    # Toolkit
    def _clear_quaritine(self, filepath):
        if sys.platform == "darwin":
            # clearing the apple's quarntine flag
            _cmd = ["xattr", "-d", "com.apple.quarantine", filepath]
            subprocess.call(_cmd)

    def _verify(self, filepath):
        _filename, _extension = os.path.splitext(filepath)
        _basename = os.path.basename(_filename)
        if _extension == TOOLKIT_EXT:
            if _basename.startswith(TOOLKIT_NAME):
                return (Code_Response.success, _basename)
            else:
                return (Code_Response.toolkit_file_not_recognized_error, None)
        else:
            return (Code_Response.toolkit_file_ext_error, None)

    def _remove_tools(self):
        # remove all subfolders except resourcepooldb
        for _root, _dirs, _files in os.walk(self.toolkit_path):
            for _dir in _dirs:
                if _dir != "resourcepooldb":
                    shutil.rmtree(os.path.join(_root, _dir))

        # remove all files in the toolkit dir
        for _f in os.listdir(self.toolkit_path):
            _filepath = os.path.join(self.toolkit_path, _f)
            if os.path.isfile(_filepath):
                os.remove(_filepath)

    def is_installed(self):
        _path = os.path.join(self.toolkit_path, self.toolkit_bin)
        return os.path.exists(_path)

    def is_running(self):
        if sys.platform.startswith('win'):
            # command to get the process ID of the remote engine
            _command = "wmic process where name='" + self.toolkit_bin + "' get ProcessId"
            _output = os.popen(_command).read()
            _lines = _output.splitlines()
            # check specifically for the remote engine process ID
            for _line in _lines:
                if _line != 'ProcessId':
                    if len(_line) > 1:
                        return True
        else:
            # command to enumerate all of the running processes
            _command = 'ps -Af'
            _tmp = os.popen(_command).read()
            # check if the remote engine name is in the running process list
            if self.toolkit_bin in _tmp[:]:
                return True
        return False

    def start(self):
        if not self.is_running():
            _path = os.path.join(self.toolkit_path, self.toolkit_bin)
            if not sys.platform.startswith("win"):
                _st = os.stat(_path)
                # set the remote engine to executable
                os.chmod(_path, _st.st_mode | stat.S_IEXEC)

            _args = []
            _args.append(_path)
            _args.append("-plugin")
            self.process = subprocess.Popen(
                _args,
                cwd=self.toolkit_path,
                shell=False,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                close_fds=True
            )
            time.sleep(0.5)
            return Code_Response.success
        else:
            return Code_Response.toolkit_already_started

    def stop(self):
        if self.process is not None:
            try:
                if sys.platform.startswith('win'):
                    self.process.kill()
                else:
                    self.process.terminate()
                    self.process.wait()
                self.process = None
                return Code_Response.success
            except Exception:
                return Code_Response.toolkit_stop_error
        else:
            return Code_Response.toolkit_process_error

    def install(self, filepath):
        try:
            _result = self._verify(filepath)
            if _result[0] != Code_Response.success:
                return _result[0]
            self._clear_quaritine(filepath)

            with zipfile.ZipFile(filepath, 'r') as _zip_ref:
                _zip_ref.extractall(self.toolkit_path)

            _version = find_between(_result[1], 'Substance3DIntegrationTools-', '+')
            _version_path = os.path.join(self.toolkit_path, TOOLKIT_VERSION_FILE)

            if os.path.exists(_version_path):
                os.remove(_version_path)
            with open(_version_path, 'w') as _fp:
                _fp.write(_version)
            self.version = None
            return Code_Response.success
        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Toolkit install failed")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return Code_Response.toolkit_install_error

    def uninstall(self):
        try:
            if self.process is not None:
                if sys.platform.startswith('win'):
                    self.process.kill()
                else:
                    self.process.terminate()
                    self.process.wait()
                self.process = None
            time.sleep(TOOLKIT_UNINSTALL_TIME)
            self._remove_tools()
            self.version = None
            return Code_Response.success
        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Uninstall failed...")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return Code_Response.toolkit_uninstall_error

    def update(self, filepath):
        try:
            _result = self.uninstall()
            if _result != Code_Response.success:
                return Code_Response.toolkit_update_uninstall_error
            _result = self.install(filepath)
            if _result != Code_Response.success:
                return Code_Response.toolkit_update_install_error
            self.version = None
            return Code_Response.success
        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Update failed...")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return Code_Response.toolkit_update_error
