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

# file: common.py
# brief: Global variables and Enumerators
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import sys
import math
import os
import pathlib
import bpy
from bpy.utils import previews
from enum import Enum


# Substance Remote Engine
if sys.platform == "win32":
    SRE_DIR = "AppData/Roaming/Adobe/Substance3DIntegrationTools"
    SRE_BIN = "substance_remote_engine.exe"
elif sys.platform == "linux":
    SRE_DIR = "Adobe/Substance3DIntegrationTools"
    SRE_BIN = "substance_remote_engine"
elif sys.platform == "darwin":
    SRE_DIR = "Library/Application Support/Adobe/Substance3DIntegrationTools"
    SRE_BIN = "substance_remote_engine"


# Addon
ADDON_PACKAGE = __package__
ADDON_ROOT = os.path.dirname(__file__)


# Draw
DRAW_DEFAULT_FACTOR = 0.3


# Path
PATH_DEFAULT = bpy.path.native_pathsep(os.path.join(pathlib.Path.home(), "Documents/Adobe/Substance3DInBlender/export"))
PATH_LIBARY_DEFAULT = bpy.path.native_pathsep(os.path.join(pathlib.Path.home(), "Desktop"))


# Substance Remote Engine
SRE_HOST = "http://127.0.0.1"
SRE_PORT = 41646
SRE_VERSION = "v1"
SRE_URI = "{}:{}/{}".format(SRE_HOST, SRE_PORT, SRE_VERSION)

# Blender Addon Server
SERVER_HOST = "127.0.0.1"
SERVER_ALLOW_LIST = ['127.0.0.1', 'localhost']
SERVER_TIMEOUT_S = 5

# Rest Client
REST_TIMEOUT_S = 10
REST_MAX_TRIES = 3
REST_THREAD_THROTTLE_MS = 5

# Render
RENDER_MAX_RESOLUTION_SYNC = [10, 10]
RENDER_KEY = "{}_{}"
RENDER_IMG_UPDATE_DELAY_S = 0.0001

# Toolkit
TOOLKIT_NAME = "Substance3DIntegrationTools"
TOOLKIT_EXT = ".zip"
TOOLKIT_VERSION_FILE = "version.txt"
TOOLKIT_UNINSTALL_TIME = 0.5
TOOLKIT_EXPECTED_VERSION = ["1.4.5", "1.4.4", "1.4.3", "1.4.2"]

# Web site links
WEB_SUBSTANCE_TOOLS = "https://substance3d.adobe.com/plugins/substance-in-blender/#:~:text=The%20Substance%203D%20add-on,optimized%20features%20for%20enhanced%20productivity.&text=The%20add-on%20is%20in%20public%20" # noqa
WEB_SUBSTANCE_SHARE = "https://share-beta.substance3d.com/"
WEB_SUBSTANCE_SOURCE = "https://source.substance3d.com/"
WEB_SUBSTANCE_DOCS = "https://substance3d.adobe.com/documentation/integrations/blender-232292555.html"
WEB_SUBSTANCE_FORUMS = "https://community.adobe.com/t5/substance-3d-plugins/ct-p/ct-substance-3d-plugins?page=1&sort=latest_replies&lang=all&tabid=all" # noqa
WEB_SUBSTANCE_DISCORD = "https://discord.gg/substance3d"

# UI Panels
UI_SPACES = (
    ['3D View', 'VIEW_3D'],
    ['Node Editor', 'NODE_EDITOR'],
    ['Image Generic', 'IMAGE_EDITOR']
)

# SHORTCUTS
SHORTCUT_CLASS_NAME = 'SUBSTANCE_MT_MAIN_{}'

# IMAGE FORMAT
IMAGE_EXPORT_FORMAT = [
    ("0", "BMP", "*.bmp"),
    ("1", "PNG", "*.png"),
    ("2", "JPEG", "*.jpeg"),
    ("3", "JPEG2000", "*.jp2"),
    ("4", "TARGA", "*.targa"),
    ("5", "TARGA_RAW", "*.targa"),
    ("6", "OPEN_EXR", "*.exr"),
    ("7", "HDR", "*.hdr"),
    ("8", "TIFF", "*.tiff")
]

# Formats
FORMATS_DICT = {
    "tga": {"label": "Targa", "ext": ".tga", "bitdepth": ["8"]},
    "exr": {"label": "Open Exr", "ext": ".exr", "bitdepth": ["32"]},
    "bmp": {"label": "Bitmap", "ext": ".bmp", "bitdepth": ["8"]},
    "png": {"label": "PNG", "ext": ".png", "bitdepth": ["16"]},
    "jpg": {"label": "JPEG", "ext": ".jpg", "bitdepth": ["32"]},
    "hdr": {"label": "HDR", "ext": ".hdr", "bitdepth": ["32"]},
    "tiff": {"label": "Tiff", "ext": ".tiff", "bitdepth": ["16"]}
}

