_skip_mesh_updates = False
_USE_DEBUG = False


import bpy
from gpu.types import GPUShader
from gpu.shader import from_builtin as gpu_shader_from_builtin

select_color = bpy.context.preferences.themes[0].view_3d.edge_select


class GLOBALS:
    SHADER_EDGE: GPUShader = gpu_shader_from_builtin('POLYLINE_UNIFORM_COLOR')
    SHADER_FACE: GPUShader = gpu_shader_from_builtin('UNIFORM_COLOR')
    THEME_EDGE = (*list(bpy.context.preferences.themes[0].view_3d.edge_select)[:3], .9)
    THEME_FACE = (*list(bpy.context.preferences.themes[0].view_3d.face_select)[:3], .25)
    THEME_TOOL_SELECTION = (select_color[0], select_color[1], select_color[2], .92)
    THEME_TOOL_SUGGESTION_ADD = (select_color[0], select_color[1], select_color[2], .92)
    THEME_TOOL_SUGGESTION_REMOVE = (1, .2, .16, .92)

    @property
    def use_debug(self) -> bool:
        return _USE_DEBUG

    @property
    def skip_mesh_updates(self) -> bool:
        global _skip_mesh_updates
        return _skip_mesh_updates
    
    @skip_mesh_updates.setter
    def skip_mesh_updates(self, state: bool) -> None:
        print("* GLOBALS.skip_mesh_updates set to ", state)
        global _skip_mesh_updates
        _skip_mesh_updates = state



class CM_SkipMeshUpdates:
    def __init__(self) -> None:
        self._skip = GLOBALS.skip_mesh_updates # Controlled by an outer scope.
    
    def __enter__(self):
        if self._skip: return
        GLOBALS.skip_mesh_updates = True
    
    def __exit__(self, exc_type, exc_value, trace):
        if self._skip: return
        GLOBALS.skip_mesh_updates = False



def print_debug(*args) -> None:
    if GLOBALS.use_debug:
        print(*args)
