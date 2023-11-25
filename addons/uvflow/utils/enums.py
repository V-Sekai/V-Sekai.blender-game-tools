from enum import Enum, auto


class PackIncludes(Enum):
    FACES = auto()
    OBJECT = auto()
    OBJECT_MATERIAL = auto()
    ACTIVE_MATERIAL = auto()
    SELECT_MATERIAL = auto()


class PackTogether(Enum):
    ALL = auto()
    MATERIAL = auto()
    OBJECT = auto()


class Alignment(Enum):
    NONE = auto()
    BOUNDS = auto()
    EDGE = auto()