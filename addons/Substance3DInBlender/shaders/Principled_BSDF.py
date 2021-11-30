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


# Substance in Blender Principled_BSDF Shader Mapping
# 7/22/2020
# flake8: noqa
from bpy.types import PropertyGroup
from bpy.props import StringProperty, FloatProperty


class PrincipledBDSFPreferences(PropertyGroup):
    bl_idname = 'PrincipledBDSFPreferences'
    name = 'Principled BDSF'
    button_name = 'Show Principled Shader Mapping'
    button_desc = "Expand this box to show/edit principle texture mappings with sbsar outputs"
    button_default_value = False
    prop_name = 'show_principled_lists'
    prop_text = 'Setup texture mapping for Principled BSDF'

    # list the textures for Principled BSDF shader for mapping
    # The name is the identifier used for the blender shader
    displacementScale: FloatProperty(
        name='Displacement Scale',
        default=0.0,
        description='The Scale value for the generated Displacement Node'
    )
    height: StringProperty(
        name='Displacement',
        default='height, Displacement',
        description='The Substance 3D material output identifier to map to Displacement'
    )
    baseColor: StringProperty(
        name='Base Color',
        default='basecolor, base color, Base Color, BaseColor',
        description='Substance 3D material output for Base Color maps')
    normal: StringProperty(
        name='Normal',
        default='normal',
        description='Substance 3D material output for Normal maps')
    specularTint: StringProperty(
        name='Specular Tint',
        default='',
        description='Substance 3D material output for Specular Tint maps')
    emissive: StringProperty(
        name='Emission',
        default='emissive',
        description='Substance 3D material output for emissive maps')
    metallic: StringProperty(
        name='Metallic',
        default='metallic',
        description='Substance 3D material output for metallic maps')
    rough: StringProperty(
        name='Roughness',
        default='roughness',
        description='Substance 3D material output for roughness maps')
    anisotropic: StringProperty(
        name='Anisotropic',
        default='anisotropicLevel',
        description='Substance 3D material output for Anisotropic maps')
    anisotropicAngle: StringProperty(
        name='Anisotropic Rotation',
        default='anisotropicAngle',
        description='Substance 3D material output for Anisotropic Rotation')
    clearCoat: StringProperty(
        name='Clearcoat',
        default='Coat Color',
        description='Substance 3D material output for the clearcoat')
    clearcoatRoughness: StringProperty(
        name='Clearcoat Roughness',
        default='Coat Roughness',
        description='Substance 3D material output for the Clearcoat Roughness')
    clearcoatNormal: StringProperty(
        name='Clearcoat Normal',
        default='Coat Normal',
        description='Substance 3D material output for the Clearcoat Normal')
    subsurfaceScattering: StringProperty(
        name='Subsurface',
        default='Subsurface Scattering',
        description='Substance 3D material output for the Subsurface Scattering')
    subsurfaceColor: StringProperty(
        name='Subsurface Color',
        default='Subsurface Color',
        description='Substance 3D material output for the Subsurface Color')
    IOR: StringProperty(
        name='IOR',
        default='IOR',
        description='Substance 3D material output for IOR')
    opacity: StringProperty(
        name='Alpha',
        default='alpha, opacity',
        description='Substance 3D material output for Alpha')
