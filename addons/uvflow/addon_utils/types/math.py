import math
from typing import Tuple, Union
from dataclasses import dataclass

from mathutils import Vector

from ..utils.math import clamp


class Vector2:
    x: float = 0.0
    y: float = 0.0

    @classmethod
    def zero(cls):
        return cls(0.0, 0.0)

    def reset(self):
        self.x = 0.0
        self.y = 0.0

    def __set__(self, instance, values: Tuple[float, float] or Tuple[int, int]):
        if not isinstance(values, (Tuple[float, float], Tuple[int, int])):
            raise TypeError('Only objects of type Tuple[float, float] and Tuple[int, int] can be assigned')
        self.x, self.y = values  # This can be self.val = MyCustomClass(val) as well.

    def copy(self) -> 'Vector2':
        return Vector2(self.x, self.y)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def __init__(self, x: float = 0, y: float = 0):
        self.x = x
        self.y = y

    def __iadd__(self, other: 'Vector2'):
        self.x += other.x
        self.y += other.y

    def __isub__(self, other: 'Vector2'):
        self.x -= other.x
        self.y -= other.y

    def __imul__(self, other: 'Vector2'):
        self.x *= other.x
        self.y *= other.y

    def __idiv__(self, other: 'Vector2'):
        self.x /= other.x
        self.y /= other.y

    def __add__(self, other: 'Vector2'):
        return Vector2(self.x+other.x, self.y+other.y)

    def __sub__(self, other: 'Vector2'):
        return Vector2(self.x-other.x, self.y-other.y)

    def __mul__(self, other: 'Vector2'):
        return Vector2(self.x*other.x, self.y*other.y)

    def __div__(self, other: 'Vector2'):
        return Vector2(self.x/other.x, self.y/other.y)


    def distance(self, other: 'Vector2') -> float:
        return math.dist([self.x, self.y], [other.x, other.y])


    def __str__(self) -> str:
        return "Vector2(float): [X:%f, Y:%f]" % (self.x, self.y)


class Vector2i:
    x: int = 0
    y: int = 0

    @classmethod
    def zero(cls):
        return cls(0, 0)

    def reset(self):
        self.x = 0
        self.y = 0

    def __set__(self, instance, values: Tuple[int, int] or 'Vector2i'):
        if isinstance(values, Vector2i):
            values = values.x, values.y
        elif not isinstance(values, (Tuple[int, int])):
            raise TypeError('Only objects of type Tuple[int, int] can be assigned')
        self.x, self.y = values  # This can be self.val = MyCustomClass(val) as well.

    def is_zero(self) -> bool:
        return int(self.x) == 0 and int(self.y) == 0

    def copy(self) -> 'Vector2i':
        return Vector2i(self.x, self.y)

    def to_tuple(self) -> Tuple[int, int]:
        return self.x, self.y

    def to_vector(self) -> Vector:
        return Vector((self.x, self.y))

    def __init__(self, x: int = 0, y: int = 0):
        self.x = x
        self.y = y

    def __iadd__(self, other: 'Vector2i'):
        self.x += other.x
        self.y += other.y

    def __isub__(self, other: 'Vector2i'):
        self.x -= other.x
        self.y -= other.y

    def __imul__(self, other: 'Vector2i'):
        self.x *= other.x
        self.y *= other.y

    def __idiv__(self, other: 'Vector2i'):
        self.x /= other.x
        self.y /= other.y

    def __add__(self, other: 'Vector2i') -> 'Vector2i':
        return Vector2i(self.x+other.x, self.y+other.y)

    def __sub__(self, other: 'Vector2i') -> 'Vector2i':
        return Vector2i(self.x-other.x, self.y-other.y)

    def __mul__(self, other: 'Vector2i') -> 'Vector2i':
        return Vector2i(self.x*other.x, self.y*other.y)

    def __truediv__(self, other: 'Vector2i') -> 'Vector2i':
        return Vector2i(self.x/other.x, self.y/other.y)

    def clamp(self, min_value: int, max_value: int) -> None:
        self.x = clamp(self.x, min_value, max_value)
        self.y = clamp(self.y, min_value, max_value)

    def distance(self, other: 'Vector2i') -> float:
        return math.dist([self.x, self.y], [other.x, other.y])


    def __str__(self) -> str:
        return "Vector2(int): [X:%i, Y:%i]" % (self.x, self.y)



@dataclass
class BBOX_2:
    min_x: Union[float, int]
    max_x: Union[float, int]
    min_y: Union[float, int]
    max_y: Union[float, int]

    @classmethod
    def from_area(cls, area) -> 'BBOX_2':
        return cls(area.x, area.x + area.width, area.y, area.y + area.height)

    @property
    def width(self) -> int:
        return self.max_x - self.min_x

    @property
    def height(self) -> int:
        return self.max_y - self.min_y

    @property
    def center_t(self) -> tuple[int, int]:
        return int(self.width / 2), int(self.height / 2)

    @property
    def center(self) -> Vector2i:
        return Vector2i(*self.center_t)

    @property
    def top_left(self) -> Vector2i:
        return Vector2i(self.min_x, self.max_y)

    @property
    def bottom_left(self) -> Vector2i:
        return Vector2i(self.min_x, self.min_y)

    @property
    def bottom_right(self) -> Vector2i:
        return Vector2i(self.max_x, self.min_y)

    @property
    def top_right(self) -> Vector2i:
        return Vector2i(self.max_x, self.max_y)

    @property
    def corners(self) -> list[Vector2i]:
        return [self.bottom_left, self.bottom_right, self.top_left, self.top_right]
