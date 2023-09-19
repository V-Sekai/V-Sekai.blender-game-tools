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

# file: ui/sbsar.py
# brief: Substance UI
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy

from ..ops.web import SUBSTANCE_OT_GotoShare, SUBSTANCE_OT_GotoSource
from ..ops.presets import SUBSTANCE_OT_AddPreset
from ..ops.parms import SUBSTANCE_OT_RandomizeSeed
from ..ops.sbsar import (
    SUBSTANCE_OT_LoadSBSAR,
    SUBSTANCE_OT_ApplySBSAR,
    SUBSTANCE_OT_DuplicateSBSAR,
    SUBSTANCE_OT_ReloadSBSAR,
    SUBSTANCE_OT_RemoveSBSAR
)

from .presets import SUBSTANCE_MT_PresetOptions
from ..api import SUBSTANCE_Api
from ..utils import SUBSTANCE_Utils
from ..common import (
    Code_SbsarLoadSuffix,
    Code_ParmWidget,
    Code_ParmType,
    Code_OutParms,
    Code_ParmIdentifier,
    Code_OutputSizeSuffix,
    DRAW_DEFAULT_FACTOR,
    SHADER_OUTPUTS_FILTER_DICT,
    ICONS_DICT,
    PARMS_CHANNELS_GROUP,
    ADDON_PACKAGE
)


class SUBSTANCE_UL_SbsarList(bpy.types.UIList):
    bl_idname = 'SUBSTANCE_UL_SbsarList'
    bl_label = 'Loaded Substance 3D Materials'

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        _suffix = item.suffix
        _is_rendering = SUBSTANCE_Api.sbsar_is_rendering(item.id)
        if item.icon == Code_SbsarLoadSuffix.render.value[1] or _is_rendering == 2:
            _icon = ICONS_DICT["render"].icon_id
            _suffix = Code_SbsarLoadSuffix.render.value[0]
        elif _is_rendering == 1:
            _icon = ICONS_DICT["render_queue"].icon_id
            _suffix = Code_SbsarLoadSuffix.render_queue.value[0]
        elif item.icon != Code_SbsarLoadSuffix.success.value[1]:
            _icon = ICONS_DICT[item.icon].icon_id
        else:
            _icon = 0

        _name = item.name + " " + _suffix
        # draw the item in the layout
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=_name, icon_value=_icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text='', icon_value=_icon)


def SubstanceMainPanelFactory(space):
    class SUBSTANCE_PT_MAIN(bpy.types.Panel):
        bl_idname = 'SUBSTANCE_PT_MAIN_{}'.format(space)
        bl_space_type = space
        bl_label = 'Substance 3D Panel'
        bl_region_type = 'UI'
        bl_category = 'Substance 3D'

        def draw(self, context):
            # Shortcut
            _shortcut = context.preferences.addons[ADDON_PACKAGE].preferences.shortcuts
            self.layout.label(text="(Quick Access: " + _shortcut.menu_label + ")")
            _row = self.layout.row(align=True)

            # Buttons (Operators)
            _row.operator(SUBSTANCE_OT_LoadSBSAR.bl_idname, text="Load")
            _row.separator()
            _row.operator(SUBSTANCE_OT_ApplySBSAR.bl_idname, text="Apply")
            _row.separator()
            _row.operator(SUBSTANCE_OT_GotoShare.bl_idname, text="", icon_value=ICONS_DICT["share_icon"].icon_id)
            _row.separator()
            _row.operator(SUBSTANCE_OT_GotoSource.bl_idname, text="", icon_value=ICONS_DICT["source_icon"].icon_id)
            _row.separator()
            _row.operator(SUBSTANCE_OT_DuplicateSBSAR.bl_idname, text="", icon='DUPLICATE')
            _row.separator()
            _row.operator(SUBSTANCE_OT_ReloadSBSAR.bl_idname, text="", icon='FILE_REFRESH')
            _row.separator()
            _row.operator(SUBSTANCE_OT_RemoveSBSAR.bl_idname, text="", icon='TRASH')
            _row.separator()

            # SBSAR List
            if len(context.scene.loaded_sbsars) > 0:
                _col = self.layout.column()
                _col.label(text="Loaded 3D Substance Materials")
                _col.template_list(
                    SUBSTANCE_UL_SbsarList.bl_idname,
                    'Loaded 3D Substance Materials',
                    context.scene,
                    'loaded_sbsars',
                    context.scene,
                    'sbsar_index')

                _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
                if len(_selected_sbsar.graphs) > 1 and _selected_sbsar.load_success:
                    _row = _col.row()
                    _split = _row.split(factor=0.25)
                    _col_1 = _split.column()
                    _col_2 = _split.column()
                    _col_1.label(text="Graph")
                    _col_2.prop(_selected_sbsar, "graphs_list", text="")

    return SUBSTANCE_PT_MAIN