COLORSPACES_DICT = (
    (
        "sRGB",
        "sRGB",
        "Color maps that have an 8 bit-depth and are in sRGB space"),
    (
        "Linear",
        "Linear",
        "Color maps that have a 16 or 32 float bit-depth and are in sRGB space or Blender Filmic colorspace"),
    (
        "sRGB OETF",
        "sRGB OETF",
        "Color maps that have an 8 bit-depth and are in sRGB space, when using Blender Filmic colorspace"),
    (
        "Non-Color",
        "Non-Color",
        "Maps that doesn't contain color information like roughness, metallic, normal, height, etc."),
    (
        "Non-Colour Data",
        "Non-Colour Data",
        "Maps that don't have color information (roughness, normal, etc.) when using Blender Filmic colorspace"),
    (
        "Utility - sRGB - Texture",
        "Utility - sRGB - Texture",
        "Color maps that have an 8 bit-depth and have sRGB color information, when using ACEScg colorspace"),
    (
        "Utility - Linear - sRGB",
        "Utility - Linear - sRGB",
        "Maps that have an 16 or 32 bit-depth and have sRGB color information, when using ACEScg colorspace"),
    (
        "ACES - ACEScg",
        "ACES - ACEScg",
        "Color maps that are already in ACEScg colorspace"),
    (
        "role_data",
        "role_data",
        "Maps that don't have color information like roughness, normal, etc. When using ACEScg colorspace"),
    (
        "Raw",
        "Raw",
        "Maps that don't have color information like height, normal, etc. When using OCIO 2.0 and ACEScg colorspace"),
    (
        "scene-linear Rec709-sRGB",
        "scene-linear Rec709-sRGB",
        "Color maps that have 32 float bit-depth and are in Linear sRGB. Use when using OCIO 2.0 and ACEScg colorspace")
)

# Icons
ICONS_DICT = previews.new()
ICONS_IMAGES = (
    {"id": "share_icon", "filename": "share.png"},
    {"id": "source_icon", "filename": "source.png"},
    {"id": "random_icon", "filename": "random.png"},
    {"id": "shuffle_icon", "filename": "shuffle.png"},

    {"id": "progress_00", "filename": "progress_00.png"},
    {"id": "progress_01", "filename": "progress_01.png"},
    {"id": "progress_02", "filename": "progress_02.png"},
    {"id": "progress_03", "filename": "progress_03.png"},
    {"id": "progress_04", "filename": "progress_04.png"},
    {"id": "progress_05", "filename": "progress_05.png"},
    {"id": "progress_06", "filename": "progress_06.png"},
    {"id": "progress_07", "filename": "progress_07.png"},
    {"id": "progress_08", "filename": "progress_08.png"},
    {"id": "progress_09", "filename": "progress_09.png"},
    {"id": "progress_error", "filename": "progress_error.png"},
    {"id": "progress_success", "filename": "progress_success.png"},

    {"id": "render", "filename": "render.png"},
    {"id": "render_queue", "filename": "render_queue.png"},
)

# Outputs Filter
SHADER_OUTPUTS_FILTER_DICT = (
    ("enabled", "Enabled", "Show enabled outputs", "CHECKMARK", 1),
    ("shader", "Shader", "Show only shader outputs", "MATERIAL", 2),
    ("all", "All", "Show all available outputs", "COLLAPSEMENU", 3)
)

SHADER_OUTPUT_UNKNOWN_USAGE = "UNKNOWN"

# Parameters
PARMS_MAX_RANDOM_SEED = 32767
PARMS_DEFAULT_GROUP = "General"
PARMS_CHANNELS_GROUP = "Channels"
PARM_ANGLE_CONVERSION = math.pi * 2
PARM_INT_MAX = 2 ** 31
PARAM_UPDATE_DELAY_S = 0.25


# RESOLUTIONS
RESOLUTIONS_DICT = (
    ('5', '32', ''),
    ('6', '64', ''),
    ('7', '128', ''),
    ('8', '256', ''),
    ('9', '512', ''),
    ('10', '1024', ''),
    ('11', '2048', ''),
    ('12', '4096', '')
)

# CLASS_NAME
CLASS_SHADER_PARMS = "SUBSTANCE_SHP_{}"
CLASS_SHADER_OUTPUTS = "SUBSTANCE_SHO_{}"

CLASS_GRAPH_PARMS = "SUBSTANCE_SGP_{}"
CLASS_GRAPH_OUTPUTS = "SUBSTANCE_SGO_{}"


# PRESET_LABELS
PRESET_DEFAULT = "Default"
PRESET_CUSTOM = "Custom"

# PRESET_EXTENSION
PRESET_EXTENSION = ".sbsprs"


class Code_ParmIdentifier(Enum):
    outputsize = "$outputsize"
    randomseed = "$randomseed"
    pixelsize = "$pixelsize"


class Code_OutputSizeSuffix(Enum):
    width = "_width"
    height = "_height"
    linked = "_linked"


class Code_RequestVerb(Enum):
    post = 1
    delete = 2
    put = 3
    patch = 4
    get = 5


