from bpy.props import *

from enum import Enum


class PropertyTypes(Enum):
    FLOAT = FloatProperty
    INT = IntProperty
    BOOL = BoolProperty
    FLOAT_VECTOR = FloatVectorProperty
    INT_VECTOR = IntVectorProperty
    BOOL_VECTOR = BoolVectorProperty
    VECTOR_2 = lambda default, **kwargs: FloatVectorProperty(default=default, size=2, **kwargs)
    VECTOR_3 = lambda default, **kwargs: FloatVectorProperty(default=default, size=3, **kwargs)
    COLOR_RGB = lambda default, **kwargs: FloatVectorProperty(default=default, min=0.0, max=1.0, size=3, **kwargs)
    COLOR_RGBA = lambda default, **kwargs: FloatVectorProperty(default=default, min=0.0, max=1.0, size=4, **kwargs)
    STRING = StringProperty
    DIRPATH = lambda **kwargs: StringProperty(subtype='DIR_PATH', **kwargs)
    FILEPATH = lambda **kwargs: StringProperty(subtype='FILE_PATH', **kwargs)
    POINTER = lambda type, **kwargs: PointerProperty(type=type, **kwargs)
    COLLECTION = lambda type, **kwargs: CollectionProperty(type=type, **kwargs)
    ENUM = EnumProperty

    def __call__(self, *args, **kwargs):
        return self.value(*args, **kwargs)
