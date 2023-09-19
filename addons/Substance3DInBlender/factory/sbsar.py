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

# file: factory/sbsar.py
# brief: Dynamic class creation for sbsar objects
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy
from copy import deepcopy
import sys
import traceback
from ..props.utils import get_bitdepths
from ..utils import SUBSTANCE_Utils
from ..sbsar.callbacks import SUBSTANCE_SbsarCallbacks
from ..common import (
    Code_ParmWidget,
    Code_ParmType,
    Code_OutParms,
    Code_ParmIdentifier,
    Code_OutputSizeSuffix,
    Code_Response,
    COLORSPACES_DICT,
    RESOLUTIONS_DICT,
    PARM_ANGLE_CONVERSION,
    PARM_INT_MAX
)


# Outputs functions
def _output_to_json(self):
    _obj = {
        "sbsar_id": self.sbsar_id,
        "outputs": {}
    }

    for _key in self.__annotations__:
        _new_key = _key.replace(Code_OutParms.enabled.value, "")
        _new_key = _new_key.replace(Code_OutParms.colorspace.value, "")
        _new_key = _new_key.replace(Code_OutParms.format.value, "")
        _new_key = _new_key.replace(Code_OutParms.bitdepth.value, "")

        if _new_key not in _obj["outputs"]:
            _obj["outputs"][_new_key] = {}

        if Code_OutParms.enabled.value in _key:
            _obj["outputs"][_new_key]["shader_enabled"] = getattr(self, _key)
        elif Code_OutParms.colorspace.value in _key:
            _obj["outputs"][_new_key]["shader_colorspace"] = getattr(self, _key)
        elif Code_OutParms.format.value in _key:
            _obj["outputs"][_new_key]["shader_format"] = getattr(self, _key)
        elif Code_OutParms.bitdepth.value in _key:
            _obj["outputs"][_new_key]["shader_bitdepth"] = getattr(self, _key)
    return _obj


def _output_from_json(self, data):
    for _key, _output in data["outputs"].items():
        setattr(self, _key + Code_OutParms.enabled.value, _output["shader_enabled"])
        setattr(self, _key + Code_OutParms.colorspace.value, _output["shader_colorspace"])
        setattr(self, _key + Code_OutParms.format.value, _output["shader_format"])
        setattr(self, _key + Code_OutParms.bitdepth.value, _output["shader_bitdepth"])


# Parameters functions
def _parms_to_json(self):
    _obj = {
        "sbsar_id": self.sbsar_id,
        "parms": {}
    }

    for _key in self.__annotations__:
        if Code_ParmIdentifier.outputsize.value in _key:
            _width = getattr(self, Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.width.value)
            _height = getattr(self, Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.height.value)
            _linked = getattr(self, Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.linked.value)
            _obj["parms"][Code_ParmIdentifier.outputsize.value] = [int(_width), int(_height)]
            _obj["parms"][Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.linked.value] = _linked
        else:
            _parm = self.default.parms[_key]
            if _parm.guiWidget == Code_ParmWidget.combobox.value:
                _value = int(getattr(self, _key))
            elif _parm.guiWidget == Code_ParmWidget.slider.value:
                if (_parm.type == Code_ParmType.integer2.name or
                        _parm.type == Code_ParmType.integer3.name or
                        _parm.type == Code_ParmType.integer4.name):
                    _value = list(getattr(self, _key))
                elif (_parm.type == Code_ParmType.float2.name or
                        _parm.type == Code_ParmType.float3.name or
                        _parm.type == Code_ParmType.float4.name):
                    _value = list(getattr(self, _key))
                else:
                    _value = getattr(self, _key)
            elif _parm.guiWidget == Code_ParmWidget.color.value:
                if _parm.type == Code_ParmType.float3.name or _parm.type == Code_ParmType.float4.name:
                    _value = list(getattr(self, _key))
                else:
                    _value = getattr(self, _key)
            elif _parm.guiWidget == Code_ParmWidget.togglebutton.value:
                _value = int(getattr(self, _key))
            elif _parm.guiWidget == Code_ParmWidget.angle.value:
                _value = getattr(self, _key) / PARM_ANGLE_CONVERSION
            elif _parm.guiWidget == Code_ParmWidget.position.value:
                _value = list(getattr(self, _key))
            elif _parm.guiWidget == Code_ParmWidget.image.value:
                _value = getattr(self, _key)
                if _value is None:
                    _value = ""
                else:
                    _value = _value.name
            else:
                _value = getattr(self, _key)
            _obj["parms"][_key] = _value
    return _obj