class Code_RequestType(Enum):
    r_sync = 1
    r_async = 2


class Code_Response(Enum):
    success = 0
    server_start_error = -1
    server_stop_error = -2
    api_server_port_error = -3
    api_server_start_error = -4
    api_server_stop_error = -5
    api_listener_remove_error = -6
    api_server_send_error = -7
    api_server_send_type_error = -8
    rest_post_error = -9
    rest_delete_error = -10
    rest_put_error = -11
    rest_patch_error = -12
    rest_get_error = -13
    rest_verb_error = -14
    rest_http_error = -15
    rest_connection_error = -16
    rest_ignore_connection_error = -17
    rest_unknown_error = -18
    toolkit_not_installed_error = -19
    toolkit_version_error = -20
    toolkit_stop_error = -21
    toolkit_process_error = -22
    toolkit_already_started = -23
    toolkit_in_use = -24
    toolkit_not_running_error = -25
    toolkit_file_not_recognized_error = -26
    toolkit_file_ext_error = -27
    toolkit_install_error = -28
    toolkit_uninstall_error = -29
    toolkit_update_uninstall_error = -30
    toolkit_update_install_error = -31
    toolkit_update_error = -32
    response_json_key_error = -33
    response_json_error = -35
    shader_preset_init_error = -36
    shader_preset_remove_error = -37
    shader_preset_default_not_exist_error = -38
    shader_preset_save_error = -39
    sbsar_create_error = -40
    sbsar_initialize_presets_error = -41
    sbsar_update_presets_error = -42
    sbsar_set_default_presets_error = -43
    sbsar_update_output_error = -44
    sbsar_initialize_outputs_error = -45
    sbsar_remove_not_found_error = -46
    sbsar_remove_error = -47
    sbsar_register_error = -48
    sbsar_factory_register_error = -49
    toolkit_version_get_error = -50
    toolkit_version_not_found_error = -51
    server_already_running_error = -52
    server_not_running_error = -53
    parm_update_async = -54
    parm_image_empty = -55
    preset_create_no_name_error = -56
    preset_create_get_error = -57
    preset_export_get_error = -58
    preset_export_error = -59
    preset_import_error = -60
    preset_import_not_graph = -61
    preset_import_protected_error = -62


class Code_ShaderParmType(Enum):
    image = "image"
    integer = "integer"
    integer_maxmin = "integer_maxmin"
    integer_slider = "integer_slider"
    integer2 = "integer2"
    integer2_maxmin = "integer2_maxmin"
    integer2_slider = "integer2_slider"
    integer3 = "integer3"
    integer3_maxmin = "integer3_maxmin"
    integer3_slider = "integer3_slider"
    integer4 = "integer4"
    integer4_maxmin = "integer4_maxmin"
    integer4_slider = "integer4_slider"
    float = "float"
    float_maxmin = "float_maxmin"
    float_slider = "float_slider"
    float2 = "float2"
    float2_maxmin = "float2_maxmin"
    float2_slider = "float2_slider"
    float3 = "float3"
    float3_maxmin = "float3_maxmin"
    float3_slider = "float3_slider"
    float4 = "float4"
    float4_maxmin = "float4_maxmin"
    float4_slider = "float4_slider"
    enum = "enum"
    other = "other"


class Code_OutParms(Enum):
    enabled = "_enabled"
    colorspace = "_colorspace"
    format = "_format"
    bitdepth = "_bitdepth"


class Code_ParmType(Enum):
    float = 0
    float2 = 1
    float3 = 2
    float4 = 3
    integer = 4
    integer2 = 8
    integer3 = 9
    integer4 = 10
    image = 5
    string = 6
    font = 7
    other = -1


class Code_ParmWidget(Enum):
    combobox = "Combobox"
    slider = "Slider"
    color = "Color"
    togglebutton = "Togglebutton"
    image = "Image"
    angle = "Angle"
    position = "Position"
    nowidget = "NoWidget"


class Code_Parm(Enum):
    combobox = "combobox"
    slider_float = "slider_float"
    slider_int = "slider_int"
    other = "other"


class Code_SbsarLoadSuffix(Enum):
    loading = [" (loading...)", "progress_00"]
    get_parms = [" (getting parms...)", "progress_01"]
    get_outputs = [" (getting outputs...)", "progress_02"]
    get_graphs = [" (getting graphs...)", "progress_03"]
    get_embedded_presets = [" (getting sbsar presets...)", "progress_04"]
    get_default_presets = [" (getting default preset...)", "progress_05"]
    create_sbsar = [" (creating substance...)", "progress_06"]
    init_preset = [" (initializing presets...)", "progress_07"]
    init_outputs = [" (initializing outputs...)", "progress_08"]
    crate_parms = [" (creating parms...)", "progress_09"]
    render = [" (rendering...)", "render"]
    render_queue = [" (render_queue...)", "render_queue"]
    error = [" (error)", "progress_error"]
    success = ["", "NONE"]
