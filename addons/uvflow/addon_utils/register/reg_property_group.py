from bpy.types import PropertyGroup
from bpy import types as bpy_types

from enum import Enum

from .reg_common import BlenderTypes
from .reg_property import PropertyRegister, Property
from ..types.property_group import PropertyGroupSupportedTypes


class PGRootTypes(Enum): # (PropertyGroupSupportedTypes):
    WINDOW_MANAGER = bpy_types.WindowManager
    TEMPORAL = WINDOW_MANAGER
    SCENE = bpy_types.Scene
    
    OBJECT = bpy_types.Object
    MESH = bpy_types.Mesh

    def __call__(self, prop_name: str = None) -> PropertyGroup:
        def decorator(decorated_cls):
            pg_cls = _register_property_group(decorated_cls)
            PropertyRegister(self.value, prop_name if prop_name else 'uvflow', Property.POINTER(pg_cls))
            return pg_cls
        return decorator


def _register_property_group(cls) -> PropertyGroup:
    pg_cls = type(
        'UVFLOW_PG_' + cls.__name__,
        (PropertyGroup, cls),
        {
            '__annotations__': cls.__annotations__,
        }
    )
    BlenderTypes.PROPERTY_GROUP.add_class(pg_cls)
    return pg_cls


##########################################################################
##########################################################################
# enum-like-class UTILITY TO REGISTER PROPERTY GROUP CLASSES PER TYPE.
##########################################################################

class PropertyGroupRegister:
    # PropertyGroup added to a root type like Scene, WindowManager or any ID (PG supported) type.
    ROOT = PGRootTypes
    # Child of another PropertyGroup.
    CHILD = _register_property_group
