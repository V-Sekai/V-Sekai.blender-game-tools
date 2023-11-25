'''
Copyright (C) 2020-2023 Orange Turbine
https://orangeturbine.com
orangeturbine@cgcookie.com

This file is part of Scattershot, created by Jonathan Lampel. 

All code distributed with this add-on is open source as described below. 

Scattershot is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <https://www.gnu.org/licenses/>.
'''


import os, bpy

def append_path(data_type):
    return bpy.path.native_pathsep(os.path.join(
        os.path.dirname(__file__), '..', 'assets', 'scenes', f"uvflow_nodes.blend\\{data_type}\\"
    ))

  
def append_node(nodes, node_tree_name, is_geo_node=True):
    if any(x.name == node_tree_name for x in bpy.data.node_groups):
        appended_group = bpy.data.node_groups[node_tree_name]
    else:
        initial_nodetrees = set(bpy.data.node_groups)
        bpy.ops.wm.append(filename=node_tree_name, directory=append_path('NodeTree'))
        appended_nodetrees = set(bpy.data.node_groups) - initial_nodetrees
        appended_group = [x for x in appended_nodetrees if node_tree_name in x.name][0]

    if nodes:
        if is_geo_node:
            node_group = nodes.new("GeometryNodeGroup")
        else:
            node_group = nodes.new("ShaderNodeGroup")
        node_group.node_tree = bpy.data.node_groups[appended_group.name]
        node_group.node_tree.name = node_tree_name
        node_group.name = node_tree_name
        return node_group
    else:
        return appended_group