def _parms_from_json(self, data):
    for _key in data["parms"]:
        if Code_ParmIdentifier.outputsize.value in _key:
            _output_size = data["parms"][Code_ParmIdentifier.outputsize.value]
            _link_key = Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.linked.value
            _output_size_linked = data["parms"][_link_key]
            setattr(
                self,
                Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.width.value,
                str(_output_size[0]))
            setattr(
                self,
                Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.height.value,
                str(_output_size[1]))
            setattr(
                self,
                Code_ParmIdentifier.outputsize.value + Code_OutputSizeSuffix.linked.value,
                _output_size_linked)
            continue
        elif not hasattr(self, _key):
            continue

        _parm = self.default.parms[_key]

        _value = data["parms"][_key]
        if _parm.guiWidget == Code_ParmWidget.combobox.value:
            _value = str(_value)
        elif _parm.guiWidget == Code_ParmWidget.slider.value:
            pass
        elif _parm.guiWidget == Code_ParmWidget.color.value:
            pass
        elif _parm.guiWidget == Code_ParmWidget.togglebutton.value:
            _value = str(_value)
        elif _parm.guiWidget == Code_ParmWidget.angle.value:
            _value = _value * PARM_ANGLE_CONVERSION
        elif _parm.guiWidget == Code_ParmWidget.position.value:
            pass
        elif _parm.guiWidget == Code_ParmWidget.image.value:
            pass
        elif _parm.identifier == Code_ParmIdentifier.randomseed.value:
            pass
        else:
            pass

        setattr(self, _key, _value)


