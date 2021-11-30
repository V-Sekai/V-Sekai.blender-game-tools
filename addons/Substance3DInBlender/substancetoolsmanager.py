"""
Copyright (C) 2021 Adobe.
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


# Substance in Blender Tools Manager
# 7/12/2020
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import time
import zipfile
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator
from .mainthread import PopCursor, PushCursor

UNINSTALL_TIME = 0.5
TOOLS_PROCESS = None
TOOLS_NAME = 'Substance3DIntegrationTools'
VERSION_FILENAME = 'version.txt'
home = pathlib.Path.home()
if sys.platform == "win32":
    INSTALL_DIR = home / "AppData/Roaming/Adobe/Substance3DIntegrationTools"
    BIN_NAME = "substance_remote_engine.exe"
elif sys.platform == "linux":
    INSTALL_DIR = home / "Adobe/Substance3DIntegrationTools"
    BIN_NAME = "substance_remote_engine"
elif sys.platform == "darwin":
    INSTALL_DIR = home / "Library/Application Support/Adobe/Substance3DIntegrationTools"
    BIN_NAME = "substance_remote_engine"


def AreToolsInstalled():
    """ Return true if the tools folder is present """
    filePath = os.path.join(INSTALL_DIR, BIN_NAME)
    return os.path.exists(filePath)


def IsTookitRunning():
    """ Is the process running """
    if sys.platform.startswith('win'):

        # command to get the process ID of the remote engine
        command = "wmic process where name='" + BIN_NAME + "' get ProcessId"
        output = os.popen(command).read()
        lines = output.splitlines()

        # check specifically for the remote engine process ID
        for line in lines:
            if line != 'ProcessId':
                if len(line) > 1:
                    return True
    else:
        # command to enumerate all of the running processes
        command = 'ps -Af'
        tmp = os.popen('ps -Af').read()

        # check if the remote engine name is in the running process list
        if BIN_NAME in tmp[:]:
            return True
    return False


def InstallTools(filepath, basename):
    """ Extract the zip file into the tools path """
    with zipfile.ZipFile(filepath, 'r') as zip_ref:
        zip_ref.extractall(INSTALL_DIR)

    version = basename.split('-')[1]
    versionFilePath = os.path.join(INSTALL_DIR, VERSION_FILENAME)
    if os.path.exists(versionFilePath):
        os.remove(versionFilePath)
    with open(versionFilePath, 'w') as fp:
        fp.write(version)


def VerifyToolsFile(filepath, ext):
    """ Verify the file selected to install tools is valid """
    try:
        filename, extension = os.path.splitext(filepath)
        basename = os.path.basename(filename)
        if extension == ext:
            if basename.startswith(TOOLS_NAME):
                return basename
            else:
                print('Please select the Substance 3D Integration Tools .zip file')
        else:
            print('Substance 3D Integration Tools installs from a .zip file')
    except Exception as e:
        print('Failed to install tools: ' + str(e))
    return ''


def GetVersion():
    """ Get the version of the installed tools """
    version = ''
    versionFilePath = os.path.join(INSTALL_DIR, VERSION_FILENAME)
    if os.path.exists(versionFilePath):
        with open(versionFilePath, 'r') as fp:
            version = 'Version: (' + fp.read() + ')'
    return version


def StartTools():
    """ Start the external Tookit process if needed """
    global TOOLS_PROCESS
    if not IsTookitRunning():
        toolsLoc = os.path.join(INSTALL_DIR, BIN_NAME)
        if not sys.platform.startswith('win'):
            st = os.stat(toolsLoc)

            # set the remote engine to executable
            os.chmod(toolsLoc, st.st_mode | stat.S_IEXEC)

        print('Starting Substance 3D Integration Tools: ' + toolsLoc)
        TOOLS_PROCESS = subprocess.Popen(toolsLoc, cwd=INSTALL_DIR, shell=False)


def UninstallTools():
    """ Stop and remove the currently installed Substance 3D Tools"""
    StopTools()
    time.sleep(UNINSTALL_TIME)
    RemoveTools()


def StopTools():
    """ Stop the external tools process if needed """
    global TOOLS_PROCESS
    if TOOLS_PROCESS is not None:
        print('Stopping Integration Tools')
        if sys.platform.startswith('win'):
            TOOLS_PROCESS.kill()
        else:
            TOOLS_PROCESS.terminate()
            TOOLS_PROCESS.wait()
        TOOLS_PROCESS = None


def RemoveTools():
    """ Delete the tools folder if it exists """

    # remove all subfolders except resourcepooldb
    for root, dirs, files in os.walk(INSTALL_DIR):
        for dir in dirs:
            if dir != 'resourcepooldb':
                shutil.rmtree(os.path.join(root, dir))

    # remove all files in the INSTALL_DIR
    for f in os.listdir(INSTALL_DIR):
        filepath = os.path.join(INSTALL_DIR, f)
        if os.path.isfile(filepath):
            os.remove(filepath)


class SUBSTANCE_OT_InstallTools(Operator, ImportHelper):
    """Open file browser to select the tools zipfile to install"""
    bl_idname = 'substance.install_tools'
    bl_label = 'Install tools'
    bl_options = {'REGISTER'}
    filename_ext = '.zip'
    filter_glob: StringProperty(default='*.zip', options={'HIDDEN'})      # noqa: F722, F821

    def __init__(self):
        """ Clear out the file path """
        self.filepath = ''

    def execute(self, context):
        """ Execute the operator to install the tools """
        PushCursor('WAIT')
        basename = VerifyToolsFile(self.filepath, self.filename_ext)
        if len(basename) > 0:
            InstallTools(self.filepath, basename)
            StartTools()
        PopCursor()
        return {'FINISHED'}


class SUBSTANCE_OT_UpdateTools(Operator, ImportHelper):
    """Open file browser to select the tools zipfile to update the tools"""
    bl_idname = 'substance.update_tools'
    bl_label = 'Update tools'
    bl_options = {'REGISTER'}
    filename_ext = '.zip'
    filter_glob: StringProperty(default='*.zip', options={'HIDDEN'})      # noqa: F722, F821

    def __init__(self):
        """ Clear out the file path """
        self.filepath = ''

    def execute(self, context):
        """ Execute the operator to update the tools """
        PushCursor('WAIT')
        basename = VerifyToolsFile(self.filepath, self.filename_ext)
        if len(basename) > 0:
            UninstallTools()
            InstallTools(self.filepath, basename)
            StartTools()
        PopCursor()
        return {'FINISHED'}


class SUBSTANCE_OT_UninstallTools(Operator):
    """Remove the installed version of Substance 3D Integration Tools"""
    bl_idname = 'substance.uninstall_tools'
    bl_label = 'UnInstall tools'
    bl_options = {'REGISTER'}

    def execute(self, context):
        """ Execute the operator to uninstall the tools """
        PushCursor('WAIT')
        try:
            UninstallTools()
        except Exception as e:
            print('Failed to uninstall tools: ' + str(e))
        PopCursor()
        return {'FINISHED'}
