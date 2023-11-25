from bpy.utils import register_class, unregister_class, register_classes_factory

from enum import Enum, auto
from typing import Dict, List, Type, Callable
from collections import defaultdict
from dataclasses import dataclass
import inspect


def get_inner_classes(cls):
    return [cls_attribute for cls_attribute in cls.__dict__.values()
            if inspect.isclass(cls_attribute)]

def get_inner_classes_by_type(cls, cls_type: type):
    return [cls_attribute for cls_attribute in cls.__dict__.values()
            if inspect.isclass(cls_attribute)
            and issubclass(cls_attribute, cls_type)]


@dataclass
class RegisterFactory:
    register: Callable
    unregister: Callable


class BlenderTypes(Enum):
    ''' Supported types. '''
    OPERATOR = auto()
    MACRO = auto()
    INTERFACE = auto() # Panel, Menu, PieMenu...
    PROPERTY_GROUP = auto()
    PREFERENCES = auto()

    def get_classes(self) -> List[Type]:
        return classes_per_type[self]

    def sort_classes(self, filter: Callable) -> None:
        classes_per_type[self] = filter(self.get_classes())

    def add_class(self, cls) -> None:
        print(f"[UVFLOW] New {self.name} class : {cls.__name__}")
        classes_per_type[self].append(cls)

    def register_classes(self) -> None:
        if reg_factory := register_factory.get(self, None):
            print(f"[UVFLOW] Register {self.name} classes")
            reg_factory.register()
        else:
            for cls in classes_per_type[self]:
                print(f"[UVFLOW] Register {self.name} class: {cls.__name__}")
                register_class(cls)

    def unregister_classes(self) -> None:
        if reg_factory := register_factory.get(self, None):
            reg_factory.unregister()
        else:
            for cls in classes_per_type[self]:
                if "bl_rna" in cls.__dict__:
                    print(f"[UVFLOW] UNRegister {self.name} class: {cls.__name__}")
                    unregister_class(cls)

    def create_classes_factory(self):
        register_factory[self] = RegisterFactory(*register_classes_factory(classes_per_type[self]))


classes_per_type: Dict[BlenderTypes, List[Type]] = defaultdict(list)
register_factory: Dict[BlenderTypes, RegisterFactory] = {}


def late_init():
    # Ensure that property group classes are correctly sorted to avoid issues with dependencies.
    from .._loader import get_ordered_pg_classes_to_register
    BlenderTypes.PROPERTY_GROUP.sort_classes(get_ordered_pg_classes_to_register)

    #for btype in BlenderTypes:
    #    btype.create_classes_factory()


def register():
    for btype in BlenderTypes:
        btype.register_classes()


def unregister():
    for btype in BlenderTypes:
        btype.unregister_classes()

    # classes_per_type.clear()
    # register_factory.clear()