class SUBSTANCE_SbsarFactory():

    # Outputs
    @staticmethod
    def create_output_items(output, class_name):
        _attributes = [
            bpy.props.BoolProperty(
                name=output.defaultChannelUse + Code_OutParms.enabled.value,
                default=output.shader_enabled,
                description="The default value to enable/disable the baking of the {} map".format(output.label),
                update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_output_changed(
                    self,
                    context,
                    output.defaultChannelUse + Code_OutParms.enabled.value)),
            bpy.props.EnumProperty(
                name=output.defaultChannelUse + Code_OutParms.colorspace.value,
                default=output.shader_colorspace,
                description="The default colorspace to be used when creating the shader network",
                items=COLORSPACES_DICT,
                update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_output_changed(
                    self,
                    context,
                    output.defaultChannelUse + Code_OutParms.colorspace.value)),
            bpy.props.EnumProperty(
                name=output.defaultChannelUse + Code_OutParms.format.value,
                default=output.shader_format,
                description="The default file format to be used by the Output",
                items=SUBSTANCE_Utils.get_formats(),
                update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_output_changed(
                    self,
                    context,
                    output.defaultChannelUse + Code_OutParms.format.value)),
            bpy.props.EnumProperty(
                name=output.defaultChannelUse + Code_OutParms.bitdepth.value,
                default=int(output.shader_bitdepth),
                description="The default bitdepth of the Output",
                items=lambda self, context: get_bitdepths(
                    self,
                    context,
                    output.defaultChannelUse + Code_OutParms.format.value),
                update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_output_changed(
                    self,
                    context,
                    output.defaultChannelUse + Code_OutParms.bitdepth.value))
        ]
        return _attributes

    @staticmethod
    def register_output_class(sbsar):
        for _graph in sbsar.graphs:
            _attributes = {}
            for _key, _output in _graph.outputs.items():
                _attribute = SUBSTANCE_SbsarFactory.create_output_items(_output, _graph.outputs_class_name)
                _attributes[_output.defaultChannelUse + Code_OutParms.enabled.value] = _attribute[0]
                _attributes[_output.defaultChannelUse + Code_OutParms.colorspace.value] = _attribute[1]
                _attributes[_output.defaultChannelUse + Code_OutParms.format.value] = _attribute[2]
                _attributes[_output.defaultChannelUse + Code_OutParms.bitdepth.value] = _attribute[3]

            _outputs_class = type(_graph.outputs_class_name, (bpy.types.PropertyGroup,), {
                "__annotations__": _attributes,
                "sbsar_id": sbsar.id,
                "default": deepcopy(_graph),
                "callback": {"enabled": True},
                "mat_callback": {"enabled": True},
                "to_json": _output_to_json,
                "from_json": _output_from_json,
            })
            bpy.utils.register_class(_outputs_class)
            setattr(
                bpy.types.Scene,
                _graph.outputs_class_name,
                bpy.props.PointerProperty(name=_graph.outputs_class_name, type=_outputs_class))

    # Parameters
    @staticmethod
    def init_enum_values(values):
        _items = []
        for _item in values:
            _items.append(
                (str(_item.first), _item.second, "{}:{}".format(_item.first, _item.second))
            )
        return _items

    @staticmethod
    def init_toggle_values(values):
        _items = []
        for _idx, _item in enumerate(values):
            _items.append(
                (str(_idx), _item, "{}:{}".format(_idx, _item))
            )
        return _items

    @staticmethod
    def create_parm_item(parm, class_name):
        if parm.guiWidget == Code_ParmWidget.combobox.value:
            return bpy.props.EnumProperty(
                name=parm.label,
                description=parm.guiDescription,
                default=str(parm.defaultValue),
                items=SUBSTANCE_SbsarFactory.init_enum_values(parm.enumValues),
                update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_parm_changed(self, context, parm.identifier))

        elif parm.guiWidget == Code_ParmWidget.slider.value:
            if parm.type == Code_ParmType.integer.name:
                _max = parm.maxValue
                _min = parm.minValue
                if _max == _min:
                    _max = PARM_INT_MAX
                    _min = PARM_INT_MAX*-1
                return bpy.props.IntProperty(
                    name=parm.label,
                    description=parm.guiDescription,
                    default=parm.defaultValue,
                    soft_max=_max,
                    soft_min=_min,
                    update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_parm_changed(
                        self,
                        context,
                        parm.identifier))
            elif parm.type == Code_ParmType.float.name:
                _max = parm.maxValue
                _min = parm.minValue
                if _max == _min:
                    _max = sys.float_info.max
                    _min = sys.float_info.min
                return bpy.props.FloatProperty(
                    name=parm.label,
                    description=parm.guiDescription,
                    default=parm.defaultValue,
                    soft_max=_max,
                    soft_min=_min,
                    update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_parm_changed(
                        self,
                        context,
                        parm.identifier))
            elif (parm.type == Code_ParmType.integer2.name or
                    parm.type == Code_ParmType.integer3.name or
                    parm.type == Code_ParmType.integer4.name):
                _dimension = len(parm.defaultValue)
                _max = parm.maxValue[0]
                _min = parm.minValue[0]
                if _max == _min:
                    _max = PARM_INT_MAX
                    _min = PARM_INT_MAX*-1
                return bpy.props.IntVectorProperty(
                    name=parm.label,
                    description=parm.guiDescription,
                    size=_dimension,
                    default=parm.defaultValue,
                    soft_max=_max,
                    soft_min=_min,
                    update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_parm_changed(
                        self,
                        context,
                        parm.identifier))
            elif (parm.type == Code_ParmType.float2.name or
                    parm.type == Code_ParmType.float3.name or
                    parm.type == Code_ParmType.float4.name):
                _dimension = len(parm.defaultValue)
                _max = parm.maxValue[0]
                _min = parm.minValue[0]
                if _max == _min:
                    _max = sys.float_info.max
                    _min = sys.float_info.min
                return bpy.props.FloatVectorProperty(
                    name=parm.label,
                    description=parm.guiDescription,
                    size=_dimension,
                    default=parm.defaultValue,
                    soft_max=_max,
                    soft_min=_min,
                    update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_parm_changed(
                        self,
                        context,
                        parm.identifier))
            else:
                return None

        elif parm.guiWidget == Code_ParmWidget.color.value:
            if parm.type == Code_ParmType.float.name:
                _max = parm.maxValue
                _min = parm.minValue
                if _max == _min:
                    _max = 1
                    _min = 0
                return bpy.props.FloatProperty(
                    name=parm.label,
                    description=parm.guiDescription,
                    default=parm.defaultValue,
                    soft_max=_max,
                    soft_min=_min,
                    update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_parm_changed(
                        self,
                        context,
                        parm.identifier))
            elif parm.type == Code_ParmType.float3.name or parm.type == Code_ParmType.float4.name:
                _dimension = len(parm.defaultValue)
                _max = parm.maxValue[0]
                _min = parm.minValue[0]
                if _max == _min:
                    _max = 1
                    _min = 0
                return bpy.props.FloatVectorProperty(
                    name=parm.label,
                    description=parm.guiDescription,
                    subtype="COLOR",
                    size=_dimension,
                    default=parm.defaultValue,
                    soft_max=_max,
                    soft_min=_min,
                    update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_parm_changed(
                        self,
                        context,
                        parm.identifier))
            else:
                return None

        elif parm.guiWidget == Code_ParmWidget.togglebutton.value:
            _label_true = parm.labelTrue if parm.labelTrue != "" else "True"
            _label_false = parm.labelFalse if parm.labelFalse != "" else "False"
            _toggle_labels = [_label_false, _label_true]
            return bpy.props.EnumProperty(
                name=parm.label,
                description=parm.guiDescription,
                default=str(parm.defaultValue),
                items=SUBSTANCE_SbsarFactory.init_toggle_values(_toggle_labels),
                update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_parm_changed(
                    self,
                    context,
                    parm.identifier))

        elif parm.guiWidget == Code_ParmWidget.angle.value:
            _max = parm.maxValue * PARM_ANGLE_CONVERSION
            _min = parm.minValue * PARM_ANGLE_CONVERSION
            _default = parm.defaultValue * PARM_ANGLE_CONVERSION
            if _max == _min:
                _max = sys.float_info.max
                _min = sys.float_info.min
            return bpy.props.FloatProperty(
                name=parm.label,
                description=parm.guiDescription,
                subtype="ANGLE",
                default=_default,
                soft_max=_max,
                soft_min=_min,
                update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_parm_changed(
                    self,
                    context,
                    parm.identifier))

        elif parm.guiWidget == Code_ParmWidget.position.value:
            _dimension = len(parm.defaultValue)
            _max = parm.maxValue[0]
            _min = parm.minValue[0]
            if _max == _min:
                _max = 1
                _min = 0
            return bpy.props.FloatVectorProperty(
                name=parm.label,
                description=parm.guiDescription,
                subtype="XYZ",
                size=_dimension,
                default=parm.defaultValue,
                soft_max=_max,
                soft_min=_min,
                update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_parm_changed(
                    self,
                    context,
                    parm.identifier))

        elif parm.guiWidget == Code_ParmWidget.image.value:
            return bpy.props.PointerProperty(
                name=parm.label,
                description=parm.guiDescription,
                type=bpy.types.Image,
                update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_parm_changed(
                    self,
                    context,
                    parm.identifier))

        elif parm.guiWidget == Code_ParmWidget.nowidget.value:
            if parm.identifier == Code_ParmIdentifier.randomseed.value:
                return bpy.props.IntProperty(
                    name=parm.label,
                    description=parm.guiDescription,
                    default=parm.defaultValue,
                    soft_max=parm.maxValue,
                    soft_min=parm.minValue,
                    update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_parm_changed(
                        self,
                        context,
                        parm.identifier))
            if parm.identifier == Code_ParmIdentifier.outputsize.value:
                return [
                    bpy.props.EnumProperty(
                        name=parm.label,
                        description=parm.guiDescription,
                        default=str(parm.defaultValue[0]),
                        items=RESOLUTIONS_DICT,
                        update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_linked_changed(
                            self,
                            context,
                            parm.identifier + Code_OutputSizeSuffix.width.value)),
                    bpy.props.EnumProperty(
                        name=parm.label,
                        description=parm.guiDescription,
                        default=str(parm.defaultValue[1]),
                        items=RESOLUTIONS_DICT,
                        update=lambda self, context:SUBSTANCE_SbsarCallbacks.on_outputsize_changed(
                            self,
                            context,
                            parm.identifier + Code_OutputSizeSuffix.height.value)),
                    bpy.props.BoolProperty(
                        name=parm.label,
                        description=parm.guiDescription,
                        default=parm.defaultValue[0] == parm.defaultValue[1],
                        update=lambda self, context: SUBSTANCE_SbsarCallbacks.on_linked_changed(
                            self,
                            context,
                            parm.identifier + Code_OutputSizeSuffix.linked.value))
                ]
            else:
                return None
        else:
            return None

    @staticmethod
    def register_parms_class(sbsar):
        for _graph in sbsar.graphs:
            _attributes = {}
            for _key, _parm in _graph.parms.items():
                _attribute = SUBSTANCE_SbsarFactory.create_parm_item(_parm, _graph.parms_class_name)
                if _attribute:
                    if _parm.identifier == Code_ParmIdentifier.outputsize.value:
                        _attributes[_parm.identifier + Code_OutputSizeSuffix.width.value] = _attribute[0]
                        _attributes[_parm.identifier + Code_OutputSizeSuffix.height.value] = _attribute[1]
                        _attributes[_parm.identifier + Code_OutputSizeSuffix.linked.value] = _attribute[2]
                    else:
                        _attributes[_parm.identifier] = _attribute
                else:
                    SUBSTANCE_Utils.log_data("WARNING", "Parameter not created [{}]".format(_parm.identifier))

            _parms_class = type(_graph.parms_class_name, (bpy.types.PropertyGroup,), {
                "__annotations__": _attributes,
                "sbsar_id": sbsar.id,
                "default": deepcopy(_graph),
                "callback": {"enabled": True},
                "to_json": _parms_to_json,
                "from_json": _parms_from_json
            })
            bpy.utils.register_class(_parms_class)
            setattr(
                bpy.types.Scene,
                _graph.parms_class_name,
                bpy.props.PointerProperty(name=_graph.parms_class_name, type=_parms_class))

    @staticmethod
    def register_sbsar_classes(sbsar):
        try:
            SUBSTANCE_SbsarFactory.register_parms_class(sbsar)
            SUBSTANCE_SbsarFactory.register_output_class(sbsar)
            return (Code_Response.success, sbsar)
        except Exception:
            SUBSTANCE_Utils.log_data("ERROR", "Exception - Susbtance register error:")
            SUBSTANCE_Utils.log_traceback(traceback.format_exc())
            return (Code_Response.sbsar_factory_register_error, None)

    @staticmethod
    def unregister_sbsar_class(class_name):
        if hasattr(bpy.context.scene, class_name):
            _object = getattr(bpy.context.scene, class_name)
            _class_type = type(_object)

            delattr(bpy.types.Scene, class_name)
            bpy.utils.unregister_class(_class_type)
