from typing import Type, Dict, List
from dataclasses import dataclass
from collections import defaultdict

from ..types.property import PropertyTypes as Property


@dataclass
class PropertyWrapper:
    prop_name: str
    property: Type


to_register_properties: Dict[Type, List[PropertyWrapper]] = defaultdict(list)


def PropertyRegister(data, prop_name, property: Property) -> None:
    to_register_properties[data].append(PropertyWrapper(prop_name, property))

def BatchPropertyRegister(data, **props: dict) -> None:
    to_register_properties[data].extend(
        [
            PropertyWrapper(prop_name, property)
            for prop_name, property in props.items()
        ]
    )


def register():
    for data, props in to_register_properties.items():
        for prop_wrap in props:
            setattr(data, prop_wrap.prop_name, prop_wrap.property)

def unregister():
    for data, props in to_register_properties.items():
        for prop_wrap in props:
            delattr(data, prop_wrap.prop_name)
