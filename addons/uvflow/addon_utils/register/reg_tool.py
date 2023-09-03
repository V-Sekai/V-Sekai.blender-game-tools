from typing import Union, Type, Callable, List, Tuple

import bpy
from bpy.types import WorkSpaceTool, Macro, Operator
from bpy import ops as OPS

from .reg_common import BlenderTypes, get_inner_classes_by_type
from .reg_operator import OperatorRegister, _register_operator, operator_types, add_macro_defines
from ..types.ui import UI_TYPES, MenuUI, PanelUI, DrawExtension
from ..types import EventType, EventValue, OpsReturn
from ..types.tools import TOOL_ACTION_TYPES


tools: List[Tuple[WorkSpaceTool, dict]] = []


##########################################################################
##########################################################################
# Decorator to register UI classes.
##########################################################################


def _register_tool(space_type: str = 'VIEW_3D',
                   context_mode: str = 'OBJECT',
                   after={'builtin.scale_cage'},
                   separator=True,
                   group=True) -> WorkSpaceTool:
    # Create new dynamic type.
    tool_kwargs = {
        'after': after,
        'separator': separator,
        'group': group
    }
    def _decorator(cls) -> WorkSpaceTool:
        tool_actions: List[TOOL_ACTION_TYPES] = get_inner_classes_by_type(cls, TOOL_ACTION_TYPES)
        op_classes: List[operator_types.ToolActionModalOperator] = [_register_operator(
            type('tool_' + tool_action.__name__, (object,), {}),
            operator_types.ToolActionModalOperator,
            tool_action=tool_action.get(),
            poll=tool_action.op_poll if hasattr(tool_action, 'op_poll') and tool_action.op_poll is not None else classmethod(lambda cls, ctx: True)
        ) for tool_action in tool_actions]
        # op_classes = [OperatorRegister.MODAL.TOOL_ACTION(tool_action) for tool_action in tool_actions]
        keymap = [
            (op.bl_idname, km, None) # {'properties': [('mode', 'ADD')]}
            for op in op_classes for km in op.tool_action.get_keymaps()
        ]

        ''' NAVIGATION PRE/POST CALLBACKS. '''
        # keymap.extend(_register_tool_navigation(cls))

        # from pprint import pprint
        # pprint(keymap)

        tool_cls: WorkSpaceTool = type(
            cls.__name__,
            (cls, WorkSpaceTool),
            {
                'bl_idname': 'UVFLOW_TOOL_' + cls.__name__.lower(),
                'bl_space_type': space_type,
                'bl_context_mode': context_mode,
                'bl_label': cls.label if hasattr(cls, 'label') else cls.__name__,
                'bl_description': cls.description if hasattr(cls, 'descrption') else '',
                'bl_icon': cls.icon if hasattr(cls, 'icon') else 'NONE',
                'bl_cursor': cls.cursor if hasattr(cls, 'cursor') else 'DEFAULT',
                'bl_keymap': tuple(keymap),
                # 'pre_navigation': pre_navigation_callback,
                # 'post_navigation': post_navigation_callback,
            }
        )

        # Add new class for the registering.
        # BlenderTypes.INTERFACE.add_class(ui_cls)
        tools.append((tool_cls, tool_kwargs))
        return tool_cls
    return _decorator


##########################################################################
##########################################################################
# enum-like-class UTILITY TO REGISTER UI CLASSES PER SUBTYPE.
##########################################################################

class ToolsRegister:
    TOOL = _register_tool


##############################################

def register():
    reg_tool = bpy.utils.register_tool
    for (cls, kwargs) in tools:
        # print(cls.__dict__)
        reg_tool(cls, **kwargs)

def unregister():
    unreg_tool = bpy.utils.unregister_tool
    for (cls, kwargs) in tools:
        unreg_tool(cls)




##############################################
# TEST CODE.
##############################################

# Currently just using default keymaps.
# TODO: Read user keymaps and detect the operators to fill up this automatically.
navigation_operators: tuple[Operator] = (
    (OPS.view3d.rotate, {'type': EventType.MIDDLEMOUSE, 'value': EventValue.PRESS}),
    (OPS.view3d.move, {'type': EventType.MIDDLEMOUSE, 'value': EventValue.PRESS, 'shift': True}),
)

def _register_tool_navigation(tool_cls):
    keymaps = []

    def pre_nav(op, context):
        print("PRE NAV")
        tool_cls.pre_navigation(context)
        return {'FINISHED'}

    def post_nav(op, context):
        print("POST NAV")
        tool_cls.post_navigation(context)
        return {'FINISHED'}

    for (nav_op, km) in navigation_operators:
        # Internal operator.
        if hasattr(nav_op, '_module'):
            op_idname: str = nav_op.idname()
            # nav_op: Operator = nav_op.get_rna_type()
            name: str = nav_op.get_rna_type().name
            is_internal = True
        else:
            op_idname: str = nav_op.bl_idname
            name: str = nav_op.name
            is_internal = False

        short_name = name.replace(' ', '').lower()

        pre_op: Operator = type(
            'MacroPre_' + short_name,
            (Operator,),
            {
                'bl_idname': 'macro_pre.' + short_name,
                'bl_label': 'PRE ' + name,
                'invoke': lambda self, ctx, evt: pre_nav(self, ctx),
                'execute': pre_nav,
                'bl_options': {'INTERNAL'}
            }
        )
        post_op: Operator = type(
            'MacroPost_' + short_name,
            (Operator,),
            {
                'bl_idname': 'macro_post.' + short_name,
                'bl_label': 'POST ' + name,
                'invoke': lambda self, ctx, evt: post_nav(self, ctx),
                'execute': post_nav,
                'bl_options': {'INTERNAL'}
            }
        )

        # class NavOpModal(operator_types.BaseModalOperator, Operator):
        #     nav_op: Callable
        #     def modal_start(self, context, event) -> None:
        #         self.start = True
        #     def modal_update(self, context, event, mouse) -> OpsReturn or None:
        #         if self.start:
        #             self.nav_op('INVOKE_DEFAULT')
        #             return OpsReturn.PASS
        #         return OpsReturn.FINISH
        # class NavOp(Operator):
        #     nav_op: Callable
        #     def invoke(self, context, event):
        #         print("Navigation Operator running...")
        #         self.nav_op('INVOKE_DEFAULT')
        #         return OpsReturn.FINISH
        # modal_op: Operator = type(
        #     'MacroPost_' + short_name,
        #     (NavOp,),
        #     {
        #         'bl_idname': 'macro_navop.' + short_name,
        #         'bl_label': 'NavOp ' + name,
        #         'bl_options': {'INTERNAL'},
        #         'nav_op': nav_op,
        #         'bl_options': {'BLOCKING'}
        #     }
        # )

        macro_op: Macro = type(
            'Macro_' + short_name,
            (Macro,),
            {
                'bl_idname': 'macro.' + short_name,
                'bl_label': '[UVFlow] ' + name,
                'bl_options': {'MACRO'} # , 'BLOCKING'
            }
        )

        operators = [pre_op.bl_idname, op_idname, post_op.bl_idname]

        BlenderTypes.OPERATOR.add_class(pre_op)
        # BlenderTypes.OPERATOR.add_class(modal_op)
        BlenderTypes.OPERATOR.add_class(post_op)
        BlenderTypes.MACRO.add_class(macro_op)
        add_macro_defines(macro_op, operators)

        keymaps.append(
            (macro_op.bl_idname, km, None)
        )

    return keymaps