def SubstanceGraphPanelFactory(space):
    class SUBSTANCE_PT_GRAPH(bpy.types.Panel):
        bl_idname = 'SUBSTANCE_PT_GRAPH_{}'.format(space)
        bl_space_type = space
        bl_label = 'Graph Parameters'
        bl_region_type = 'UI'
        bl_category = 'Substance 3D'

        @classmethod
        def poll(cls, context):
            if len(context.scene.loaded_sbsars) > 0:
                _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
                return _selected_sbsar.load_success
            return False

        def draw(self, context):
            _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)

            _col = self.layout.column(align=True)

            # Presets
            _row = _col.row()
            _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
            _col_1 = _split.column()
            _col_2 = _split.column()
            _row = _col_1.row()
            _row.alignment = "RIGHT"
            _row.label(text="Preset")
            _row = _col_2.row()
            _row.prop(_selected_graph, "presets_list", text='')
            _row.operator(SUBSTANCE_OT_AddPreset.bl_idname, text='', icon='ADD')
            _row.menu(SUBSTANCE_MT_PresetOptions.bl_idname, icon='TRIA_DOWN')

            # Phyisical Size
            _row = _col.row()
            _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
            _col_1 = _split.column()
            _col_2 = _split.column()
            _row = _col_1.row()
            _row.alignment = "RIGHT"
            _row.label(text="Physical SIze")
            _row = _col_2.row()
            _row.prop(_selected_graph.physical_size, "x", text='')
            _row.enabled = False
            _row_2 = _row.column()
            _row_2.prop(_selected_graph.physical_size, "y", text='')
            _row_2.enabled = False
            _row_3 = _row.column()
            _row_3.prop(_selected_graph.physical_size, "z", text='')
            _row_3.enabled = False

            # Tiling
            _row = _col.row()
            _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
            _col_1 = _split.column()
            _col_2 = _split.column()
            _row = _col_1.row()
            _row.alignment = "RIGHT"
            _row.label(text="Tiling")
            _row = _col_2.row()
            _row.prop(_selected_graph.tiling, "x", text='')
            _row_2 = _row.column()
            _row_2.prop(_selected_graph.tiling, "y", text='')
            _row_2.enabled = not _selected_graph.tiling.linked
            _row_3 = _row.column()
            _row_3.prop(_selected_graph.tiling, "z", text='')
            _row_3.enabled = not _selected_graph.tiling.linked
            _row.prop(_selected_graph.tiling, "linked", text='', icon='LOCKED')

            _parms = getattr(context.scene, _selected_graph.parms_class_name)
            if _selected_graph.outputsize_exists:
                _row = _col.row()
                _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
                _col_1 = _split.column()
                _col_2 = _split.column()
                _row = _col_1.row()
                _row.alignment = "RIGHT"
                _row.label(text="Resolution")
                _row = _col_2.row()
                _row.prop(_parms, Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.width.value, text='')
                _row_2 = _row.column()
                _row_2.prop(_parms, Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.height.value, text='')
                _linked = getattr(_parms, Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.linked.value)
                _row_2.enabled = not _linked
                _row.prop(
                    _parms,
                    Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.linked.value,
                    text='',
                    icon='LOCKED')

            if _selected_graph.randomseed_exists:
                _row = _col.row()
                _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
                _col_1 = _split.column()
                _col_2 = _split.column()
                _row = _col_1.row()
                _row.alignment = "RIGHT"
                _row.label(text="Random Seed")
                _row = _col_2.row()
                _row.prop(_parms, Code_ParmIdentifier.randomseed.value, text="")
                _row.operator(
                    SUBSTANCE_OT_RandomizeSeed.bl_idname,
                    text="",
                    icon_value=ICONS_DICT["random_icon"].icon_id)

    return SUBSTANCE_PT_GRAPH


