import re

from .reg_common import BlenderTypes
from ..types import operator as operator_types, EventStateMachineNode, EventStateMachineAction, EventType, ToolAction

from bpy.types import Operator, Macro


macro_defines: dict[Macro, tuple[Operator]] = {}


def add_macro_defines(macro, defines: tuple[Operator]):
    macro_defines[macro] = defines


##########################################################################
##########################################################################
# Decorator to register Operator classes.
##########################################################################

class DummyClass:
    pass


def _register_operator(cls, base_cls=operator_types.BaseOperator, **kwargs) -> operator_types.BaseOperator:
    # Prepare.
    name_no_spaces = cls.__name__.replace(' ', '')
    keywords = re.findall('[A-Z][^A-Z]*', name_no_spaces)
    idname: str = '_'.join([word.lower() for word in keywords])
    bl_idname = 'uvflow.' + idname
    if hasattr(cls, 'draw_ui'):
        kwargs['draw'] = lambda self, ctx: self.draw_ui(self, ctx, self.layout)
    if hasattr(cls, 'label'):
        label = cls.label
    else:
        label: str = ' '.join(keywords).replace('_', ' ')

    if issubclass(cls, operator_types.BaseOperator):
        base_cls = DummyClass

    # Create new dynamic type.
    op_cls: operator_types.BaseOperator = type(
        'UVFLOW_OT_' + name_no_spaces.lower(),
        (cls, base_cls, Operator),
        {
            'ori_cls': cls,
            'bl_idname': bl_idname,
            'bl_label': label,
            **kwargs
        }
    )

    # Add new class for the registering.
    BlenderTypes.OPERATOR.add_class(op_cls)
    return op_cls


def _register_modal_operator(cls: operator_types.BaseModalOperator, base_cls) -> operator_types.BaseModalOperator:
    modal_op_cls = _register_operator(cls, base_cls)
    # if cls.modal_triggers:
    #     # TODO: Register the shortcuts that trigger the modal operator... (if register flag?)
    #     pass
    return modal_op_cls


def _register_state_machine_modal_operator(cls: operator_types.StateMachineModalOperator) -> operator_types.StateMachineModalOperator:
    tool_event_state_machine_nodes = []
    tool_event_state_machine_actions = []
    for annot_name, annot in cls.__annotations__.items():
        if isinstance(annot, EventStateMachineNode):
            if not annot.idname:
                annot.idname = annot_name
            tool_event_state_machine_nodes.append(annot)
        if isinstance(annot, EventStateMachineAction):
            if not annot.idname:
                annot.idname = annot_name
            tool_event_state_machine_actions.append(annot)
    modal_op_cls = _register_operator(cls, operator_types.StateMachineModalOperator,
                                    tool_event_state_machine_nodes=tool_event_state_machine_nodes,
                                    tool_event_state_machine_actions=tool_event_state_machine_actions)
    return modal_op_cls


def _register_tool_action_modal_operator(tool_action: ToolAction) -> operator_types.ToolActionModalOperator:
    def _decorator(cls):
        modal_op_cls = _register_operator(cls, operator_types.ToolActionModalOperator,
                                        tool_action=tool_action())
        return modal_op_cls
    return _decorator


def _register_macro__execute_after_modal(modal_operator: Operator) -> operator_types.MacroOperator__AfterModal:
    def _decorator(cls):
        new_op_cls = _register_operator(cls)
        new_macro_cls: Macro = type(
            'MACRO_' + cls.__name__,
            (Macro,),
            {
                'bl_idname': 'uvflow.macro__' + new_op_cls.bl_idname.split('.')[1],
                'bl_label': new_op_cls.bl_label,
                'modal_operator': modal_operator, 
                'after_operator': new_op_cls,
            }
        )
        BlenderTypes.MACRO.add_class(new_macro_cls)
        macro_defines[new_macro_cls] = (
            modal_operator,
            new_op_cls
        )
        return new_macro_cls
    return _decorator


def _register_macro(idname: str, operators: tuple) -> Macro:
    name_no_spaces = idname.replace(' ', '')
    macro_cls: Macro = type(
        'MACRO_' + name_no_spaces,
        (Macro,),
        {
            'bl_idname': 'uvflow.macro__' + name_no_spaces.lower(),
            'bl_label': idname
        }
    )
    BlenderTypes.MACRO.add_class(macro_cls)
    macro_defines[macro_cls] = operators
    return macro_cls


def _register_macro__modal_wrapper(modal_operator: Operator) -> Macro:
    def _decorator(cls) -> Macro:
        name = cls.__name__.lower()
        before_modal = _register_operator(
            type(
                'BEFORE_MODAL_' + name,
                (operator_types.BaseOperator,),
                {
                    'action': cls.before_modal,
                }
            )
        )
        modal = _register_operator(
            type(
                'MODAL_' + name,
                (operator_types.BaseOperator,),
                {
                    'action': lambda self, *args: self.modal_operator('INVOKE_DEFAULT'),
                }
            )
        )
        after_modal = _register_operator(
            type(
                'AFTER_MODAL_' + name,
                (operator_types.BaseOperator,),
                {
                    'action': cls.after_modal,
                }
            )
        )
        macro_cls: Macro = type(
            'MACRO_' + cls.__name__,
            (cls, Macro),
            {
                'bl_idname': 'uvflow.macro__' + name,
                'bl_label': name,
                'modal_operator': modal, 
                'after_operator': after_modal,
                'before_operator': before_modal
            }
        )
        BlenderTypes.MACRO.add_class(macro_cls)
        macro_defines[macro_cls] = (
            before_modal,
            modal,
            after_modal
        )
        return macro_cls
    return _decorator


##########################################################################
##########################################################################
# enum-like-class UTILITY TO REGISTER OPERATOR CLASSES PER SUBTYPE.
##########################################################################

class OperatorRegister:
    # Generic Operator. Using our base Operator class type.
    GENERIC = lambda cls: _register_operator(cls, operator_types.BaseOperator)

    def INVOKE_PROPS(cls) -> operator_types.InvokePropsOperator:
        return _register_operator(cls, operator_types.InvokePropsOperator)

    class MODAL:
        GENERIC = lambda cls: _register_modal_operator(cls, operator_types.BaseModalOperator)
        STATE_MACHINE = _register_state_machine_modal_operator
        TOOL_ACTION = _register_tool_action_modal_operator


    class MACRO:
        GENERIC = _register_macro
        AFTER_MODAL = _register_macro__execute_after_modal
        MODAL_WRAPPER = _register_macro__modal_wrapper



def late_register():
    for macro, macro_ops in macro_defines.items():
        print("Define Macro:", macro.bl_idname)
        for op in macro_ops:
            if isinstance(op, str):
                op_idname = op
            else:
                op_idname = op.bl_idname if hasattr(op, 'bl_idname') else op.idname()
            print("\t-", op_idname)
            macro.define(op_idname)
