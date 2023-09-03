from gpu.types import GPUShader

from enum import Enum
import pathlib
from typing import Dict


SHADERS_DIR = pathlib.Path(__file__).parent / 'shaders'
SHADERS_FRAG_DIR = SHADERS_DIR / 'frag'
SHADERS_VERT_DIR = SHADERS_DIR / 'vert'

cache_shaders: Dict[str, GPUShader] = {}


class SHADERS(Enum):
    LINE_DASHED_3D = 'LINE_3D', 'LINE_DASHED'
    LINE_DASHED_2D = 'LINE_2D', 'LINE_DASHED'
    POINT_3D = 'gpu_shader_3D_point_uniform_size_aa', 'gpu_shader_point_uniform_color_aa'
    POINT_OUTLINE_3D = 'gpu_shader_3d_point_uniform_size_outline_aa', 'gpu_shader_point_uniform_color_outline_aa'

    @property
    def vertex_shader(self) -> str:
        filename: str = self.value[0].lower() + '.vert'
        with (SHADERS_VERT_DIR / filename).open('r') as f:
            return f.read()

    @property
    def fragment_shader(self) -> str:
        filename: str = self.value[1].lower() + '.frag'
        with (SHADERS_FRAG_DIR / filename).open('r') as f:
            return f.read()

    def __call__(self) -> GPUShader:
        if self.name in cache_shaders:
            return cache_shaders[self.name]
        new_sh = GPUShader(self.vertex_shader, self.fragment_shader)
        cache_shaders[self.name] = new_sh
        return new_sh