def SubstanceOutputPanelFactory(space):
    class SUBSTANCE_PT_OUTPUTS(bpy.types.Panel):
        bl_idname = 'SUBSTANCE_PT_OUTPUTS_{}'.format(space)
        bl_space_type = space
        bl_label = 'Outputs'
        bl_region_type = 'UI'
        bl_category = 'Substance 3D'

        @classmethod
        def poll(cls, context):
            if len(context.scene.loaded_sbsars) > 0:
                _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
                return _selected_sbsar.load_success
            return False

        def draw(self, context):
            _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)

            _col = self.layout.column(align=True)

            _box = _col.box()

            _row = _box.row()
            _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
            _col_1 = _split.column()
            _col_2 = _split.column()
            _row = _col_1.row()
            _row.alignment = "RIGHT"
            _row.label(text="Shader")
            _row = _col_2.row()
            _row.prop(_selected_graph, 'shader_preset_list', text="")
            _row.prop(_selected_graph, 'outputs_filter', text="", expand=True)

            # Show current outputs
            _selected_preset_idx = int(_selected_graph.shader_preset_list)
            _, _selected_shader_preset = SUBSTANCE_Utils.get_selected_shader_preset(context, _selected_preset_idx)
            _shader_outputs = _selected_shader_preset.outputs

            _outputs = getattr(context.scene, _selected_graph.outputs_class_name)
            for _idx, _output in enumerate(_selected_graph.outputs):
                _enabled = getattr(_outputs, _output.name + Code_OutParms.enabled.value)
                if _selected_graph.outputs_filter == SHADER_OUTPUTS_FILTER_DICT[0][0] and not _enabled:
                    continue

                if (_selected_graph.outputs_filter == SHADER_OUTPUTS_FILTER_DICT[1][0] and
                        _output.usage not in _shader_outputs):
                    continue

                _row = _box.row()
                _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
                _col_1 = _split.column()
                _col_2 = _split.column()
                _row = _col_1.row()
                _row.alignment = "RIGHT"
                _row.label(text=_output.label)
                _row = _col_2.row()
                _row.prop(_outputs, _output.name + Code_OutParms.enabled.value, text="")
                _row.prop(_outputs, _output.name + Code_OutParms.format.value, text="")
                _row.prop(_outputs, _output.name + Code_OutParms.bitdepth.value, text="")

    return SUBSTANCE_PT_OUTPUTS


def SubstanceParmsPanelFactory(space):
    class SUBSTANCE_PT_PARMS(bpy.types.Panel):
        bl_idname = 'SUBSTANCE_PT_PARMS_{}'.format(space)
        bl_space_type = space
        bl_label = 'Parameters'
        bl_region_type = 'UI'
        bl_category = 'Substance 3D'

        @classmethod
        def poll(cls, context):
            if len(context.scene.loaded_sbsars) > 0:
                _selected_sbsar = context.scene.loaded_sbsars[context.scene.sbsar_index]
                return _selected_sbsar.load_success
            return False

        def draw(self, context):
            _selected_graph = SUBSTANCE_Utils.get_selected_graph(context)

            _col = self.layout.column(align=True)

            if SUBSTANCE_Utils.parms_empty(_selected_graph.parms):
                _row = _col.row()
                _row.label(text="No parameters available")
            else:
                for _idx, _group in enumerate(_selected_graph.parm_groups):
                    if _group.name == PARMS_CHANNELS_GROUP:
                        continue

                    _empty = True
                    for _idx, _parm in enumerate(_selected_graph.parms):
                        if _group.name == _parm.group and _parm.visible:
                            _empty = False
                            break

                    if _empty:
                        continue

                    _box = _col.box()
                    _row = _box.row()
                    _row.alignment = "LEFT"
                    _row.prop(
                        _group,
                        "collapsed",
                        icon='TRIA_DOWN' if not _group.collapsed else 'TRIA_RIGHT',
                        text=_group.name+":",
                        emboss=False)

                    if not _group.collapsed:
                        _parms = getattr(context.scene, _selected_graph.parms_class_name)
                        for _idx, _parm in enumerate(_selected_graph.parms):
                            if _parm.group != _group.name:
                                continue
                            if _parm.widget == Code_ParmWidget.nowidget.value:
                                continue
                            if not _parm.visible:
                                continue

                            _row = _box.row()
                            _split = _row.split(factor=DRAW_DEFAULT_FACTOR)
                            _col_1 = _split.column()
                            _col_2 = _split.column()
                            _row = _col_1.row()
                            _row.alignment = "RIGHT"
                            _row.label(text=_parm.label)
                            _row = _col_2.row()

                            if _parm.widget == Code_ParmWidget.combobox.value:
                                _row.prop(_parms, _parm.name, text="")
                            elif _parm.widget == Code_ParmWidget.slider.value:
                                _row.prop(_parms, _parm.name, text="", slider=True)
                            elif _parm.widget == Code_ParmWidget.togglebutton.value:
                                _row.prop(_parms, _parm.name, expand=True)
                            elif _parm.widget == Code_ParmWidget.color.value:
                                if _parm.type == Code_ParmType.float.name:
                                    _row.prop(_parms, _parm.name, text="", slider=True)
                                else:
                                    _row.prop(_parms, _parm.name, text="")
                            elif _parm.widget == Code_ParmWidget.angle.value:
                                _row.prop(_parms, _parm.name, text="", slider=True)
                            elif _parm.widget == Code_ParmWidget.position.value:
                                _row.prop(_parms, _parm.name, text="", slider=True)
                            elif _parm.widget == Code_ParmWidget.image.value:
                                _row.template_ID(_parms, _parm.name, open="image.open")
                            else:
                                _row.alert = True
                                _row.label(text="Parameter type [{}] not supported yet".format(_parm.widget))
                                _row.alert = False

    return SUBSTANCE_PT_PARMS
